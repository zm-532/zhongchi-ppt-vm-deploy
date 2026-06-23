import json
import os
import shutil
import threading
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case_matcher import (
    extract_project_tags,
    load_case_index,
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
from .m1m2_classifier import M1M2Classification, classify_m1_m2_project
from .m5_case_scanner import get_m5_case_by_id, recommend_m5_case, scan_m5_cases
from .ppt_generation import render_project_ppt
from .quality_review import quality_review_failed_report, review_project_quality

# 进程内锁，保护 load/save 的读-改-写流程，防止并发请求导致数据损坏
_db_lock = threading.Lock()


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
        "full_ppt_cases": [],
    }


class JsonStore:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or get_data_dir()
        self.db_path = self.data_dir / "mock_db.json"
        self.uploads_dir = self.data_dir / "uploads"

    # ── 内部无锁方法，仅在 _transaction 或已持锁时调用 ──

    def _load_unlocked(self) -> dict[str, Any]:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        if not self.db_path.exists():
            state = _initial_state()
            self._save_unlocked(state)
            return state
        state = json.loads(self.db_path.read_text(encoding="utf-8"))
        state.setdefault("full_ppt_cases", [])
        return state

    def _save_unlocked(self, state: dict[str, Any]) -> None:
        """原子写入：先写临时文件，再 os.replace 替换，避免写入中断导致文件损坏。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.db_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp_path), str(self.db_path))

    # ── 事务式 helper：持锁覆盖整个读-改-写 ──

    @contextmanager
    def _transaction(self):
        """获取进程内锁，加载 state，yield 给调用方修改，退出时自动原子保存。

        用法::

            with self._transaction() as state:
                state["projects"].append(project)

        正常退出自动保存；异常退出不保存（避免写入损坏中间状态）。
        """
        with _db_lock:
            state = self._load_unlocked()
            yield state
            self._save_unlocked(state)

    # ── 公开方法（供外部 / 测试直接调用）──

    def load(self) -> dict[str, Any]:
        with _db_lock:
            return self._load_unlocked()

    def save(self, state: dict[str, Any]) -> None:
        with _db_lock:
            self._save_unlocked(state)

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
        with self._transaction() as state:
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
                "include_print_tail_page": False,
                "quality_report": {},
            }
            state["projects"].append(project)
            return project

    def get_project(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        return next((project for project in state["projects"] if project["project_id"] == project_id), None)

    def delete_project(self, project_id: int) -> bool:
        with self._transaction() as state:
            project_count = len(state["projects"])
            state["projects"] = [project for project in state["projects"] if project["project_id"] != project_id]
            if len(state["projects"]) == project_count:
                return False

            state["files"] = [file_record for file_record in state["files"] if file_record["project_id"] != project_id]
            for path in (
                self.uploads_dir / str(project_id),
                self.data_dir / "parsed_text" / str(project_id),
                self.data_dir / "outputs" / f"project_{project_id}",
            ):
                if path.exists():
                    shutil.rmtree(path)
            return True

    def update_project(self, project_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
        """部分更新项目基础信息。None 值不覆盖原值，空字符串视具体情况处理。"""
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None

            # 只允许更新的字段
            allowed_fields = ("project_name", "project_location", "owner_unit", "product_line")
            for field in allowed_fields:
                if field in payload:
                    value = payload[field]
                    # None 表示不更新，保留原值
                    if value is None:
                        continue
                    # project_name 不允许空字符串
                    if field == "project_name" and isinstance(value, str) and value.strip() == "":
                        continue
                    project[field] = value

            return project

    def _m3_materials_response(self, project: dict[str, Any]) -> dict[str, Any]:
        materials = project.get("m3_materials") or {}
        texts = materials.get("texts") or {}
        images = materials.get("images") or []
        tables = materials.get("tables") or []
        page_texts = materials.get("page_texts") or {}
        image_summary: dict[str, int] = {}
        for image in images:
            purpose = image.get("purpose", "")
            image_summary[purpose] = image_summary.get(purpose, 0) + 1
        table_summary: dict[str, int] = {}
        for table in tables:
            purpose = table.get("purpose", "")
            table_summary[purpose] = table_summary.get(purpose, 0) + 1
        return {
            "project_id": project["project_id"],
            "texts": texts,
            "images": images,
            "tables": tables,
            "page_texts": page_texts,
            "text_completed_count": sum(1 for value in texts.values() if isinstance(value, str) and value.strip()),
            "text_total_count": 9,
            "image_count": len(images),
            "image_summary": image_summary,
            "table_count": len(tables),
            "table_summary": table_summary,
        }

    def get_m3_materials(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        return self._m3_materials_response(project)

    def save_m3_materials(
        self,
        project_id: int,
        texts: dict[str, str],
        images: list[dict[str, Any]],
        tables: list[dict[str, Any]] | None = None,
        page_texts: dict[str, list[str]] | None = None,
    ) -> dict[str, Any] | None:
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None

            materials_dir = self.uploads_dir / str(project_id) / "m3_materials"
            if materials_dir.exists():
                shutil.rmtree(materials_dir)
            materials_dir.mkdir(parents=True, exist_ok=True)

            image_records: list[dict[str, Any]] = []
            table_records: list[dict[str, Any]] = []
            file_index = 1
            for image in images:
                purpose = str(image.get("purpose", ""))
                filename = str(image.get("filename", "upload"))
                content_type = str(image.get("content_type", "application/octet-stream"))
                content = image.get("content", b"")
                safe_filename = Path(filename).name or "upload"
                stored_path = materials_dir / f"{file_index}_{safe_filename}"
                file_index += 1
                stored_path.write_bytes(content)
                image_records.append(
                    {
                        "purpose": purpose,
                        "filename": safe_filename,
                        "content_type": content_type,
                        "stored_path": str(stored_path),
                        "description": str(image.get("description", "")),
                        "page_index": int(image.get("page_index", 1)),
                    }
                )
            for table in tables or []:
                purpose = str(table.get("purpose", ""))
                filename = str(table.get("filename", "upload.xlsx"))
                content_type = str(table.get("content_type", "application/octet-stream"))
                content = table.get("content", b"")
                safe_filename = Path(filename).name or "upload.xlsx"
                stored_path = materials_dir / f"{file_index}_{safe_filename}"
                file_index += 1
                stored_path.write_bytes(content)
                table_records.append(
                    {
                        "purpose": purpose,
                        "filename": safe_filename,
                        "content_type": content_type,
                        "stored_path": str(stored_path),
                        "page_index": int(table.get("page_index", 1)),
                    }
                )

            project["m3_materials"] = {
                "texts": texts,
                "images": image_records,
                "tables": table_records,
                "page_texts": page_texts or {},
            }
            return self._m3_materials_response(project)

    def add_file(self, project_id: int, module_id: str, filename: str, content_type: str, content: bytes) -> dict[str, Any] | None:
        with self._transaction() as state:
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
                "vector_status": "not_indexed",
                "vector_chunk_count": 0,
                "vector_error_message": "",
            }
            state["files"].append(file_record)

            module = next(item for item in project["modules"] if item["module_id"] == module_id)
            self._set_module_status(module, "uploaded")
            module["uploaded_file_ids"].append(file_id)

            return file_record

    def add_project_files(self, project_id: int, files: list[tuple[str, str, bytes]]) -> list[dict[str, Any]] | None:
        with self._transaction() as state:
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
                    "vector_status": "not_indexed",
                    "vector_chunk_count": 0,
                    "vector_error_message": "",
                }
                state["files"].append(file_record)
                records.append(file_record)

            self._set_project_status(project, "待分析")
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

    def _detect_project_type_by_rules(self, project: dict[str, Any], files: list[dict[str, Any]]) -> M1M2Classification:
        sources = self._detection_sources(project, files)
        text = " ".join(source_text for _, source_text in sources).lower()

        # Rail context: keywords that indicate rail/transit projects
        rail_context_keywords = ["地铁", "轨道交通", "铁路", "轨交", "城市轨道", "metro"]
        # Strong constraint keywords: high weight when rail context present
        strong_constraint_keywords = ["既有线", "运营线", "天窗", "短窗口"]
        # Weak constraint keywords: low weight, need multiple to outweigh metro
        weak_constraint_keywords = ["改造", "夜间"]

        has_rail_context = any(kw in text for kw in rail_context_keywords)

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

            if project_type == "existing_rail_transit":
                if has_rail_context:
                    # Weighted: strong=1.0, weak=0.5, generic "改造" alone won't beat metro
                    strong = sum(1.0 for kw in matched if kw in strong_constraint_keywords)
                    weak = sum(0.5 for kw in matched if kw in weak_constraint_keywords)
                    effective_count = strong + weak
                else:
                    # Without rail context, only count strong rail-specific keywords
                    effective_count = sum(1 for kw in matched if kw in strong_constraint_keywords)
            elif project_type == "metro":
                # When strong reconstruction constraints appear, metro should be demoted
                has_strong_constraint = any(kw in text for kw in strong_constraint_keywords)
                effective_count = len(matched) * (0.5 if has_strong_constraint else 1.0)
            else:
                effective_count = len(matched)
            scores.append((effective_count, project_type, matched, evidence))
        score, project_type, matched_keywords, detection_evidence = max(scores, key=lambda item: item[0])
        if score == 0:
            return M1M2Classification("metro", 0.35, [], [], "rule_fallback", fallback_reason="规则未命中关键词，默认使用地铁模板")
        return M1M2Classification(project_type, min(0.95, 0.55 + score * 0.12), matched_keywords, detection_evidence, "rule_fallback")

    def _detect_project_type(self, project: dict[str, Any], files: list[dict[str, Any]]) -> M1M2Classification:
        sources = self._detection_sources(project, files)
        rule_result = self._detect_project_type_by_rules(project, files)
        return classify_m1_m2_project(project, sources, rule_result)

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
        """推荐 M5 案例。

        第 1 阶段：只推荐 1 个 M5 文件夹固定案例，不混入旧 case_matcher 结果。
        后续阶段可扩展为多来源混合推荐。
        """
        m5_recommended = recommend_m5_case(project_type)
        if m5_recommended is None:
            return []

        type_names = {
            "highway": "公路",
            "railway": "铁路",
            "metro": "轨道交通",
            "existing_rail_transit": "轨道交通",
        }
        type_name = type_names.get(project_type, project_type)
        return [{
            "case_id": m5_recommended["case_id"],
            "title": m5_recommended["title"],
            "match_reason": f"同为{type_name}类型固定案例",
            "matched_tags": [f"项目类型:{project_type}"],
            "source_path": m5_recommended["source_path"],
        }]

    def analyze_project(self, project_id: int) -> dict[str, Any] | None:
        with self._transaction() as state:
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
                file_record["text_preview"] = analysis.extracted_text[:1500] if analysis.extracted_text else ""
                if analysis.extracted_text:
                    parsed_text_path = parsed_dir / f"{file_record['file_id']}.txt"
                    parsed_text_path.write_text(analysis.extracted_text, encoding="utf-8")
                    file_record["parsed_text_path"] = str(parsed_text_path)
                else:
                    file_record["parsed_text_path"] = ""

            self._set_project_status(project, "类型识别中")
            classification_result = self._detect_project_type(project, project_files)
            project_type = classification_result.project_type
            confidence = classification_result.confidence
            matched_keywords = classification_result.matched_keywords
            detection_evidence = classification_result.detection_evidence

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
                "classification_method": classification_result.classification_method,
                "llm_reasoning_summary": classification_result.llm_reasoning_summary,
                "fallback_reason": classification_result.fallback_reason,
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
            return classification

    def get_classification(self, project_id: int) -> dict[str, Any] | None:
        state = self.load()
        project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
        if project is None:
            return None
        return project.get("classification_result")

    # 特殊案例 ID 白名单：前端 M5_DEMO_CASE 使用 "m5_demo" 作为演示占位符
    DEMO_CASE_IDS: frozenset[str] = frozenset({"m5_demo", "1", 1})

    def _validate_case_id(self, case_id: str | int, classification: dict[str, Any], state: dict[str, Any]) -> bool:
        """Validate that a case_id exists in recommended cases, store case library, or demo allowlist."""
        str_id = str(case_id)
        # Demo/演示占位符：前端内置的 M5 演示案例
        if str_id in self.DEMO_CASE_IDS:
            return True
        # Check recommended cases from classification
        recommended = classification.get("case_selection", {}).get("recommended_cases", [])
        for case in recommended:
            if str(case.get("case_id")) == str_id:
                return True
        # Check store's case library (mock demo cases)
        for case in state.get("cases", []):
            if str(case.get("case_id")) == str_id:
                return True
        # Check M5 folder cases
        if get_m5_case_by_id(str_id) is not None:
            return True
        return False

    def review_classification(
        self,
        project_id: int,
        confirmed_project_type: str,
        template_selection: dict[str, Any],
        confirmed_case_id: str | int | None,
        m3_selection: str,
        include_print_tail_page: bool,
        notes: str,
    ) -> dict[str, Any] | None:
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None
            classification = project.get("classification_result")
            if classification is None:
                return None
            if confirmed_project_type not in PROJECT_TYPES:
                return None

            # Validate confirmed_case_id
            if confirmed_case_id is not None and str(confirmed_case_id).strip() not in ("", "null", "None", "__none__"):
                if not self._validate_case_id(confirmed_case_id, classification, state):
                    return {"_validation_error": "invalid_case_id"}

            project["confirmed_project_type"] = confirmed_project_type
            project["classification_status"] = "reviewed"
            project["template_selection"] = self._review_template_selection(confirmed_project_type, template_selection)
            case_selection = deepcopy(project.get("case_selection", {}))
            case_selection["confirmed_case_id"] = confirmed_case_id
            project["case_selection"] = case_selection
            # m3_selection: "m3_template" = 包含M3, "m3_skip" = 跳过M3
            project["m3_selection"] = m3_selection if m3_selection in ("m3_template", "m3_skip") else "m3_template"
            project["include_print_tail_page"] = bool(include_print_tail_page)
            project["classification_review"] = {"notes": notes}

            classification["classification_status"] = "reviewed"
            classification["confirmed_project_type"] = confirmed_project_type
            classification["template_selection"] = project["template_selection"]
            classification["case_selection"] = case_selection
            return classification

    def generate_reviewed_project(self, project_id: int) -> dict[str, Any] | None:
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None
            if project.get("classification_status") != "reviewed":
                return None

            # 生成前清空旧结果，避免失败后仍下载旧文件
            project["final_ppt_path"] = ""
            project["quality_report"] = {}
            for module in project["modules"]:
                module["chapter_ppt_path"] = ""
                module["error_message"] = ""

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
                return project

            # 判断是否选择了案例（M5 是否参与）
            confirmed_case_id = project.get("case_selection", {}).get("confirmed_case_id")
            raw_case_id = confirmed_case_id
            has_case = raw_case_id is not None and str(raw_case_id).strip() not in ("", "null", "None", "__none__")

            # M3 选择：默认包含M3，"m3_skip" 时跳过
            include_m3 = project.get("m3_selection", "m3_template") == "m3_template"

            for module in project["modules"]:
                module_id = module["module_id"]
                if module_id == "M5":
                    if not has_case:
                        # 未选择案例，M5 跳过
                        self._set_module_status(module, "skipped")
                        module["chapter_ppt_path"] = ""
                    else:
                        self._set_module_status(module, "rendered")
                        module["chapter_ppt_path"] = str(chapter_paths["M5"])
                elif module_id == "M3":
                    if not include_m3:
                        self._set_module_status(module, "skipped")
                        module["chapter_ppt_path"] = ""
                    else:
                        self._set_module_status(module, "rendered")
                        module["chapter_ppt_path"] = str(chapter_paths["M3"])
                else:
                    self._set_module_status(module, "rendered")
                    module["chapter_ppt_path"] = str(chapter_paths[module["module_id"]])
            project["final_ppt_path"] = str(final_path)
            try:
                project["quality_report"] = review_project_quality(project, final_path)
            except Exception as exc:
                project["quality_report"] = quality_review_failed_report(exc)
            self._set_project_status(project, "合并中")
            self._set_project_status(project, "完成")
            return project

    def generate_mock_outline(self, project_id: int) -> dict[str, Any] | None:
        with self._transaction() as state:
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
            return project

    def review_project(self, project_id: int, approved: bool, notes: str) -> dict[str, Any] | None:
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None
            self._set_project_status(project, "章节渲染中" if approved else "待确认")
            project["review"] = {"approved": approved, "notes": notes}
            if approved:
                # 生成前清空旧结果
                project["final_ppt_path"] = ""
                for module in project["modules"]:
                    module["chapter_ppt_path"] = ""
                    module["error_message"] = ""

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
                    return project

                confirmed_case_id = project.get("case_selection", {}).get("confirmed_case_id")
                raw_case_id = confirmed_case_id
                has_case = raw_case_id is not None and str(raw_case_id).strip() not in ("", "null", "None", "__none__")

                for module in project["modules"]:
                    module_id = module["module_id"]
                    if module_id == "M5":
                        if not has_case:
                            self._set_module_status(module, "skipped")
                            module["chapter_ppt_path"] = ""
                        else:
                            self._set_module_status(module, "rendered")
                            module["chapter_ppt_path"] = str(chapter_paths["M5"])
                    else:
                        self._set_module_status(module, "rendered")
                        module["chapter_ppt_path"] = str(chapter_paths[module["module_id"]])
                project["final_ppt_path"] = str(final_path)
                self._set_project_status(project, "合并中")
                self._set_project_status(project, "完成")
            return project

    def get_assets(self, module_id: str | None = None) -> list[dict[str, Any]]:
        assets = deepcopy(self.load()["assets"])
        if module_id:
            return [asset for asset in assets if asset["module_id"] == module_id]
        return assets

    def get_cases(self) -> list[dict[str, Any]]:
        # 合并 mock cases 和 M5 文件夹扫描结果
        mock_cases = self.load()["cases"]
        m5_cases = scan_m5_cases()
        # 按 case_id 去重，M5 文件夹案例优先
        seen = {c["case_id"] for c in m5_cases}
        merged = list(m5_cases)
        for c in mock_cases:
            cid = str(c.get("case_id", ""))
            if cid not in seen:
                seen.add(cid)
                merged.append(c)
        return merged

    def save_full_ppt_case(self, project_id: int) -> dict[str, Any] | None:
        """将项目生成后的最终 PPTX 归档到完整 PPT 案例库。

        同一 project_id 使用稳定 case_id，重复保存覆盖同一条记录。
        """
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return None

            final_path_raw = str(project.get("final_ppt_path") or "")
            if project.get("task_status") != "完成" or not final_path_raw:
                raise ValueError("最终PPTX尚未生成，请先完成PPT生成")

            final_path = Path(final_path_raw)
            if not final_path.exists() or not final_path.is_file():
                raise FileNotFoundError("最终PPTX文件不存在")
            if final_path.suffix.lower() != ".pptx":
                raise ValueError("最终文件不是 PPTX，无法存入完整PPT案例库")

            case_id = f"full_ppt_case:{project_id}"
            safe_filename = final_path.name or f"project_{project_id}.pptx"
            archive_dir = self.data_dir / "full_ppt_case_library" / f"project_{project_id}"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archived_path = archive_dir / safe_filename
            shutil.copy2(final_path, archived_path)

            case = {
                "case_id": case_id,
                "project_id": project_id,
                "title": project.get("project_name") or safe_filename,
                "filename": safe_filename,
                "project_type": project.get("confirmed_project_type") or project.get("detected_project_type") or "",
                "source_path": str(archived_path),
                "source_type": "full_ppt",
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "file_size": archived_path.stat().st_size,
                "download_url": f"/api/cases/full-ppt/{case_id}/download",
            }

            cases = state.setdefault("full_ppt_cases", [])
            existing_index = next((index for index, item in enumerate(cases) if item.get("case_id") == case_id), None)
            if existing_index is None:
                cases.append(case)
            else:
                cases[existing_index] = case
            return case

    def get_full_ppt_cases(self) -> list[dict[str, Any]]:
        return deepcopy(self.load().get("full_ppt_cases", []))

    def get_full_ppt_case(self, case_id: str) -> dict[str, Any] | None:
        return next((case for case in self.get_full_ppt_cases() if case.get("case_id") == case_id), None)

    def index_project_vector(
        self,
        project_id: int,
        file_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        Index project files into the vector store after user confirmation.

        Reads parsed text files, chunks them, generates embeddings, and upserts to pgvector.
        Does NOT write to vector store during analyze_project() - only via this method.

        Args:
            project_id: The project to index
            file_ids: Optional list of specific file_ids to index. If None, indexes all
                     files with parse_status='parsed' and a valid parsed_text_path.

        Returns:
            Dict with indexing results: indexed_files, indexed_chunks, skipped_files, message
        """
        with self._transaction() as state:
            project = next((item for item in state["projects"] if item["project_id"] == project_id), None)
            if project is None:
                return {
                    "project_id": project_id,
                    "status": "error",
                    "indexed_files": 0,
                    "indexed_chunks": 0,
                    "skipped_files": [],
                    "message": "项目不存在",
                }

            # Get files to index
            all_files = [f for f in state["files"] if f["project_id"] == project_id]
            skipped_files: list[str] = []

            if file_ids is not None:
                files_to_index = [f for f in all_files if f["file_id"] in file_ids]
            else:
                # Default: all files with parse_status that could yield content for indexing
                # Only files with parse_status='parsed' can produce content
                files_to_index = [
                    f for f in all_files
                    if f.get("parse_status") == "parsed" and f.get("parsed_text_path")
                ]
                # Also track files that will be skipped (not parsed) for reporting
                for f in all_files:
                    if f not in files_to_index:
                        ps = f.get("parse_status", "unknown")
                        skipped_files.append(f["filename"])
                        f["vector_status"] = "skipped"
                        f["vector_error_message"] = f"跳过：parse_status={ps}"

            indexed_files = 0
            indexed_chunks = 0

            # Import here to avoid circular imports and handle optional pgvector
            from .chunking import chunk_text
            from .embedding import create_embedding_provider
            from .vector_service import ChunkMetadata, get_vector_store

            vector_store = get_vector_store()
            embedding_provider = create_embedding_provider()
            vector_enabled = vector_store.is_available()

            for file_record in files_to_index:
                parse_status = file_record.get("parse_status", "")
                # Skip non-parsed files
                if parse_status not in ("parsed",):
                    skipped_files.append(file_record["filename"])
                    file_record["vector_status"] = "skipped"
                    file_record["vector_error_message"] = f"跳过：parse_status={parse_status}"
                    continue

                parsed_text_path = file_record.get("parsed_text_path")
                if not parsed_text_path or not Path(parsed_text_path).exists():
                    skipped_files.append(file_record["filename"])
                    file_record["vector_status"] = "skipped"
                    file_record["vector_error_message"] = "跳过：无 parsed_text_path 或文件不存在"
                    continue

                try:
                    text = Path(parsed_text_path).read_text(encoding="utf-8", errors="ignore")
                except OSError as exc:
                    file_record["vector_status"] = "failed"
                    file_record["vector_error_message"] = f"读取失败：{exc}"
                    skipped_files.append(file_record["filename"])
                    continue

                if not text or not text.strip():
                    skipped_files.append(file_record["filename"])
                    file_record["vector_status"] = "skipped"
                    file_record["vector_error_message"] = "跳过：解析文本为空"
                    continue

                # Chunk the text
                chunks = chunk_text(text)
                if not chunks:
                    skipped_files.append(file_record["filename"])
                    file_record["vector_status"] = "skipped"
                    file_record["vector_error_message"] = "跳过：切块结果为空"
                    continue

                # Generate embeddings
                try:
                    embeddings = embedding_provider.embed(chunks)
                except Exception as exc:
                    file_record["vector_status"] = "failed"
                    file_record["vector_error_message"] = f"Embedding 失败：{exc}"
                    skipped_files.append(file_record["filename"])
                    continue

                # Build metadata for each chunk
                metadata: list[ChunkMetadata] = []
                for idx, chunk in enumerate(chunks):
                    meta = ChunkMetadata(
                        filename=file_record["filename"],
                        source_path=file_record.get("stored_path", ""),
                        document_role=file_record.get("document_role", "unknown"),
                        assigned_modules=file_record.get("assigned_modules", []),
                        chunk_index=idx,
                        project_id=project_id,
                        file_id=file_record["file_id"],
                        doc_type="project",
                    )
                    metadata.append(meta)

                # Upsert to vector store
                if vector_enabled:
                    try:
                        inserted = vector_store.upsert(chunks, embeddings, metadata)
                        file_record["vector_status"] = "indexed"
                        file_record["vector_chunk_count"] = inserted
                        file_record["vector_error_message"] = ""
                        indexed_files += 1
                        indexed_chunks += inserted
                    except Exception as exc:
                        file_record["vector_status"] = "failed"
                        file_record["vector_error_message"] = str(exc)
                        skipped_files.append(file_record["filename"])
                        continue
                else:
                    # Vector store not available - do NOT count as indexed, mark as not_indexed
                    file_record["vector_status"] = "not_indexed"
                    file_record["vector_chunk_count"] = len(chunks)
                    file_record["vector_error_message"] = "向量库未配置（ZHONGCHI_VECTOR_DSN 未设置）"
                    # Add to skipped so frontend knows nothing was actually stored
                    skipped_files.append(file_record["filename"])
                    # Do NOT increment indexed_files/indexed_chunks

            if vector_enabled:
                message = "已存入向量库"
                status = "indexed"
            else:
                message = "向量库未配置（ZHONGCHI_VECTOR_DSN 未设置），本次未实际入库"
                status = "not_configured"

            return {
                "project_id": project_id,
                "status": status,
                "indexed_files": indexed_files,
                "indexed_chunks": indexed_chunks,
                "skipped_files": skipped_files,
                "message": message,
            }


def get_store() -> JsonStore:
    return JsonStore()
