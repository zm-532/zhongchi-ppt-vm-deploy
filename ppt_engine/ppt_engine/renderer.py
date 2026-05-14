from copy import deepcopy
import shutil
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


# =============================================================================
# 模板路径配置（统一入口，禁止散落硬编码）
# =============================================================================
PPT_TEMPLATE_ROOT = Path(r"D:\中驰股份\code\ppt_engine\templates\solution_fixed_modules")

# M1/M2 固定模板映射表：project_type -> 模板文件名
M1_M2_TEMPLATE_MAP = {
    "highway": "公路全封闭声屏障（M1_&_M2）.pptx",
    "metro": "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx",
    "existing_rail_transit": "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx",
    "railway": "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx",
}

# M5 案例模板文件名
M5_TEMPLATE_FILENAME = "南昌轨道交通4号线声屏障工程项目案例模板（M5）.pptx"

# M6 固定模板文件名
M6_TEMPLATE_FILENAME = "中驰企业介绍合并初版（M6）.pptx"


# =============================================================================
# 合并顺序与模块标题
# =============================================================================
# 最终 PPT 合并顺序：M1/M2 -> M5 -> M6
MERGE_ORDER = ("M1_M2", "M5", "M6")

MODULE_TITLES = {
    "M1_M2": "行业背景与技术标准",
    "M5": "同类型案例匹配",
    "M6": "企业背书与荣誉",
}

# M1/M2 模板的 project_type 枚举
PROJECT_TYPES = ("highway", "metro", "existing_rail_transit", "railway")

PRIMARY_BLUE = RGBColor(0x15, 0x65, 0xC0)
DEEP_BLUE = RGBColor(0x1A, 0x3A, 0x6B)
ACCENT_GOLD = RGBColor(0xCA, 0x8A, 0x04)
LIGHT_BG = RGBColor(0xF7, 0xFA, 0xFC)
BODY_TEXT = RGBColor(0x1F, 0x29, 0x37)


# =============================================================================
# 辅助函数
# =============================================================================


def _validate_project_type(project_type: str) -> None:
    """验证 project_type 是否为合法枚举值。"""
    if project_type not in PROJECT_TYPES:
        raise ValueError(
            f"无效的 project_type：{project_type}，可选值：{PROJECT_TYPES}。"
        )


def _validate_module(module_id: str) -> None:
    """验证 module_id 是否为合法模块。"""
    if module_id not in MERGE_ORDER:
        raise ValueError("本阶段 PPT 引擎只支持 M1_M2/M5/M6，M3/M4 为后续动态模块。")


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


def _copy_fixed_template(source_path: Path, dest_path: Path) -> None:
    """Copy fixed template PPTX to destination. Creates parent directories if needed."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)


def _render_m6_fixed_template(project: dict[str, Any], output_dir: Path) -> Path:
    """渲染 M6 固定企业介绍模板（不做字段替换）。

    直接复制固定模板到输出目录，不做任何字段替换或素材替换。
    """
    source_template = PPT_TEMPLATE_ROOT / M6_TEMPLATE_FILENAME
    if not source_template.exists():
        # Fallback: 创建占位页
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11), Inches(1.5))
        text_frame = slide.shapes[-1].text_frame
        text_frame.paragraphs[0].text = f"[M6] 企业背书与荣誉 - 模板文件未找到：{M6_TEMPLATE_FILENAME}"
        file_path = output_dir / f"M6_{MODULE_TITLES['M6']}.pptx"
        prs.save(file_path)
        return file_path

    file_path = output_dir / f"M6_{MODULE_TITLES['M6']}.pptx"
    _copy_fixed_template(source_template, file_path)
    return file_path


def _render_m1_m2_fixed(
    project_type: str, project: dict[str, Any], output_dir: Path
) -> Path:
    """渲染 M1/M2 固定模板（根据 project_type 选择，不做字段替换）。

    根据 confirmed_project_type 从 M1_M2_TEMPLATE_MAP 选择对应模板，
    复制模板文件作为章节输出，不做字段替换。
    """
    _validate_project_type(project_type)
    template_filename = M1_M2_TEMPLATE_MAP[project_type]
    source_template = PPT_TEMPLATE_ROOT / template_filename

    if not source_template.exists():
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11), Inches(1.5))
        text_frame = slide.shapes[-1].text_frame
        text_frame.paragraphs[0].text = (
            f"[M1/M2] 行业背景与技术标准 - 模板文件未找到：{template_filename}"
        )
        file_path = output_dir / f"M1_M2_{MODULE_TITLES['M1_M2']}.pptx"
        prs.save(file_path)
        return file_path

    file_path = output_dir / f"M1_M2_{MODULE_TITLES['M1_M2']}.pptx"
    _copy_fixed_template(source_template, file_path)
    return file_path


def _render_m5_case_template(
    case_data: dict[str, Any] | None, project: dict[str, Any], output_dir: Path
) -> Path:
    """渲染 M5 案例模板（保留字段填充入口）。

    复制 M5 案例模板到输出目录。案例字段填充能力本阶段可先跳过，
    后续再完善字段映射。
    """
    source_template = PPT_TEMPLATE_ROOT / M5_TEMPLATE_FILENAME
    if not source_template.exists():
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11), Inches(1.5))
        text_frame = slide.shapes[-1].text_frame
        text_frame.paragraphs[0].text = (
            f"[M5] 同类型案例匹配 - 模板文件未找到：{M5_TEMPLATE_FILENAME}"
        )
        file_path = output_dir / f"M5_{MODULE_TITLES['M5']}.pptx"
        prs.save(file_path)
        return file_path

    file_path = output_dir / f"M5_{MODULE_TITLES['M5']}.pptx"
    _copy_fixed_template(source_template, file_path)
    return file_path


def render_chapter_ppt(
    module_id: str,
    project: dict[str, Any],
    outline: dict[str, Any],
    output_dir: str | Path,
) -> Path:
    """渲染单个章节 PPTX。

    Args:
        module_id: 模块标识，支持 M1_M2 / M5 / M6。
        project: 项目基础信息字典。
        outline: 章节配置。对于 M1_M2，outline 应包含 project_type；对于 M5，应包含 case_data；
                 对于 M6，outline 被忽略（固定模板）。
        output_dir: 输出目录路径。

    Returns:
        生成的章节 PPTX 文件路径。
    """
    _validate_module(module_id)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if module_id == "M1_M2":
        # M1/M2：根据 project_type 选择固定模板，只复制不替换
        project_type = outline.get("project_type", "highway")
        return _render_m1_m2_fixed(project_type, project, output_path)

    if module_id == "M5":
        # M5：案例模板填充入口，case_data 可为 None（允许先输出模板章节）
        case_data = outline.get("case_data")
        return _render_m5_case_template(case_data, project, output_path)

    if module_id == "M6":
        # M6：直接使用固定企业介绍模板，不做字段替换
        return _render_m6_fixed_template(project, output_path)

    # 不应到达此处（_validate_module 已拦截）
    raise ValueError(f"不支持的模块：{module_id}")


def _append_slide(target: Presentation, source_slide) -> None:
    blank = target.slides.add_slide(target.slide_layouts[6])
    for shape in source_slide.shapes:
        blank.shapes._spTree.insert_element_before(deepcopy(shape.element), "p:extLst")

    if source_slide.background.fill.type is not None:
        blank.background.fill.solid()
        try:
            blank.background.fill.fore_color.rgb = source_slide.background.fill.fore_color.rgb
        except (AttributeError, TypeError):
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


def render_final_ppt(
    project: dict[str, Any],
    outlines: dict[str, dict[str, Any]],
    output_dir: str | Path,
) -> Path:
    """按 M1/M2 -> M5 -> M6 顺序合并章节 PPTX。

    Args:
        project: 项目基础信息字典。
        outlines: 章节配置字典，key 为模块标识，value 为模块配置。
                  M1_M2 需要包含 project_type；M5 需要包含 case_data；M6 被忽略。
        output_dir: 输出目录路径。

    Returns:
        生成的最终 PPTX 文件路径。
    """
    output_path = Path(output_dir)
    chapters_dir = output_path / "chapters"
    chapter_paths = []
    for module_id in MERGE_ORDER:
        outline = outlines.get(module_id, {})
        chapter_path = render_chapter_ppt(module_id, project, outline, chapters_dir)
        chapter_paths.append(chapter_path)
    final_name = f"{_safe_text(project.get('project_name'), '项目名称')}_中驰智能PPT_Demo.pptx"
    return merge_pptx(chapter_paths, output_path / final_name)

