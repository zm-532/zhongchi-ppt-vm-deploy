from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .constants import ALLOWED_EXTENSIONS, ALLOWED_MODULE_IDS, PROJECT_TYPES
from .schemas import ClassificationResult, ClassificationReviewRequest, Project, ProjectCreate, ReviewRequest, StoredFile
from .storage import get_store

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


@app.get("/api/cases")
def list_cases() -> list[dict]:
    return get_store().get_cases()


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
