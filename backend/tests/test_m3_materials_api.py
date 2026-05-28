import importlib
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


def _table_bytes(name: str = "现场勘查情况.xlsx") -> bytes:
    template_root = Path(__file__).resolve().parents[2] / "ppt_engine" / "templates" / "solution_fixed_modules" / "M3表格模板"
    return (template_root / name).read_bytes()


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
                ("descriptions", (None, "项目基本情况-1：正式第一张\n项目基本情况-2：正式第二张\n现场踏勘-1：踏勘说明")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
                ("files", ("项目基本情况-2.png", _png_bytes((200, 80, 20)), "image/png")),
                ("files", ("现场踏勘-1.png", _png_bytes((40, 180, 80)), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["project_id"], self.project_id)
        self.assertEqual(body["texts"]["m3_basic_summary"], "正式第一张")
        self.assertEqual(body["texts"]["m3_site_survey_summary"], "踏勘说明")
        self.assertEqual(body["text_completed_count"], 2)
        self.assertEqual(body["image_count"], 3)
        self.assertEqual(body["image_summary"]["image:m3_basic"], 2)
        self.assertEqual(body["image_summary"]["image:m3_site_survey"], 1)
        self.assertEqual(body["images"][0]["description"], "正式第一张")
        self.assertEqual(body["images"][1]["description"], "正式第二张")
        self.assertEqual(body["page_texts"]["image:m3_basic"], ["正式第一张", "正式第二张"])

        get_response = self.client.get(f"/api/projects/{self.project_id}/m3-materials")
        self.assertEqual(get_response.status_code, 200)
        saved = get_response.json()
        self.assertEqual(saved["texts"], body["texts"])
        self.assertEqual(saved["page_texts"], body["page_texts"])
        self.assertEqual(saved["image_count"], 3)
        for image in saved["images"]:
            self.assertTrue(Path(image["stored_path"]).exists())

    def test_save_and_get_m3_materials_with_xlsx_table(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("files", ("现场勘查情况.xlsx", _table_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                ("files", ("现场勘察情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["image_count"], 1)
        self.assertEqual(body["table_count"], 1)
        self.assertEqual(body["table_summary"]["image:m3_investigation"], 1)
        self.assertEqual(body["tables"][0]["purpose"], "image:m3_investigation")
        self.assertEqual(body["tables"][0]["filename"], "现场勘查情况.xlsx")
        self.assertTrue(Path(body["tables"][0]["stored_path"]).exists())

        get_response = self.client.get(f"/api/projects/{self.project_id}/m3-materials")
        self.assertEqual(get_response.status_code, 200)
        saved = get_response.json()
        self.assertEqual(saved["table_count"], 1)
        self.assertEqual(saved["table_summary"]["image:m3_investigation"], 1)

    def test_m3_materials_rejects_xls_table(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("files", ("现场勘查情况.xls", b"old excel", "application/vnd.ms-excel")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("暂不支持旧版表格", response.text)

    def test_m3_materials_rejects_description_without_image(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("descriptions", (None, "项目基本情况-2：没有对应图片")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("描述没有对应图片", response.text)

    def test_m3_materials_rejects_unknown_filename_category(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("files", ("其他图片-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("无法识别图片分类", response.text)

    def test_m3_materials_rejects_purposes_manual_mode(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("purposes", (None, "image:m3_basic")),
                ("files", ("项目基本情况-1.png", _png_bytes(), "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("不再支持按模块手动上传", response.text)

    def test_m3_materials_rejects_damaged_image(self):
        response = self.client.post(
            f"/api/projects/{self.project_id}/m3-materials",
            files=[
                ("files", ("项目基本情况-1.png", b"not an image", "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("图片文件无效或已损坏", response.text)


if __name__ == "__main__":
    unittest.main()
