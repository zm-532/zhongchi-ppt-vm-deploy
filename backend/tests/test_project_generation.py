import importlib
import json
import os
import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image
from pptx import Presentation


def _png_bytes(color=(20, 120, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 360), color).save(buffer, format="PNG")
    return buffer.getvalue()


TEXTS = {
    "m3_basic_summary": "正式项目基本情况文字",
    "m3_line_summary": "正式项目线路图文字",
    "m3_sensitive_points_summary": "正式敏感点路段文字",
    "m3_quantity_summary": "正式工程量统计文字",
    "m3_structure_summary": "正式结构形式文字",
    "m3_site_survey_summary": "正式现场踏勘文字",
    "m3_investigation_summary": "正式现场勘察情况文字",
    "m3_risk_summary": "正式项目重难点分析文字",
    "m3_solution_summary": "正式重难点应对措施文字",
}


class ProjectGenerationM3MaterialsTest(unittest.TestCase):
    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "test_tmp"
        test_tmp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name
        os.environ["ZHONGCHI_PPT_MERGE_ENGINE"] = "python-pptx"

        from fastapi.testclient import TestClient

        app_module = importlib.import_module("app.main")
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("ZHONGCHI_DATA_DIR", None)
        os.environ.pop("ZHONGCHI_PPT_MERGE_ENGINE", None)

    def _review_project(self, project_id: int) -> None:
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("南京地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        classification = self.client.post(f"/api/projects/{project_id}/analyze").json()
        response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={
                "confirmed_project_type": "metro",
                "template_selection": classification["template_selection"],
                "confirmed_case_id": None,
                "m3_selection": "m3_template",
                "notes": "确认正式 M3 materials",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_generate_uses_saved_m3_materials_with_multi_image_expansion(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "M3正式生成项目", "project_location": "南京"},
        ).json()["project_id"]
        self._review_project(project_id)

        save_response = self.client.post(
            f"/api/projects/{project_id}/m3-materials",
            files=[
                ("texts", (None, json.dumps(TEXTS, ensure_ascii=False))),
                ("purposes", (None, "image:m3_basic")),
                ("purposes", (None, "image:m3_basic")),
                ("files", ("basic1.png", _png_bytes(), "image/png")),
                ("files", ("basic2.png", _png_bytes((200, 80, 20)), "image/png")),
            ],
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202, generate_response.text)

        detail = self.client.get(f"/api/projects/{project_id}").json()
        m3_module = next(module for module in detail["modules"] if module["module_id"] == "M3")
        m3_path = Path(m3_module["chapter_ppt_path"])
        self.assertTrue(m3_path.exists())

        m3_prs = Presentation(str(m3_path))
        self.assertEqual(len(m3_prs.slides), 10)
        m3_text = "\n".join(
            shape.text
            for slide in m3_prs.slides
            for shape in slide.shapes
            if hasattr(shape, "text") and shape.text
        )
        self.assertIn("正式现场踏勘文字", m3_text)
        self.assertIn("正式项目线路图文字", m3_text)
        self.assertNotIn("{{m3_", m3_text)
        self.assertNotIn("{{image:m3_basic}}", m3_text)

    def test_generate_without_m3_images_still_succeeds(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "M3无图正式生成项目", "project_location": "南京"},
        ).json()["project_id"]
        self._review_project(project_id)
        save_response = self.client.post(
            f"/api/projects/{project_id}/m3-materials",
            files=[("texts", (None, json.dumps(TEXTS, ensure_ascii=False)))],
        )
        self.assertEqual(save_response.status_code, 200, save_response.text)

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202, generate_response.text)
        detail = self.client.get(f"/api/projects/{project_id}").json()
        self.assertTrue(Path(detail["final_ppt_path"]).exists())


if __name__ == "__main__":
    unittest.main()
