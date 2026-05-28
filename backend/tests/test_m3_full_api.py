import importlib
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


def _png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 360), (20, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


TABLE_TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "ppt_engine" / "templates" / "solution_fixed_modules" / "M3表格模板"


class M3FullApiTest(unittest.TestCase):
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

    def test_m3_full_render_accepts_valid_upload(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整接口测试")),
                ("descriptions", (None, "项目基本情况-1：基础描述")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("/api/test/m3-full-render/download/", body["download_url"])
        self.assertTrue(Path(body["pptx_path"]).exists())

    def test_m3_full_render_accepts_multiple_images_for_one_section(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整多图接口测试")),
                ("descriptions", (None, "项目基本情况-1：第一张\n项目基本情况-2：第二张")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
                ("files", ("项目基本情况-2.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["slide_count"], 10)

    def test_m3_full_render_accepts_xlsx_table_and_image_upload(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整表格接口测试")),
                ("descriptions", (None, "敏感点路段-1：敏感点图片说明")),
                ("files", ("敏感点路段.xlsx", TABLE_TEMPLATE_ROOT.joinpath("敏感点路段.xlsx").read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                ("files", ("敏感点路段-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["slide_count"], 10)
        self.assertEqual(body["image_summary"]["image:m3_sensitive_points"], 1)
        self.assertEqual(body["table_summary"]["image:m3_sensitive_points"], 1)

    def test_m3_full_render_rejects_corrupt_xlsx_table(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整损坏表格接口测试")),
                ("files", ("敏感点路段.xlsx", b"not an xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Excel 表格文件无效或已损坏", response.text)

    def test_m3_full_render_rejects_description_without_image(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整描述错误")),
                ("descriptions", (None, "项目基本情况-2：多余描述")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("描述没有对应图片", response.text)

    def test_m3_full_render_rejects_purposes_manual_mode(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            files=[
                ("project_name", (None, "M3完整手动模式错误")),
                ("purposes", (None, "image:m3_basic")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不再支持按模块手动上传", response.text)

    def test_m3_full_download_rejects_path_traversal(self):
        response = self.client.get("/api/test/m3-full-render/download/..%2Fbad.pptx")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
