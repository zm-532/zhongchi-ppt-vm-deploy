"""M3 完整测试渲染（文字 + 图片，占位符替换，不接入正式流程）。"""

import tempfile
import unittest
from io import BytesIO

from PIL import Image
from pptx import Presentation

from ppt_engine.renderer import (
    M3_FULL_SECTIONS,
    M3_FULL_TEST_TEMPLATE_FILENAME,
    PPT_TEMPLATE_ROOT,
    render_m3_full_test_ppt,
    validate_m3_full_template_placeholders,
)


def _png_bytes(color: tuple[int, int, int] = (30, 90, 160), size: tuple[int, int] = (640, 360)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, format="PNG")
    return buffer.getvalue()


TEXTS = {
    section["text_field"]: f"{section['title']}测试文字"
    for section in M3_FULL_SECTIONS
}


class M3FullRendererTest(unittest.TestCase):
    def test_m3_full_template_exists_and_has_9_slides(self):
        template = PPT_TEMPLATE_ROOT / M3_FULL_TEST_TEMPLATE_FILENAME
        self.assertTrue(template.exists(), f"M3 完整测试模板不存在：{template}")
        prs = Presentation(str(template))
        self.assertEqual(len(prs.slides), 9)

    def test_m3_full_template_has_all_text_and_image_placeholders(self):
        template = PPT_TEMPLATE_ROOT / M3_FULL_TEST_TEMPLATE_FILENAME
        self.assertEqual(validate_m3_full_template_placeholders(template), [])

    def test_render_m3_full_single_image_per_section_outputs_9_slides(self):
        images = {
            section["image_field"]: [_png_bytes()]
            for section in M3_FULL_SECTIONS
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = render_m3_full_test_ppt("M3完整测试", TEXTS, images, temp_dir)
            prs = Presentation(str(output_path))
            self.assertEqual(len(prs.slides), 9)

    def test_render_m3_full_duplicates_section_when_two_images_uploaded(self):
        images = {
            "image:m3_basic": [_png_bytes((200, 40, 40)), _png_bytes((40, 200, 40))],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = render_m3_full_test_ppt("M3完整多图测试", TEXTS, images, temp_dir)
            prs = Presentation(str(output_path))
            self.assertEqual(len(prs.slides), 10)

    def test_render_m3_full_counts_multiple_sections_with_extra_images(self):
        images = {
            "image:m3_basic": [_png_bytes(), _png_bytes()],
            "image:m3_line": [_png_bytes(), _png_bytes(), _png_bytes()],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = render_m3_full_test_ppt("M3完整多部分多图", TEXTS, images, temp_dir)
            prs = Presentation(str(output_path))
            self.assertEqual(len(prs.slides), 12)

    def test_render_m3_full_does_not_modify_source_template(self):
        template = PPT_TEMPLATE_ROOT / M3_FULL_TEST_TEMPLATE_FILENAME
        before = template.stat().st_mtime
        with tempfile.TemporaryDirectory() as temp_dir:
            render_m3_full_test_ppt("不修改源模板", TEXTS, {"image:m3_basic": [_png_bytes()]}, temp_dir)
        self.assertEqual(template.stat().st_mtime, before)

    def test_render_m3_full_rejects_invalid_image_purpose(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                render_m3_full_test_ppt("非法用途", TEXTS, {"bad_purpose": [_png_bytes()]}, temp_dir)

    def test_render_m3_full_rejects_corrupt_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                render_m3_full_test_ppt("损坏图片", TEXTS, {"image:m3_basic": [b"not-an-image"]}, temp_dir)


if __name__ == "__main__":
    unittest.main()
