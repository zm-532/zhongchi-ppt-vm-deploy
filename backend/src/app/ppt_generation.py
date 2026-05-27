from __future__ import annotations

import sys
import shutil
from pathlib import Path
from typing import Any

from .m5_case_scanner import get_m5_case_by_id


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
        (final_path, chapter_paths)，其中 chapter_paths 的 key 为 M1/M2/M3/M5/M6，
        与 storage.py 的存储逻辑兼容。
    """
    _ensure_ppt_engine_path()

    from ppt_engine.renderer import MERGE_ORDER, merge_pptx, render_chapter_ppt

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir = output_dir / "chapters"

    # ── 1. 从 project 构造新版 outlines ──────────────────────────────────────
    # 兜底：旧流程（如直接 review 而未经 classify_review）可能没有 confirmed_project_type
    confirmed_project_type = project.get("confirmed_project_type") or "highway"
    case_selection = project.get("case_selection", {})
    confirmed_case_id = case_selection.get("confirmed_case_id")

    # 只有明确选择了案例才生成 M5；否则跳过 M5
    # confirmed_case_id 必须是有效非空值（不是 None、不是空字符串、不是 "null" 等）
    raw_case_id = case_selection.get("confirmed_case_id")
    has_case = raw_case_id is not None and str(raw_case_id).strip() not in ("", "null", "None", "__none__")

    # M3 选择：默认包含M3，"m3_skip" 时跳过
    include_m3 = project.get("m3_selection", "m3_template") == "m3_template"
    include_print_tail_page = bool(project.get("include_print_tail_page", False))

    parsed_sources: list[str] = []
    for file_record in project.get("classification_result", {}).get("files", []):
        parsed_text_path = file_record.get("parsed_text_path")
        if not parsed_text_path:
            continue
        path = Path(parsed_text_path)
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if text.strip():
            parsed_sources.append(text)

    m3_materials = project.get("m3_materials") or {}
    m3_outline: dict[str, Any] = {"parsed_sources": parsed_sources}
    if m3_materials:
        images_by_purpose: dict[str, list[bytes]] = {}
        for image_record in m3_materials.get("images", []):
            purpose = image_record.get("purpose", "")
            stored_path = image_record.get("stored_path", "")
            if not purpose or not stored_path:
                continue
            path = Path(stored_path)
            if not path.exists():
                continue
            try:
                blob = path.read_bytes()
            except OSError:
                continue
            images_by_purpose.setdefault(purpose, []).append(blob)
        m3_outline["m3_materials"] = {
            "texts": m3_materials.get("texts") or {},
            "images_by_purpose": images_by_purpose,
            "page_texts": m3_materials.get("page_texts") or {},
        }

    # 构建 M5 case_data：fixed_m5_case 需要解析完整案例信息
    m5_case_data: dict[str, Any] | None = None
    if has_case:
        m5_case_data = {"case_id": raw_case_id}
        # 如果是 fixed_m5_case，从 M5 文件夹解析完整案例信息
        if str(raw_case_id).startswith("fixed_m5_case:"):
            resolved = get_m5_case_by_id(str(raw_case_id))
            if not resolved:
                raise FileNotFoundError(
                    f"fixed_m5_case 未在 M5 文件夹中找到：case_id={raw_case_id}。"
                    "案例文件可能已被移动或删除，请重新扫描 M5 案例库。"
                )
            m5_case_data.update({
                "source_path": resolved["source_path"],
                "filename": resolved["filename"],
                "title": resolved["title"],
                "source_type": resolved["source_type"],
            })

    # 新版 outline 结构
    outlines = {
        "M1_M2": {"project_type": confirmed_project_type},
        "M3": m3_outline,
        "M5": {"case_data": m5_case_data},
        "M6": {},
    }

    # ── 2. 调用新版 render_chapter_ppt（返回 M1_M2/M3/M5/M6 章节文件）────────────
    chapter_paths_new: dict[str, Path] = {}
    for module_id in MERGE_ORDER:
        # 跳过 M5（当没有选择案例时）
        if module_id == "M5" and not has_case:
            continue
        # 跳过 M3（当用户选择跳过 M3 时）
        if module_id == "M3" and not include_m3:
            continue
        # 跳过尾页打印版（当用户未选择添加时）
        if module_id == "TAIL_PRINT" and not include_print_tail_page:
            continue
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
        "M6": chapter_paths_new["M6"],
    }
    if has_case:
        chapter_paths["M5"] = chapter_paths_new["M5"]
    if include_m3:
        chapter_paths["M3"] = chapter_paths_new["M3"]

    # ── 4. 合并章节 PPTX ───────────────────────────────────────────────────
    safe_name = "".join(
        char if char not in '\\/:*?"<>|' else "_"
        for char in project.get("project_name", "中驰智能PPT")
    )
    # 根据实际渲染出的章节动态调整文件名和合并顺序，保持与 ppt_engine.MERGE_ORDER 一致。
    merge_order = tuple(k for k in MERGE_ORDER if k in chapter_paths_new)
    final_name = f"{safe_name}_{'_'.join(merge_order)}_最终稿.pptx"
    final_path = output_dir / final_name
    merge_pptx([chapter_paths_new[module_id] for module_id in merge_order], final_path)

    if not final_path.exists():
        raise RuntimeError("最终PPTX生成失败")

    return final_path, chapter_paths
