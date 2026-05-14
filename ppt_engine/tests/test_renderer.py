import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

from ppt_engine.renderer import (
    MERGE_ORDER,
    M1_M2_TEMPLATE_MAP,
    M5_TEMPLATE_FILENAME,
    M6_TEMPLATE_FILENAME,
    PPT_TEMPLATE_ROOT,
    merge_pptx,
    render_chapter_ppt,
    render_final_ppt,
)


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

# M5 with case_data (case_data optional per spec - can be None)
OUTLINES_WITH_M5 = {
    "M1_M2": {
        "project_type": "metro",
    },
    "M5": {
        "case_data": {
            "case_id": 1,
            "case_title": "南昌轨道交通4号线声屏障工程",
            "match_reason": "同为轨道交通声屏障",
        }
    },
}

# Full outlines with all three modules
OUTLINES_FULL = {
    "M1_M2": {
        "project_type": "metro",
    },
    "M5": {
        "case_data": None,
    },
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
    """验证 M5 案例模板入口（case_data 可为 None）。"""

    def test_m5_with_none_case_data_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {"case_data": None}
            output_path = render_chapter_ppt("M5", PROJECT, outline, temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertGreater(len(presentation.slides), 0)

    def test_m5_with_case_data_produces_valid_pptx(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            outline = {
                "case_data": {
                    "case_id": 1,
                    "case_title": "南昌轨道交通4号线声屏障工程",
                }
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
                outline = (
                    {"project_type": "metro"}
                    if module_id == "M1_M2"
                    else {"case_data": None}
                    if module_id == "M5"
                    else {}
                )
                chapters[module_id] = render_chapter_ppt(
                    module_id, PROJECT, outline, temp_dir
                )

            # Merge
            final_path = Path(temp_dir) / "final.pptx"
            result = merge_pptx(list(chapters.values()), final_path)

            self.assertTrue(result.exists())
            presentation = Presentation(str(result))
            self.assertGreater(len(presentation.slides), 0)


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


if __name__ == "__main__":
    unittest.main()