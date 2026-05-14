from copy import deepcopy
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


MODULE_ORDER = ("M1", "M2", "M5", "M6")

MODULE_TITLES = {
    "M1": "行业背景与技术标准",
    "M2": "项目概况与现场挑战",
    "M5": "同类型案例匹配",
    "M6": "企业背书与荣誉",
}

PRIMARY_BLUE = RGBColor(0x15, 0x65, 0xC0)
DEEP_BLUE = RGBColor(0x1A, 0x3A, 0x6B)
ACCENT_GOLD = RGBColor(0xCA, 0x8A, 0x04)
LIGHT_BG = RGBColor(0xF7, 0xFA, 0xFC)
BODY_TEXT = RGBColor(0x1F, 0x29, 0x37)


def _validate_module(module_id: str) -> None:
    if module_id not in MODULE_ORDER:
        raise ValueError("本阶段 PPT 引擎只支持 M1/M2/M5/M6，M3/M4 为后续动态模块。")


def _safe_text(value: Any, field_name: str) -> str:
    if value is None or value == "":
        return f"[待补充：{field_name}]"
    return str(value)


def _set_run(run, size: int, color: RGBColor = BODY_TEXT, bold: bool = False) -> None:
    run.font.name = "Microsoft YaHei"
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold


def _add_textbox(slide, left, top, width, height, text: str, size: int, color: RGBColor = BODY_TEXT, bold: bool = False):
    shape = slide.shapes.add_textbox(left, top, width, height)
    frame = shape.text_frame
    frame.clear()
    paragraph = frame.paragraphs[0]
    run = paragraph.add_run()
    run.text = text
    _set_run(run, size=size, color=color, bold=bold)
    return shape


def _add_header(slide, module_id: str, page_label: str) -> None:
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = LIGHT_BG

    bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(0.18))
    bar.fill.solid()
    bar.fill.fore_color.rgb = PRIMARY_BLUE
    bar.line.fill.background()

    _add_textbox(slide, Inches(0.55), Inches(0.35), Inches(7.2), Inches(0.3), "中驰智能PPT Demo", 12, DEEP_BLUE, True)
    _add_textbox(slide, Inches(10.4), Inches(0.35), Inches(2.3), Inches(0.3), f"{module_id} | {page_label}", 11, ACCENT_GOLD, True)


def _add_cover_slide(prs: Presentation, module_id: str, project: dict[str, Any]) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, module_id, "章节封面")

    _add_textbox(slide, Inches(0.9), Inches(1.35), Inches(9.2), Inches(0.7), MODULE_TITLES[module_id], 32, DEEP_BLUE, True)
    _add_textbox(
        slide,
        Inches(0.95),
        Inches(2.25),
        Inches(8.8),
        Inches(0.55),
        _safe_text(project.get("project_name"), "项目名称"),
        20,
        BODY_TEXT,
        False,
    )
    _add_textbox(
        slide,
        Inches(0.95),
        Inches(3.05),
        Inches(10.8),
        Inches(0.45),
        f"项目所在地：{_safe_text(project.get('project_location'), '项目所在地')}    产品线：{_safe_text(project.get('product_line'), '产品线')}",
        15,
        BODY_TEXT,
        False,
    )

    accent = slide.shapes.add_shape(1, Inches(0.95), Inches(4.4), Inches(2.1), Inches(0.08))
    accent.fill.solid()
    accent.fill.fore_color.rgb = ACCENT_GOLD
    accent.line.fill.background()


def _add_outline_slide(prs: Presentation, module_id: str, slide_data: dict[str, Any], page_number: int) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_header(slide, module_id, f"第 {page_number} 页")

    _add_textbox(
        slide,
        Inches(0.75),
        Inches(0.95),
        Inches(11.6),
        Inches(0.55),
        _safe_text(slide_data.get("page_title"), "页面标题"),
        25,
        DEEP_BLUE,
        True,
    )
    _add_textbox(
        slide,
        Inches(0.8),
        Inches(1.75),
        Inches(11.2),
        Inches(0.65),
        _safe_text(slide_data.get("core_insight"), "核心观点"),
        17,
        BODY_TEXT,
        True,
    )

    bullet_points = slide_data.get("bullet_points") or ["[待补充：本页要点]"]
    bullet_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.75), Inches(10.9), Inches(2.6))
    frame = bullet_box.text_frame
    frame.clear()
    for index, bullet in enumerate(bullet_points[:5]):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = str(bullet)
        paragraph.level = 0
        paragraph.font.name = "Microsoft YaHei"
        paragraph.font.size = Pt(17)
        paragraph.font.color.rgb = BODY_TEXT

    missing_fields = slide_data.get("missing_fields") or []
    if missing_fields:
        marker_text = "  ".join(f"[待补充：{field}]" for field in missing_fields)
        _add_textbox(slide, Inches(0.85), Inches(6.0), Inches(11.5), Inches(0.4), marker_text, 13, ACCENT_GOLD, True)


def render_chapter_ppt(module_id: str, project: dict[str, Any], outline: dict[str, Any], output_dir: str | Path) -> Path:
    _validate_module(module_id)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    _add_cover_slide(prs, module_id, project)

    for index, slide_data in enumerate(outline.get("slides") or [], start=1):
        _add_outline_slide(prs, module_id, slide_data, index)

    if not outline.get("slides"):
        _add_outline_slide(
            prs,
            module_id,
            {
                "page_title": MODULE_TITLES[module_id],
                "core_insight": "[待补充：章节大纲]",
                "bullet_points": ["[待补充：章节要点]"],
                "missing_fields": ["章节大纲"],
            },
            1,
        )

    file_path = output_path / f"{module_id}_{MODULE_TITLES[module_id]}.pptx"
    prs.save(file_path)
    return file_path


def _append_slide(target: Presentation, source_slide) -> None:
    blank = target.slides.add_slide(target.slide_layouts[6])
    for shape in source_slide.shapes:
        blank.shapes._spTree.insert_element_before(deepcopy(shape.element), "p:extLst")

    if source_slide.background.fill.type is not None:
        blank.background.fill.solid()
        try:
            blank.background.fill.fore_color.rgb = source_slide.background.fill.fore_color.rgb
        except AttributeError:
            pass


def merge_pptx(chapter_paths: list[str | Path], output_path: str | Path) -> Path:
    merged = Presentation()
    merged.slide_width = Inches(13.333)
    merged.slide_height = Inches(7.5)

    if len(merged.slides) > 0:
        xml_slides = merged.slides._sldIdLst
        for slide_id in list(xml_slides):
            xml_slides.remove(slide_id)

    for chapter_path in chapter_paths:
        chapter = Presentation(str(chapter_path))
        for slide in chapter.slides:
            _append_slide(merged, slide)

    final_path = Path(output_path)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    merged.save(final_path)
    return final_path


def render_final_ppt(project: dict[str, Any], outlines: dict[str, dict[str, Any]], output_dir: str | Path) -> Path:
    output_path = Path(output_dir)
    chapters_dir = output_path / "chapters"
    chapter_paths = [
        render_chapter_ppt(module_id, project, outlines.get(module_id, {"slides": []}), chapters_dir)
        for module_id in MODULE_ORDER
    ]
    final_name = f"{_safe_text(project.get('project_name'), '项目名称')}_中驰智能PPT_Demo.pptx"
    return merge_pptx(chapter_paths, output_path / final_name)

