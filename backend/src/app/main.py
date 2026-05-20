from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .constants import ALLOWED_EXTENSIONS, ALLOWED_MODULE_IDS, PROJECT_TYPES
from .schemas import ClassificationResult, ClassificationReviewRequest, DocumentParseTestResult, LlmTestRequest, LlmTestResponse, M3ImageRenderTestResponse, M3RenderTestRequest, M3RenderTestResponse, Project, ProjectCreate, ProjectUpdate, ReviewRequest, StoredFile, VectorIndexRequest, VectorIndexResponse
from .storage import get_data_dir, get_store

# 在模块加载时将 ppt_engine 路径注入 sys.path（供 TestClient 共享）
import sys as _sys
_ppt_engine_root = Path(__file__).resolve().parents[3] / "ppt_engine"
if str(_ppt_engine_root) not in _sys.path:
    _sys.path.insert(0, str(_ppt_engine_root))
del _sys, _ppt_engine_root


def _m3_safe_filename(name: str) -> str:
    """清洗文件名，移除 Windows 非法字符。"""
    illegal = '\\/:*?"<>|'
    for ch in illegal:
        name = name.replace(ch, "_")
    return name or "unnamed"


def _get_m3_test_output_dir() -> Path:
    """获取 M3 测试输出目录，运行时解析（受 ZHONGCHI_DATA_DIR 影响）。"""
    return get_data_dir() / "outputs" / "m3_test"


def _get_m3_image_test_output_dir() -> Path:
    """获取 M3 图片替换测试输出目录，运行时解析（受 ZHONGCHI_DATA_DIR 影响）。"""
    return get_data_dir() / "outputs" / "m3_image_test"

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


@app.post("/api/projects/{project_id}/modules/{module_id}/files", response_model=StoredFile, status_code=status.HTTP_201_CREATED)
async def upload_module_file(project_id: int, module_id: str, file: UploadFile = File(...)) -> dict:
    validate_module_id(module_id)
    validate_extension(file.filename or "")
    content = await file.read()
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
        upload_items.append((file.filename or "upload", file.content_type or "application/octet-stream", await file.read()))
    file_records = get_store().add_project_files(project_id=project_id, files=upload_items)
    if file_records is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return file_records


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
        notes=payload.notes,
    )
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
        }
    project = get_store().generate_mock_outline(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project_id": project_id, "task_status": project["task_status"], "status_history": project["status_history"], "modules": project["modules"]}


@app.get("/api/projects/{project_id}/task")
def get_project_task(project_id: int) -> dict:
    project = get_store().get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"project_id": project_id, "task_status": project["task_status"], "status_history": project["status_history"], "modules": project["modules"]}


@app.post("/api/projects/{project_id}/review")
def review_project(project_id: int, payload: ReviewRequest) -> dict:
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
    if not final_path or not Path(final_path).exists():
        raise HTTPException(status_code=404, detail="最终PPTX尚未生成")
    return FileResponse(final_path, filename=Path(final_path).name)


@app.get("/api/assets")
def list_assets(module_id: str | None = None) -> list[dict]:
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


@app.post("/api/dev/llm-test", response_model=LlmTestResponse)
def dev_llm_test(payload: LlmTestRequest) -> dict:
    from .llm import test_llm_connection

    return test_llm_connection(payload.prompt)


def _ensure_ppt_engine_path() -> None:
    import sys
    from pathlib import Path as PP

    code_dir = Path(__file__).resolve().parents[3]
    ppt_engine_dir = code_dir / "ppt_engine"
    if str(ppt_engine_dir) not in sys.path:
        sys.path.insert(0, str(ppt_engine_dir))


@app.post("/api/test/m3-render", response_model=M3RenderTestResponse)
def m3_render_test(payload: M3RenderTestRequest) -> dict:
    """M3 独立测试接口：将模拟资料文本替换到 M3 PPT 模板并输出独立 PPTX。

    不接入正式生产流程，不修改 render_project_ppt() 的行为。
    输出文件存放在 data/outputs/m3_test/ 目录下（受 ZHONGCHI_DATA_DIR 影响）。
    """
    _ensure_ppt_engine_path()
    from ppt_engine.renderer import build_m3_replacement_map, render_m3_test_ppt

    if not payload.project_name or not payload.project_name.strip():
        raise HTTPException(status_code=400, detail="project_name 不能为空")

    safe_name = _m3_safe_filename(payload.project_name)
    project = {
        "project_name": payload.project_name,
        "project_location": payload.project_location,
        "owner_unit": payload.owner_unit,
        "product_line": payload.product_line,
    }

    output_dir = _get_m3_test_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 构建替换映射（用于返回给前端）
        replacements = build_m3_replacement_map(project, payload.parsed_sources)

        pptx_path = render_m3_test_ppt(project, payload.parsed_sources, output_dir)
        filename = pptx_path.name
        return {
            "ok": True,
            "pptx_path": str(pptx_path),
            "download_url": f"/api/test/m3-render/download/{filename}",
            "replacements": replacements,
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"M3 模板缺失：{exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"M3 渲染失败：{exc}")


@app.get("/api/test/m3-render/download/{filename}")
def m3_render_download(filename: str) -> FileResponse:
    """下载 M3 测试生成的 PPTX 文件。

    安全约束：
    - 只允许下载 data/outputs/m3_test 目录下的文件
    - 防止路径穿越（不允许 .. 或绝对路径）
    """
    # 防止路径穿越：禁止包含 .. 或绝对路径标记
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    # 白名单：限制在 m3_test 目录（运行时解析，受 ZHONGCHI_DATA_DIR 影响）
    safe_dir = _get_m3_test_output_dir().resolve()
    file_path = safe_dir / filename

    # 确保文件在安全目录内
    try:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(safe_dir):
            raise HTTPException(status_code=400, detail="无效的文件名")
    except Exception:
        raise HTTPException(status_code=400, detail="无效的文件名")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(resolved, filename=filename)


@app.post("/api/test/m3-image-render", response_model=M3ImageRenderTestResponse)
async def m3_image_render_test(
    project_name: str = Form(...),
    purposes: list[str] = Form(...),
    files: list[UploadFile] = File(...),
) -> dict:
    """M3 图片替换独立测试接口，不接入正式生产流程。"""
    _ensure_ppt_engine_path()
    from ppt_engine.renderer import M3_IMAGE_PURPOSES, render_m3_image_test_ppt

    if not project_name or not project_name.strip():
        raise HTTPException(status_code=400, detail="project_name 不能为空")
    if len(files) != len(purposes):
        raise HTTPException(status_code=400, detail="图片文件数量和用途数量必须一致")

    images_by_purpose: dict[str, list[bytes]] = {}
    for purpose, upload in zip(purposes, files):
        if purpose not in M3_IMAGE_PURPOSES:
            raise HTTPException(status_code=400, detail=f"非法图片用途：{purpose}")
        if not (upload.content_type or "").startswith("image/"):
            raise HTTPException(status_code=400, detail=f"文件不是图片：{upload.filename}")
        blob = await upload.read()
        images_by_purpose.setdefault(purpose, []).append(blob)

    output_dir = _get_m3_image_test_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        pptx_path = render_m3_image_test_ppt(project_name, images_by_purpose, output_dir)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"M3 图片测试模板缺失：{exc}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"M3 图片替换失败：{exc}")

    summary = {purpose: len(items) for purpose, items in images_by_purpose.items()}
    filename = pptx_path.name
    return {
        "ok": True,
        "pptx_path": str(pptx_path),
        "download_url": f"/api/test/m3-image-render/download/{filename}",
        "image_summary": summary,
    }


@app.get("/api/test/m3-image-render/download/{filename}")
def m3_image_render_download(filename: str) -> FileResponse:
    """下载 M3 图片替换测试生成的 PPTX 文件。"""
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")

    safe_dir = _get_m3_image_test_output_dir().resolve()
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


# =============================================================================
# DEPRECATED ENDPOINT — 前端已不再调用此端点
# 文档解析测试现已改为调用真实业务流程：
#   POST /api/projects/{id}/files  →  上传文件到真实项目
#   POST /api/projects/{id}/analyze  →  走 document_analysis + _detect_project_type + match_cases 全流程
#   GET  /api/projects/{id}/classification  →  获取包含每个文件 parse_status/document_role/assigned_modules 的结果
# 此端点保留用于向后兼容，不建议在生产流程中使用。
# =============================================================================
@app.post("/api/document-parse-test", response_model=list[DocumentParseTestResult], status_code=status.HTTP_200_OK, deprecated=True)
async def document_parse_test(files: list[UploadFile] = File(...)) -> list[dict]:
    from .document_analysis import analyze_document, classify_document
    from .storage import get_store
    import tempfile
    from pathlib import Path

    results: list[dict] = []
    store = get_store()

    for file in files:
        filename = file.filename or "upload"
        suffix = Path(filename).suffix.lower()
        content_type = file.content_type or "application/octet-stream"

        # Check extension
        if suffix not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": filename,
                "suffix": suffix,
                "content_type": content_type,
                "parse_status": "failed",
                "document_role": "unknown",
                "assigned_modules": [],
                "text": "",
                "text_preview": "",
                "sections": [],
                "tables": [],
                "slides": [],
                "metadata": {},
                "error_message": f"不支持的文件类型: {suffix}",
            })
            continue

        # Read file content
        try:
            content = await file.read()
        except Exception as exc:
            results.append({
                "filename": filename,
                "suffix": suffix,
                "content_type": content_type,
                "parse_status": "failed",
                "document_role": "unknown",
                "assigned_modules": [],
                "text": "",
                "text_preview": "",
                "sections": [],
                "tables": [],
                "slides": [],
                "metadata": {},
                "error_message": f"文件读取失败: {exc}",
            })
            continue

        # Handle CAD (not images — images now go through analyze_document)
        if suffix in {".dwg", ".dxf"}:
            context_text = ""
            role, modules = classify_document(filename, "", context_text)
            results.append({
                "filename": filename,
                "suffix": suffix,
                "content_type": content_type,
                "parse_status": "pending_enhancement",
                "document_role": role,
                "assigned_modules": modules,
                "text": "",
                "text_preview": "",
                "sections": [],
                "tables": [],
                "slides": [],
                "metadata": {"original_size_bytes": len(content)},
                "error_message": "CAD 文件当前返回 pending_enhancement，不接入大模型，不编造内容。",
            })
            continue

        # Save to temp file for parsing
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            analysis = analyze_document(filename, tmp_path)

            text_preview = analysis.extracted_text[:200] if analysis.extracted_text else ""

            # Extract sections/tables/slides based on file type
            sections: list[str] = []
            tables: list[dict] = []
            slides: list[dict] = []

            if suffix == ".txt":
                text = analysis.extracted_text
                sections = [line.strip() for line in text.split("\n") if line.strip()][:50]

            elif suffix == ".pdf":
                text = analysis.extracted_text
                sections = [line.strip() for line in text.split("\n") if line.strip()][:50]
                # Use MinerU parse status directly; no longer infer "pending_ocr" from empty text
                results.append({
                    "filename": filename,
                    "suffix": suffix,
                    "content_type": content_type,
                    "parse_status": analysis.parse_status,
                    "document_role": analysis.document_role,
                    "assigned_modules": analysis.assigned_modules,
                    "text": text,
                    "text_preview": text[:200] if text else "",
                    "sections": sections,
                    "tables": [],
                    "slides": [],
                    "metadata": {"original_size_bytes": len(content)},
                    "error_message": analysis.error_message,
                })
                continue

            elif suffix == ".docx":
                text = analysis.extracted_text
                sections = [line.strip() for line in text.split("\n") if line.strip()][:50]
                # Extract tables from docx - tables are in word/document.xml as w:tbl elements
                import zipfile
                from xml.etree import ElementTree
                try:
                    with zipfile.ZipFile(tmp_path) as z:
                        if "word/document.xml" in z.namelist():
                            doc_xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
                            doc_root = ElementTree.fromstring(doc_xml)
                            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
                            for tbl in doc_root.iter(f"{ns}tbl"):
                                table_texts = []
                                for t in tbl.iter(f"{ns}t"):
                                    if t.text and t.text.strip():
                                        table_texts.append(t.text.strip())
                                if table_texts:
                                    tables.append({"table_index": len(tables), "text": " ".join(table_texts[:100])})
                except Exception:
                    pass

            elif suffix == ".doc":
                # fallback for old .doc format
                text = analysis.extracted_text
                results.append({
                    "filename": filename,
                    "suffix": suffix,
                    "content_type": content_type,
                    "parse_status": "parsed",
                    "document_role": analysis.document_role,
                    "assigned_modules": analysis.assigned_modules,
                    "text": text,
                    "text_preview": text_preview,
                    "sections": [line.strip() for line in text.split("\n") if line.strip()][:50],
                    "tables": [],
                    "slides": [],
                    "metadata": {"original_size_bytes": len(content)},
                    "error_message": ".doc 老格式解析能力有限，仅提取了部分文本。",
                })
                continue

            elif suffix == ".xlsx":
                import zipfile
                from xml.etree import ElementTree
                text_parts: list[str] = []
                try:
                    with zipfile.ZipFile(tmp_path) as z:
                        # Get shared strings
                        shared_strings: list[str] = []
                        if "xl/sharedStrings.xml" in z.namelist():
                            ss_xml = z.read("xl/sharedStrings.xml").decode("utf-8", errors="ignore")
                            ss_root = ElementTree.fromstring(ss_xml)
                            for si in ss_root:
                                t_texts = []
                                for t in si.iter():
                                    if t.text:
                                        t_texts.append(t.text)
                                shared_strings.append("".join(t_texts))

                        # Get real sheet names from workbook.xml
                        sheet_name_map: dict[int, str] = {}
                        if "xl/workbook.xml" in z.namelist():
                            wb_xml = z.read("xl/workbook.xml").decode("utf-8", errors="ignore")
                            wb_root = ElementTree.fromstring(wb_xml)
                            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                            for idx, sheet in enumerate(wb_root.iter(f"{ns}sheet")):
                                name = sheet.get("name", f"Sheet{idx + 1}")
                                sheet_name_map[idx + 1] = name
                        else:
                            for i in range(1, 20):
                                sheet_name_map[i] = f"Sheet{i}"

                        # Get sheet files
                        sheet_files = sorted([n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")])
                        for idx, sheet_file in enumerate(sheet_files):
                            sheet_xml = z.read(sheet_file).decode("utf-8", errors="ignore")
                            sheet_root = ElementTree.fromstring(sheet_xml)
                            rows_data: list[list[str]] = []
                            for row in sheet_root.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                                row_cells = []
                                for cell in row:
                                    cell_type = cell.get("t", "")
                                    v = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                                    if v is not None and v.text is not None:
                                        if cell_type == "s":
                                            try:
                                                row_cells.append(shared_strings[int(v.text)])
                                            except (ValueError, IndexError):
                                                row_cells.append(v.text)
                                        else:
                                            row_cells.append(v.text)
                                    else:
                                        row_cells.append("")
                                rows_data.append(row_cells)

                            preview_rows = rows_data[:20] if rows_data else []
                            sheet_name = sheet_name_map.get(idx + 1, f"Sheet{idx + 1}")
                            sheet_text = " ".join([" | ".join(row) for row in rows_data])
                            text_parts.append(f"[{sheet_name}] {sheet_text}")

                            slides.append({
                                "sheet_index": idx + 1,
                                "sheet_name": sheet_name,
                                "rows": len(rows_data),
                                "columns": len(rows_data[0]) if rows_data else 0,
                                "preview_rows": preview_rows,
                                "text": sheet_text[:500],
                            })
                except Exception as exc:
                    pass

                text = " ".join(text_parts) if text_parts else analysis.extracted_text

            elif suffix == ".xls":
                results.append({
                    "filename": filename,
                    "suffix": suffix,
                    "content_type": content_type,
                    "parse_status": "pending_enhancement",
                    "document_role": analysis.document_role,
                    "assigned_modules": analysis.assigned_modules,
                    "text": analysis.extracted_text,
                    "text_preview": analysis.extracted_text[:200],
                    "sections": [],
                    "tables": [],
                    "slides": [],
                    "metadata": {"original_size_bytes": len(content)},
                    "error_message": ".xls 老格式当前返回 pending_enhancement，不支持结构化解析。",
                })
                continue

            elif suffix == ".pptx":
                import zipfile
                from xml.etree import ElementTree
                try:
                    with zipfile.ZipFile(tmp_path) as z:
                        slide_files = sorted([n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")])
                        for idx, slide_file in enumerate(slide_files):
                            xml_content = z.read(slide_file).decode("utf-8", errors="ignore")
                            root = ElementTree.fromstring(xml_content)
                            texts = []
                            for t in root.iter():
                                if t.text and t.text.strip():
                                    texts.append(t.text.strip())
                            slide_text = " ".join(texts)
                            title = texts[0] if texts else ""
                            slides.append({
                                "slide_index": idx + 1,
                                "title": title,
                                "texts": texts[:20],
                            })
                except Exception:
                    pass
                text = analysis.extracted_text

            elif suffix == ".ppt":
                results.append({
                    "filename": filename,
                    "suffix": suffix,
                    "content_type": content_type,
                    "parse_status": "pending_enhancement",
                    "document_role": analysis.document_role,
                    "assigned_modules": analysis.assigned_modules,
                    "text": analysis.extracted_text,
                    "text_preview": analysis.extracted_text[:200],
                    "sections": [],
                    "tables": [],
                    "slides": [],
                    "metadata": {"original_size_bytes": len(content)},
                    "error_message": ".ppt 老格式当前返回 pending_enhancement，不支持结构化解析。",
                })
                continue

            else:
                text = analysis.extracted_text

            results.append({
                "filename": filename,
                "suffix": suffix,
                "content_type": content_type,
                "parse_status": analysis.parse_status,
                "document_role": analysis.document_role,
                "assigned_modules": analysis.assigned_modules,
                "text": text if suffix != ".xlsx" else "\n".join(text_parts),
                "text_preview": text_preview,
                "sections": sections if suffix not in {".xlsx", ".pptx"} else [],
                "tables": tables,
                "slides": slides if suffix in {".xlsx", ".pptx"} else [],
                "metadata": {"original_size_bytes": len(content)},
                "error_message": analysis.error_message,
            })

        except Exception as exc:
            results.append({
                "filename": filename,
                "suffix": suffix,
                "content_type": content_type,
                "parse_status": "failed",
                "document_role": "unknown",
                "assigned_modules": [],
                "text": "",
                "text_preview": "",
                "sections": [],
                "tables": [],
                "slides": [],
                "metadata": {},
                "error_message": str(exc),
            })
        finally:
            Path(tmp_path).unlink()

    return results


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
