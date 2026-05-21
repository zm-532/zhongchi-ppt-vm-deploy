import importlib
import json
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


TEXTS = {
    "m3_basic_summary": "项目基本情况文字",
    "m3_line_summary": "项目线路图文字",
    "m3_sensitive_points_summary": "敏感点路段文字",
    "m3_quantity_summary": "工程量统计文字",
    "m3_structure_summary": "结构形式文字",
    "m3_site_survey_summary": "现场踏勘文字",
    "m3_investigation_summary": "现场勘察情况文字",
    "m3_risk_summary": "项目重难点分析文字",
    "m3_solution_summary": "重难点应对措施文字",
}


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
            data={
                "project_name": "M3完整接口测试",
                "texts": json.dumps(TEXTS, ensure_ascii=False),
                "purposes": "image:m3_basic",
            },
            files=[("files", ("basic.png", _png_bytes(), "image/png"))],
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
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("purposes", (None, "image:m3_basic")),
                ("purposes", (None, "image:m3_basic")),
                ("files", ("basic1.png", _png_bytes(), "image/png")),
                ("files", ("basic2.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["slide_count"], 10)

    def test_m3_full_render_rejects_mismatched_files_and_purposes(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            data={
                "project_name": "M3完整数量错误",
                "texts": json.dumps(TEXTS, ensure_ascii=False),
            },
            files=[("files", ("basic.png", _png_bytes(), "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("图片文件数量和用途数量必须一致", response.text)

    def test_m3_full_render_rejects_invalid_purpose(self):
        response = self.client.post(
            "/api/test/m3-full-render",
            data={
                "project_name": "M3完整非法用途",
                "texts": json.dumps(TEXTS, ensure_ascii=False),
                "purposes": "bad_purpose",
            },
            files=[("files", ("basic.png", _png_bytes(), "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("非法图片用途", response.text)

    def test_m3_full_download_rejects_path_traversal(self):
        response = self.client.get("/api/test/m3-full-render/download/..%2Fbad.pptx")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
