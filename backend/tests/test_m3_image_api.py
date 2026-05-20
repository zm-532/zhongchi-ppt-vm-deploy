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


class M3ImageApiTest(unittest.TestCase):
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

    def test_m3_image_render_accepts_valid_upload(self):
        response = self.client.post(
            "/api/test/m3-image-render",
            data={
                "project_name": "M3图片接口测试",
                "purposes": "project_scope_map",
            },
            files=[("files", ("scope.png", _png_bytes(), "image/png"))],
        )

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertIn("/api/test/m3-image-render/download/", body["download_url"])
        self.assertTrue(Path(body["pptx_path"]).exists())

    def test_m3_image_render_rejects_invalid_purpose(self):
        response = self.client.post(
            "/api/test/m3-image-render",
            data={
                "project_name": "M3图片非法用途",
                "purposes": "bad_purpose",
            },
            files=[("files", ("scope.png", _png_bytes(), "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("非法图片用途", response.text)

    def test_m3_image_render_rejects_corrupt_image(self):
        response = self.client.post(
            "/api/test/m3-image-render",
            data={
                "project_name": "M3图片损坏文件",
                "purposes": "project_scope_map",
            },
            files=[("files", ("scope.png", b"not-an-image", "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("图片文件无效", response.text)


if __name__ == "__main__":
    unittest.main()
