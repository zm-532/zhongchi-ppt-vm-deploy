from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


MODULE_ORDER = ("M1", "M2", "M5", "M6")

MODULE_TITLES = {
    "M1": "行业背景与技术标准",
    "M2": "项目概况与现场挑战",
    "M5": "同类型案例匹配",
    "M6": "企业背书与荣誉",
}


class WorkflowStatus(StrEnum):
    PENDING = "待生成"
    PARSING = "模块解析中"
    MATCHING = "素材匹配中"
    OUTLINING = "章节生成中"
    WAITING_REVIEW = "待确认"
    RENDERING = "章节渲染中"
    MERGING = "合并中"
    FINISHED = "完成"
    FAILED = "失败"


@dataclass
class ModuleState:
    module_id: str
    status: str = "pending"
    uploaded_file_ids: list[int] = field(default_factory=list)
    parsed_summary: str = ""
    tags: list[str] = field(default_factory=list)
    matched_asset_ids: list[int] = field(default_factory=list)
    matched_case_ids: list[int] = field(default_factory=list)
    outline: dict[str, Any] = field(default_factory=dict)
    chapter_ppt_path: str = ""
    error_message: str = ""


@dataclass
class WorkflowState:
    project_id: int
    project_name: str
    product_line: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    modules: list[ModuleState] = field(default_factory=list)
    completed_nodes: list[str] = field(default_factory=list)
    mock_fallbacks: dict[str, bool] = field(default_factory=lambda: {"llm": False, "embedding": False})
    final_ppt_path: str = ""
    quality_report: dict[str, Any] = field(default_factory=dict)
    review: dict[str, Any] = field(default_factory=dict)


class WorkflowEngine:
    """Replaceable workflow engine with LangGraph-compatible node boundaries."""

    def __init__(self, use_mock_llm: bool = True, use_mock_embedding: bool = True):
        self.use_mock_llm = use_mock_llm
        self.use_mock_embedding = use_mock_embedding

    def run_until_review(self, payload: dict[str, Any]) -> WorkflowState:
        state = self.load_project(payload)
        state = self.prepare_modules(state, payload.get("modules", []))
        state = self.parse_module_files(state)
        state = self.extract_module_tags(state)
        state = self.retrieve_module_assets(state)
        state = self.match_cases(state)
        state = self.generate_module_outlines(state)
        state = self.human_review(state)
        return state

    def resume_after_review(self, state: WorkflowState, approved: bool, notes: str = "") -> WorkflowState:
        state.review = {"approved": approved, "notes": notes}
        if not approved:
            state.status = WorkflowStatus.WAITING_REVIEW
            state.completed_nodes.append("human_review_rejected")
            return state

        state = self.render_chapter_ppts(state)
        state = self.merge_ppt(state)
        state = self.quality_check(state)
        state.status = WorkflowStatus.FINISHED
        return state

    def load_project(self, payload: dict[str, Any]) -> WorkflowState:
        state = WorkflowState(
            project_id=int(payload["project_id"]),
            project_name=str(payload.get("project_name") or "[待补充：项目名称]"),
            product_line=str(payload.get("product_line") or ""),
        )
        state.completed_nodes.append("load_project")
        return state

    def prepare_modules(self, state: WorkflowState, modules: list[dict[str, Any]]) -> WorkflowState:
        provided = {module["module_id"]: module for module in modules}
        unexpected = [module_id for module_id in provided if module_id not in MODULE_ORDER]
        if unexpected:
            raise ValueError("本阶段工作流只支持 M1/M2/M5/M6，M3/M4 为后续动态模块。")

        state.modules = [
            ModuleState(
                module_id=module_id,
                status=provided.get(module_id, {}).get("status", "pending"),
                uploaded_file_ids=list(provided.get(module_id, {}).get("uploaded_file_ids", [])),
            )
            for module_id in MODULE_ORDER
        ]
        state.completed_nodes.append("prepare_modules")
        return state

    def parse_module_files(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.PARSING
        for module in state.modules:
            file_count = len(module.uploaded_file_ids)
            module.parsed_summary = f"{MODULE_TITLES[module.module_id]}已解析 {file_count} 个上传文件；缺失内容使用待补充占位。"
            module.status = "parsed"
        state.completed_nodes.append("parse_module_files")
        return state

    def extract_module_tags(self, state: WorkflowState) -> WorkflowState:
        for module in state.modules:
            base_tags = [MODULE_TITLES[module.module_id], state.product_line or "[待补充：产品线]"]
            if module.module_id == "M5":
                base_tags.append("同类型案例")
            if module.module_id == "M6":
                base_tags.append("企业背书")
            module.tags = base_tags
        state.completed_nodes.append("extract_module_tags")
        return state

    def retrieve_module_assets(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.MATCHING
        state.mock_fallbacks["embedding"] = self.use_mock_embedding
        for index, module in enumerate(state.modules, start=1):
            module.matched_asset_ids = [index * 100 + 1]
            module.status = "matched"
        state.completed_nodes.append("retrieve_module_assets")
        return state

    def match_cases(self, state: WorkflowState) -> WorkflowState:
        for module in state.modules:
            module.matched_case_ids = [501] if module.module_id == "M5" else []
        state.completed_nodes.append("match_cases")
        return state

    def generate_module_outlines(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.OUTLINING
        state.mock_fallbacks["llm"] = self.use_mock_llm
        for module in state.modules:
            module.outline = {
                "slides": [
                    {
                        "module_id": module.module_id,
                        "page_number": 1,
                        "page_title": MODULE_TITLES[module.module_id],
                        "core_insight": f"{MODULE_TITLES[module.module_id]}使用 Mock 大纲，等待人工确认。",
                        "bullet_points": [
                            module.parsed_summary,
                            f"匹配素材：{module.matched_asset_ids}",
                            "[待补充：人工确认后的重点表达]",
                        ],
                        "asset_ids": module.matched_asset_ids,
                        "case_ids": module.matched_case_ids,
                        "visual_suggestion": "使用中驰蓝白模板占位页",
                        "missing_fields": ["人工确认后的重点表达"],
                    }
                ]
            }
            module.status = "outlined"
        state.completed_nodes.append("generate_module_outlines")
        return state

    def human_review(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.WAITING_REVIEW
        state.completed_nodes.append("human_review")
        return state

    def render_chapter_ppts(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.RENDERING
        for module in state.modules:
            module.chapter_ppt_path = f"outputs/project_{state.project_id}/{module.module_id}_chapter.pptx"
            module.status = "rendered"
        state.completed_nodes.append("render_chapter_ppts")
        return state

    def merge_ppt(self, state: WorkflowState) -> WorkflowState:
        state.status = WorkflowStatus.MERGING
        state.final_ppt_path = f"outputs/project_{state.project_id}/final_M1_M2_M5_M6.pptx"
        state.completed_nodes.append("merge_ppt")
        return state

    def quality_check(self, state: WorkflowState) -> WorkflowState:
        state.quality_report = {
            "module_order": list(MODULE_ORDER),
            "missing_fields_policy": "[待补充：字段名]",
            "dynamic_modules": "M3/M4 后续动态模块，本阶段不生成",
            "passed": True,
        }
        state.completed_nodes.append("quality_check")
        return state


def build_workflow_engine(use_mock_llm: bool = True, use_mock_embedding: bool = True) -> WorkflowEngine:
    return WorkflowEngine(use_mock_llm=use_mock_llm, use_mock_embedding=use_mock_embedding)

