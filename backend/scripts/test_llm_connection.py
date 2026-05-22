"""Test the configured OpenAI-compatible LLM endpoint.

Reads:
- ZHONGCHI_LLM_BASE_URL: full callable chat/completions URL
- ZHONGCHI_LLM_API_KEY
- ZHONGCHI_LLM_MODEL

The URL is used exactly as configured. No path suffix is appended.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
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


def build_payload(model: str, prompt: str) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a concise test assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": 40,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Zhongchi LLM connection.")
    parser.add_argument("--prompt", default="请只回复：LLM连接成功")
    parser.add_argument(
        "--use-env-proxy",
        action="store_true",
        help="Allow HTTP(S)_PROXY from the current environment.",
    )
    parser.add_argument(
        "--show-json",
        action="store_true",
        help="Print the full response JSON. API key is never printed.",
    )
    args = parser.parse_args()

    base_url = get_configured_env(ENV_BASE_URL).strip()
    api_key = get_configured_env(ENV_API_KEY).strip()
    model = get_configured_env(ENV_MODEL).strip()

    print(f"{ENV_BASE_URL} configured: {bool(base_url)}")
    print(f"{ENV_API_KEY} configured: {bool(api_key)}")
    print(f"{ENV_MODEL} configured: {bool(model)}")

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
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = build_payload(model, args.prompt)

    print(f"Request URL: {base_url}")
    print(f"Request model: {model}")

    try:
        with httpx.Client(timeout=60.0, trust_env=args.use_env_proxy, follow_redirects=True) as client:
            response = client.post(base_url, headers=headers, json=payload)
        print(f"HTTP status: {response.status_code}")
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        print("HTTP request reached the server but failed.")
        print(exc.response.text)
        return 1
    except httpx.HTTPError as exc:
        print("HTTP request failed before a valid response was received.")
        print(str(exc))
        return 1

    data = response.json()
    if args.show_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    choices = data.get("choices") or []
    reply = ""
    if choices:
        message = choices[0].get("message") or {}
        reply = str(message.get("content") or "")

    print(f"Response model: {data.get('model', '')}")
    print(f"Reply: {reply}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
