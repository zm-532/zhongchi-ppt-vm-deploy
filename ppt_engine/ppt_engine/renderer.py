from copy import deepcopy
from io import BytesIO
import os
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
PPT_TEMPLATE_ROOT = Path(
    os.environ.get(
        "ZHONGCHI_PPT_TEMPLATE_ROOT",
        Path(__file__).resolve().parents[1] / "templates" / "solution_fixed_modules",
    )
)

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
EMU_PER_POINT = 12700


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
    模板缺失时抛出异常，不生成静默占位页。
    """
    source_template = PPT_TEMPLATE_ROOT / M6_TEMPLATE_FILENAME
    if not source_template.exists():
        raise FileNotFoundError(
            f"M6 固定模板未找到：{source_template}。"
            "请确认 PPT_TEMPLATE_ROOT 配置正确且模板文件存在。"
        )

    file_path = output_dir / f"M6_{MODULE_TITLES['M6']}.pptx"
    _copy_fixed_template(source_template, file_path)
    return file_path


def _render_m1_m2_fixed(
    project_type: str, project: dict[str, Any], output_dir: Path
) -> Path:
    """渲染 M1/M2 固定模板（根据 project_type 选择，不做字段替换）。

    根据 confirmed_project_type 从 M1_M2_TEMPLATE_MAP 选择对应模板，
    复制模板文件作为章节输出，不做字段替换。
    模板缺失时抛出异常，不生成静默占位页。
    """
    _validate_project_type(project_type)
    template_filename = M1_M2_TEMPLATE_MAP[project_type]
    source_template = PPT_TEMPLATE_ROOT / template_filename

    if not source_template.exists():
        raise FileNotFoundError(
            f"M1/M2 固定模板未找到：{source_template}。"
            f"请确认 project_type={project_type} 对应的模板文件存在。"
        )

    file_path = output_dir / f"M1_M2_{MODULE_TITLES['M1_M2']}.pptx"
    _copy_fixed_template(source_template, file_path)
    return file_path


def _render_m5_case_template(
    case_data: dict[str, Any] | None, project: dict[str, Any], output_dir: Path
) -> Path:
    """渲染 M5 案例模板（保留字段填充入口）。

    复制 M5 案例模板到输出目录。案例字段填充能力本阶段可先跳过，
    后续再完善字段映射。
    模板缺失时抛出异常，不生成静默占位页。
    """
    source_template = PPT_TEMPLATE_ROOT / M5_TEMPLATE_FILENAME
    if not source_template.exists():
        raise FileNotFoundError(
            f"M5 案例模板未找到：{source_template}。"
            "请确认 PPT_TEMPLATE_ROOT 配置正确且模板文件存在。"
        )

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
        # M5：案例模板填充入口，必须有有效的 case_data 才能渲染
        case_data = outline.get("case_data")
        if not case_data or not case_data.get("case_id"):
            raise ValueError("未选择 M5 案例，禁止生成 M5 案例模板。")
        return _render_m5_case_template(case_data, project, output_path)

    if module_id == "M6":
        # M6：直接使用固定企业介绍模板，不做字段替换
        return _render_m6_fixed_template(project, output_path)

    # 不应到达此处（_validate_module 已拦截）
    raise ValueError(f"不支持的模块：{module_id}")


def _append_slide(target: Presentation, source_slide) -> None:
    """将 source_slide 完整追加到 target，包括其 OPC 关系（图片/媒体/图表等）。"""
    blank = target.slides.add_slide(target.slide_layouts[6])

    # 复制 shape XML，并记录复制内容实际引用的关系 ID。
    copied_elements = []
    used_relationship_ids = set()
    for shape in source_slide.shapes:
        copied_element = deepcopy(shape.element)
        copied_elements.append(copied_element)
        for element in copied_element.iter():
            for value in element.attrib.values():
                if isinstance(value, str) and value.startswith("rId"):
                    used_relationship_ids.add(value)
        blank.shapes._spTree.insert_element_before(copied_element, "p:extLst")

    # 复制 copied XML 实际引用的 slide.rels，并记录 old rId -> new rId。
    relationship_id_map = {}
    if hasattr(source_slide, "part") and hasattr(source_slide.part, "rels"):
        target_slide_part = blank.part
        for rId, rel in source_slide.part.rels.items():
            if rId not in used_relationship_ids:
                continue
            if rel.reltype.endswith("/relationships/image") and not rel.is_external:
                _, new_rId = target_slide_part.get_or_add_image_part(
                    BytesIO(rel.target_part.blob)
                )
                relationship_id_map[rId] = new_rId
                continue
            # 非图片内部关系：复制对应 Part；外部关系：传 URI 字符串。
            target_obj = rel.target_part if not rel.is_external else rel.target_ref
            relationship_id_map[rId] = target_slide_part.rels._add_relationship(
                rel.reltype, target_obj, rel.is_external
            )

    # copied XML 仍然带着源 slide 的 rId，必须重写为目标 slide 新 rId。
    for copied_element in copied_elements:
        for element in copied_element.iter():
            for attribute_name, value in list(element.attrib.items()):
                if value in relationship_id_map:
                    element.set(attribute_name, relationship_id_map[value])

    # 复制背景
    if source_slide.background.fill.type is not None:
        blank.background.fill.solid()
        try:
            blank.background.fill.fore_color.rgb = source_slide.background.fill.fore_color.rgb
        except (AttributeError, TypeError):
            pass


def _presentation_size(path: str | Path) -> tuple[int, int]:
    presentation = Presentation(str(path))
    return int(presentation.slide_width), int(presentation.slide_height)


def _validate_chapter_sizes(chapter_paths: list[str | Path]) -> tuple[int, int]:
    first_width, first_height = _presentation_size(chapter_paths[0])
    for chapter_path in chapter_paths[1:]:
        width, height = _presentation_size(chapter_path)
        if width != first_width or height != first_height:
            raise ValueError(
                "章节 PPTX 尺寸不一致，当前合并器暂不支持跨尺寸合并："
                f"{chapter_path} 的尺寸为 {width}x{height}，"
                f"首个章节尺寸为 {first_width}x{first_height}。"
            )
    return first_width, first_height


def _merge_pptx_with_powerpoint(chapter_paths: list[str | Path], output_path: str | Path) -> bool:
    """使用 PowerPoint COM 原样合并幻灯片；不可用时返回 False。"""
    if os.name != "nt":
        return False

    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        return False

    final_path = Path(output_path).resolve()
    final_path.parent.mkdir(parents=True, exist_ok=True)

    app = None
    target = None
    opened_sources = []
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        target = app.Presentations.Add(WithWindow=False)

        # PowerPoint COM 使用 points；12700 EMU = 1 point。
        first_width, first_height = _presentation_size(chapter_paths[0])
        target.PageSetup.SlideWidth = first_width / EMU_PER_POINT
        target.PageSetup.SlideHeight = first_height / EMU_PER_POINT

        insert_index = 0
        for chapter_path in chapter_paths:
            source_path = str(Path(chapter_path).resolve())
            source = app.Presentations.Open(source_path, ReadOnly=True, Untitled=False, WithWindow=False)
            opened_sources.append(source)
            slide_count = source.Slides.Count
            source.Close()
            opened_sources.pop()
            if slide_count == 0:
                continue
            target.Slides.InsertFromFile(source_path, insert_index, 1, slide_count)
            insert_index += slide_count

        target.SaveAs(str(final_path))
        return True
    except Exception:
        return False
    finally:
        for source in reversed(opened_sources):
            try:
                source.Close()
            except Exception:
                pass
        if target is not None:
            try:
                target.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass


def merge_pptx(chapter_paths: list[str | Path], output_path: str | Path) -> Path:
    if not chapter_paths:
        raise ValueError("至少需要一个章节 PPTX 用于合并。")

    _validate_chapter_sizes(chapter_paths)

    merge_engine = os.environ.get("ZHONGCHI_PPT_MERGE_ENGINE", "auto").lower()
    if merge_engine not in {"auto", "powerpoint", "python-pptx"}:
        raise ValueError("ZHONGCHI_PPT_MERGE_ENGINE 只允许 auto/powerpoint/python-pptx。")

    if merge_engine in {"auto", "powerpoint"}:
        merged_by_powerpoint = _merge_pptx_with_powerpoint(chapter_paths, output_path)
        if merged_by_powerpoint:
            return Path(output_path)
        if merge_engine == "powerpoint":
            raise RuntimeError("PowerPoint COM 合并不可用，请确认已安装 pywin32 和 Microsoft PowerPoint。")

    chapters = [Presentation(str(chapter_path)) for chapter_path in chapter_paths]
    first_chapter = chapters[0]

    merged = Presentation()
    merged.slide_width = first_chapter.slide_width
    merged.slide_height = first_chapter.slide_height

    if len(merged.slides) > 0:
        xml_slides = merged.slides._sldIdLst
        for slide_id in list(xml_slides):
            xml_slides.remove(slide_id)

    for chapter in chapters:
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
