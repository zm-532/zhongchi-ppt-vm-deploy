from typing import Any

from pydantic import BaseModel, Field


class ModuleResult(BaseModel):
    module_id: str
    status: str = "pending"
    status_history: list[str] = Field(default_factory=lambda: ["pending"])
    uploaded_file_ids: list[int] = Field(default_factory=list)
    matched_asset_ids: list[int] = Field(default_factory=list)
    outline: dict[str, Any] = Field(default_factory=dict)
    chapter_ppt_path: str = ""
    error_message: str = ""


class ProjectCreate(BaseModel):
    project_name: str
    project_location: str = ""
    owner_unit: str = ""
    product_line: str = ""
    project_fields: dict[str, Any] = Field(default_factory=dict)


class Project(ProjectCreate):
    project_id: int
    task_status: str
    status_history: list[str] = Field(default_factory=list)
    modules: list[ModuleResult]
    final_ppt_path: str = ""
    detected_project_type: str | None = None
    confirmed_project_type: str | None = None
    classification_status: str = "pending"
    template_selection: dict[str, Any] = Field(default_factory=dict)
    case_selection: dict[str, Any] = Field(default_factory=dict)


class StoredFile(BaseModel):
    file_id: int
    project_id: int
    module_id: str | None = None
    filename: str
    content_type: str
    stored_path: str
    document_role: str = "unknown"
    assigned_modules: list[str] = Field(default_factory=list)
    parse_status: str = "pending"
    parsed_text_path: str = ""
    text_preview: str = ""  # 解析文本预览，截断至约1500字
    error_message: str = ""
    # Vector store fields
    vector_status: str = "not_indexed"  # not_indexed, indexed, skipped, failed
    vector_chunk_count: int = 0
    vector_error_message: str = ""


class ReviewRequest(BaseModel):
    approved: bool
    notes: str = ""


class ClassificationResult(BaseModel):
    project_id: int
    classification_status: str
    detected_project_type: str
    confirmed_project_type: str | None = None
    confidence: float
    matched_keywords: list[str] = Field(default_factory=list)
    detection_evidence: list[dict[str, Any]] = Field(default_factory=list)
    template_selection: dict[str, Any] = Field(default_factory=dict)
    case_selection: dict[str, Any] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    files: list[StoredFile] = Field(default_factory=list)


class ClassificationReviewRequest(BaseModel):
    confirmed_project_type: str
    template_selection: dict[str, Any] = Field(default_factory=dict)
    confirmed_case_id: str | int | None = None
    m3_selection: str = "m3_template"  # "m3_template" = 包含M3, "m3_skip" = 跳过M3
    notes: str = ""


class VectorIndexRequest(BaseModel):
    """Request body for POST /api/projects/{project_id}/vector-index."""
    file_ids: list[int] | None = None  # If None, index all parsed files


class VectorIndexResponse(BaseModel):
    """Response for POST /api/projects/{project_id}/vector-index."""
    project_id: int
    status: str  # "indexed", "error"
    indexed_files: int
    indexed_chunks: int
    skipped_files: list[str] = Field(default_factory=list)
    message: str


class DocumentParseTestResult(BaseModel):
    filename: str
    suffix: str
    content_type: str
    parse_status: str
    document_role: str
    assigned_modules: list[str] = Field(default_factory=list)
    text: str = ""
    text_preview: str = ""
    sections: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    slides: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""


class ProjectUpdate(BaseModel):
    """用于部分更新项目基础信息的请求体。"""
    project_name: str | None = None
    project_location: str | None = None
    owner_unit: str | None = None
    product_line: str | None = None


class LlmTestRequest(BaseModel):
    prompt: str = "请用一句话回复：LLM连接成功，并说明你收到了中驰售前PPT助手的测试请求。"


class LlmTestResponse(BaseModel):
    ok: bool
    status_code: int
    model: str = ""
    reply: str = ""
    error: str = ""
    configured: dict[str, bool] = Field(default_factory=dict)


class M3RenderTestRequest(BaseModel):
    project_name: str
    project_location: str = ""
    owner_unit: str = ""
    product_line: str = ""
    parsed_sources: list[str] = Field(default_factory=list)


class M3RenderTestResponse(BaseModel):
    ok: bool
    pptx_path: str = ""
    download_url: str = ""
    replacements: dict[str, str] = Field(default_factory=dict)


class M3ImageRenderTestResponse(BaseModel):
    ok: bool
    pptx_path: str = ""
    download_url: str = ""
    image_summary: dict[str, int] = Field(default_factory=dict)


class M3FullRenderTestResponse(BaseModel):
    ok: bool
    pptx_path: str = ""
    download_url: str = ""
    slide_count: int = 0
    image_summary: dict[str, int] = Field(default_factory=dict)
