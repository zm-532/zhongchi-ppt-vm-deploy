import importlib
import os
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from pptx import Presentation


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, text in entries.items():
            archive.writestr(name, text)
    return buffer.getvalue()


def _docx_bytes(text: str) -> bytes:
    return _zip_bytes({"word/document.xml": f"<w:document><w:body><w:t>{text}</w:t></w:body></w:document>"})


def _pptx_bytes(text: str) -> bytes:
    return _zip_bytes({"ppt/slides/slide1.xml": f"<p:sld><a:t>{text}</a:t></p:sld>"})


def _xlsx_bytes(text: str) -> bytes:
    return _zip_bytes({"xl/sharedStrings.xml": f"<sst><si><t>{text}</t></si></sst>"})


class BackendApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["ZHONGCHI_DATA_DIR"] = self.temp_dir.name

        from fastapi.testclient import TestClient

        app_module = importlib.import_module("app.main")
        self.client = TestClient(app_module.app)

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("ZHONGCHI_DATA_DIR", None)

    def test_project_create_list_and_detail(self):
        response = self.client.post(
            "/api/projects",
            json={
                "project_name": "某城市轨道交通声屏障改造项目",
                "project_location": "南京",
                "owner_unit": "某建设单位",
                "product_line": "轨交既有线改造",
            },
        )

        self.assertEqual(response.status_code, 201)
        project = response.json()
        self.assertEqual(project["project_name"], "某城市轨道交通声屏障改造项目")
        self.assertEqual(project["task_status"], "待生成")
        self.assertEqual([module["module_id"] for module in project["modules"]], ["M1", "M2", "M5", "M6"])

        list_response = self.client.get("/api/projects")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        detail_response = self.client.get(f"/api/projects/{project['project_id']}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["project_id"], project["project_id"])

    def test_upload_records_file_against_allowed_module(self):
        project_id = self.client.post("/api/projects", json={"project_name": "上传测试项目"}).json()["project_id"]

        response = self.client.post(
            f"/api/projects/{project_id}/modules/M1/files",
            files={"file": ("m1.pdf", b"M1 material", "application/pdf")},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["module_id"], "M1")
        self.assertEqual(payload["filename"], "m1.pdf")

        detail = self.client.get(f"/api/projects/{project_id}").json()
        m1 = next(module for module in detail["modules"] if module["module_id"] == "M1")
        self.assertEqual(m1["status"], "uploaded")
        self.assertEqual(m1["uploaded_file_ids"], [payload["file_id"]])

    def test_unified_upload_accepts_multiple_files_without_module_id(self):
        project_id = self.client.post("/api/projects", json={"project_name": "统一上传测试项目"}).json()["project_id"]

        response = self.client.post(
            f"/api/projects/{project_id}/files",
            files=[
                ("files", ("项目简介.pdf", b"metro project brief", "application/pdf")),
                ("files", ("案例材料.docx", b"case material", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ],
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertTrue(all(item["module_id"] is None for item in payload))
        self.assertTrue(all(item["assigned_modules"] == [] for item in payload))
        self.assertTrue(all(item["parse_status"] == "pending" for item in payload))

    def test_upload_rejects_disallowed_module(self):
        project_id = self.client.post("/api/projects", json={"project_name": "模块校验项目"}).json()["project_id"]

        response = self.client.post(
            f"/api/projects/{project_id}/modules/M3/files",
            files={"file": ("m3.pdf", b"M3 material", "application/pdf")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("module_id", response.json()["detail"])

    def test_analyze_classification_review_and_generate_use_confirmed_selection(self):
        project_id = self.client.post(
            "/api/projects",
            json={
                "project_name": "南京地铁声屏障项目",
                "project_location": "南京",
                "owner_unit": "某建设单位",
                "product_line": "轨道交通声屏障",
            },
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[
                ("files", ("南京地铁项目简介.pdf", b"metro line noise barrier", "application/pdf")),
                ("files", ("南昌轨道交通案例.docx", b"case rail transit", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
            ],
        )

        analyze_response = self.client.post(f"/api/projects/{project_id}/analyze")
        self.assertEqual(analyze_response.status_code, 200)
        classification = analyze_response.json()
        self.assertEqual(classification["detected_project_type"], "metro")
        self.assertEqual(classification["classification_status"], "analyzed")
        self.assertEqual(classification["template_selection"]["M1_M2"]["template_key"], "metro")
        self.assertEqual(classification["template_selection"]["M1_M2"]["template_filename"], "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx")
        self.assertNotIn("template_path", classification["template_selection"]["M1_M2"])
        self.assertEqual(classification["template_selection"]["M6"]["template_key"], "enterprise")
        self.assertIn("recommended_cases", classification["case_selection"])

        get_response = self.client.get(f"/api/projects/{project_id}/classification")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["detected_project_type"], "metro")

        review_response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={
                "confirmed_project_type": "metro",
                "template_selection": classification["template_selection"],
                "confirmed_case_id": 1,
                "notes": "确认地铁模板和推荐案例",
            },
        )
        self.assertEqual(review_response.status_code, 200)
        reviewed = review_response.json()
        self.assertEqual(reviewed["classification_status"], "reviewed")
        self.assertEqual(reviewed["confirmed_project_type"], "metro")
        self.assertEqual(reviewed["case_selection"]["confirmed_case_id"], 1)

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202)
        generated = generate_response.json()
        self.assertEqual(generated["task_status"], "完成")
        self.assertEqual([module["module_id"] for module in generated["modules"]], ["M1", "M2", "M5", "M6"])
        self.assertTrue(all(module["module_id"] not in {"M3", "M4"} for module in generated["modules"]))

        detail = self.client.get(f"/api/projects/{project_id}").json()
        self.assertEqual(detail["confirmed_project_type"], "metro")
        self.assertTrue(Path(detail["final_ppt_path"]).exists())

    def test_generate_omits_m5_when_review_confirms_no_case(self):
        project_id = self.client.post(
            "/api/projects",
            json={
                "project_name": "不选择案例项目",
                "project_location": "南京",
                "product_line": "轨道交通声屏障",
            },
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("南京地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        classification = self.client.post(f"/api/projects/{project_id}/analyze").json()

        review_response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={
                "confirmed_project_type": "metro",
                "template_selection": classification["template_selection"],
                "confirmed_case_id": None,
                "notes": "本次不选择 M5 案例",
            },
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertIsNone(review_response.json()["case_selection"]["confirmed_case_id"])

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202)
        generated = generate_response.json()
        m5_module = next(module for module in generated["modules"] if module["module_id"] == "M5")
        self.assertEqual(m5_module["status"], "skipped")
        self.assertEqual(m5_module["chapter_ppt_path"], "")

        detail = self.client.get(f"/api/projects/{project_id}").json()
        final_path = Path(detail["final_ppt_path"])
        self.assertTrue(final_path.exists())
        self.assertIn("M1_M2_M6", final_path.name)
        self.assertNotIn("M5", final_path.name)
        self.assertFalse((final_path.parent / "chapters" / "M5_同类型案例匹配.pptx").exists())
        self.assertEqual(len(Presentation(str(final_path)).slides), 20)

    def test_generate_keeps_string_case_id_and_renders_m5(self):
        project_id = self.client.post(
            "/api/projects",
            json={
                "project_name": "字符串案例项目",
                "project_location": "南京",
                "product_line": "轨道交通声屏障",
            },
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("南京地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        classification = self.client.post(f"/api/projects/{project_id}/analyze").json()

        review_response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={
                "confirmed_project_type": "metro",
                "template_selection": classification["template_selection"],
                "confirmed_case_id": "sr_case_abc123",
                "notes": "选择真实案例库字符串 ID",
            },
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["case_selection"]["confirmed_case_id"], "sr_case_abc123")

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202)
        generated = generate_response.json()
        m5_module = next(module for module in generated["modules"] if module["module_id"] == "M5")
        self.assertEqual(m5_module["status"], "rendered")
        self.assertTrue(m5_module["chapter_ppt_path"])

        detail = self.client.get(f"/api/projects/{project_id}").json()
        final_path = Path(detail["final_ppt_path"])
        self.assertTrue(final_path.exists())
        self.assertIn("M1_M2_M5_M6", final_path.name)

    def test_project_type_detection_distinguishes_four_fixed_m1_m2_templates(self):
        cases = [
            (
                {
                    "project_name": "沪宁高速公路声屏障改造项目",
                    "product_line": "公路声屏障",
                },
                [("files", ("高速公路降噪需求.pdf", "高速 公路 全封闭 声屏障 改造".encode(), "application/pdf"))],
                "highway",
                "公路全封闭声屏障（M1_&_M2）.pptx",
            ),
            (
                {
                    "project_name": "京沪铁路声屏障新建工程",
                    "product_line": "铁路声屏障",
                },
                [("files", ("铁路技术标准.pdf", "铁路 干线 声屏障 技术标准".encode(), "application/pdf"))],
                "railway",
                "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx",
            ),
            (
                {
                    "project_name": "南京地铁三号线声屏障项目",
                    "product_line": "地铁声屏障",
                },
                [("files", ("地铁项目简介.pdf", "地铁 车站 区间 声屏障".encode(), "application/pdf"))],
                "metro",
                "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx",
            ),
            (
                {
                    "project_name": "既有轨道交通线路声屏障改造工程",
                    "product_line": "轨交既有线改造",
                },
                [("files", ("既有线夜间施工窗口.pdf", "既有线 轨道交通 改造 夜间 施工窗口".encode(), "application/pdf"))],
                "existing_rail_transit",
                "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx",
            ),
        ]

        for project_payload, files, expected_type, expected_template in cases:
            with self.subTest(expected_type=expected_type):
                project_id = self.client.post("/api/projects", json=project_payload).json()["project_id"]
                self.client.post(f"/api/projects/{project_id}/files", files=files)

                classification = self.client.post(f"/api/projects/{project_id}/analyze").json()

                self.assertEqual(classification["detected_project_type"], expected_type)
                self.assertEqual(classification["template_selection"]["M1_M2"]["template_key"], expected_type)
                self.assertEqual(classification["template_selection"]["M1_M2"]["template_filename"], expected_template)
                self.assertGreater(classification["confidence"], 0.5)
                self.assertTrue(classification["matched_keywords"])

    def test_real_pdf_extracts_rail_transit_keyword_and_returns_evidence(self):
        source_pdf = Path(r"D:\中驰股份\06中海寰宇\20.噪声污染意见.pdf")
        if not source_pdf.exists():
            self.skipTest("真实 PDF 样例不存在")
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "M1/M2真实PDF识别测试", "product_line": ""},
        ).json()["project_id"]

        with source_pdf.open("rb") as file:
            upload_response = self.client.post(
                f"/api/projects/{project_id}/files",
                files=[("files", (source_pdf.name, file.read(), "application/pdf"))],
            )
        self.assertEqual(upload_response.status_code, 201)

        classification = self.client.post(f"/api/projects/{project_id}/analyze").json()

        self.assertEqual(classification["detected_project_type"], "metro")
        self.assertIn("轨道交通", classification["matched_keywords"])
        self.assertGreater(classification["confidence"], 0.5)
        self.assertTrue(any("轨道交通" in item["snippet"] for item in classification["detection_evidence"]))
        self.assertEqual(classification["template_selection"]["M1_M2"]["template_key"], "metro")

    def test_review_rejects_project_type_outside_fixed_enum(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "南京地铁声屏障项目", "product_line": "地铁声屏障"},
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        self.client.post(f"/api/projects/{project_id}/analyze")

        response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={"confirmed_project_type": "airport"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("project_type", response.json()["detail"])

    def test_review_override_reselects_m1_m2_template_when_selection_is_not_supplied(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "南京地铁声屏障项目", "product_line": "地铁声屏障"},
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        self.client.post(f"/api/projects/{project_id}/analyze")

        response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={"confirmed_project_type": "railway"},
        )

        self.assertEqual(response.status_code, 200)
        reviewed = response.json()
        self.assertEqual(reviewed["confirmed_project_type"], "railway")
        self.assertEqual(reviewed["template_selection"]["M1_M2"]["template_key"], "railway")
        self.assertEqual(reviewed["template_selection"]["M1_M2"]["template_filename"], "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx")

    def test_review_override_keeps_m1_m2_template_consistent_with_confirmed_type(self):
        project_id = self.client.post(
            "/api/projects",
            json={"project_name": "南京地铁声屏障项目", "product_line": "地铁声屏障"},
        ).json()["project_id"]
        self.client.post(
            f"/api/projects/{project_id}/files",
            files=[("files", ("地铁项目简介.pdf", b"metro line noise barrier", "application/pdf"))],
        )
        classification = self.client.post(f"/api/projects/{project_id}/analyze").json()

        response = self.client.post(
            f"/api/projects/{project_id}/classification/review",
            json={
                "confirmed_project_type": "highway",
                "template_selection": classification["template_selection"],
            },
        )

        self.assertEqual(response.status_code, 200)
        reviewed = response.json()
        self.assertEqual(reviewed["confirmed_project_type"], "highway")
        self.assertEqual(reviewed["template_selection"]["M1_M2"]["template_key"], "highway")
        self.assertEqual(reviewed["template_selection"]["M1_M2"]["template_filename"], "公路全封闭声屏障（M1_&_M2）.pptx")

    def test_analyze_extracts_office_text_and_classifies_document_roles(self):
        project_id = self.client.post(
            "/api/projects",
            json={
                "project_name": "北京高速声屏障项目",
                "project_location": "北京",
                "product_line": "公路声屏障",
            },
        ).json()["project_id"]

        upload_response = self.client.post(
            f"/api/projects/{project_id}/files",
            files=[
                ("files", ("技术标书.docx", _docx_bytes("招标文件 技术标准 高速 公路 声屏障"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ("files", ("现场调研表.xlsx", _xlsx_bytes("现场调研 痛点 施工窗口 降噪需求"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
                ("files", ("企业资质介绍.pptx", _pptx_bytes("企业介绍 CNAS 专利 荣誉 产能"), "application/vnd.openxmlformats-officedocument.presentationml.presentation")),
                ("files", ("总平面图.png", b"\x89PNG\r\n\x1a\n", "image/png")),
            ],
        )
        self.assertEqual(upload_response.status_code, 201)

        analyze_response = self.client.post(f"/api/projects/{project_id}/analyze")
        self.assertEqual(analyze_response.status_code, 200)
        files_by_name = {item["filename"]: item for item in analyze_response.json()["files"]}

        self.assertEqual(files_by_name["技术标书.docx"]["document_role"], "tender")
        self.assertEqual(files_by_name["技术标书.docx"]["assigned_modules"], ["M1", "M2", "M5"])
        self.assertEqual(files_by_name["技术标书.docx"]["parse_status"], "parsed")
        self.assertTrue(Path(files_by_name["技术标书.docx"]["parsed_text_path"]).exists())

        self.assertEqual(files_by_name["现场调研表.xlsx"]["document_role"], "survey")
        self.assertEqual(files_by_name["现场调研表.xlsx"]["assigned_modules"], ["M2", "M5"])

        self.assertEqual(files_by_name["企业资质介绍.pptx"]["document_role"], "enterprise_material")
        self.assertEqual(files_by_name["企业资质介绍.pptx"]["assigned_modules"], ["M6"])

        self.assertEqual(files_by_name["总平面图.png"]["document_role"], "drawing")
        self.assertEqual(files_by_name["总平面图.png"]["parse_status"], "pending_enhancement")

    def test_task_generate_and_review_flow_uses_mock_statuses(self):
        project_id = self.client.post("/api/projects", json={"project_name": "生成状态项目"}).json()["project_id"]

        generate_response = self.client.post(f"/api/projects/{project_id}/generate")
        self.assertEqual(generate_response.status_code, 202)
        self.assertEqual(generate_response.json()["task_status"], "待确认")

        task_response = self.client.get(f"/api/projects/{project_id}/task")
        self.assertEqual(task_response.status_code, 200)
        task = task_response.json()
        self.assertEqual(task["task_status"], "待确认")
        self.assertEqual({module["status"] for module in task["modules"]}, {"outlined"})
        self.assertEqual(
            task["status_history"],
            ["待生成", "模块解析中", "素材匹配中", "章节生成中", "待确认"],
        )
        for module in task["modules"]:
            self.assertEqual(module["status_history"], ["pending", "uploaded", "parsed", "matched", "outlined"])

        review_response = self.client.post(
            f"/api/projects/{project_id}/review",
            json={"approved": True, "notes": "确认使用 Mock 大纲"},
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertEqual(review_response.json()["task_status"], "完成")
        self.assertEqual(
            review_response.json()["status_history"],
            ["待生成", "模块解析中", "素材匹配中", "章节生成中", "待确认", "章节渲染中", "合并中", "完成"],
        )

    def test_end_to_end_generate_review_and_download_final_pptx(self):
        project_id = self.client.post(
            "/api/projects",
            json={
                "project_name": "端到端验收项目",
                "project_location": "南京",
                "owner_unit": "某建设单位",
                "product_line": "轨交既有线改造",
            },
        ).json()["project_id"]

        for module_id in ["M1", "M2", "M5", "M6"]:
            upload_response = self.client.post(
                f"/api/projects/{project_id}/modules/{module_id}/files",
                files={"file": (f"{module_id}.pdf", f"{module_id} material".encode(), "application/pdf")},
            )
            self.assertEqual(upload_response.status_code, 201)

        self.assertEqual(self.client.post(f"/api/projects/{project_id}/generate").status_code, 202)
        review_response = self.client.post(
            f"/api/projects/{project_id}/review",
            json={"approved": True, "notes": "端到端验收确认"},
        )

        self.assertEqual(review_response.status_code, 200)
        reviewed = review_response.json()
        self.assertEqual(reviewed["task_status"], "完成")
        self.assertEqual(reviewed["status_history"][-3:], ["章节渲染中", "合并中", "完成"])
        modules_by_id = {module["module_id"]: module for module in reviewed["modules"]}
        self.assertEqual(modules_by_id["M5"]["status"], "skipped")
        self.assertEqual(modules_by_id["M5"]["chapter_ppt_path"], "")
        self.assertTrue(all(module["status"] == "rendered" for module_id, module in modules_by_id.items() if module_id != "M5"))

        detail = self.client.get(f"/api/projects/{project_id}").json()
        final_path = Path(detail["final_ppt_path"])
        self.assertTrue(final_path.exists())
        self.assertIn("M1_M2_M6", final_path.name)
        self.assertEqual(len(Presentation(str(final_path)).slides), 25)

        download_response = self.client.get(f"/api/projects/{project_id}/download")
        self.assertEqual(download_response.status_code, 200)
        self.assertTrue(download_response.content.startswith(b"PK"))

    def test_review_failure_marks_project_and_modules_failed(self):
        project_id = self.client.post("/api/projects", json={"project_name": "失败路径项目"}).json()["project_id"]
        self.assertEqual(self.client.post(f"/api/projects/{project_id}/generate").status_code, 202)

        with patch("app.storage.render_project_ppt", side_effect=RuntimeError("render failed")):
            review_response = self.client.post(
                f"/api/projects/{project_id}/review",
                json={"approved": True, "notes": "触发失败路径"},
            )

        self.assertEqual(review_response.status_code, 200)
        payload = review_response.json()
        self.assertEqual(payload["task_status"], "失败")
        self.assertTrue(all(module["status"] == "failed" for module in payload["modules"]))
        self.assertTrue(all(module["status_history"][-1] == "failed" for module in payload["modules"]))

    def test_assets_are_filtered_by_module(self):
        response = self.client.get("/api/assets", params={"module_id": "M5"})

        self.assertEqual(response.status_code, 200)
        assets = response.json()
        self.assertGreaterEqual(len(assets), 1)
        self.assertTrue(all(asset["module_id"] == "M5" for asset in assets))

    def test_cors_allows_frontend_dev_server(self):
        response = self.client.options(
            "/api/projects",
            headers={
                "Origin": "http://127.0.0.1:3001",
                "Access-Control-Request-Method": "POST",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://127.0.0.1:3001")


if __name__ == "__main__":
    unittest.main()
