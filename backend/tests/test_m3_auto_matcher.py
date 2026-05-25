import importlib
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.m3_auto_matcher import build_m3_auto_render_payload


def _png_bytes(color=(20, 120, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 360), color).save(buffer, format="PNG")
    return buffer.getvalue()


class M3AutoMatcherTest(unittest.TestCase):
    def test_orders_unnumbered_image_before_numbered_images(self):
        payload = build_m3_auto_render_payload(
            filenames=["项目基本情况-1.jpg", "项目基本情况.jpg", "项目基本情况-2.jpg"],
            blobs=[b"one", b"zero", b"two"],
            descriptions="项目基本情况：第一张\n项目基本情况-1：第二张\n项目基本情况-2：第三张",
        )

        self.assertEqual(payload.images_by_purpose["image:m3_basic"], [b"zero", b"one", b"two"])
        self.assertEqual(payload.texts["m3_basic_summary"], "第一张")
        self.assertEqual(payload.page_texts["image:m3_basic"], ["第一张", "第二张", "第三张"])

    def test_allows_images_without_descriptions(self):
        payload = build_m3_auto_render_payload(
            filenames=["项目线路图-1.png"],
            blobs=[b"line"],
            descriptions="",
        )

        self.assertEqual(payload.images_by_purpose["image:m3_line"], [b"line"])
        self.assertEqual(payload.texts["m3_line_summary"], "")
        self.assertEqual(payload.page_texts["image:m3_line"], [""])

    def test_rejects_unknown_image_category(self):
        with self.assertRaisesRegex(ValueError, "无法识别图片分类"):
            build_m3_auto_render_payload(
                filenames=["其他图片.jpg"],
                blobs=[b"bad"],
                descriptions="",
            )

    def test_rejects_duplicate_unnumbered_images(self):
        with self.assertRaisesRegex(ValueError, "存在多个未编号图片"):
            build_m3_auto_render_payload(
                filenames=["项目基本情况.jpg", "项目基本情况.png"],
                blobs=[b"a", b"b"],
                descriptions="",
            )

    def test_rejects_duplicate_numbered_images(self):
        with self.assertRaisesRegex(ValueError, "图片编号重复"):
            build_m3_auto_render_payload(
                filenames=["项目基本情况-1.jpg", "项目基本情况-1.png"],
                blobs=[b"a", b"b"],
                descriptions="",
            )

    def test_rejects_description_without_image(self):
        with self.assertRaisesRegex(ValueError, "描述没有对应图片"):
            build_m3_auto_render_payload(
                filenames=["项目基本情况.jpg"],
                blobs=[b"a"],
                descriptions="项目基本情况-1：多余描述",
            )


class M3AutoMatcherApiTest(unittest.TestCase):
    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "test_tmp"
        test_tmp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name

        from fastapi.testclient import TestClient

        app_module = importlib.import_module("app.main")
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("ZHONGCHI_DATA_DIR", None)

    def test_auto_mode_generates_with_matching_descriptions(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3自动匹配接口测试")),
                ("texts", (None, json.dumps({}, ensure_ascii=False))),
                ("descriptions", (None, "项目基本情况：基础描述\n项目基本情况-1：补充描述")),
                ("files", ("项目基本情况.jpg", _png_bytes(), "image/png")),
                ("files", ("项目基本情况-1.jpg", _png_bytes((200, 80, 20)), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["slide_count"], 10)
        self.assertEqual(body["image_summary"]["image:m3_basic"], 2)

    def test_auto_mode_rejects_description_without_image(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3自动匹配错误接口测试")),
                ("descriptions", (None, "项目基本情况-1：多余描述")),
                ("files", ("项目基本情况.jpg", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("描述没有对应图片", response.text)


if __name__ == "__main__":
    unittest.main()
