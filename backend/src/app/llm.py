"""Small LLM client for development checks and future backend integration."""

from __future__ import annotations

import os
import platform
from typing import Any

import httpx

ENV_BASE_URL = "ZHONGCHI_LLM_BASE_URL"
ENV_API_KEY = "ZHONGCHI_LLM_API_KEY"
ENV_MODEL = "ZHONGCHI_LLM_MODEL"


def _read_windows_registry_env(name: str) -> str:
    if platform.system() != "Windows":
        return ""
    try:
        import winreg
    except ImportError:
        return ""

    locations = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
    )
    for hive, path in locations:
        try:
            with winreg.OpenKey(hive, path) as key:
                value, _ = winreg.QueryValueEx(key, name)
                if value:
                    return str(value)
        except OSError:
            continue
    return ""


def get_configured_env(name: str) -> str:
    return os.environ.get(name, "") or _read_windows_registry_env(name)


def llm_config_status() -> dict[str, bool]:
    return {
        "base_url": bool(get_configured_env(ENV_BASE_URL).strip()),
        "api_key": bool(get_configured_env(ENV_API_KEY).strip()),
        "model": bool(get_configured_env(ENV_MODEL).strip()),
    }


def test_llm_connection(prompt: str) -> dict[str, Any]:
    base_url = get_configured_env(ENV_BASE_URL).strip()
    api_key = get_configured_env(ENV_API_KEY).strip()
    model = get_configured_env(ENV_MODEL).strip()

    missing = [
        name
        for name, value in (
            (ENV_BASE_URL, base_url),
            (ENV_API_KEY, api_key),
            (ENV_MODEL, model),
        )
        if not value
    ]
    if missing:
        return {
            "ok": False,
            "status_code": 0,
            "model": model,
            "reply": "",
            "error": "缺少环境变量：" + ", ".join(missing),
            "configured": llm_config_status(),
        }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是中驰售前PPT助手的开发连通性测试模型，请简洁回答。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 120,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=60.0, trust_env=False, follow_redirects=True) as client:
            response = client.post(base_url, headers=headers, json=payload)
        status_code = response.status_code
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        return {
            "ok": False,
            "status_code": exc.response.status_code,
            "model": model,
            "reply": "",
            "error": exc.response.text,
            "configured": llm_config_status(),
        }
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "status_code": 0,
            "model": model,
            "reply": "",
            "error": str(exc),
            "configured": llm_config_status(),
        }

    choices = data.get("choices") or []
    reply = ""
    if choices:
        message = choices[0].get("message") or {}
        reply = str(message.get("content") or "")

    return {
        "ok": True,
        "status_code": status_code,
        "model": str(data.get("model") or model),
        "reply": reply,
        "error": "",
        "configured": llm_config_status(),
    }
