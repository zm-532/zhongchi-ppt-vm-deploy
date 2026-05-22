from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import httpx

from .constants import M1_M2_TEMPLATE_FILENAMES, PROJECT_TYPES
from .llm import ENV_API_KEY, ENV_BASE_URL, ENV_MODEL, get_configured_env


MIN_LLM_CONFIDENCE = 0.6
MAX_SOURCE_CHARS = 12000


TEMPLATE_PROFILES: dict[str, dict[str, Any]] = {
    "highway": {
        "template_name": M1_M2_TEMPLATE_FILENAMES["highway"],
        "applicable_scenarios": "高速公路、公路桥梁、公路沿线全封闭声屏障项目。",
        "typical_keywords": ["公路", "高速", "高速公路", "桥梁", "路段", "收费站"],
        "not_applicable": ["城市地铁线路", "普通铁路干线", "既有线轨交改造"],
        "boundary": "资料核心对象是公路或高速路段时优先选择 highway。",
    },
    "metro": {
        "template_name": M1_M2_TEMPLATE_FILENAMES["metro"],
        "applicable_scenarios": "城市地铁、城市轨道交通新建线路或常规地铁声屏障项目。",
        "typical_keywords": ["地铁", "城市轨道", "轨道交通", "车站", "区间", "线路"],
        "not_applicable": ["高速公路", "普通铁路干线", "明确既有线改造或运营线加装"],
        "boundary": "资料出现地铁或城市轨道交通，但没有明显既有线改造约束时选择 metro。",
    },
    "existing_rail_transit": {
        "template_name": M1_M2_TEMPLATE_FILENAMES["existing_rail_transit"],
        "applicable_scenarios": "铁路或轨道交通既有线、运营线、改造、加装、夜间短窗口施工项目。",
        "typical_keywords": ["既有线", "运营线", "改造", "加装", "夜间", "天窗", "短窗口"],
        "not_applicable": ["纯新建公路", "无改造约束的普通地铁新线", "普通铁路行业背景"],
        "boundary": "资料同时出现轨道交通/铁路和既有线、运营线、改造、夜间短窗口等约束时优先选择 existing_rail_transit。",
    },
    "railway": {
        "template_name": M1_M2_TEMPLATE_FILENAMES["railway"],
        "applicable_scenarios": "普通铁路、铁路干线、铁路声屏障行业背景与技术发展项目。",
        "typical_keywords": ["铁路", "铁路线", "铁路声屏障", "普速铁路", "高铁", "铁路沿线"],
        "not_applicable": ["高速公路", "城市地铁项目", "明确既有线改造/运营线加装项目"],
        "boundary": "资料核心对象是铁路线路，但没有明显既有线改造施工约束时选择 railway。",
    },
}


@dataclass(frozen=True)
class M1M2Classification:
    project_type: str
    confidence: float
    matched_keywords: list[str]
    detection_evidence: list[dict[str, str]]
    classification_method: str
    llm_reasoning_summary: str = ""
    fallback_reason: str = ""


def classify_m1_m2_project(
    project: dict[str, Any],
    sources: list[tuple[str, str]],
    rule_result: M1M2Classification,
) -> M1M2Classification:
    """LLM-first M1/M2 classifier with deterministic rule fallback."""
    if os.environ.get("ZHONGCHI_M1M2_LLM_ENABLED", "1").strip().lower() in {"0", "false", "no"}:
        return M1M2Classification(
            project_type=rule_result.project_type,
            confidence=rule_result.confidence,
            matched_keywords=rule_result.matched_keywords,
            detection_evidence=rule_result.detection_evidence,
            classification_method="rule_fallback",
            fallback_reason="M1/M2 LLM 分类已通过环境变量关闭",
        )
    try:
        llm_result = call_llm_project_classifier(project, sources)
        return _normalize_llm_result(llm_result)
    except Exception as exc:
        return M1M2Classification(
            project_type=rule_result.project_type,
            confidence=rule_result.confidence,
            matched_keywords=rule_result.matched_keywords,
            detection_evidence=rule_result.detection_evidence,
            classification_method="rule_fallback",
            fallback_reason=str(exc),
        )


def call_llm_project_classifier(project: dict[str, Any], sources: list[tuple[str, str]]) -> dict[str, Any]:
    base_url = get_configured_env(ENV_BASE_URL).strip()
    api_key = get_configured_env(ENV_API_KEY).strip()
    model = get_configured_env(ENV_MODEL).strip()
    missing = [name for name, value in ((ENV_BASE_URL, base_url), (ENV_API_KEY, api_key), (ENV_MODEL, model)) if not value]
    if missing:
        raise RuntimeError("缺少环境变量：" + ", ".join(missing))

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是中驰智能PPT的M1/M2模板分类器。"
                    "只能从 highway、metro、existing_rail_transit、railway 四个枚举中选择。"
                    "必须返回JSON，不要输出Markdown。"
                ),
            },
            {"role": "user", "content": _build_prompt(project, sources)},
        ],
        "temperature": 0,
        "max_tokens": 600,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=60.0, trust_env=False) as client:
        response = client.post(base_url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("LLM 响应缺少 choices")
    content = str((choices[0].get("message") or {}).get("content") or "").strip()
    return _parse_json_object(content)


def _build_prompt(project: dict[str, Any], sources: list[tuple[str, str]]) -> str:
    source_text = "\n\n".join(
        f"【{source}】\n{text[:MAX_SOURCE_CHARS]}"
        for source, text in sources
        if text
    )
    prompt_payload = {
        "task": "根据模板画像和项目资料判断M1/M2应选择哪个固定模板。",
        "template_profiles": TEMPLATE_PROFILES,
        "project": {
            "project_name": project.get("project_name", ""),
            "project_location": project.get("project_location", ""),
            "owner_unit": project.get("owner_unit", ""),
            "product_line": project.get("product_line", ""),
        },
        "project_sources": source_text[:MAX_SOURCE_CHARS],
        "output_schema": {
            "project_type": "highway|metro|existing_rail_transit|railway",
            "confidence": "0到1之间的小数",
            "matched_keywords": ["命中的关键词"],
            "evidence": [{"project_type": "枚举", "keyword": "关键词", "source": "来源", "snippet": "依据片段"}],
            "reasoning_summary": "一句话说明判断原因",
        },
    }
    return json.dumps(prompt_payload, ensure_ascii=False)


def _parse_json_object(content: str) -> dict[str, Any]:
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("LLM 响应不是 JSON 对象")
    data = json.loads(content[start : end + 1])
    if not isinstance(data, dict):
        raise RuntimeError("LLM 响应不是 JSON 对象")
    return data


def _normalize_llm_result(data: dict[str, Any]) -> M1M2Classification:
    project_type = str(data.get("project_type") or "").strip()
    if project_type not in PROJECT_TYPES:
        raise RuntimeError(f"LLM 返回非法 project_type：{project_type}")
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("LLM 返回 confidence 非法") from exc
    if confidence < MIN_LLM_CONFIDENCE:
        raise RuntimeError(f"LLM 置信度过低：{confidence}")

    matched_keywords = [str(item) for item in data.get("matched_keywords", []) if str(item).strip()]
    evidence = []
    for item in data.get("evidence", []):
        if not isinstance(item, dict):
            continue
        evidence.append(
            {
                "project_type": project_type,
                "keyword": str(item.get("keyword") or ""),
                "source": str(item.get("source") or "LLM"),
                "snippet": str(item.get("snippet") or ""),
            }
        )
    return M1M2Classification(
        project_type=project_type,
        confidence=max(0.0, min(1.0, confidence)),
        matched_keywords=matched_keywords,
        detection_evidence=evidence,
        classification_method="llm",
        llm_reasoning_summary=str(data.get("reasoning_summary") or ""),
    )
