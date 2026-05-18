import os
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from ppt_engine.renderer import (
    MERGE_ORDER,
    M1_M2_TEMPLATE_MAP,
    M5_TEMPLATE_FILENAME,
    M6_TEMPLATE_FILENAME,
    PPT_TEMPLATE_ROOT,
    build_m1_m2_replacement_map,
    merge_pptx,
    move_project_info_slide_to_front,
    render_chapter_ppt,
    render_final_ppt,
    replace_text_placeholders,
)

os.environ["ZHONGCHI_PPT_MERGE_ENGINE"] = "python-pptx"


PROJECT = {
    "project_name": "某城市轨道交通声屏障改造项目",
    "project_location": "南京",
    "owner_unit": "某建设单位",
    "product_line": "轨交既有线改造",
}

# project_type -> M1_M2 template selection
OUTLINES_M1_M2_ONLY = {
    "M1_M2": {
        "project_type": "metro",
    },
}

M5_CASE_DATA = {
    "case_id": "sr_case_abc123",
    "case_title": "南昌轨道交通4号线声屏障工程",
    "match_reason": "同为轨道交通声屏障",
}


def outline_for_module(module_id: str) -> dict:
    if module_id == "M1_M2":
        return {"project_type": "metro"}
    if module_id == "M5":
        return {"case_data": M5_CASE_DATA}
    return {}


# M5 with case_data
OUTLINES_WITH_M5 = {
    "M1_M2": {
        "project_type": "metro",
    },
    "M5": {"case_data": M5_CASE_DATA},
}

# Full outlines with all three modules
OUTLINES_FULL = {
    "M1_M2": {
        "project_type": "metro",
    },
    "M5": {"case_data": M5_CASE_DATA},
    "M6": {},
}


def slide_count(path: Path) -> int:
    presentation = Presentation(str(path))
    return len(presentation.slides)


def slide_texts(path: Path) -> list[str]:
    presentation = Presentation(str(path))
    texts = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                texts.append(shape.text)
    return texts


def slide_image_relationship_errors(path: Path) -> list[str]:
    errors = []
    with zipfile.ZipFile(path) as pptx_zip:
        slide_names = sorted(
            [
                name
                for name in pptx_zip.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            ],
            key=lambda name: int(
                name.removeprefix("ppt/slides/slide").removesuffix(".xml")
            ),
        )
        for slide_name in slide_names:
            slide_xml = pptx_zip.read(slide_name).decode("utf-8")
            rels_name = slide_name.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
            rels_xml = pptx_zip.read(rels_name).decode("utf-8")
            for relationship_id in set(slide_xml.split('r:embed="')[1:]):
                relationship_id = relationship_id.split('"', 1)[0]
                marker = f'Id="{relationship_id}"'
                if marker not in rels_xml:
                    errors.append(f"{slide_name}: missing {relationship_id}")
                    continue
                rel_start = rels_xml.index(marker)
                rel_end = rels_xml.find("/>", rel_start)
                rel_fragment = rels_xml[rel_start:rel_end]
                if "/relationships/image" not in rel_fragment:
                    errors.append(f"{slide_name}: {relationship_id} is not image")
    return errors


def duplicate_zip_entries(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as pptx_zip:
        counts = Counter(pptx_zip.namelist())
    return sorted(name for name, count in counts.items() if count > 1)


class TemplateConfigTest(unittest.TestCase):
    """验证模板路径配置统一入口。"""

    def test_ppt_template_root_is_absolute_path(self):
        self.assertTrue(PPT_TEMPLATE_ROOT.is_absolute())

    def test_m1_m2_template_map_has_four_project_types(self):
        self.assertEqual(
            set(M1_M2_TEMPLATE_MAP.keys()),
            {"highway", "metro", "existing_rail_transit", "railway"},
        )

    def test_merge_order_is_m1_m2_then_m5_then_m6(self):
        self.assertEqual(MERGE_ORDER, ("M1_M2", "M5", "M6"))

    def test_m6_template_filename_correct(self):
        self.assertEqual(M6_TEMPLATE_FILENAME, "中驰企业介绍合并初版（M6）.pptx")

    def test_m5_template_filename_correct(self):
        self.assertEqual(M5_TEMPLATE_FILENAME, "南昌轨道交通4号线声屏障工程项目案例模板（M5）.pptx")


class M1M2TemplateSelectionTest(unittest.TestCase):
    """验证 M1/M2 根据 project_type 选择固定模板。"""

    def test_m1_m2_metro_template_copy_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            # Metro template should have multiple slides
            self.assertGreater(len(presentation.slides), 0)

    def test_m1_m2_highway_template_copy_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "highway"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertGreater(len(presentation.slides), 0)

    def test_m1_m2_existing_rail_transit_template_copy_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "existing_rail_transit"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertGreater(len(presentation.slides), 0)

    def test_m1_m2_railway_template_copy_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "railway"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertGreater(len(presentation.slides), 0)

    def test_m1_m2_rejects_invalid_project_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "invalid_type"}
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)

            self.assertIn("invalid_type", str(context.exception))


class M5CaseTemplateTest(unittest.TestCase):
    """验证 M5 案例模板入口。"""

    def test_m5_with_none_case_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"case_data": None}
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M5", PROJECT, outline, temp_dir)
            self.assertIn("未选择 M5 案例", str(context.exception))

    def test_m5_with_case_data_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {
                "case_data": M5_CASE_DATA
            }
            output_path = render_chapter_ppt("M5", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertGreater(len(presentation.slides), 0)


class M6FixedTemplateTest(unittest.TestCase):
    """验证 M6 固定企业介绍模板（不做字段替换）。"""

    def test_m6_fixed_template_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {}
            output_path = render_chapter_ppt("M6", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            # M6 fixed template has 15 slides per spec
            self.assertEqual(len(presentation.slides), 15)

            texts = slide_texts(output_path)
            text_blob = "\n".join(texts)
            # Verify M6 fixed template content is present (enterprise content)
            self.assertTrue(
                any("中驰" in t or "企业" in t for t in texts),
                "M6 should contain enterprise content from fixed template",
            )
            # Verify project data does NOT appear (no field substitution)
            self.assertNotIn("某城市轨道交通声屏障改造项目", text_blob)
            self.assertNotIn("轨交既有线改造", text_blob)


class RenderChapterPptValidationTest(unittest.TestCase):
    """验证 render_chapter_ppt 参数校验。"""

    def test_rejects_m3(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M3", PROJECT, {}, temp_dir)

            self.assertIn("M3", str(context.exception))

    def test_rejects_m4(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M4", PROJECT, {}, temp_dir)

            self.assertIn("M4", str(context.exception))

    def test_rejects_m1_alone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M1", PROJECT, {}, temp_dir)

            self.assertIn("M1", str(context.exception))

    def test_rejects_m2_alone(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M2", PROJECT, {}, temp_dir)

            self.assertIn("M2", str(context.exception))


class MergePptxTest(unittest.TestCase):
    """验证 PPTX 合并功能。"""

    def test_merge_pptx_produces_valid_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Render each chapter
            chapters = {}
            for module_id in MERGE_ORDER:
                outline = outline_for_module(module_id)
                chapters[module_id] = render_chapter_ppt(
                    module_id, PROJECT, outline, temp_dir
                )

            # Merge
            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(list(chapters.values()), final_path)

            self.assertTrue(result.exists())
            presentation = Presentation(str(result))
            self.assertGreater(len(presentation.slides), 0)

    def test_merge_pptx_preserves_source_slide_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chapters = []
            for module_id in MERGE_ORDER:
                outline = outline_for_module(module_id)
                chapters.append(render_chapter_ppt(module_id, PROJECT, outline, temp_dir))

            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(chapters, final_path)

            first_chapter = Presentation(str(chapters[0]))
            merged = Presentation(str(result))
            self.assertEqual(merged.slide_width, first_chapter.slide_width)
            self.assertEqual(merged.slide_height, first_chapter.slide_height)

    def test_merge_pptx_keeps_blip_relationships_pointing_to_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chapters = []
            for module_id in MERGE_ORDER:
                outline = outline_for_module(module_id)
                chapters.append(render_chapter_ppt(module_id, PROJECT, outline, temp_dir))

            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(chapters, final_path)

            self.assertEqual(slide_image_relationship_errors(result), [])

    def test_merge_pptx_does_not_write_duplicate_zip_entries(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chapters = []
            for module_id in MERGE_ORDER:
                outline = outline_for_module(module_id)
                chapters.append(render_chapter_ppt(module_id, PROJECT, outline, temp_dir))

            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(chapters, final_path)

            self.assertEqual(duplicate_zip_entries(result), [])

    def test_merge_pptx_slide_count_matches_chapter_slide_count_sum(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            chapters = []
            for module_id in MERGE_ORDER:
                outline = outline_for_module(module_id)
                chapters.append(render_chapter_ppt(module_id, PROJECT, outline, temp_dir))

            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(chapters, final_path)

            expected_count = sum(slide_count(chapter) for chapter in chapters)
            self.assertEqual(slide_count(result), expected_count)

    def test_merge_pptx_rejects_mismatched_slide_sizes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first = Presentation()
            first.slide_width = Inches(10)
            first.slide_height = Inches(5.625)
            first.slides.add_slide(first.slide_layouts[6])
            first_path = Path(temp_dir) / "first.pptx"
            first.save(first_path)

            second = Presentation()
            second.slide_width = Inches(13.333)
            second.slide_height = Inches(7.5)
            second.slides.add_slide(second.slide_layouts[6])
            second_path = Path(temp_dir) / "second.pptx"
            second.save(second_path)

            with self.assertRaises(ValueError) as context:
                merge_pptx([first_path, second_path], Path(temp_dir) / "final.pptx")

            self.assertIn("尺寸不一致", str(context.exception))


class RenderFinalPptTest(unittest.TestCase):
    """验证 render_final_ppt 按 M1/M2 -> M5 -> M6 顺序合并。"""

    def test_final_ppt_merge_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            final_path = render_final_ppt(PROJECT, OUTLINES_FULL, temp_dir)

            self.assertTrue(final_path.exists())
            presentation = Presentation(str(final_path))
            # Verify total slides > 0
            self.assertGreater(len(presentation.slides), 0)

    def test_final_ppt_contains_all_three_modules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            final_path = render_final_ppt(PROJECT, OUTLINES_FULL, temp_dir)

            texts = slide_texts(final_path)
            text_blob = "\n".join(texts)
            # M6 fixed template should contain "中驰"
            self.assertTrue(any("中驰" in t for t in texts))

    def test_final_ppt_excludes_m3_m4(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            final_path = render_final_ppt(PROJECT, OUTLINES_FULL, temp_dir)

            texts = slide_texts(final_path)
            text_blob = "\n".join(texts)
            # M3/M4 should not appear
            self.assertNotIn("定制化设计方案", text_blob)
            self.assertNotIn("工程量与施工周期测算", text_blob)

    def test_final_ppt_filename_contains_project_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            final_path = render_final_ppt(PROJECT, OUTLINES_FULL, temp_dir)

            self.assertIn("某城市轨道交通声屏障改造项目", final_path.name)


class ReplaceTextPlaceholdersTest(unittest.TestCase):
    """验证 replace_text_placeholders 通用占位符替换能力。"""

    def _create_test_pptx_with_placeholder(self, placeholder: str, dest_dir: Path) -> Path:
        """创建一个包含指定占位符的测试 PPTX。"""
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(5.625)
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
        tf = shape.text_frame
        tf.clear()
        para = tf.paragraphs[0]
        run = para.add_run()
        # f-string 中 {{ 产生字面 {，所以 {{project_name}} 要写成 {{{{project_name}}}}
        run.text = f"项目名称：{{{{{placeholder}}}}}"
        path = dest_dir / "test_placeholder.pptx"
        prs.save(str(path))
        return path

    def test_replaces_placeholder_with_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pptx_path = self._create_test_pptx_with_placeholder("project_name", Path(temp_dir))
            replace_text_placeholders(pptx_path, {"project_name": "南京地铁3号线声屏障工程"})
            prs = Presentation(str(pptx_path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            self.assertIn("南京地铁3号线声屏障工程", "\n".join(texts))
            self.assertNotIn("{{project_name}}", "\n".join(texts))

    def test_empty_field_uses_placeholder_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pptx_path = self._create_test_pptx_with_placeholder("project_location", Path(temp_dir))
            # build_m1_m2_replacement_map 对空字段会填充中文兜底
            # 测试：传中文兜底值进去，PPTX 里显示的也是中文兜底
            replace_text_placeholders(pptx_path, {"project_location": "[待补充：项目所在地]"})
            prs = Presentation(str(pptx_path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            self.assertIn("[待补充：项目所在地]", "\n".join(texts))

    def test_no_placeholder_in_template_does_not_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prs = Presentation()
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(5.625)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(1))
            tf = shape.text_frame
            tf.clear()
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = "没有任何占位符的普通文本"
            pptx_path = Path(temp_dir) / "no_placeholder.pptx"
            prs.save(str(pptx_path))
            # 不应抛出异常
            result = replace_text_placeholders(pptx_path, {"project_name": "测试项目"})
            self.assertTrue(result.exists())

    def test_multiple_placeholders_in_same_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            prs = Presentation()
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(5.625)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
            tf = shape.text_frame
            tf.clear()
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = "{{project_name}} 位于 {{project_location}}，由 {{owner_unit}} 负责建设"
            pptx_path = Path(temp_dir) / "multi_placeholder.pptx"
            prs.save(str(pptx_path))
            replace_text_placeholders(pptx_path, {
                "project_name": "南京地铁3号线",
                "project_location": "南京市",
                "owner_unit": "南京地铁集团",
            })
            prs2 = Presentation(str(pptx_path))
            texts = []
            for slide in prs2.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            text_blob = "\n".join(texts)
            self.assertIn("南京地铁3号线", text_blob)
            self.assertIn("南京市", text_blob)
            self.assertIn("南京地铁集团", text_blob)


class BuildM1M2ReplacementMapTest(unittest.TestCase):
    """验证 build_m1_m2_replacement_map 字段映射构建。"""

    def test_basic_fields_from_project(self):
        project = {
            "project_name": "南京地铁3号线声屏障改造工程",
            "project_location": "南京市",
            "owner_unit": "南京地铁集团",
            "product_line": "轨道交通声屏障",
        }
        outline = {}
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["project_name"], "南京地铁3号线声屏障改造工程")
        self.assertEqual(result["project_location"], "南京市")
        self.assertEqual(result["owner_unit"], "南京地铁集团")
        self.assertEqual(result["product_line"], "轨道交通声屏障")

    def test_missing_basic_field_uses_fallback(self):
        project = {
            "project_name": "南京地铁3号线",
            "project_location": "",
        }
        outline = {}
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["project_name"], "南京地铁3号线")
        self.assertEqual(result["project_location"], "[待补充：项目所在地]")
        self.assertEqual(result["owner_unit"], "[待补充：建设/业主单位]")
        self.assertEqual(result["product_line"], "[待补充：产品线]")

    def test_detected_and_confirmed_project_type(self):
        project = {
            "detected_project_type": "metro",
            "confirmed_project_type": "metro",
        }
        outline = {}
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["detected_project_type"], "metro")
        self.assertEqual(result["confirmed_project_type"], "metro")

    def test_m1_m2_template_from_template_selection(self):
        project = {
            "project_name": "测试项目",
            "template_selection": {
                "M1_M2": {
                    "template_filename": "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx"
                }
            },
        }
        outline = {}
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(
            result["m1_m2_template"],
            "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx"
        )

    def test_rule_field_line_name_from_filename(self):
        project = {"project_name": "测试项目"}
        outline = {
            "files": [
                {"filename": "南京地铁3号线施工方案.pdf"}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["line_name"], "3号线")

    def test_rule_field_line_name_s1_identifier(self):
        """S1号线 应识别为 S1号线，不是 1号线。"""
        project = {"project_name": "测试项目"}
        outline = {
            "files": [
                {"filename": "S1号线机场快线施工组织设计.pdf"}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["line_name"], "S1号线")

    def test_rule_field_site_pain_points_from_text(self):
        project = {"project_name": "测试项目"}
        outline = {
            "files": [
                {"filename": "施工方案.pdf", "parsed_text_path": None}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        # 无关键词时应返回待补充
        self.assertEqual(result["site_pain_points"], "[待补充：现场痛点]")

    def test_rule_field_construction_scenario_recognized(self):
        project = {"project_name": "测试项目"}
        outline = {
            "files": [
                {"filename": "既有线改造施工方案.pdf"}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        self.assertIn("既有线改造", result["construction_scenario"])

    def test_rule_field_no_match_uses_fallback(self):
        project = {"project_name": "测试项目"}
        outline = {
            "files": [
                {"filename": "普通文档.pdf"}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["line_name"], "[待补充：线路名称]")
        self.assertEqual(result["site_pain_points"], "[待补充：现场痛点]")
        self.assertEqual(result["construction_scenario"], "[待补充：施工场景]")


class M1M2FieldReplacementTest(unittest.TestCase):
    """验证 M1/M2 渲染后字段被正确替换。"""

    def test_m1_m2_replacement_map_includes_confirmed_project_type(self):
        project = {
            "project_name": "南京地铁3号线声屏障改造工程",
            "project_location": "南京市",
            "owner_unit": "南京地铁集团",
            "product_line": "轨道交通声屏障",
            "detected_project_type": "metro",
            "confirmed_project_type": "metro",
            "template_selection": {
                "M1_M2": {
                    "template_filename": "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx"
                }
            },
        }
        outline = {
            "project_type": "metro",
            "files": [
                {"filename": "南京地铁3号线施工组织设计.pdf"}
            ]
        }
        result = build_m1_m2_replacement_map(project, outline)
        self.assertEqual(result["confirmed_project_type"], "metro")
        self.assertEqual(result["project_name"], "南京地铁3号线声屏障改造工程")

    def test_m1_m2_renders_with_field_replacement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {
                "project_type": "metro",
                "files": [
                    {"filename": "南京地铁3号线施工组织设计.pdf"}
                ]
            }
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            self.assertTrue(output_path.exists())
            # 能打开即有效
            prs = Presentation(str(output_path))
            self.assertGreater(len(prs.slides), 0)

    def test_placeholder_replacement_with_m1_m2_map(self):
        """验证使用 build_m1_m2_replacement_map 生成的映射能正确替换占位符。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个含占位符的临时 PPTX
            from ppt_engine.renderer import (
                build_m1_m2_replacement_map,
                replace_text_placeholders,
            )
            prs = Presentation()
            prs.slide_width = Inches(10)
            prs.slide_height = Inches(5.625)
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
            tf = shape.text_frame
            tf.clear()
            para = tf.paragraphs[0]
            run = para.add_run()
            run.text = "项目名称：{{project_name}}，项目所在地：{{project_location}}"
            src_path = Path(temp_dir) / "src.pptx"
            prs.save(str(src_path))

            # 用 M1/M2 映射替换
            replacements = build_m1_m2_replacement_map(PROJECT, {})
            replace_text_placeholders(src_path, replacements)

            # 验证占位符已被替换为项目数据
            prs2 = Presentation(str(src_path))
            texts = []
            for slide in prs2.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            text_blob = "\n".join(texts)
            self.assertNotIn("{{project_name}}", text_blob)
            self.assertNotIn("{{project_location}}", text_blob)
            self.assertIn("某城市轨道交通声屏障改造项目", text_blob)
            self.assertIn("南京", text_blob)


class M5CaseTemplateNoReplacementTest(unittest.TestCase):
    """验证 M5 渲染不做字段替换（M5 只复制模板）。"""

    def test_m5_no_field_replacement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"case_data": M5_CASE_DATA}
            output_path = render_chapter_ppt("M5", PROJECT, outline, temp_dir)
            self.assertTrue(output_path.exists())
            prs = Presentation(str(output_path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            # M5 不应有 project_name 等项目字段被写入（只有模板原始内容）
            # 这里只验证能正常打开，具体内容由模板决定


class M6FixedTemplateNoProjectFieldsTest(unittest.TestCase):
    """验证 M6 固定模板不写入项目字段。"""

    def test_m6_fixed_template_no_project_field_replacement(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {}
            output_path = render_chapter_ppt("M6", PROJECT, outline, temp_dir)
            self.assertTrue(output_path.exists())
            prs = Presentation(str(output_path))
            texts = []
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text"):
                        texts.append(shape.text)
            text_blob = "\n".join(texts)
            # M6 是固定模板，不应有项目字段被替换的痕迹
            self.assertNotIn("某城市轨道交通声屏障改造项目", text_blob)


REQUIRED_PLACEHOLDERS = [
    "project_name",
    "project_location",
    "owner_unit",
    "product_line",
    "line_name",
    "site_pain_points",
    "construction_scenario",
]


class M1M2TemplateHasPlaceholdersTest(unittest.TestCase):
    """验证 4 个 M1/M2 固化模板已包含项目信息占位符。"""

    def test_all_four_m1_m2_templates_contain_all_seven_placeholders(self):
        """验证每个 M1/M2 模板都包含完整 7 个占位符。"""
        import re
        PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")
        for tmpl_filename in M1_M2_TEMPLATE_MAP.values():
            tmpl_path = PPT_TEMPLATE_ROOT / tmpl_filename
            prs = Presentation(str(tmpl_path))
            all_text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        all_text += shape.text
            found_placeholders = set(PLACEHOLDER_PATTERN.findall(all_text))
            missing = [f for f in REQUIRED_PLACEHOLDERS if f not in found_placeholders]
            self.assertEqual(
                missing, [],
                f"{tmpl_filename} 缺少占位符: {missing}",
            )

    def test_rendered_m1_m2_output_no_longer_contains_placeholder(self):
        """渲染 M1/M2 模板后，输出 PPTX 不再包含 {{project_name}}。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            prs = Presentation(str(output_path))
            all_text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        all_text += shape.text
            self.assertNotIn("{{project_name}}", all_text)

    def test_rendered_m1_m2_output_contains_project_name(self):
        """渲染 M1/M2 模板后，输出 PPTX 包含测试项目的名称。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            prs = Presentation(str(output_path))
            all_text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        all_text += shape.text
            self.assertIn("某城市轨道交通声屏障改造项目", all_text)

    def test_rendered_m1_m2_output_contains_project_info_fields(self):
        """渲染 M1/M2 模板后，输出 PPTX 包含项目信息的实际值，不含待补充标记。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            prs = Presentation(str(output_path))
            all_text = ""
            for slide in prs.slides:
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        all_text += shape.text
            # 关键字段应被替换为实际值
            self.assertIn("某城市轨道交通声屏障改造项目", all_text)  # project_name
            self.assertIn("南京", all_text)  # project_location
            self.assertIn("某建设单位", all_text)  # owner_unit
            self.assertIn("轨交既有线改造", all_text)  # product_line
            # 不应出现未替换的占位符标记
            self.assertNotIn("{{project_name}}", all_text)
            self.assertNotIn("{{project_location}}", all_text)


class ProjectInfoSlideReorderTest(unittest.TestCase):
    """验证"项目生成信息"页被移动到 M1/M2 章节第一页。"""

    def test_project_info_slide_is_first_after_render(self):
        """渲染后第1页应为"项目生成信息"页，且字段已替换。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            prs = Presentation(str(output_path))
            first_slide = prs.slides[0]
            first_text = ""
            for shape in first_slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    first_text += shape.text
            self.assertIn("项目生成信息", first_text)
            self.assertIn("某城市轨道交通声屏障改造项目", first_text)
            self.assertNotIn("{{project_name}}", first_text)

    def test_move_project_info_slide_to_front_is_idempotent(self):
        """连续调用两次 move_project_info_slide_to_front 不会产生重复页。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"project_type": "metro"}
            output_path = render_chapter_ppt("M1_M2", PROJECT, outline, temp_dir)
            move_project_info_slide_to_front(output_path)
            move_project_info_slide_to_front(output_path)
            prs = Presentation(str(output_path))
            # 统计包含"项目生成信息"的幻灯片数量（按 slide 计，非按文本出现次数）
            slides_with_project_info = sum(
                1 for slide in prs.slides
                if any("项目生成信息" in shape.text for shape in slide.shapes
                      if hasattr(shape, "text") and shape.text)
            )
            self.assertEqual(slides_with_project_info, 1)
            # 第一页仍是"项目生成信息"
            first_slide = prs.slides[0]
            first_text = "".join(
                shape.text for shape in first_slide.shapes if hasattr(shape, "text") and shape.text
            )
            self.assertIn("项目生成信息", first_text)


if __name__ == "__main__":
    unittest.main()
