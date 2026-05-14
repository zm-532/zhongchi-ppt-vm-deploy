import tempfile
import unittest
from pathlib import Path

from pptx import Presentation

from ppt_engine.renderer import render_chapter_ppt, render_final_ppt


PROJECT = {
    "project_name": "某城市轨道交通声屏障改造项目",
    "project_location": "",
    "owner_unit": "某建设单位",
    "product_line": "轨交既有线改造",
}

OUTLINES = {
    "M1": {
        "slides": [
            {
                "module_id": "M1",
                "page_title": "行业背景与技术发展",
                "core_insight": "政策标准推动声屏障产品升级。",
                "bullet_points": ["标准体系持续完善", "降噪与耐久性要求提升"],
                "missing_fields": ["项目所在地"],
            }
        ]
    },
    "M2": {
        "slides": [
            {
                "module_id": "M2",
                "page_title": "项目概况与现场挑战",
                "core_insight": "现场工况需要兼顾降噪、施工窗口和运营安全。",
                "bullet_points": [],
                "missing_fields": [],
            }
        ]
    },
    "M5": {
        "slides": [
            {
                "module_id": "M5",
                "page_title": "同类型案例匹配",
                "core_insight": "历史案例可支撑本项目技术路线。",
                "bullet_points": ["案例工况相近", "解决成效可复用"],
                "missing_fields": [],
            }
        ]
    },
    "M6": {
        "slides": [
            {
                "module_id": "M6",
                "page_title": "企业背书与荣誉",
                "core_insight": "企业资质与产能支撑项目交付。",
                "bullet_points": ["CNAS 与专利能力", "产能与质量体系"],
                "missing_fields": [],
            }
        ]
    },
}


def slide_texts(path: Path) -> list[str]:
    presentation = Presentation(str(path))
    texts = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text") and shape.text:
                texts.append(shape.text)
    return texts


class PptRendererTest(unittest.TestCase):
    def test_render_chapter_ppt_creates_editable_slide_with_missing_field_marker(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = render_chapter_ppt("M1", PROJECT, OUTLINES["M1"], temp_dir)

            self.assertTrue(output_path.exists())
            presentation = Presentation(str(output_path))
            self.assertEqual(len(presentation.slides), 2)
            text_blob = "\n".join(slide_texts(output_path))
            self.assertIn("行业背景与技术标准", text_blob)
            self.assertIn("行业背景与技术发展", text_blob)
            self.assertIn("[待补充：项目所在地]", text_blob)

    def test_render_chapter_ppt_rejects_dynamic_modules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError) as context:
                render_chapter_ppt("M3", PROJECT, {"slides": []}, temp_dir)

            self.assertIn("M1/M2/M5/M6", str(context.exception))

    def test_render_final_ppt_merges_only_m1_m2_m5_m6_in_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            final_path = render_final_ppt(PROJECT, OUTLINES, output_dir)

            self.assertTrue(final_path.exists())
            presentation = Presentation(str(final_path))
            self.assertEqual(len(presentation.slides), 8)
            texts = slide_texts(final_path)
            module_positions = [
                next(index for index, text in enumerate(texts) if module_name in text)
                for module_name in ["行业背景与技术标准", "项目概况与现场挑战", "同类型案例匹配", "企业背书与荣誉"]
            ]
            self.assertEqual(module_positions, sorted(module_positions))
            self.assertNotIn("定制化设计方案", "\n".join(texts))
            self.assertNotIn("工程量与施工周期测算", "\n".join(texts))


if __name__ == "__main__":
    unittest.main()
