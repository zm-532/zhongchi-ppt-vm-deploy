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
    _ensure_ppt_engine_path()

    from ppt_engine.renderer import MODULE_ORDER, MODULE_TITLES, merge_pptx, render_chapter_ppt

    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"
    outlines = {module["module_id"]: module.get("outline", {"slides": []}) for module in project["modules"]}
    chapter_paths: dict[str, Path] = {}

    for module_id in MODULE_ORDER:
        chapter_paths[module_id] = render_chapter_ppt(module_id, project, outlines.get(module_id, {"slides": []}), chapters_dir)

    safe_name = "".join(char if char not in '\\/:*?"<>|' else "_" for char in project.get("project_name", "中驰智能PPT"))
    final_path = output_dir / f"{safe_name}_M1_M2_M5_M6_最终稿.pptx"
    merge_pptx([chapter_paths[module_id] for module_id in MODULE_ORDER], final_path)

    expected_titles = [MODULE_TITLES[module_id] for module_id in MODULE_ORDER]
    if not final_path.exists():
        raise RuntimeError("最终PPTX生成失败")
    if not expected_titles:
        raise RuntimeError("章节配置为空")

    return final_path, chapter_paths
