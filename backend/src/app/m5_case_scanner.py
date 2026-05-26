"""
M5 案例库扫描模块

扫描 ppt_engine/templates/solution_fixed_modules/M5 目录下的 .pptx 文件，
将其识别为 M5 固定案例，供案例匹配和推荐使用。

文件名格式：{类型前缀}：{案例名称}.pptx
类型前缀支持中文冒号"："和英文冒号":"。
"""

import hashlib
import logging
import re
from pathlib import Path

from .constants import PPT_TEMPLATE_ROOT

logger = logging.getLogger(__name__)

M5_FOLDER = Path(PPT_TEMPLATE_ROOT) / "M5"

# 文件名前缀 → project_type 映射
_PREFIX_TYPE_MAP: dict[str, str] = {
    "公路": "highway",
    "铁路": "railway",
    "轨道交通": "metro",
}


def _parse_filename(filename: str) -> tuple[str, str]:
    """从文件名解析类型前缀和案例标题。

    Returns:
        (prefix, title) — 如 ("公路", "申嘉湖高速光伏声屏障项目")
        若无匹配前缀，prefix 为空字符串。
    """
    stem = Path(filename).stem
    # 支持中文冒号和英文冒号
    match = re.match(r"^(.+?)[：:](.+)$", stem)
    if match:
        prefix = match.group(1).strip()
        title = match.group(2).strip()
        return prefix, title
    return "", stem


def _generate_case_id(filename: str) -> str:
    """基于文件名生成稳定的 case_id。"""
    h = hashlib.sha1(filename.encode("utf-8")).hexdigest()[:12]
    return f"fixed_m5_case:{h}"


def scan_m5_cases() -> list[dict]:
    """扫描 M5 文件夹，返回案例列表。

    每个案例包含：
    - case_id: 稳定 ID（基于文件名 hash）
    - title: 案例标题
    - filename: 原始文件名
    - project_type: high/railway/metro
    - source_path: 文件绝对路径
    - module_id: "M5"
    - source_type: "fixed_m5"
    """
    if not M5_FOLDER.exists():
        logger.warning(f"M5 folder not found: {M5_FOLDER}")
        return []

    cases: list[dict] = []
    for f in sorted(M5_FOLDER.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() != ".pptx":
            continue
        # 跳过临时文件（以 ~$ 开头）
        if f.name.startswith("~$"):
            continue

        prefix, title = _parse_filename(f.name)
        project_type = _PREFIX_TYPE_MAP.get(prefix, "")

        case = {
            "case_id": _generate_case_id(f.name),
            "title": title,
            "filename": f.name,
            "project_type": project_type,
            "source_path": str(f),
            "module_id": "M5",
            "source_type": "fixed_m5",
        }
        cases.append(case)

    return cases


def get_m5_case_by_id(case_id: str) -> dict | None:
    """根据 case_id 查找 M5 案例。"""
    for case in scan_m5_cases():
        if case["case_id"] == case_id:
            return case
    return None


def recommend_m5_case(project_type: str) -> dict | None:
    """根据 project_type 推荐 1 个 M5 案例。

    规则：
    - highway → 公路开头文件
    - railway → 铁路开头文件
    - metro → 轨道交通开头文件
    - existing_rail_transit → 暂归到轨道交通
    """
    type_to_prefix = {
        "highway": "公路",
        "railway": "铁路",
        "metro": "轨道交通",
        "existing_rail_transit": "轨道交通",
    }
    target_prefix = type_to_prefix.get(project_type, "")
    if not target_prefix:
        return None

    for case in scan_m5_cases():
        prefix, _ = _parse_filename(case["filename"])
        if prefix == target_prefix:
            return case
    return None
