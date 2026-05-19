import hashlib
import json
import os
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


def _data_id_from_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()[:16]


def _make_zip_with_full_md(md_content: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("full.md", md_content.encode("utf-8"))
    return buf.getvalue()


def _mock_batch_response(
    batch_id: str = "batch-123",
    file_url: str = "https://mineru.net/upload/file-0",
    data_id: str | None = None,
    file_name: str | None = None,
) -> dict:
    files_entry: dict = {"name": file_name or "test.pdf"}
    if data_id is not None:
        files_entry["data_id"] = data_id
    return {
        "code": 0,
        "data": {
            "batch_id": batch_id,
            "file_urls": [file_url],
            "files": [files_entry],
        },
    }


def _mock_poll_result(
    state: str,
    full_zip_url: str = "",
    err_msg: str = "",
    data_id: str | None = None,
    file_name: str | None = None,
) -> dict:
    result_entry: dict = {"state": state}
    if data_id is not None:
        result_entry["data_id"] = data_id
    if file_name is not None:
        result_entry["file_name"] = file_name
    if state == "done":
        result_entry["full_zip_url"] = full_zip_url
    if state == "failed":
        result_entry["err_msg"] = err_msg
    return {
        "code": 0,
        "data": {
            "state": state,
            "extract_result": [result_entry],
        },
    }


class MineruPdfParseTest(unittest.TestCase):

    def setUp(self):
        test_tmp_root = Path(__file__).resolve().parents[1] / "test_tmp"
        test_tmp_root.mkdir(exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(dir=test_tmp_root)
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name
        os.environ["ZHONGCHI_PDF_PARSE_ENGINE"] = "mineru_api"
        os.environ["ZHONGCHI_MINERU_API_BASE_URL"] = "https://mineru.net/api/v4"
        os.environ["ZHONGCHI_MINERU_API_TOKEN"] = "test-mineru-token"
        os.environ["ZHONGCHI_MINERU_MODEL_VERSION"] = "vlm"
        os.environ["ZHONGCHI_MINERU_LANGUAGE"] = "ch"
        os.environ["ZHONGCHI_MINERU_IS_OCR"] = "true"
        os.environ["ZHONGCHI_MINERU_ENABLE_TABLE"] = "true"
        os.environ["ZHONGCHI_MINERU_ENABLE_FORMULA"] = "true"
        os.environ["ZHONGCHI_MINERU_TIMEOUT_SECONDS"] = "30"
        os.environ["ZHONGCHI_MINERU_POLL_INTERVAL_SECONDS"] = "1"
        os.environ["ZHONGCHI_MINERU_MAX_WAIT_SECONDS"] = "10"

        import importlib
        import app.main
        importlib.reload(app.main)
        self.client = TestClient(app.main.app)

    def tearDown(self):
        self.temp_dir.cleanup()
        for key in [
            "ZHONGCHI_PDF_PARSE_ENGINE",
            "ZHONGCHI_MINERU_API_BASE_URL",
            "ZHONGCHI_MINERU_API_TOKEN",
            "ZHONGCHI_MINERU_MODEL_VERSION",
            "ZHONGCHI_MINERU_LANGUAGE",
            "ZHONGCHI_MINERU_IS_OCR",
            "ZHONGCHI_MINERU_ENABLE_TABLE",
            "ZHONGCHI_MINERU_ENABLE_FORMULA",
            "ZHONGCHI_MINERU_TIMEOUT_SECONDS",
            "ZHONGCHI_MINERU_POLL_INTERVAL_SECONDS",
            "ZHONGCHI_MINERU_MAX_WAIT_SECONDS",
        ]:
            os.environ.pop(key, None)

    def test_mineru_success_returns_parsed(self):
        filename = "技术标准.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "MinerU成功测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test content" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                "batch-abc",
                "https://mineru.net/upload/file-0",
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_result(
                "done",
                full_zip_url="https://mineru.net/results/result.zip",
                file_name=filename,
            )

            zip_bytes = _make_zip_with_full_md(
                "南京地铁3号线声屏障既有线改造工程\n技术标准文件。"
            )
            zip_resp = MagicMock()
            zip_resp.status_code = 200
            zip_resp.content = zip_bytes

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.side_effect = [poll_done, zip_resp]

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "parsed")
        self.assertEqual(pdf_file["error_message"], "")
        self.assertEqual(pdf_file["document_role"], "tender")

    def test_mineru_full_md_empty_returns_pending_ocr(self):
        filename = "空白.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF空文本测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_result(
                "done", full_zip_url="https://mineru.net/out.zip", file_name=filename
            )

            zip_bytes = _make_zip_with_full_md("")
            zip_resp = MagicMock()
            zip_resp.status_code = 200
            zip_resp.content = zip_bytes

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.side_effect = [poll_done, zip_resp]

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "pending_ocr")
        self.assertIn("解析结果为空", pdf_file["error_message"])

    def test_mineru_batch_code_error_returns_failed(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF失败测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = {"code": 1001, "msg": "invalid token"}

            mock_instance.post.return_value = batch_resp

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("失效.pdf", pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == "失效.pdf")
        self.assertEqual(pdf_file["parse_status"], "failed")
        self.assertIn("code=1001", pdf_file["error_message"])

    def test_mineru_put_upload_fails_returns_failed(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF上传失败测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response()

            put_resp = MagicMock()
            put_resp.status_code = 403

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", ("无权限.pdf", pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == "无权限.pdf")
        self.assertEqual(pdf_file["parse_status"], "failed")
        self.assertIn("403", pdf_file["error_message"])

    def test_mineru_job_failed_returns_failed(self):
        filename = "损坏.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF任务失败测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_failed = MagicMock()
            poll_failed.status_code = 200
            poll_failed.json.return_value = _mock_poll_result(
                "failed", err_msg="文件格式不支持", file_name=filename
            )

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.return_value = poll_failed

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "failed")
        self.assertIn("文件格式不支持", pdf_file["error_message"])

    def test_mineru_poll_timeout_returns_failed(self):
        filename = "大文件.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF轮询超时测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_running = MagicMock()
            poll_running.status_code = 200
            poll_running.json.return_value = _mock_poll_result("running", file_name=filename)

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.return_value = poll_running

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep", lambda s: None):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "failed")
        self.assertIn("轮询超时", pdf_file["error_message"])

    def test_mineru_zip_missing_full_md_returns_failed(self):
        filename = "无内容.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF无fullmd测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_result(
                "done", full_zip_url="https://mineru.net/out.zip", file_name=filename
            )

            buf = BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("README.txt", b"no full.md here")
            zip_resp = MagicMock()
            zip_resp.status_code = 200
            zip_resp.content = buf.getvalue()

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.side_effect = [poll_done, zip_resp]

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "failed")
        self.assertIn("未找到 full.md", pdf_file["error_message"])

    def test_mineru_not_enabled_returns_pending_enhancement(self):
        os.environ.pop("ZHONGCHI_PDF_PARSE_ENGINE", None)

        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF未启用测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test" + b"\x00" * 100
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("未启用.pdf", pdf_bytes, "application/pdf"))],
        )

        analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == "未启用.pdf")
        self.assertEqual(pdf_file["parse_status"], "pending_enhancement")
        self.assertIn("未启用", pdf_file["error_message"])

    def test_document_parse_test_pdf_shows_mineru_status(self):
        filename = "技术标书.pdf"
        pdf_bytes = b"%PDF-1.4 test content" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                "batch-doc-test",
                "https://mineru.net/upload/f0",
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_result(
                "done", "https://mineru.net/out.zip", file_name=filename
            )

            zip_bytes = _make_zip_with_full_md("招标文件 技术标准 高速 公路 声屏障")
            zip_resp = MagicMock()
            zip_resp.status_code = 200
            zip_resp.content = zip_bytes

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.side_effect = [poll_done, zip_resp]

            with patch("time.sleep"):
                response = self.client.post(
                    "/api/document-parse-test",
                    files=[("files", (filename, pdf_bytes, "application/pdf"))],
                )

        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["suffix"], ".pdf")
        self.assertIn(result["parse_status"], ["parsed", "pending_ocr", "failed"])
        self.assertIn("document_role", result)
        self.assertIn("error_message", result)
        self.assertNotEqual(result["parse_status"], "pending_ocr")

    def test_analyze_project_writes_parsed_text_path_for_pdf(self):
        filename = "项目简介.pdf"
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "PDF写入路径测试", "product_line": "轨道交通声屏障"},
        ).json()["project_id"]

        pdf_bytes = b"%PDF-1.4 test content" + b"\x00" * 100

        with patch("httpx.Client") as mock_client_cls:
            mock_instance = MagicMock()
            mock_client_cls.return_value.__enter__.return_value = mock_instance

            batch_resp = MagicMock()
            batch_resp.status_code = 200
            batch_resp.json.return_value = _mock_batch_response(
                "batch-path",
                "https://mineru.net/upload/p0",
                data_id=_data_id_from_bytes(pdf_bytes),
                file_name=filename,
            )

            put_resp = MagicMock()
            put_resp.status_code = 201

            poll_done = MagicMock()
            poll_done.status_code = 200
            poll_done.json.return_value = _mock_poll_result(
                "done", "https://mineru.net/out.zip", file_name=filename
            )

            zip_bytes = _make_zip_with_full_md("南京地铁声屏障项目简介")
            zip_resp = MagicMock()
            zip_resp.status_code = 200
            zip_resp.content = zip_bytes

            mock_instance.post.return_value = batch_resp
            mock_instance.put.return_value = put_resp
            mock_instance.get.side_effect = [poll_done, zip_resp]

            self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (filename, pdf_bytes, "application/pdf"))],
            )

            with patch("time.sleep"):
                analyze_resp = self.client.post(f"/api/projects/{project_id}/analyze")

        self.assertEqual(analyze_resp.status_code, 200)
        classification = analyze_resp.json()
        pdf_file = next(f for f in classification["files"] if f["filename"] == filename)
        self.assertEqual(pdf_file["parse_status"], "parsed")
        self.assertTrue(pdf_file.get("parsed_text_path"))
        if pdf_file.get("parsed_text_path"):
            text = Path(pdf_file["parsed_text_path"]).read_text(encoding="utf-8")
            self.assertIn("南京地铁", text)


if __name__ == "__main__":
    unittest.main()