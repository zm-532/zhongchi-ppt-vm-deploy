import importlib
import os
import tempfile
import types
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image


class _BusySlide:
    def __init__(self, calls):
        self.calls = calls

    def Export(self, output_path, fmt, width, height):
        self.calls["export"] += 1
        if self.calls["export"] == 1:
            raise RuntimeError("(-2147418111, '被呼叫方拒绝接收呼叫。', None, None)")
        Path(output_path).write_bytes(_png_bytes())


class _BusySlides:
    Count = 1

    def __init__(self, calls):
        self.calls = calls

    def __call__(self, index):
        return _BusySlide(self.calls)


class _BusyPresentation:
    def __init__(self, calls):
        self.Slides = _BusySlides(calls)

    def Close(self):
        pass


class _BusyPresentations:
    def __init__(self, calls):
        self.calls = calls

    def Open(self, *args, **kwargs):
        return _BusyPresentation(self.calls)


class _BusyPowerPointApp:
    def __init__(self, calls):
        self.Presentations = _BusyPresentations(calls)

    def Quit(self):
        pass


def _png_bytes(color=(20, 120, 200)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (640, 360), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _mock_export_slides(pptx_path, preview_dir):
    """模拟 PowerPoint COM 导出：写入 3 张假 PNG。"""
    preview_dir.mkdir(parents=True, exist_ok=True)
    slide_files = []
    for i in range(1, 4):
        filename = f"slide-{i:03d}.png"
        (preview_dir / filename).write_bytes(_png_bytes())
        slide_files.append(filename)
    return 3, slide_files


def _mock_export_slides_5(pptx_path, preview_dir):
    """模拟 PowerPoint COM 导出：写入 5 张假 PNG。"""
    preview_dir.mkdir(parents=True, exist_ok=True)
    slide_files = []
    for i in range(1, 6):
        filename = f"slide-{i:03d}.png"
        (preview_dir / filename).write_bytes(_png_bytes((i * 40, 100, 200 - i * 20)))
        slide_files.append(filename)
    return 5, slide_files


class PptPreviewTest(unittest.TestCase):
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

    def _create_project_with_pptx(self):
        """创建项目并在 store 中设置 final_ppt_path。"""
        response = self.client.post("/api/projects", json={"project_name": "预览测试项目"})
        self.assertIn(response.status_code, (200, 201), response.text)
        project_id = response.json()["project_id"]

        output_dir = Path(self.temp_dir.name) / "outputs" / f"project_{project_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        pptx_path = output_dir / "final.pptx"
        pptx_path.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # minimal fake ZIP header

        from app.storage import get_store

        store = get_store()
        state = store.load()
        project = next(p for p in state["projects"] if p["project_id"] == project_id)
        project["final_ppt_path"] = str(pptx_path)
        store.save(state)

        return project_id, pptx_path

    # ── 测试 1: 项目不存在 ──

    def test_preview_project_not_found(self):
        response = self.client.post("/api/projects/99999/preview")
        self.assertEqual(response.status_code, 404)
        self.assertIn("项目不存在", response.text)

    # ── 测试 2: PPTX 未生成 ──

    def test_preview_pptx_not_generated(self):
        response = self.client.post("/api/projects", json={"project_name": "空项目"})
        project_id = response.json()["project_id"]

        response = self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(response.status_code, 400)
        self.assertIn("最终PPTX尚未生成", response.text)

    # ── 测试 3: 首次生成成功 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides)
    def test_preview_first_generation_success(self, mock_export):
        project_id, _ = self._create_project_with_pptx()

        response = self.client.post(f"/api/projects/{project_id}/preview")

        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["slide_count"], 3)
        self.assertEqual(len(body["slides"]), 3)
        self.assertEqual(body["slides"][0]["index"], 1)
        self.assertIn(f"/api/projects/{project_id}/preview/slides/slide-001.png", body["slides"][0]["image_url"])
        self.assertEqual(body["slides"][2]["index"], 3)
        self.assertIn("slide-003.png", body["slides"][2]["image_url"])
        mock_export.assert_called_once()

    # ── 测试 4: 缓存复用 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides)
    def test_preview_cache_reuse(self, mock_export):
        project_id, _ = self._create_project_with_pptx()

        # 第一次调用
        response1 = self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(mock_export.call_count, 1)

        # 第二次调用 -- 应复用缓存，不再调用导出
        response2 = self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_export.call_count, 1)  # 仍然只调用 1 次
        self.assertEqual(response1.json(), response2.json())

    # ── 测试 4b: PNG 文件被删除后缓存失效，重新生成 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides)
    def test_preview_cache_miss_when_png_deleted(self, mock_export):
        project_id, _ = self._create_project_with_pptx()

        # 第一次生成
        self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(mock_export.call_count, 1)

        # 删除其中一个 PNG 文件
        preview_dir = Path(self.temp_dir.name) / "outputs" / f"project_{project_id}" / "preview"
        (preview_dir / "slide-002.png").unlink()

        # 第二次调用 -- manifest 存在但 PNG 缺失，应重新生成
        self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(mock_export.call_count, 2)

    # ── 测试 5: PPTX 变化后重新生成 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides)
    def test_preview_pptx_changed_re_generates(self, mock_export):
        project_id, pptx_path = self._create_project_with_pptx()

        # 第一次生成
        response1 = self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(mock_export.call_count, 1)

        # 修改 PPTX 文件内容（改变大小）
        pptx_path.write_bytes(b"PK\x03\x04" + b"\x00" * 200)

        # 第二次调用 -- 应重新生成
        response2 = self.client.post(f"/api/projects/{project_id}/preview")
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(mock_export.call_count, 2)

    # ── 测试 6: slide 图片接口防路径穿越 ──

    def test_preview_slide_path_traversal_rejected(self):
        project_id, _ = self._create_project_with_pptx()

        payloads = [
            "..%2F..%2Fetc%2Fpasswd",
            "..\\..\\windows\\system32",
            "/etc/passwd",
            "slide-001.png/../../etc/passwd",
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.get(f"/api/projects/{project_id}/preview/slides/{payload}")
                self.assertIn(response.status_code, (400, 404), f"应拒绝路径穿越: {payload}")

    # ── 测试 7: PowerPoint COM 不可用时返回清晰错误 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=RuntimeError("预览生成需要安装 pywin32 (pip install pywin32)。仍可下载 PPTX。"))
    def test_preview_com_unavailable_returns_error(self, mock_export):
        project_id, _ = self._create_project_with_pptx()

        response = self.client.post(f"/api/projects/{project_id}/preview")

        self.assertEqual(response.status_code, 500)
        self.assertIn("pywin32", response.text)
        self.assertIn("仍可下载", response.text)

    def test_export_slides_retries_when_powerpoint_rejects_call(self):
        from app import ppt_preview

        project_id, pptx_path = self._create_project_with_pptx()
        preview_dir = Path(self.temp_dir.name) / "outputs" / f"project_{project_id}" / "preview_retry"
        calls = {"export": 0}

        class FakeClient:
            @staticmethod
            def DispatchEx(name):
                self.assertEqual(name, "PowerPoint.Application")
                return _BusyPowerPointApp(calls)

        fake_win32com = types.SimpleNamespace(client=FakeClient)

        with patch.object(ppt_preview.os, "name", "nt"), \
             patch.dict("sys.modules", {"win32com": fake_win32com, "win32com.client": FakeClient}), \
             patch.object(ppt_preview.time, "sleep", return_value=None):
            slide_count, slide_files = ppt_preview._export_slides_to_png(pptx_path, preview_dir)

        self.assertEqual(slide_count, 1)
        self.assertEqual(slide_files, ["slide-001.png"])
        self.assertEqual(calls["export"], 2)
        self.assertTrue((preview_dir / "slide-001.png").exists())

    # ── 附加测试: slide 图片接口正常返回 ──

    @patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides)
    def test_preview_slide_serves_png(self, mock_export):
        project_id, _ = self._create_project_with_pptx()

        # 先生成预览
        self.client.post(f"/api/projects/{project_id}/preview")

        # 获取第一页图片
        response = self.client.get(f"/api/projects/{project_id}/preview/slides/slide-001.png")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "image/png")

    # ── 附加测试: slide 图片不存在时返回 404 ──

    def test_preview_slide_not_found(self):
        project_id, _ = self._create_project_with_pptx()

        response = self.client.get(f"/api/projects/{project_id}/preview/slides/slide-999.png")
        self.assertEqual(response.status_code, 404)

    # ── 附加测试: 非 PNG 文件被拒绝 ──

    def test_preview_slide_rejects_non_png(self):
        project_id, _ = self._create_project_with_pptx()

        # 创建一个非 PNG 文件在 preview 目录中
        preview_dir = Path(self.temp_dir.name) / "outputs" / f"project_{project_id}" / "preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        (preview_dir / "malicious.exe").write_bytes(b"MZ\x00\x00")

        response = self.client.get(f"/api/projects/{project_id}/preview/slides/malicious.exe")
        self.assertEqual(response.status_code, 400)
        self.assertIn("PNG", response.text)

    # ── 附加测试: 下载接口不受预览功能影响 ──

    def test_download_still_works_after_preview(self):
        project_id, pptx_path = self._create_project_with_pptx()

        # 生成预览
        with patch("app.ppt_preview._export_slides_to_png", side_effect=_mock_export_slides):
            self.client.post(f"/api/projects/{project_id}/preview")

        # 下载仍可用
        response = self.client.get(f"/api/projects/{project_id}/download")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
