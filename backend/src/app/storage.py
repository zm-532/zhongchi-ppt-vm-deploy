import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .case_matcher import (
    extract_project_tags,
    load_case_index,
    match_cases,
)
from .constants import (
    ALLOWED_MODULE_IDS,
    INITIAL_TASK_STATUS,
    M1_M2_TEMPLATE_FILENAMES,
    M5_TEMPLATE_FILENAME,
    M6_TEMPLATE_FILENAME,
    MODULE_NAMES,
    PROJECT_TYPES,
)
from .document_analysis import analyze_document
from .ppt_generation import render_project_ppt


def get_data_dir() -> Path:
    configured = os.environ.get("ZHONGCHI_DATA_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3] / "data"


def _module_results() -> list[dict[str, Any]]:
    return [
        {
            "module_id": module_id,
            "status": "pending",
            "status_history": ["pending"],
            "uploaded_file_ids": [],
            "matched_asset_ids": [],
            "outline": {},
            "chapter_ppt_path": "",
            "error_message": "",
        }
        for module_id in ALLOWED_MODULE_IDS
    ]


def _mock_assets() -> list[dict[str, Any]]:
    return [
        {"asset_id": 101, "module_id": "M1", "title": "行业政策与技术标准素材", "tags": ["行业背景", "技术标准"]},
        {"asset_id": 201, "module_id": "M2", "title": "现场挑战与客户痛点素材", "tags": ["现场挑战", "客户痛点"]},
        {"asset_id": 501, "module_id": "M5", "title": "同类型项目案例素材", "tags": ["案例匹配", "解决成效"]},
        {"asset_id": 601, "module_id": "M6", "title": "企业资质与荣誉素材", "tags": ["企业背书", "荣誉资质"]},
    ]


def _initial_state() -> dict[str, Any]:
    return {
        "counters": {"project_id": 1, "file_id": 1, "case_id": 1},
        "projects": [],
        "files": [],
        "assets": _mock_assets(),
        "cases": [
            {
                "case_id": 1,
                "title": "南昌轨道交通4号线声屏障工程",
                "module_id": "M5",
                "tags": ["轨道交通", "声屏障", "改造"],
            }
        ],
    }


class JsonStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_data_dir()
        self.db_path = self.data_dir / "mock_db.json"
        self.uploads_dir = self.data_dir / "uploads"

    def load(self) -> dict[str, Any]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            state = _initial_state()
            self.save(state)
            return state
        return json.loads(self.db_path.read_text(encoding="utf-8"))

    def save(self, state: dict[str, Any]) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def next_id(self, state: dict[str, Any], name: str) -> int:
        value = state["counters"][name]
        state["counters"][name] += 1
        return value

    def _set_project_status(self, project: dict[str, Any], status: str) -> None:
        project["task_status"] = status
        history = project.setdefault("status_history", [])
        if not history or history[-1] != status:
            history.append(status)

    def _set_module_status(self, module: dict[str, Any], status: str) -> None:
        module["status"] = status
        history = module.setdefault("status_history", [])
        if not history or history[-1] != status:
            history.append(status)

    def list_projects(self) -> list[dict[str, Any]]:
        return self.load()["projects"]

    def create_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        state = self.load()
        project = {
            **payload,
            "project_id": self.next_id(state, "project_id"),
            "task_status": INITIAL_TASK_STATUS,
            "status_history": [INITIAL_TASK_STATUS],
            "modules": _module_results(),
            "final_ppt_path": "",
            "detected_project_type": None,
            "confirmed_project_type": None,
            "classification_status": "pending",
            "template_selection": {},
            "case_selection": {},
        }
        state["projects"].append(project)
        self.save(state)
        return project

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        return next((project for project in state["projects"] if project["project_id"] == project_id), None)

    def add_file(self, project_id: int, module_id: str, filename: str, content_type: str, content: bytes) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None

        file_id = self.next_id(state, "file_id")
        safe_filename = Path(filename).name
        module_dir = self.uploads_dir / str(project_id) / module_id
        module_dir.mkdir(parents=True, exist_ok=True)
        stored_path = module_dir / f"{file_id}_{safe_filename}"
        stored_path.write_bytes(content)

        file_record = {
            "file_id": file_id,
            "project_id": project_id,
            "module_id": module_id,
            "filename": safe_filename,
            "content_type": content_type,
            "stored_path": str(stored_path),
            "document_role": "unknown",
            "assigned_modules": [module_id],
            "parse_status": "pending",
            "parsed_text_path": "",
            "error_message": "",
        }
        state["files"].append(file_record)

        module = next(item for item in project["modules"] if item["module_id"] == module_id)
        self._set_module_status(module, "uploaded")
        module["uploaded_file_ids"].append(file_id)

        self.save(state)
        return file_record

    def add_project_files(self, project_id: int, files: list[tuple[str, str, bytes]]) -> list[dict[str, Any]] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None

        project_dir = self.uploads_dir / str(project_id) / "unclassified"
        project_dir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []
        for filename, content_type, content in files:
            file_id = self.next_id(state, "file_id")
            safe_filename = Path(filename).name or "upload"
            stored_path = project_dir / f"{file_id}_{safe_filename}"
            stored_path.write_bytes(content)
            file_record = {
                "file_id": file_id,
                "project_id": project_id,
                "module_id": None,
                "filename": safe_filename,
                "content_type": content_type,
                "stored_path": str(stored_path),
                "document_role": "unknown",
                "assigned_modules": [],
                "parse_status": "pending",
                "parsed_text_path": "",
                "error_message": "",
            }
            state["files"].append(file_record)
            records.append(file_record)

        self._set_project_status(project, "待分析")
        self.save(state)
        return records

    def _detection_sources(self, project: dict[str, Any], files: list[dict[str, Any]]) -> list[tuple[str, str]]:
        sources = [
            ("项目名称", project.get("project_name", "")),
            ("项目所在地", project.get("project_location", "")),
            ("业主单位", project.get("owner_unit", "")),
            ("产品线", project.get("product_line", "")),
        ]
        for file_record in files:
            filename = file_record.get("filename", "")
            sources.append((f"文件名：{filename}", filename))
            parsed_text_path = file_record.get("parsed_text_path")
            source_path = parsed_text_path or file_record.get("stored_path")
            if source_path:
                try:
                    source_text = Path(source_path).read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    source_text = ""
                if source_text:
                    sources.append((f"解析文本：{filename}", source_text))
        return sources

    def _keyword_evidence(self, project_type: str, keyword: str, source: str, text: str) -> dict[str, str] | None:
        index = text.lower().find(keyword.lower())
        if index < 0:
            return None
        start = max(0, index - 32)
        end = min(len(text), index + len(keyword) + 32)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        snippet = f"{prefix}{text[start:end]}{suffix}"
        return {
            "project_type": project_type,
            "keyword": keyword,
            "source": source,
            "snippet": " ".join(snippet.split()),
        }

    def _detect_project_type(self, project: dict[str, Any], files: list[dict[str, Any]]) -> tuple[str, float, list[str], list[dict[str, str]]]:
        sources = self._detection_sources(project, files)
        text = " ".join(source_text for _, source_text in sources).lower()
        candidates = [
            ("existing_rail_transit", ["既有线", "改造", "夜间", "短窗口"]),
            ("metro", ["地铁", "metro", "轨道交通", "城市轨道", "昌平线", "轨交"]),
            ("highway", ["公路", "高速", "highway"]),
            ("railway", ["铁路", "railway"]),
        ]
        scores: list[tuple[int, str, list[str], list[dict[str, str]]]] = []
        for project_type, keywords in candidates:
            matched = [keyword for keyword in keywords if keyword.lower() in text]
            evidence: list[dict[str, str]] = []
            for keyword in matched:
                for source, source_text in sources:
                    item = self._keyword_evidence(project_type, keyword, source, source_text)
                    if item:
                        evidence.append(item)
                        break
            scores.append((len(matched), project_type, matched, evidence))
        score, project_type, matched_keywords, detection_evidence = max(scores, key=lambda item: item[0])
        if score == 0:
            return "metro", 0.35, [], []
        return project_type, min(0.95, 0.55 + score * 0.12), matched_keywords, detection_evidence

    def _template_selection(self, project_type: str) -> dict[str, Any]:
        template_filename = M1_M2_TEMPLATE_FILENAMES.get(project_type, M1_M2_TEMPLATE_FILENAMES["metro"])
        return {
            "M1_M2": {"template_key": project_type, "template_filename": template_filename},
            "M5": {"template_key": "case", "template_filename": M5_TEMPLATE_FILENAME},
            "M6": {"template_key": "enterprise", "template_filename": M6_TEMPLATE_FILENAME},
        }

    def _review_template_selection(self, confirmed_project_type: str, template_selection: dict[str, Any]) -> dict[str, Any]:
        reviewed_selection = deepcopy(template_selection) if template_selection else self._template_selection(confirmed_project_type)
        reviewed_selection["M1_M2"] = self._template_selection(confirmed_project_type)["M1_M2"]
        reviewed_selection.setdefault("M5", {"template_key": "case", "template_filename": M5_TEMPLATE_FILENAME})
        reviewed_selection.setdefault("M6", {"template_key": "enterprise", "template_filename": M6_TEMPLATE_FILENAME})
        return reviewed_selection

    def _recommended_cases(self, project_type: str, files: list[dict[str, Any]], project_tags: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """使用真实案例库匹配推荐案例"""
        # 加载案例索引
        case_index = load_case_index()

        if not case_index:
            return []

        # 如果没有传入项目标签，从文件解析提取
        if project_tags is None:
            # 从文件名和解析文本中提取标签
            filename_text = " ".join(file_record.get("filename", "") for file_record in files)
            parsed_texts = []
            for file_record in files:
                parsed_path = file_record.get("parsed_text_path")
                if parsed_path and Path(parsed_path).exists():
                    try:
                        text = Path(parsed_path).read_text(encoding="utf-8", errors="ignore")
                        parsed_texts.append(text)
                    except OSError:
                        pass
            combined_text = filename_text + " " + " ".join(parsed_texts)
            project_tags = extract_project_tags(combined_text, {
                "project_type": project_type,
            })
            # 确保项目类型被设置
            project_tags.setdefault("project_type", project_type)

        # 使用 case_matcher 进行匹配
        recommendations = match_cases(project_tags, case_index, top_n=3)

        return recommendations

    def analyze_project(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None

        self._set_project_status(project, "资料解析中")
        project_files = [file_record for file_record in state["files"] if file_record["project_id"] == project_id]
        parsed_dir = self.data_dir / "parsed_text" / str(project_id)
        parsed_dir.mkdir(parents=True, exist_ok=True)
        project_context = {
            "project_name": project.get("project_name", ""),
            "project_location": project.get("project_location", ""),
            "owner_unit": project.get("owner_unit", ""),
            "product_line": project.get("product_line", ""),
        }
        for file_record in project_files:
            analysis = analyze_document(
                filename=file_record["filename"],
                stored_path=file_record["stored_path"],
                project_context=project_context,
            )
            file_record["document_role"] = analysis.document_role
            file_record["assigned_modules"] = analysis.assigned_modules
            file_record["parse_status"] = analysis.parse_status
            file_record["error_message"] = analysis.error_message
            if analysis.extracted_text:
                parsed_text_path = parsed_dir / f"{file_record['file_id']}.txt"
                parsed_text_path.write_text(analysis.extracted_text, encoding="utf-8")
                file_record["parsed_text_path"] = str(parsed_text_path)
            else:
                file_record["parsed_text_path"] = ""

        self._set_project_status(project, "类型识别中")
        project_type, confidence, matched_keywords, detection_evidence = self._detect_project_type(project, project_files)

        # 提取项目标签用于案例匹配（综合项目基础信息、文件名和解析文本）
        combined_text_parts = [
            project.get("project_name", ""),
            project.get("project_location", ""),
            project.get("owner_unit", ""),
            project.get("product_line", ""),
        ]
        # 添加文件名
        for file_record in project_files:
            combined_text_parts.append(file_record.get("filename", ""))
            # 添加解析文本
            parsed_path = file_record.get("parsed_text_path")
            if parsed_path and Path(parsed_path).exists():
                try:
                    text = Path(parsed_path).read_text(encoding="utf-8", errors="ignore")
                    if text:
                        combined_text_parts.append(text[:5000])  # 限制每个文件文本长度
                except OSError:
                    pass

        combined_text = " ".join(combined_text_parts)
        project_tags = extract_project_tags(combined_text, {"project_type": project_type})
        project_tags["project_type"] = project_type

        self._set_project_status(project, "案例匹配中")
        template_selection = self._template_selection(project_type)

        # 执行案例匹配
        recommended_cases = self._recommended_cases(project_type, project_files, project_tags)

        # 构建案例选择结果，包含状态信息
        if not recommended_cases:
            # 判断无匹配原因
            case_index = load_case_index()
            if not case_index:
                case_status = "case_library_empty"
                case_message = "案例库为空，请先导入历史案例"
            else:
                case_status = "no_high_match"
                case_message = "未找到高匹配案例，请检查上传资料是否包含足够项目信息"
        else:
            case_status = "matched"
            case_message = f"找到 {len(recommended_cases)} 个相似案例"

        case_selection = {
            "recommended_cases": recommended_cases,
            "confirmed_case_id": None,
            "status": case_status,
            "message": case_message,
        }
        classification = {
            "project_id": project_id,
            "classification_status": "analyzed",
            "detected_project_type": project_type,
            "confirmed_project_type": project.get("confirmed_project_type"),
            "confidence": confidence,
            "matched_keywords": matched_keywords,
            "detection_evidence": detection_evidence,
            "template_selection": template_selection,
            "case_selection": case_selection,
            "missing_fields": ["线路名称", "现场痛点确认"],
            "files": project_files,
        }
        project["detected_project_type"] = project_type
        project["classification_status"] = "analyzed"
        project["template_selection"] = template_selection
        project["case_selection"] = case_selection
        project["classification_result"] = classification
        self._set_project_status(project, "待确认")
        self.save(state)
        return classification

    def get_classification(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        return project.get("classification_result")

    def review_classification(
        self,
        project_id: int,
        confirmed_project_type: str,
        template_selection: dict[str, Any],
        confirmed_case_id: int | None,
        notes: str,
    ) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        classification = project.get("classification_result")
        if classification is None:
            return None
        if confirmed_project_type not in PROJECT_TYPES:
            return None

        project["confirmed_project_type"] = confirmed_project_type
        project["classification_status"] = "reviewed"
        project["template_selection"] = self._review_template_selection(confirmed_project_type, template_selection)
        case_selection = deepcopy(project.get("case_selection", {}))
        case_selection["confirmed_case_id"] = confirmed_case_id
        project["case_selection"] = case_selection
        project["classification_review"] = {"notes": notes}

        classification["classification_status"] = "reviewed"
        classification["confirmed_project_type"] = confirmed_project_type
        classification["template_selection"] = project["template_selection"]
        classification["case_selection"] = case_selection
        self.save(state)
        return classification

    def generate_reviewed_project(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        if project.get("classification_status") != "reviewed":
            return None

        self._set_project_status(project, "生成中")
        for module in project["modules"]:
            module_id = module["module_id"]
            self._set_module_status(module, "outlined")
            module["outline"] = {
                "slides": [
                    {
                        "module_id": module_id,
                        "page_number": 1,
                        "page_title": MODULE_NAMES[module_id],
                        "core_insight": f"{MODULE_NAMES[module_id]}按确认后的项目类型、模板和案例进入 Demo 生成。",
                        "bullet_points": ["[待补充：项目关键信息]", "[待补充：模板字段]", "[待补充：案例确认]"],
                        "asset_ids": [],
                        "case_ids": [project["case_selection"].get("confirmed_case_id")] if module_id == "M5" and project.get("case_selection", {}).get("confirmed_case_id") else [],
                        "visual_suggestion": "使用确认后的固化模板和占位字段",
                        "missing_fields": ["项目关键信息", "模板字段", "案例确认"],
                    }
                ]
            }
        try:
            final_path, chapter_paths = render_project_ppt(project, self.data_dir / "outputs" / f"project_{project_id}")
        except Exception as exc:
            self._set_project_status(project, "失败")
            for module in project["modules"]:
                self._set_module_status(module, "failed")
                module["error_message"] = str(exc)
            self.save(state)
            return project
        for module in project["modules"]:
            self._set_module_status(module, "rendered")
            module["chapter_ppt_path"] = str(chapter_paths[module["module_id"]])
        project["final_ppt_path"] = str(final_path)
        self._set_project_status(project, "合并中")
        self._set_project_status(project, "完成")
        self.save(state)
        return project

    def generate_mock_outline(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None

        self._set_project_status(project, "模块解析中")
        for module in project["modules"]:
            if module["status"] == "pending":
                self._set_module_status(module, "uploaded")
            self._set_module_status(module, "parsed")

        self._set_project_status(project, "素材匹配中")
        for module in project["modules"]:
            self._set_module_status(module, "matched")

        self._set_project_status(project, "章节生成中")
        for module in project["modules"]:
            module_id = module["module_id"]
            matched_assets = [asset["asset_id"] for asset in state["assets"] if asset["module_id"] == module_id][:3]
            self._set_module_status(module, "outlined")
            module["matched_asset_ids"] = matched_assets
            module["outline"] = {
                "slides": [
                    {
                        "module_id": module_id,
                        "page_number": 1,
                        "page_title": MODULE_NAMES[module_id],
                        "core_insight": f"{MODULE_NAMES[module_id]}章节使用 Mock 大纲，等待人工确认。",
                        "bullet_points": ["[待补充：项目关键信息]", "[待补充：模块材料摘要]", "[待补充：推荐素材确认]"],
                        "asset_ids": matched_assets,
                        "case_ids": [case["case_id"] for case in state["cases"] if module_id == "M5"],
                        "visual_suggestion": "使用中驰蓝白模板占位页",
                        "missing_fields": ["项目关键信息", "模块材料摘要", "推荐素材确认"],
                    }
                ]
            }
        self._set_project_status(project, "待确认")

        self.save(state)
        return project

    def review_project(self, project_id: int, approved: bool, notes: str) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        self._set_project_status(project, "章节渲染中" if approved else "待确认")
        project["review"] = {"approved": approved, "notes": notes}
        if approved:
            for module in project["modules"]:
                if module["status"] == "outlined":
                    self._set_module_status(module, "reviewed")
            try:
                final_path, chapter_paths = render_project_ppt(project, self.data_dir / "outputs" / f"project_{project_id}")
            except Exception as exc:
                self._set_project_status(project, "失败")
                for module in project["modules"]:
                    self._set_module_status(module, "failed")
                    module["error_message"] = str(exc)
                self.save(state)
                return project
            for module in project["modules"]:
                self._set_module_status(module, "rendered")
                module["chapter_ppt_path"] = str(chapter_paths[module["module_id"]])
            project["final_ppt_path"] = str(final_path)
            self._set_project_status(project, "合并中")
            self._set_project_status(project, "完成")
        self.save(state)
        return project

    def get_assets(self, module_id: str | None = None) -> list[dict[str, Any]]:
        assets = deepcopy(self.load()["assets"])
        if module_id:
            return [asset for asset in assets if asset["module_id"] == module_id]
        return assets

    def get_cases(self) -> list[dict[str, Any]]:
        return self.load()["cases"]


def get_store() -> JsonStore:
    return JsonStore()
