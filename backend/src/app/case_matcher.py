"""
案例匹配模块 - M5 案例匹配核心逻辑

从真实案例库（case_library）和历史资料（SR智能PPT拆分）召回相似案例。
禁止编造案例，找不到时返回"暂无高匹配案例"。
"""

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from .document_analysis import extract_text

logger = logging.getLogger(__name__)

# 案例库路径
CODE_DIR = Path(__file__).resolve().parents[3]
WORKSPACE_DIR = CODE_DIR.parent
CASE_LIBRARY_DIR = Path(os.environ.get("ZHONGCHI_CASE_LIBRARY_DIR", CODE_DIR / "data" / "case_library"))
SR_PPT_SPLIT_DIR = Path(os.environ.get("ZHONGCHI_SR_PPT_SPLIT_DIR", WORKSPACE_DIR / "SR智能PPT拆分"))
CASES_INDEX_PATH = CASE_LIBRARY_DIR / "cases_index.json"

# 项目类型关键词
PROJECT_TYPE_KEYWORDS = {
    "existing_rail_transit": ["既有线", "改造", "夜间", "短窗口", "加装"],
    "metro": ["地铁", "metro", "轨道交通", "城市轨道", "昌平线", "轨交"],
    "highway": ["公路", "高速", "highway"],
    "railway": ["铁路", "railway"],
}

# 施工场景关键词
CONSTRUCTION_SCENARIO_KEYWORDS = {
    "新建": ["新建", "新建工程"],
    "既有线改造": ["既有线", "改造", "夜间", "短窗口"],
    "加装": ["加装", "增设", "新增"],
}

# 痛点关键词
PAIN_POINT_KEYWORDS = {
    "噪声治理": ["噪声", "噪音", "降噪", "噪声治理"],
    "施工窗口短": ["窗口", "夜间", "天窗", "短窗口", "时间紧"],
    "技术难度高": ["技术难点", "复杂", "难度", "高难度"],
    "工期紧张": ["工期", "紧张", "赶工", "交付"],
}

# 技术难点关键词
TECH_DIFFICULTY_KEYWORDS = {
    "既有线施工": ["既有线", "运营线", "不停运"],
    "高空作业": ["高空", "高支架", "吊装"],
    "精度要求高": ["精度", "精密", "误差"],
}


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_text(text: str) -> str:
    return _compact_text(text).lower()


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text.lower() for keyword in keywords)


def _ensure_case_library_dir() -> None:
    """确保案例库目录存在"""
    CASE_LIBRARY_DIR.mkdir(parents=True, exist_ok=True)


def _detect_project_type_from_text(text: str) -> str:
    """从文本中检测项目类型"""
    text_lower = _normalize_text(text)
    # Rail context keywords that indicate a rail/transit project
    rail_context_keywords = ["地铁", "轨道交通", "铁路", "轨交", "城市轨道", "metro"]
    strong_constraint = ["既有线", "运营线", "天窗", "短窗口"]
    weak_constraint = ["改造", "夜间", "加装"]
    has_rail_context = any(kw in text_lower for kw in rail_context_keywords)

    scores: dict[str, float] = {}
    for project_type, keywords in PROJECT_TYPE_KEYWORDS.items():
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        if project_type == "existing_rail_transit":
            if has_rail_context:
                s = sum(1.0 for kw in matched if kw in strong_constraint)
                w = sum(0.5 for kw in matched if kw in weak_constraint)
                scores[project_type] = s + w
            else:
                scores[project_type] = sum(1 for kw in matched if kw in strong_constraint)
        elif project_type == "metro":
            has_strong_constraint = any(kw in text_lower for kw in strong_constraint)
            scores[project_type] = len(matched) * (0.5 if has_strong_constraint else 1.0)
        else:
            scores[project_type] = len(matched)
    if not scores or max(scores.values()) == 0:
        return "metro"  # 默认地铁
    return max(scores, key=scores.get)


def _extract_tags_from_text(text: str) -> dict[str, list[str]]:
    """从文本中提取标签（关键词fallback）"""
    text_normalized = _normalize_text(text)

    # 提取项目类型
    project_type = _detect_project_type_from_text(text)

    # 提取城市
    city_patterns = [
        r"南昌|武汉|合肥|宁波|杭州|南京|苏州|上海|北京|广州|深圳|成都|重庆|西安|郑州|长沙|济南|青岛|天津|沈阳|大连|哈尔滨|长春|福州|厦门|南宁|昆明|贵阳|太原|石家庄|兰州|乌鲁木齐|呼和浩特|银川|西宁|拉萨|海口",
    ]
    cities = []
    for pattern in city_patterns:
        matches = re.findall(pattern, text_normalized)
        cities.extend(matches)

    # 提取线路（如 4号线、S1号线）
    line_patterns = [
        r"(\d+号线|[\d.]+km|\d+[Kk]m)",
        r"([一二三四五六七八九十]+号线)",
    ]
    lines = []
    for pattern in line_patterns:
        matches = re.findall(pattern, text)
        lines.extend(matches)

    # 提取施工场景
    construction_scenarios = []
    for scenario, keywords in CONSTRUCTION_SCENARIO_KEYWORDS.items():
        if _has_any(text_normalized, keywords):
            construction_scenarios.append(scenario)

    # 提取痛点
    pain_points = []
    for pain_point, keywords in PAIN_POINT_KEYWORDS.items():
        if _has_any(text_normalized, keywords):
            pain_points.append(pain_point)

    # 提取技术难点
    tech_difficulties = []
    for tech_diff, keywords in TECH_DIFFICULTY_KEYWORDS.items():
        if _has_any(text_normalized, keywords):
            tech_difficulties.append(tech_diff)

    # 通用标签提取
    tags = []
    if _has_any(text_normalized, ["声屏障"]):
        tags.append("声屏障")
    if _has_any(text_normalized, ["轨道交通", "地铁", "metro"]):
        tags.append("轨道交通")
    if _has_any(text_normalized, ["铁路", "railway"]):
        tags.append("铁路")
    if _has_any(text_normalized, ["公路", "高速"]):
        tags.append("公路")
    if _has_any(text_normalized, ["案例", "case", "业绩"]):
        tags.append("案例")

    return {
        "project_type": project_type,
        "cities": list(set(cities)),
        "lines": list(set(lines)),
        "construction_scenarios": construction_scenarios,
        "pain_points": pain_points,
        "tech_difficulties": tech_difficulties,
        "tags": list(set(tags)),
    }


def _parse_ppt_for_tags(ppt_dir: Path) -> dict[str, Any]:
    """解析PPT文件夹，提取所有文本并提取标签"""
    all_text = []
    for ppt_file in ppt_dir.glob("*.pptx"):
        try:
            text = extract_text(ppt_file, ".pptx")
            if text:
                all_text.append(text)
        except Exception as e:
            logger.warning(f"Failed to extract text from {ppt_file}: {e}")

    combined_text = " ".join(all_text)
    tags = _extract_tags_from_text(combined_text)

    return {
        "text": combined_text,
        "tags": tags,
    }


def _index_sr_ppt_cases() -> list[dict[str, Any]]:
    """索引 SR智能PPT拆分 目录下的案例"""
    cases = []
    if not SR_PPT_SPLIT_DIR.exists():
        logger.warning(f"SR PPT split directory not found: {SR_PPT_SPLIT_DIR}")
        return cases

    for project_dir in SR_PPT_SPLIT_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        project_name = project_dir.name
        parsed = _parse_ppt_for_tags(project_dir)
        text = parsed["text"]
        extracted_tags = parsed["tags"]

        # 生成case_id：使用路径的hash后10位，避免中文目录名冲突
        path_hash = hashlib.sha1(str(project_dir).encode('utf-8')).hexdigest()[:10]
        # 提取目录名中的有效字符作为前缀
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_name)
        safe_name = re.sub(r'_+', '_', safe_name).strip('_')[:15]  # 保留前15个有效字符
        case_id = f"sr_{safe_name}_{path_hash}"

        case = {
            "case_id": case_id,
            "title": project_name,
            "source_path": str(project_dir),
            "source_type": "sr_ppt_split",
            "project_type": extracted_tags.get("project_type", "metro"),
            "city": extracted_tags.get("cities", []),
            "line": extracted_tags.get("lines", []),
            "tags": extracted_tags.get("tags", []),
            "construction_scenarios": extracted_tags.get("construction_scenarios", []),
            "pain_points": extracted_tags.get("pain_points", []),
            "tech_difficulties": extracted_tags.get("tech_difficulties", []),
            "text_preview": text[:500] if text else "",
        }
        cases.append(case)

    return cases


def _load_case_library_cases() -> list[dict[str, Any]]:
    """从 case_library 目录加载结构化案例"""
    cases = []
    if not CASE_LIBRARY_DIR.exists():
        return cases

    # 查找 JSON 索引文件
    if CASES_INDEX_PATH.exists():
        try:
            index_data = json.loads(CASES_INDEX_PATH.read_text(encoding="utf-8"))
            return index_data.get("cases", [])
        except Exception as e:
            logger.warning(f"Failed to load cases index: {e}")

    # 如果没有索引文件，扫描子目录
    for case_dir in CASE_LIBRARY_DIR.iterdir():
        if not case_dir.is_dir():
            continue

        # 查找该案例的索引文件
        case_index_file = case_dir / "case_info.json"
        if case_index_file.exists():
            try:
                case_info = json.loads(case_index_file.read_text(encoding="utf-8"))
                case_info["source_type"] = "case_library"
                cases.append(case_info)
            except Exception as e:
                logger.warning(f"Failed to load case info from {case_index_file}: {e}")
                continue

    return cases


def build_case_index() -> list[dict[str, Any]]:
    """构建案例索引，同时从两个来源召回案例"""
    _ensure_case_library_dir()

    # 从 case_library 加载
    library_cases = _load_case_library_cases()

    # 从 SR智能PPT拆分 索引
    sr_cases = _index_sr_ppt_cases()

    # 合并去重（按source_path）
    seen_paths = set()
    all_cases = []
    for case in library_cases + sr_cases:
        source_path = case.get("source_path", "")
        if source_path and source_path not in seen_paths:
            seen_paths.add(source_path)
            all_cases.append(case)

    # 保存合并后的索引
    index_data = {
        "version": "1.0",
        "updated_at": str(Path(__file__).stat().st_mtime),
        "cases": all_cases,
    }
    CASES_INDEX_PATH.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Case index built with {len(all_cases)} cases")

    return all_cases


def load_case_index(force_rebuild: bool = False) -> list[dict[str, Any]]:
    """加载案例索引，如果不存在或为空则构建

    Args:
        force_rebuild: 是否强制重建索引
    """
    if force_rebuild:
        logger.info("Force rebuilding case index")
        return build_case_index()

    if CASES_INDEX_PATH.exists():
        try:
            index_data = json.loads(CASES_INDEX_PATH.read_text(encoding="utf-8"))
            cases = index_data.get("cases", [])
            # 如果索引为空，触发重建以扫描 SR 历史案例
            if cases:
                return cases
            logger.info("Case index is empty, rebuilding to scan SR historical cases")
        except Exception as e:
            logger.warning(f"Failed to load cases index, rebuilding: {e}")

    return build_case_index()


def _calculate_match_score(project_tags: dict, case: dict) -> tuple[int, list[str]]:
    """计算项目标签与案例的匹配得分"""
    score = 0
    matched_tags = []

    project_type = project_tags.get("project_type", "")
    case_project_type = case.get("project_type", "")

    # 项目类型匹配（权重高）
    if project_type and project_type == case_project_type:
        score += 10
        matched_tags.append(f"项目类型:{project_type}")

    # 项目类型相近（降级匹配）
    if project_type == "existing_rail_transit" and case_project_type == "metro":
        score += 5
        matched_tags.append("项目类型相近:既有线/地铁")
    if project_type == "metro" and case_project_type == "existing_rail_transit":
        score += 5
        matched_tags.append("项目类型相近:地铁/既有线")

    # 城市匹配
    project_cities = set(project_tags.get("cities", []))
    case_cities = set(case.get("city", []))
    if project_cities and case_cities:
        city_match = project_cities & case_cities
        if city_match:
            score += len(city_match) * 3
            matched_tags.extend([f"城市:{c}" for c in city_match])

    # 施工场景匹配
    project_scenarios = set(project_tags.get("construction_scenarios", []))
    case_scenarios = set(case.get("construction_scenarios", []))
    if project_scenarios and case_scenarios:
        scenario_match = project_scenarios & case_scenarios
        if scenario_match:
            score += len(scenario_match) * 4
            matched_tags.extend([f"场景:{s}" for s in scenario_match])

    # 痛点匹配
    project_pains = set(project_tags.get("pain_points", []))
    case_pains = set(case.get("pain_points", []))
    if project_pains and case_pains:
        pain_match = project_pains & case_pains
        if pain_match:
            score += len(pain_match) * 3
            matched_tags.extend([f"痛点:{p}" for p in pain_match])

    # 通用标签匹配
    project_tags_set = set(project_tags.get("tags", []))
    case_tags_set = set(case.get("tags", []))
    if project_tags_set and case_tags_set:
        tag_match = project_tags_set & case_tags_set
        if tag_match:
            score += len(tag_match) * 2
            matched_tags.extend(list(tag_match))

    return score, matched_tags


def _generate_match_reason(project_tags: dict, case: dict, matched_tags: list[str]) -> str:
    """生成匹配理由说明"""
    reasons = []

    project_type = project_tags.get("project_type", "")
    case_project_type = case.get("project_type", "")

    if project_type == case_project_type:
        type_names = {
            "metro": "轨道交通",
            "existing_rail_transit": "既有线改造",
            "railway": "铁路",
            "highway": "公路",
        }
        type_name = type_names.get(project_type, project_type)
        reasons.append(f"同为{type_name}项目")

    # 场景相近
    project_scenarios = set(project_tags.get("construction_scenarios", []))
    case_scenarios = set(case.get("construction_scenarios", []))
    if project_scenarios & case_scenarios:
        common = project_scenarios & case_scenarios
        reasons.append(f"施工场景相近：{'、'.join(common)}")

    # 痛点相近
    project_pains = set(project_tags.get("pain_points", []))
    case_pains = set(case.get("pain_points", []))
    if project_pains & case_pains:
        common = project_pains & case_pains
        reasons.append(f"痛点相近：{'、'.join(common)}")

    # 城市相同
    project_cities = set(project_tags.get("cities", []))
    case_cities = set(case.get("city", []))
    if project_cities & case_cities:
        common = project_cities & case_cities
        reasons.append(f"同一城市：{'、'.join(common)}")

    if not reasons:
        reasons.append("同为声屏障相关项目，场景可参考")

    return "，".join(reasons)


def match_cases(
    project_tags: dict,
    case_index: list[dict[str, Any]] | None = None,
    top_n: int = 3,
) -> list[dict[str, Any]]:
    """
    匹配相似案例

    Args:
        project_tags: 项目标签，包含 project_type, cities, construction_scenarios, pain_points, tags 等
        case_index: 案例索引列表，如果为 None 则自动加载
        top_n: 返回前 N 个推荐案例

    Returns:
        推荐案例列表，每个案例包含 case_id, title, match_reason, matched_tags, source_path
    """
    if case_index is None:
        case_index = load_case_index()

    if not case_index:
        logger.warning("No cases found in index")
        return []

    # 按项目类型过滤
    project_type = project_tags.get("project_type", "")
    filtered_cases = case_index

    # 如果有明确的项目类型，先按类型过滤
    if project_type:
        # 精确匹配
        type_matched = [c for c in filtered_cases if c.get("project_type") == project_type]
        if type_matched:
            filtered_cases = type_matched
        else:
            # 降级匹配：existing_rail_transit <-> metro
            related_types = {"metro": ["existing_rail_transit"], "existing_rail_transit": ["metro"]}
            related = related_types.get(project_type, [])
            type_matched = [c for c in filtered_cases if c.get("project_type") in related]
            if type_matched:
                filtered_cases = type_matched

    # 计算得分
    scored_cases = []
    for case in filtered_cases:
        score, matched_tags = _calculate_match_score(project_tags, case)
        if score > 0:
            match_reason = _generate_match_reason(project_tags, case, matched_tags)
            scored_cases.append({
                "case_id": case.get("case_id", ""),
                "title": case.get("title", ""),
                "match_reason": match_reason,
                "matched_tags": matched_tags[:10],  # 限制标签数量
                "source_path": case.get("source_path", ""),
                "score": score,
            })

    # 按得分排序
    scored_cases.sort(key=lambda x: x["score"], reverse=True)

    # 返回 top N
    result = scored_cases[:top_n]

    # 清理结果中的 score 字段（不对外暴露）
    for item in result:
        item.pop("score", None)

    if not result:
        logger.info("No matching cases found")
        return []

    logger.info(f"Matched {len(result)} cases for project type: {project_type}")
    return result


def extract_tags_with_llm(text: str, project_context: dict[str, str] | None = None) -> dict[str, Any] | None:
    """
    使用 LLM 提取结构化标签（可选增强）

    如果 LLM 未配置，返回 None 触发 fallback 到关键词提取。
    预留接口，后续可接入真实 LLM。
    """
    # TODO: 当配置了 LLM 时，调用 LLM 提取标签
    # 目前返回 None 表示使用关键词 fallback
    logger.debug("LLM not configured, using keyword fallback for tag extraction")
    return None


def extract_project_tags(text: str, project_context: dict[str, str] | None = None) -> dict[str, Any]:
    """
    提取项目标签

    优先尝试 LLM 提取，失败则使用关键词 fallback。
    """
    # 尝试 LLM
    llm_tags = extract_tags_with_llm(text, project_context)
    if llm_tags:
        return llm_tags

    # Fallback: 关键词提取
    return _extract_tags_from_text(text)
