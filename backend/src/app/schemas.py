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
    error_message: str = ""


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
    notes: str = ""
