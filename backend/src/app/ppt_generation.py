from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _ensure_ppt_engine_path() -> None:
    code_dir = Path(__file__).resolve().parents[3]
    ppt_engine_dir = code_dir / "ppt_engine"
    path_text = str(ppt_engine_dir)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)


def render_project_ppt(project: dict[str, Any], output_dir: Path) -> tuple[Path, dict[str, Path]]:
    """生成项目 PPTX（适配新版 PPT 引擎接口）。

    将后端旧版 project["modules"] 结构映射到新版 outlines 结构，
    调用 ppt_engine.renderer 的新 API，生成后返回兼容旧存储的 chapter_paths。

    Args:
        project: 项目字典，包含 modules、confirmed_project_type、case_selection 等。
        output_dir: 输出目录。

    Returns:
        (final_path, chapter_paths)，其中 chapter_paths 的 key 为 M1/M2/M5/M6，
        与 storage.py 的存储逻辑兼容。
    """
    _ensure_ppt_engine_path()

    from ppt_engine.renderer import MERGE_ORDER, merge_pptx, render_chapter_ppt

    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"

    # ── 1. 从 project 构造新版 outlines ──────────────────────────────────────
    # 兜底：旧流程（如直接 review 而未经 classify_review）可能没有 confirmed_project_type
    confirmed_project_type = project.get("confirmed_project_type") or "highway"
    case_selection = project.get("case_selection", {})
    confirmed_case_id = case_selection.get("confirmed_case_id")

    # 新版 outline 结构
    outlines = {
        "M1_M2": {"project_type": confirmed_project_type},
        "M5": {"case_data": {"case_id": confirmed_case_id} if confirmed_case_id else None},
        "M6": {},
    }

    # ── 2. 调用新版 render_chapter_ppt（返回 M1_M2/M5/M6 章节文件）────────────
    chapter_paths_new: dict[str, Path] = {}
    for module_id in MERGE_ORDER:
        outline = outlines.get(module_id, {})
        chapter_paths_new[module_id] = render_chapter_ppt(
            module_id, project, outline, chapters_dir
        )

    # ── 3. 将 M1_M2 章节路径映射回 M1、M2，兼容后端 storage.py ───────────────
    # storage.py 按 module["module_id"]（M1/M2/M5/M6）存储 chapter_ppt_path，
    # 故需将同一个 M1_M2 章节文件路径同时赋值给 M1 和 M2。
    m1_m2_path = chapter_paths_new["M1_M2"]
    chapter_paths: dict[str, Path] = {
        "M1": m1_m2_path,
        "M2": m1_m2_path,   # M1/M2 共用同一份章节文件（M1&M2 合并模板）
        "M5": chapter_paths_new["M5"],
        "M6": chapter_paths_new["M6"],
    }

    # ── 4. 合并章节 PPTX（M1_M2 -> M5 -> M6）──────────────────────────────────
    safe_name = "".join(
        char if char not in '\\/:*?"<>|' else "_"
        for char in project.get("project_name", "中驰智能PPT")
    )
    final_path = output_dir / f"{safe_name}_M1_M2_M5_M6_最终稿.pptx"
    merge_pptx([chapter_paths_new[module_id] for module_id in MERGE_ORDER], final_path)

    if not final_path.exists():
        raise RuntimeError("最终PPTX生成失败")

    return final_path, chapter_paths