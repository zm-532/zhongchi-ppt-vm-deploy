import importlib
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


def _png_bytes(color=(20, 120, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 360), color).save(buffer, format="PNG")
    return buffer.getvalue()


TEXTS = {
    "m3_basic_summary": "项目基本情况正式文字",
    "m3_line_summary": "项目线路图正式文字",
    "m3_sensitive_points_summary": "敏感点路段正式文字",
    "m3_quantity_summary": "工程量统计正式文字",
    "m3_structure_summary": "结构形式正式文字",
    "m3_site_survey_summary": "现场踏勘正式文字",
    "m3_investigation_summary": "现场勘察情况正式文字",
    "m3_risk_summary": "项目重难点分析正式文字",
    "m3_solution_summary": "重难点应对措施正式文字",
}


class M3MaterialsApiTest(unittest.TestCase):
    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "test_tmp"
        test_tmp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name

        from fastapi.testclient import TestClient

        app_module = importlib.import_module("app.main")
        self.client = TestClient(app_module.app)
        self.project_id = self.client.post(
            "/api/projects",
            json={"project_name": "M3正式资料项目", "project_location": "南京"},
        ).json()["project_id"]

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("ZHONGCHI_DATA_DIR", None)

    def test_save_and_get_m3_materials(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("purposes", (None, "image:m3_basic")),
                ("purposes", (None, "image:m3_basic")),
                ("purposes", (None, "image:m3_site_survey")),
                ("files", ("basic1.png", _png_bytes(), "image/png")),
                ("files", ("basic2.png", _png_bytes((200, 80, 20)), "image/png")),
                ("files", ("survey.png", _png_bytes((40, 180, 80)), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["project_id"], self.project_id)
        self.assertEqual(body["texts"]["m3_site_survey_summary"], "现场踏勘正式文字")
        self.assertEqual(body["text_completed_count"], 9)
        self.assertEqual(body["image_count"], 3)
        self.assertEqual(body["image_summary"]["image:m3_basic"], 2)
        self.assertEqual(body["image_summary"]["image:m3_site_survey"], 1)

        get_response = self.client.get(f"/api/projects/{self.project_id}/m3-materials")
        self.assertEqual(get_response.status_code, 200)
        saved = get_response.json()
        self.assertEqual(saved["texts"], body["texts"])
        self.assertEqual(saved["image_count"], 3)
        for image in saved["images"]:
            self.assertTrue(Path(image["stored_path"]).exists())

    def test_m3_materials_rejects_mismatched_files_and_purposes(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("files", ("basic.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("图片文件数量和用途数量必须一致", response.text)

    def test_m3_materials_rejects_invalid_purpose(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("purposes", (None, "bad_purpose")),
                ("files", ("basic.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("非法图片用途", response.text)

    def test_m3_materials_rejects_damaged_image(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("purposes", (None, "image:m3_basic")),
                ("files", ("bad.png", b"not an image", "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("图片文件无效或已损坏", response.text)


if __name__ == "__main__":
    unittest.main()
