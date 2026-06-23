import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


def _mock_job_response(job_id: str = "test-job-123") -> dict:
    return {"code": 0, "data": {"jobId": job_id}}


def _mock_poll_response(state: str, result_url: str = "https://result.example.com/output.jsonl", error_msg: str = "") -> dict:
    data = {"state": state}
    if state == "done":
        data["resultUrl"] = {"jsonUrl": result_url}
    if state == "failed":
        data["errorMsg"] = error_msg
    return {"code": 0, "data": data}


def _mock_jsonl_response(records: list[dict]) -> str:
    return "\n".join(json.dumps(r) for r in records)


class PaddleOcrApiTest(unittest.TestCase):
    """Tests for PaddleOCR API integration in document_analysis."""

    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "test_tmp"
        test_tmp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name
        # Enable PaddleOCR
        os.environ["ZHONGCHI_IMAGE_OCR_ENABLED"] = "true"
        os.environ["ZHONGCHI_IMAGE_OCR_ENGINE"] = "paddleocr_api"
        os.environ["ZHONGCHI_PADDLEOCR_API_URL"] = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
        os.environ["ZHONGCHI_PADDLEOCR_API_KEY"] = "test-token"
        os.environ["ZHONGCHI_PADDLEOCR_MODEL"] = "PaddleOCR-VL-1.5"
        os.environ["ZHONGCHI_PADDLEOCR_TIMEOUT_SECONDS"] = "30"
        os.environ["ZHONGCHI_PADDLEOCR_POLL_INTERVAL_SECONDS"] = "1"
        os.environ["ZHONGCHI_PADDLEOCR_MAX_WAIT_SECONDS"] = "10"

        import importlib
        import app.main
        importlib.reload(app.main)
        self.client = TestClient(app.main.app)

    def tearDown(self):
        self.temp_dir.cleanup()
        for key in [
            "ZHONGCHI_IMAGE_OCR_ENABLED",
            "ZHONGCHI_IMAGE_OCR_ENGINE",
            "ZHONGCHI_PADDLEOCR_API_URL",
            "ZHONGCHI_PADDLEOCR_API_KEY",
            "ZHONGCHI_PADDLEOCR_MODEL",
            "ZHONGCHI_PADDLEOCR_TIMEOUT_SECONDS",
            "ZHONGCHI_PADDLEOCR_POLL_INTERVAL_SECONDS",
            "ZHONGCHI_PADDLEOCR_MAX_WAIT_SECONDS",
        ]:
            os.environ.pop(key, None)

    def test_analyze_project_with_image_calls_ocr_and_returns_parsed(self):
        """OCR 成功且有文本返回 parsed。"""
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "图片OCR测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        # PNG with minimal header
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            # 1st call: create job → pending
            # 2nd call: poll → running
            # 3rd call: poll → done + jsonUrl
            # 4th call: download jsonl

            create_resp = MagicMock()
            create_resp.status_code = 200
            create_resp.json.return_value = _mock_job_response("job-abc")

            poll_pending = MagicMock()
            poll_pending.status_code = 200
            poll_pending.json.return_value = _mock_poll_response("pending")

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_response("done", "https://result.example.com/out.jsonl")

            jsonl_resp = MagicMock()
            jsonl_resp.status_code = 200
            jsonl_resp.text = _mock_jsonl_response([
                {"result": {"layoutParsingResults": [{"markdown": {"text": "南京地铁3号线声屏障"}}]}},
                {"result": {"layoutParsingResults": [{"markdown": {"text": "既有线改造工程"}}]}},
            ])

            mock_instance.post.return_value = create_resp
            mock_instance.get.side_effect = [poll_pending, poll_done, jsonl_resp]

            upload_resp = self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("总平面图.png", image_bytes, "image/png"))],
            )
            self.assertEqual(upload_resp.status_code, 201)

            # Patch time.sleep to avoid actual waiting
            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        png_file = next(f for f in classification["files"] if f["filename"] == "总平面图.png")

        self.assertEqual(png_file["parse_status"], "parsed")
        self.assertEqual(png_file["document_role"], "drawing")
        self.assertEqual(png_file["error_message"], "")
        # Verify actual OCR text was written to parsed_text_path
        if png_file.get("parsed_text_path"):
            text_content = Path(png_file["parsed_text_path"]).read_text(encoding="utf-8")
            self.assertIn("南京地铁", text_content)
            self.assertIn("既有线改造", text_content)

    def test_analyze_project_with_image_returns_pending_ocr_when_no_text(self):
        """OCR 成功但无文本返回 pending_ocr。"""
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "空图片OCR测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            create_resp = MagicMock()
            create_resp.status_code = 200
            create_resp.json.return_value = _mock_job_response("job-empty")

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_response("done", "https://result.example.com/empty.jsonl")

            jsonl_resp = MagicMock()
            jsonl_resp.status_code = 200
            jsonl_resp.text = _mock_jsonl_response([
                {"result": {"layoutParsingResults": [{"markdown": {"text": ""}}]}},
            ])

            mock_instance.post.return_value = create_resp
            mock_instance.get.side_effect = [poll_done, jsonl_resp]

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("空白图.png", image_bytes, "image/png"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        png_file = next(f for f in classification["files"] if f["filename"] == "空白图.png")
        self.assertEqual(png_file["parse_status"], "pending_ocr")
        self.assertIn("未提取到有效文本", png_file["error_message"])

    def test_analyze_project_with_image_returns_failed_on_job_error(self):
        """Job failed 返回 failed。"""
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "OCR失败测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            create_resp = MagicMock()
            create_resp.status_code = 200
            create_resp.json.return_value = _mock_job_response("job-fail")

            poll_failed = MagicMock()
            poll_failed.status_code = 200
            poll_failed.json.return_value = _mock_poll_response("failed", error_msg="Model inference error")

            mock_instance.post.return_value = create_resp
            mock_instance.get.return_value = poll_failed

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("损坏图片.png", image_bytes, "image/png"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        png_file = next(f for f in classification["files"] if f["filename"] == "损坏图片.png")
        self.assertEqual(png_file["parse_status"], "failed")
        self.assertIn("Model inference error", png_file["error_message"])

    def test_analyze_project_with_image_returns_failed_on_poll_timeout(self):
        """轮询超时返回 failed。"""
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "轮询超时测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            create_resp = MagicMock()
            create_resp.status_code = 200
            create_resp.json.return_value = _mock_job_response("job-timeout")

            poll_running = MagicMock()
            poll_running.status_code = 200
            poll_running.json.return_value = _mock_poll_response("running")

            mock_instance.post.return_value = create_resp
            mock_instance.get.return_value = poll_running

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("大图片.png", image_bytes, "image/png"))],
            )

            # Patch time.sleep to 0 so we iterate fast but max_wait=10 with poll_interval=1 means ~10 iterations
            with patch("time.sleep", lambda s: None):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        png_file = next(f for f in classification["files"] if f["filename"] == "大图片.png")
        self.assertEqual(png_file["parse_status"], "failed")
        self.assertIn("轮询超时", png_file["error_message"])

    def test_analyze_project_with_image_returns_pending_enhancement_when_not_configured(self):
        """API 未配置返回 pending_enhancement。"""
        # Unset OCR env vars
        for key in ["ZHONGCHI_IMAGE_OCR_ENABLED", "ZHONGCHI_IMAGE_OCR_ENGINE"]:
            os.environ.pop(key, None)

        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "OCR未配置测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("总平面图.png", image_bytes, "image/png"))],
        )

        analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        png_file = next(f for f in classification["files"] if f["filename"] == "总平面图.png")
        self.assertEqual(png_file["parse_status"], "pending_enhancement")
        self.assertIn("未启用", png_file["error_message"])

    def test_document_parse_test_with_image_uses_analyze_document(self):
        """document-parse-test 中 .png/.jpg/.jpeg 走 analyze_document 而非提前返回。"""
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            create_resp = MagicMock()
            create_resp.status_code = 200
            create_resp.json.return_value = _mock_job_response("job-doc-test")

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_response("done", "https://result.example.com/doc.jsonl")

            jsonl_resp = MagicMock()
            jsonl_resp.status_code = 200
            jsonl_resp.text = _mock_jsonl_response([
                {"result": {"layoutParsingResults": [{"markdown": {"text": "技术标书 招标 项目"}}]}},
            ])

            mock_instance.post.return_value = create_resp
            mock_instance.get.side_effect = [poll_done, jsonl_resp]

            with patch("time.sleep"):
                response = self.client.post(
                    "/api/document-parse-test",
                    files=[("files", ("技术标书图片.png", image_bytes, "image/png"))],
                )

        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["suffix"], ".png")
        # Should NOT be pending_enhancement — should go through OCR
        self.assertIn(result["parse_status"], ["parsed", "pending_ocr", "failed"], f"Expected parsed/pending_ocr/failed, got {result['parse_status']}")
        self.assertIn("document_role", result)
        self.assertIn("error_message", result)


if __name__ == "__main__":
    unittest.main()