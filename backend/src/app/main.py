import os
import sys as _sys
from pathlib import Path

# 在模块加载时将 ppt_engine 路径注入 sys.path（供 TestClient 共享）
# 必须在任何依赖 ppt_engine 的 import 之前执行。
_ppt_engine_root = Path(__file__).resolve().parents[3] / "ppt_engine"
if str(_ppt_engine_root) not in _sys.path:
    _sys.path.insert(0, str(_ppt_engine_root))
del _sys, _ppt_engine_root

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .constants import ALLOWED_EXTENSIONS, ALLOWED_MODULE_IDS, PROJECT_TYPES
from .schemas import (
    ClassificationResult,
    ClassificationReviewRequest,
    LlmTestRequest,
    LlmTestResponse,
    M3FullRenderTestResponse,
    M3MaterialsResponse,
    Project,
    ProjectCreate,
    ProjectUpdate,
    ReviewRequest,
    StoredFile,
    VectorIndexRequest,
    VectorIndexResponse,
)
from .storage import get_data_dir, get_store


def _get_m3_full_test_output_dir() -> Path:
    """获取 M3 完整测试输出目录，运行时解析（受 ZHONGCHI_DATA_DIR 影响）。"""
    return get_data_dir() / "outputs" / "m3_full_test"

app = FastAPI(title="中驰智能PPT Demo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3101",
        "http://127.0.0.1:3102",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3101",
        "http://localhost:3102",
        "http://192.168.0.202:3001",
        "http://192.168.0.202:8010",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_module_id(module_id: str) -> None:
    if module_id not in ALLOWED_MODULE_IDS:
        allowed = ", ".join(ALLOWED_MODULE_IDS)
        raise HTTPException(status_code=400, detail=f"module_id 只允许 {allowed}")


def validate_extension(filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="暂不支持该文件类型")


def validate_project_type(project_type: str) -> None:
    if project_type not in PROJECT_TYPES:
        allowed = ", ".join(PROJECT_TYPES)
        raise HTTPException(status_code=400, detail=f"project_type 只允许 {allowed}")


def _get_max_upload_bytes() -> int:
    """获取上传文件大小上限（字节），默认 200MB，可通过 ZHONGCHI_MAX_UPLOAD_BYTES 环境变量配置。"""
    raw = os.environ.get("ZHONGCHI_MAX_UPLOAD_BYTES", "")
    if raw:
        try:
            value = int(raw)
            if value > 0:
                return value
        except ValueError:
            pass
    return 200 * 1024 * 1024  # 200 MB


async def _read_file_with_size_limit(file: UploadFile, label: str = "文件") -> bytes:
    """分块读取上传文件内容，累计超过上限时立即抛出 413，避免超大文件全量进入内存。"""
    max_bytes = _get_max_upload_bytes()
    chunk_size = 1024 * 1024  # 1 MB
    collected = bytearray()
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        collected.extend(chunk)
        if len(collected) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"{label}大小超出限制（最大 {max_bytes // (1024 * 1024)}MB）",
            )
    return bytes(collected)


def _validate_image_blob(blob: bytes) -> None:
    from io import BytesIO

    from PIL import Image

    try:
        with Image.open(BytesIO(blob)) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="图片文件无效或已损坏") from exc


@app.get("/api/projects", response_model=list[Project])
def list_projects() -> list[dict]:
    return get_store().list_projects()


@app.post("/api/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate) -> dict:
    return get_store().create_project(payload.model_dump())


@app.get("/api/projects/{project_id}", response_model=Project)
def get_project(project_id: int) -> dict:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int) -> None:
    deleted = get_store().delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="项目不存在")


@app.patch("/api/projects/{project_id}", response_model=Project)
def patch_project(project_id: int, payload: ProjectUpdate) -> dict:
    updated = get_store().update_project(project_id, payload.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return updated


@app.post(
    "/api/projects/{project_id}/modules/{module_id}/files",
    response_model=StoredFile,
    status_code=status.HTTP_201_CREATED,
    deprecated=True,
)
async def upload_module_file(project_id: int, module_id: str, file: UploadFile = File(...)) -> dict:
    """兼容历史模块上传测试接口；正式流程请使用 /api/projects/{project_id}/files。"""
    validate_module_id(module_id)
    validate_extension(file.filename or "")
    content = await _read_file_with_size_limit(file, "上传文件")
    file_record = get_store().add_file(
        project_id=project_id,
        module_id=module_id,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    if file_record is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return file_record


@app.post("/api/projects/{project_id}/files", response_model=list[StoredFile], status_code=status.HTTP_201_CREATED)
async def upload_project_files(project_id: int, files: list[UploadFile] = File(...)) -> list[dict]:
    upload_items: list[tuple[str, str, bytes]] = []
    for file in files:
        validate_extension(file.filename or "")
        upload_items.append((file.filename or "upload", file.content_type or "application/octet-stream", await _read_file_with_size_limit(file, file.filename or "上传文件")))
    file_records = get_store().add_project_files(project_id=project_id, files=upload_items)
    if file_records is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return file_records


@app.get("/api/projects/{project_id}/m3-materials", response_model=M3MaterialsResponse)
def get_project_m3_materials(project_id: int) -> dict:
    materials = get_store().get_m3_materials(project_id)
    if materials is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return materials


@app.post("/api/projects/{project_id}/m3-materials", response_model=M3MaterialsResponse)
async def save_project_m3_materials(
    project_id: int,
    descriptions: str = Form(""),
    purposes: list[str] = Form([]),
    files: list[UploadFile] = File([]),
) -> dict:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    if purposes:
        raise HTTPException(status_code=400, detail="M3资料上传不再支持按模块手动上传，请按文件名自动分类批量上传")

    from .m3_auto_matcher import build_m3_auto_render_payload

    filenames: list[str] = []
    blobs: list[bytes] = []
    content_types: dict[str, str] = {}
    for upload in files:
        filename = upload.filename or "upload"
        suffix = Path(filename).suffix.lower()
        if suffix == ".xls":
            raise HTTPException(status_code=400, detail=f"暂不支持旧版表格，请另存为 .xlsx 后上传：{filename}")
        is_xlsx = suffix == ".xlsx"
        is_image = (upload.content_type or "").startswith("image/")
        if not is_xlsx and not is_image:
            raise HTTPException(status_code=400, detail=f"文件不是图片或 .xlsx 表格：{filename}")
        blob = await _read_file_with_size_limit(upload, filename)
        if is_image:
            _validate_image_blob(blob)
        filenames.append(filename)
        blobs.append(blob)
        content_types[filename] = upload.content_type or "application/octet-stream"

    try:
        auto_payload = build_m3_auto_render_payload(filenames, blobs, descriptions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    upload_items = [
        {
            "purpose": item["purpose"],
            "filename": item["filename"],
            "content_type": content_types.get(str(item["filename"]), "application/octet-stream"),
            "content": item["blob"],
            "description": item["description"],
            "page_index": item["page_index"],
        }
        for item in auto_payload.ordered_images
    ]
    table_items = [
        {
            "purpose": item["purpose"],
            "filename": item["filename"],
            "content_type": content_types.get(str(item["filename"]), "application/octet-stream"),
            "content": item["blob"],
            "page_index": item["page_index"],
        }
        for item in auto_payload.ordered_tables
    ]

    saved = get_store().save_m3_materials(
        project_id,
        auto_payload.texts,
        upload_items,
        table_items,
        auto_payload.page_texts,
    )
    if saved is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return saved


@app.post("/api/projects/{project_id}/analyze", response_model=ClassificationResult)
def analyze_project(project_id: int) -> dict:
    classification = get_store().analyze_project(project_id)
    if classification is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return classification


@app.get("/api/projects/{project_id}/classification", response_model=ClassificationResult)
def get_project_classification(project_id: int) -> dict:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    classification = get_store().get_classification(project_id)
    if classification is None:
        raise HTTPException(status_code=404, detail="识别结果尚未生成")
    return classification


@app.post("/api/projects/{project_id}/classification/review", response_model=ClassificationResult)
def review_project_classification(project_id: int, payload: ClassificationReviewRequest) -> dict:
    validate_project_type(payload.confirmed_project_type)
    classification = get_store().review_classification(
        project_id=project_id,
        confirmed_project_type=payload.confirmed_project_type,
        template_selection=payload.template_selection,
        confirmed_case_id=payload.confirmed_case_id,
        m3_selection=payload.m3_selection,
        include_print_tail_page=payload.include_print_tail_page,
        notes=payload.notes,
    )
    if isinstance(classification, dict) and classification.get("_validation_error") == "invalid_case_id":
        raise HTTPException(status_code=400, detail="confirmed_case_id 无效：未在推荐案例或案例库中找到该 ID")
    if classification is None:
        project = get_store().get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")
        raise HTTPException(status_code=404, detail="识别结果尚未生成")
    return classification


@app.post("/api/projects/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_project(project_id: int) -> dict:
    reviewed_project = get_store().generate_reviewed_project(project_id)
    if reviewed_project is not None:
        return {
            "project_id": project_id,
            "task_status": reviewed_project["task_status"],
            "status_history": reviewed_project["status_history"],
            "modules": reviewed_project["modules"],
            "quality_report": reviewed_project.get("quality_report", {}),
        }
    # 兼容旧 mock 链路：历史测试会在未 classification/review 时直接 generate + review。
    # 正式流程应先调用 /classification/review，再由 generate_reviewed_project 生成。
    project = get_store().generate_mock_outline(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "project_id": project_id,
        "task_status": project["task_status"],
        "status_history": project["status_history"],
        "modules": project["modules"],
        "quality_report": project.get("quality_report", {}),
    }


@app.get("/api/projects/{project_id}/task")
def get_project_task(project_id: int) -> dict:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {
        "project_id": project_id,
        "task_status": project["task_status"],
        "status_history": project["status_history"],
        "modules": project["modules"],
        "quality_report": project.get("quality_report", {}),
    }


@app.post("/api/projects/{project_id}/review", deprecated=True)
def review_project(project_id: int, payload: ReviewRequest) -> dict:
    """兼容旧 mock 人工确认接口；正式流程请使用 /classification/review。"""
    project = get_store().review_project(project_id, payload.approved, payload.notes)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project_id": project_id, "task_status": project["task_status"], "status_history": project["status_history"], "modules": project["modules"]}


@app.post("/api/projects/{project_id}/vector-index", response_model=VectorIndexResponse)
def index_project_vector(project_id: int, payload: VectorIndexRequest | None = None) -> dict:
    """
    Index parsed project files into the vector store.

    This endpoint is called after user confirmation. It reads parsed text files,
    generates chunks and embeddings, and stores them in pgvector.

    If file_ids is not provided in the request body, all files with parse_status='parsed'
    and a valid parsed_text_path will be indexed.

    Vector store must be configured via ZHONGCHI_VECTOR_DSN. If not configured,
    the endpoint returns an error but does not block the main flow.
    """
    file_ids = payload.file_ids if payload else None
    result = get_store().index_project_vector(project_id, file_ids)

    if result["status"] == "error" and "项目不存在" in result.get("message", ""):
        raise HTTPException(status_code=404, detail=result["message"])

    return result


@app.get("/api/projects/{project_id}/download")
def download_project(project_id: int) -> FileResponse:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    final_path = project.get("final_ppt_path")
    if not final_path:
        raise HTTPException(status_code=404, detail="最终PPTX尚未生成")

    # 路径穿越防护：final_ppt_path 必须落在数据目录的 outputs 下
    # （与 preview/slides、m3-full-render/download 端点保持一致）
    safe_dir = (get_data_dir() / "outputs").resolve()
    try:
        resolved = Path(final_path).resolve()
        if not resolved.is_relative_to(safe_dir):
            raise HTTPException(status_code=400, detail="无效的文件路径")
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="无效的文件路径")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="最终PPTX尚未生成")
    return FileResponse(resolved, filename=resolved.name)


@app.post("/api/projects/{project_id}/full-ppt-case", status_code=status.HTTP_201_CREATED)
def save_project_full_ppt_case(project_id: int) -> dict:
    try:
        saved = get_store().save_full_ppt_case(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return saved


@app.post("/api/projects/{project_id}/preview")
def generate_project_preview(project_id: int) -> dict:
    """生成或复用项目 PPT 预览图片。"""
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    final_path = project.get("final_ppt_path")
    if not final_path or not Path(final_path).exists():
        raise HTTPException(status_code=400, detail="最终PPTX尚未生成，请先完成PPT生成")
    try:
        from .ppt_preview import build_project_ppt_preview
        output_root = get_data_dir() / "outputs" / f"project_{project_id}"
        return build_project_ppt_preview(project_id, project, output_root)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/projects/{project_id}/preview/slides/{filename:path}")
def get_preview_slide(project_id: int, filename: str) -> FileResponse:
    """返回项目预览的单页 PNG 图片。仅允许读取当前项目 preview 目录下的 .png 文件。"""
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 路径穿越防护
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    safe_dir = (get_data_dir() / "outputs" / f"project_{project_id}" / "preview").resolve()
    file_path = safe_dir / filename

    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(safe_dir):
            raise HTTPException(status_code=400, detail="无效的文件名")
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="无效的文件名")

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="预览图片不存在")

    if resolved.suffix.lower() != ".png":
        raise HTTPException(status_code=400, detail="仅允许预览 PNG 文件")

    return FileResponse(resolved, media_type="image/png")


@app.get("/api/assets", deprecated=True)
def list_assets(module_id: str | None = None) -> list[dict]:
    """兼容旧资产调试查询接口，不作为正式生成主流程入口。"""
    if module_id is not None:
        validate_module_id(module_id)
    return get_store().get_assets(module_id)


@app.get("/api/projects/{project_id}/files/{file_id}/parsed-text")
def get_file_parsed_text(project_id: int, file_id: int) -> dict:
    """
    获取指定文件的完整解析文本。

    安全约束：
    - 必须根据 project_id 找到项目
    - 必须根据 file_id 找到该项目下的文件
    - 只读取该文件记录里的 parsed_text_path
    - 文件不存在、未解析、无文本时返回清晰错误或空结果
    """
    store = get_store()
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    state = store.load()
    file_record = next(
        (f for f in state["files"] if f["file_id"] == file_id and f["project_id"] == project_id),
        None,
    )
    if file_record is None:
        raise HTTPException(status_code=404, detail="文件不存在")

    parse_status = file_record.get("parse_status", "")
    if parse_status not in ("parsed",):
        return {
            "file_id": file_id,
            "filename": file_record.get("filename", ""),
            "parse_status": parse_status,
            "text": "",
            "error_message": f"文件 parse_status={parse_status}，尚无解析文本",
        }

    parsed_text_path = file_record.get("parsed_text_path", "")
    if not parsed_text_path:
        return {
            "file_id": file_id,
            "filename": file_record.get("filename", ""),
            "parse_status": parse_status,
            "text": "",
            "error_message": "文件无 parsed_text_path",
        }

    path = Path(parsed_text_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="解析文本文件不存在")

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return {
            "file_id": file_id,
            "filename": file_record.get("filename", ""),
            "parse_status": parse_status,
            "text": "",
            "error_message": f"读取解析文本失败：{exc}",
        }

    return {
        "file_id": file_id,
        "filename": file_record.get("filename", ""),
        "parse_status": parse_status,
        "text": text,
        "error_message": "",
    }


@app.get("/api/cases")
def list_cases() -> list[dict]:
    return get_store().get_cases()


@app.get("/api/cases/full-ppt")
def list_full_ppt_cases() -> list[dict]:
    return get_store().get_full_ppt_cases()


@app.get("/api/cases/full-ppt/{case_id}/download")
def download_full_ppt_case(case_id: str) -> FileResponse:
    case = get_store().get_full_ppt_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="完整PPT案例不存在")

    path = Path(str(case.get("source_path") or ""))
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="完整PPT案例文件不存在")
    if path.suffix.lower() != ".pptx":
        raise HTTPException(status_code=400, detail="完整PPT案例文件格式无效")

    library_root = (get_data_dir() / "full_ppt_case_library").resolve()
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(library_root):
            raise HTTPException(status_code=400, detail="完整PPT案例路径无效")
    except (ValueError, OSError):
        raise HTTPException(status_code=400, detail="完整PPT案例路径无效")

    return FileResponse(resolved, filename=case.get("filename") or resolved.name)


@app.post("/api/dev/llm-test", response_model=LlmTestResponse)
def dev_llm_test(payload: LlmTestRequest) -> dict:
    from .llm import test_llm_connection

    return test_llm_connection(payload.prompt)


def _ensure_ppt_engine_path() -> None:
    import sys

    code_dir = Path(__file__).resolve().parents[3]
    ppt_engine_dir = code_dir / "ppt_engine"
    if str(ppt_engine_dir) not in sys.path:
        sys.path.insert(0, str(ppt_engine_dir))


@app.post("/api/test/m3-full-render", response_model=M3FullRenderTestResponse)
async def m3_full_render_test(
    project_name: str = Form(...),
    descriptions: str = Form(""),
    purposes: list[str] = Form([]),
    files: list[UploadFile] = File([]),
) -> dict:
    """M3 完整独立测试接口：9 部分文字 + 图片替换，支持多图扩页。"""
    _ensure_ppt_engine_path()
    # 延迟导入，避免模块加载时强制依赖 pptx/ppt_engine
    from ppt_engine.renderer import render_m3_full_test_ppt  # noqa: E402
    from pptx import Presentation  # noqa: E402

    if not project_name or not project_name.strip():
        raise HTTPException(status_code=400, detail="project_name 不能为空")
    if purposes:
        raise HTTPException(status_code=400, detail="M3完整测试不再支持按模块手动上传，请按文件名自动分类批量上传")

    from .m3_auto_matcher import build_m3_auto_render_payload

    filenames: list[str] = []
    blobs: list[bytes] = []
    for upload in files:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix == ".xls":
            raise HTTPException(status_code=400, detail=f"M3完整测试暂不支持 .xls 旧版表格：{upload.filename}")
        if suffix != ".xlsx" and not (upload.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail=f"文件不是图片：{upload.filename}")
        filenames.append(upload.filename or "upload")
        blobs.append(await _read_file_with_size_limit(upload, upload.filename or "M3图片"))
    try:
        auto_payload = build_m3_auto_render_payload(filenames, blobs, descriptions)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    output_dir = _get_m3_full_test_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        pptx_path = render_m3_full_test_ppt(
            project_name,
            auto_payload.texts,
            auto_payload.images_by_purpose,
            output_dir,
            auto_payload.page_texts,
            auto_payload.tables_by_purpose,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"M3 完整测试模板缺失：{exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"M3 完整测试渲染失败：{exc}")

    summary = {purpose: len(items) for purpose, items in auto_payload.images_by_purpose.items()}
    table_summary = {purpose: len(items) for purpose, items in auto_payload.tables_by_purpose.items()}
    filename = pptx_path.name
    slide_count = len(Presentation(str(pptx_path)).slides)
    return {
        "ok": True,
        "pptx_path": str(pptx_path),
        "download_url": f"/api/test/m3-full-render/download/{filename}",
        "slide_count": slide_count,
        "image_summary": summary,
        "table_summary": table_summary,
    }


@app.get("/api/test/m3-full-render/download/{filename:path}")
def m3_full_render_download(filename: str) -> FileResponse:
    """下载 M3 完整测试生成的 PPTX 文件。"""
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    safe_dir = _get_m3_full_test_output_dir().resolve()
    file_path = safe_dir / filename

    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(safe_dir):
            raise HTTPException(status_code=400, detail="无效的文件名")
    except Exception:
        raise HTTPException(status_code=400, detail="无效的文件名")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(resolved, filename=filename)


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
