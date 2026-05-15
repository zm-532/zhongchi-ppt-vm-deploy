"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const statuses = ["待上传", "资料解析中", "类型识别中", "案例匹配中", "待确认", "生成中", "合并中", "完成"];

const projectTypes = [
  { value: "highway", label: "公路" },
  { value: "railway", label: "铁路" },
  { value: "metro", label: "轨道交通/地铁" },
  { value: "existing_rail_transit", label: "铁路/轨交既有线" },
];

const m1m2Templates = [
  { value: "highway", label: "公路全封闭声屏障（M1_&_M2）.pptx" },
  { value: "metro", label: "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx" },
  { value: "existing_rail_transit", label: "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx" },
  { value: "railway", label: "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx" },
];

type ViewId = "projects" | "create" | "cases" | "m1m2-test" | "m5-test" | "document-parse-test";
type Project = {
  project_id: number;
  project_name: string;
  project_location?: string;
  owner_unit?: string;
  product_line?: string;
  task_status: string;
  status_history?: string[];
  final_ppt_path?: string;
};
type StoredFile = { file_id: number; filename: string; content_type?: string; document_role?: string; assigned_modules?: string[] };
type CaseSelection = {
  recommended_cases?: Array<{ case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string }>;
  confirmed_case_id?: number | string | null;
  status?: string;
  message?: string;
};
type ClassificationResult = {
  detected_project_type?: string;
  confirmed_project_type?: string;
  confidence?: number;
  matched_keywords?: string[];
  detection_evidence?: Array<{ project_type?: string; keyword?: string; source?: string; snippet?: string }>;
  template_selection?: {
    M1_M2?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
    M5?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
    M6?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
  };
  case_selection?: CaseSelection;
  missing_fields?: string[];
};
type TaskState = { project_id: number; task_status: string; status_history: string[] };
type ReviewForm = { projectType: string; m1m2Template: string; caseId?: string; notes: string };
type RecommendedCase = { case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string };
type DocumentParseSlide = { slide_index?: number; sheet_name?: string; title?: string; rows?: number; columns?: number; preview_rows?: string[][]; texts?: string[]; text?: string };
type DocumentParseTestResult = {
  filename: string; suffix: string; content_type: string; parse_status: string;
  document_role: string; assigned_modules: string[]; text: string;
  text_preview: string; sections: string[]; tables: Array<Record<string, unknown>>;
  slides: DocumentParseSlide[]; metadata: Record<string, unknown>; error_message: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const PROJECT_LIST_PREVIEW_LIMIT = 10;
const viewTitles: Record<ViewId, { title: string; description: string }> = {
  projects: { title: "我的项目", description: "创建项目、统一上传项目资料，并确认系统识别结果。" },
  create: { title: "新建项目", description: "填写基础信息后创建一个新的售前 PPT 项目。" },
  cases: { title: "案例库管理", description: "维护历史案例，供系统按项目标签推荐引用。" },
  "m1m2-test": { title: "M1/M2选择测试", description: "上传测试资料，根据文件名和解析文本识别项目类型并选择对应 M1/M2 固化模板。" },
  "m5-test": { title: "M5选择测试", description: "上传测试资料，根据项目标签从案例库匹配相似案例并显示匹配理由。" },
  "document-parse-test": { title: "文档解析测试", description: "用于测试不同格式资料的文本与结构化解析效果。" },
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(await response.text());
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function labelForProjectType(value?: string) {
  return projectTypes.find((item) => item.value === value)?.label ?? value ?? "待识别";
}

function firstTemplateName(item?: { template_path?: string; template_name?: string; template_key?: string; template_filename?: string }) {
  if (!item) return "待识别";
  return item.template_filename || item.template_name || item.template_path?.split(/[\\/]/).pop() || item.template_key || "待识别";
}

export default function HomePage() {
  const [activeView, setActiveView] = useState<ViewId>("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [task, setTask] = useState<TaskState | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<StoredFile[]>([]);
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  const [reviewForm, setReviewForm] = useState<ReviewForm>({ projectType: "", m1m2Template: "", caseId: undefined, notes: "" });
  const [m1m2TestFiles, setM1m2TestFiles] = useState<File[]>([]);
  const [m1m2TestProjectName, setM1m2TestProjectName] = useState("M1/M2选择测试项目");
  const [m1m2TestResult, setM1m2TestResult] = useState<ClassificationResult | null>(null);
  const [m1m2TestUploadedFiles, setM1m2TestUploadedFiles] = useState<StoredFile[]>([]);
  const [m1m2TestMessage, setM1m2TestMessage] = useState("请选择一个或多个资料文件后开始测试。");
  const [m5TestFiles, setM5TestFiles] = useState<File[]>([]);
  const [m5TestProjectName, setM5TestProjectName] = useState("M5案例匹配测试项目");
  const [m5TestResult, setM5TestResult] = useState<ClassificationResult | null>(null);
  const [m5TestUploadedFiles, setM5TestUploadedFiles] = useState<StoredFile[]>([]);
  const [m5TestMessage, setM5TestMessage] = useState("请上传项目资料，系统将根据案例库匹配相似案例。");
  const [documentParseTestFiles, setDocumentParseTestFiles] = useState<File[]>([]);
  const [documentParseTestResults, setDocumentParseTestResults] = useState<DocumentParseTestResult[]>([]);
  const [documentParseTestMessage, setDocumentParseTestMessage] = useState("请上传文件以测试解析效果。");
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("请先创建项目，再统一上传项目资料。");
  const [projectListExpanded, setProjectListExpanded] = useState(false);
  const [isManagingProjects, setIsManagingProjects] = useState(false);
  const [selectedProjectIds, setSelectedProjectIds] = useState<number[]>([]);
  const activeStatus = task?.task_status ?? currentProject?.task_status ?? "待上传";
  const recommendedCases = useMemo(() => classification?.case_selection?.recommended_cases ?? [], [classification]);
  const hasMoreProjects = projects.length > PROJECT_LIST_PREVIEW_LIMIT;
  const visibleProjects = projectListExpanded ? projects : projects.slice(0, PROJECT_LIST_PREVIEW_LIMIT);

  const statusHistory = useMemo(
    () => (task?.status_history ?? currentProject?.status_history ?? ["待上传"]).join(" -> "),
    [currentProject, task],
  );

  useEffect(() => {
    function syncViewFromHash() {
      const nextView = window.location.hash.replace("#", "");
      setActiveView(nextView === "create" || nextView === "cases" || nextView === "m1m2-test" || nextView === "m5-test" || nextView === "document-parse-test" ? nextView : "projects");
    }

    syncViewFromHash();
    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  useEffect(() => {
    requestJson<Project[]>("/api/projects")
      .then((items) => {
        setProjects(items);
        if (items[0]) setCurrentProject(items[0]);
      })
      .catch(() => setMessage("后端未连接，请确认 FastAPI 运行在 127.0.0.1:8000。"));
  }, []);

  useEffect(() => {
    const detectedType = classification?.confirmed_project_type || classification?.detected_project_type || "";
    const templateKey = classification?.template_selection?.M1_M2?.template_key || detectedType;
    const confirmedCaseId = classification?.case_selection?.confirmed_case_id;

    setReviewForm((value) => {
      // 只有在 caseId 从未设置过（undefined）时才用默认值初始化，
      // 一旦用户明确选择过（包括空字符串），就不再覆盖。
      const needsInitCaseId = value.caseId === undefined || value.caseId === null;
      let newCaseId = value.caseId;
      if (needsInitCaseId) {
        // 首次初始化：优先用后端确认的 caseId，其次用推荐列表第一个，均无则为 null（表示暂不选择）
        newCaseId = confirmedCaseId !== undefined && confirmedCaseId !== null
          ? String(confirmedCaseId)
          : (recommendedCases[0]?.case_id !== undefined ? String(recommendedCases[0].case_id) : "");
      }

      return {
        ...value,
        projectType: value.projectType || detectedType || "",
        m1m2Template: value.m1m2Template || templateKey || "",
        caseId: newCaseId,
      };
    });
  }, [classification, recommendedCases]);

  async function createProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    try {
      const formData = new FormData(event.currentTarget);
      const project = await requestJson<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: formData.get("project_name") || "中驰智能PPT演示项目",
          project_location: formData.get("project_location") || "",
          owner_unit: formData.get("owner_unit") || "",
          product_line: formData.get("product_line") || "",
        }),
      });
      setProjects((items) => [project, ...items]);
      setCurrentProject(project);
      setTask(null);
      setUploadedFiles([]);
      setUploadSuccess(false);
      setClassification(null);
      setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, notes: "" });
      setActiveView("projects");
      window.location.hash = "projects";
      setMessage(`项目已创建：${project.project_name}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "创建项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function uploadProjectFiles() {
    if (!currentProject) return setMessage("请先创建项目。");
    if (selectedFiles.length === 0) return setMessage("请先选择需要上传的项目资料。");
    setBusy(true);
    try {
      const body = new FormData();
      selectedFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[] | StoredFile>(`/api/projects/${currentProject.project_id}/files`, { method: "POST", body });
      setUploadedFiles(Array.isArray(stored) ? stored : [stored]);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      setSelectedFiles([]);
      setUploadSuccess(true);
      setMessage("项目资料已统一上传，可点击开始识别资料。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "统一上传失败");
    } finally {
      setBusy(false);
    }
  }

  async function analyzeProject() {
    if (!currentProject) return setMessage("请先创建项目。");
    setBusy(true);
    try {
      await requestJson(`/api/projects/${currentProject.project_id}/analyze`, { method: "POST" });
      const result = await requestJson<ClassificationResult>(`/api/projects/${currentProject.project_id}/classification`);
      setClassification(result);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      setMessage("识别结果已返回，请确认项目类型、模板与案例。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "资料识别失败");
    } finally {
      setBusy(false);
    }
  }

  async function submitClassificationReview() {
    if (!currentProject) return setMessage("请先创建项目。");
    setBusy(true);
    try {
      await requestJson(`/api/projects/${currentProject.project_id}/classification/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          confirmed_project_type: reviewForm.projectType,
          template_selection: {
            M1_M2: { template_key: reviewForm.m1m2Template },
            M5: classification?.template_selection?.M5,
            M6: classification?.template_selection?.M6,
          },
          confirmed_case_id: reviewForm.caseId || null,
          notes: reviewForm.notes || "前端人工确认",
        }),
      });
      const latest = await requestJson<ClassificationResult>(`/api/projects/${currentProject.project_id}/classification`);
      setClassification(latest);
      const caseMsg = reviewForm.caseId ? "" : "（本次不使用 M5 案例）";
      setMessage(`人工确认已提交${caseMsg}，可启动最终生成。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "人工确认失败");
    } finally {
      setBusy(false);
    }
  }

  async function generate() {
    if (!currentProject) return setMessage("请先创建项目。");
    setBusy(true);
    try {
      await requestJson<TaskState>(`/api/projects/${currentProject.project_id}/generate`, { method: "POST" });
      const latest = await requestJson<TaskState>(`/api/projects/${currentProject.project_id}/task`);
      setTask(latest);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      setMessage(`生成任务已启动，当前状态：${latest.task_status}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "启动生成失败");
    } finally {
      setBusy(false);
    }
  }

  async function saveToVectorStore() {
    if (!currentProject) return setMessage("请先创建项目。");
    setBusy(true);
    try {
      const result = await requestJson<{ status: string; indexed_files: number; indexed_chunks: number; skipped_files: string[]; message: string }>(
        `/api/projects/${currentProject.project_id}/vector-index`,
        { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) }
      );
      if (result.status === "not_configured") {
        setMessage(result.message || "向量库未配置（ZHONGCHI_VECTOR_DSN 未设置），未实际入库。");
      } else if (result.status === "error" || (result.indexed_chunks === 0 && result.skipped_files.length > 0)) {
        setMessage("当前没有可存入向量库的解析文本。");
      } else {
        setMessage(`已存入向量库：${result.indexed_files} 个文件，${result.indexed_chunks} 个文本块。`);
      }
      // Refresh current project to get updated vector_status
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "存入向量库失败");
    } finally {
      setBusy(false);
    }
  }

  function toggleProjectManagement() {
    setIsManagingProjects((value) => !value);
    setSelectedProjectIds([]);
  }

  function toggleProjectSelection(projectId: number) {
    setSelectedProjectIds((ids) => (ids.includes(projectId) ? ids.filter((id) => id !== projectId) : [...ids, projectId]));
  }

  async function deleteSelectedProjects() {
    if (selectedProjectIds.length === 0) return setMessage("请先选择要删除的项目。");
    setBusy(true);
    try {
      const idsToDelete = [...selectedProjectIds];
      await Promise.all(idsToDelete.map((projectId) => requestJson(`/api/projects/${projectId}`, { method: "DELETE" })));
      const remainingProjects = projects.filter((project) => !idsToDelete.includes(project.project_id));
      setProjects(remainingProjects);
      setSelectedProjectIds([]);
      if (currentProject && idsToDelete.includes(currentProject.project_id)) {
        setCurrentProject(remainingProjects[0] ?? null);
        setTask(null);
        setClassification(null);
      }
      setMessage(`已删除 ${idsToDelete.length} 个项目。`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "删除项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function runM1M2TemplateTest() {
    if (m1m2TestFiles.length === 0) return setM1m2TestMessage("请先选择一个或多个测试资料文件。");
    setBusy(true);
    setM1m2TestResult(null);
    setM1m2TestUploadedFiles([]);
    try {
      const project = await requestJson<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: m1m2TestProjectName || "M1/M2选择测试项目",
          project_location: "",
          owner_unit: "",
          product_line: "",
        }),
      });
      const body = new FormData();
      m1m2TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM1m2TestUploadedFiles(stored);
      setM1m2TestResult(result);
      setProjects((items) => [project, ...items]);
      setM1m2TestMessage("M1/M2 类型识别与模板选择已完成。");
    } catch (error) {
      setM1m2TestMessage(error instanceof Error ? error.message : "M1/M2 选择测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function runM5CaseTest() {
    if (m5TestFiles.length === 0) return setM5TestMessage("请先选择一个或多个测试资料文件。");
    setBusy(true);
    setM5TestResult(null);
    setM5TestUploadedFiles([]);
    try {
      const project = await requestJson<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: m5TestProjectName || "M5案例匹配测试项目",
          project_location: "",
          owner_unit: "",
          product_line: "",
        }),
      });
      const body = new FormData();
      m5TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM5TestUploadedFiles(stored);
      setM5TestResult(result);
      setProjects((items) => [project, ...items]);
      const cases = result.case_selection?.recommended_cases;
      if (cases && cases.length > 0) {
        setM5TestMessage(`案例匹配完成，找到 ${cases.length} 个相似案例。`);
      } else {
        setM5TestMessage("未找到高匹配案例，请检查案例库或上传更完整的项目资料。");
      }
    } catch (error) {
      setM5TestMessage(error instanceof Error ? error.message : "M5 案例匹配测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function runDocumentParseTest() {
    if (documentParseTestFiles.length === 0) return setDocumentParseTestMessage("请先选择要测试的文件。");
    setBusy(true);
    setDocumentParseTestResults([]);
    try {
      const body = new FormData();
      documentParseTestFiles.forEach((file) => body.append("files", file));
      const results = await requestJson<DocumentParseTestResult[]>("/api/document-parse-test", { method: "POST", body });
      setDocumentParseTestResults(results);
      setDocumentParseTestMessage(`解析完成，共 ${results.length} 个文件。`);
    } catch (error) {
      setDocumentParseTestMessage(error instanceof Error ? error.message : "解析测试失败");
    } finally {
      setBusy(false);
    }
  }

  function downloadFinal() {
    if (!currentProject) return setMessage("请先创建项目。");
    window.location.href = `${API_BASE}/api/projects/${currentProject.project_id}/download`;
  }

  const pageTitle = viewTitles[activeView];

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand"><div className="brandMark" aria-hidden="true" /><div><strong>中驰售前PPT助手</strong></div></div>
        <nav>
          <a className={activeView === "projects" ? "navItem active" : "navItem"} href="#projects">我的项目</a>
          <a className={activeView === "create" ? "navItem active" : "navItem"} href="#create">新建项目</a>
          <a className={activeView === "cases" ? "navItem active" : "navItem"} href="#cases">案例库管理</a>
          <a className={activeView === "m1m2-test" ? "navItem active" : "navItem"} href="#m1m2-test">M1/M2选择测试</a>
          <a className={activeView === "m5-test" ? "navItem active" : "navItem"} href="#m5-test">M5选择测试</a>
          <a className={activeView === "document-parse-test" ? "navItem active" : "navItem"} href="#document-parse-test">文档解析测试</a>
        </nav>
      </aside>
      <section className="content">
        <header className="topbar"><div><h1>{pageTitle.title}</h1><p>{pageTitle.description}</p></div>{activeView === "projects" ? <div className="topbarActions"><button className="secondaryButton" onClick={toggleProjectManagement} type="button">{isManagingProjects ? "取消管理" : "管理项目"}</button><a className="primaryButton" href="#create">新建项目</a></div> : null}</header>

        {activeView === "projects" ? (
          <>
            <section id="projects" className="section">
              <div className="sectionHeader"><h2>项目列表</h2><span className="badge">{projects.length ? `${projects.length} 个项目` : "Demo 数据"}</span></div>
              {projects.length === 0 ? <div className="emptyState"><div className="emptyIcon" aria-hidden="true">+</div><h3>还没有任何项目</h3><p>点击右上角新建项目，填写基础信息后即可进入资料上传。</p><a className="secondaryButton" href="#create">创建第一个项目</a></div> : (
                <>
                  {isManagingProjects ? (
                    <div className="projectManageBar"><span>已选择 {selectedProjectIds.length} 个项目</span><button className="dangerButton" disabled={busy || selectedProjectIds.length === 0} onClick={deleteSelectedProjects} type="button">删除选中</button></div>
                  ) : null}
                  <div className="projectList">{visibleProjects.map((project) => isManagingProjects ? (
                    <label className={selectedProjectIds.includes(project.project_id) ? "projectItem manageItem selected" : "projectItem manageItem"} key={project.project_id}>
                      <input checked={selectedProjectIds.includes(project.project_id)} onChange={() => toggleProjectSelection(project.project_id)} type="checkbox" />
                      <strong>{project.project_name}</strong>
                      <span>{project.task_status}</span>
                    </label>
                  ) : (
                    <button className={currentProject?.project_id === project.project_id ? "projectItem selected" : "projectItem"} key={project.project_id} onClick={() => { setCurrentProject(project); setTask(null); setClassification(null); }} type="button"><strong>{project.project_name}</strong><span>{project.task_status}</span></button>
                  ))}</div>
                  {hasMoreProjects ? (
                    <div className="projectListFooter">
                      <span>{projectListExpanded ? `已显示全部 ${projects.length} 个项目` : `已显示前 ${PROJECT_LIST_PREVIEW_LIMIT} 个，共 ${projects.length} 个项目`}</span>
                      <button className="secondaryButton" onClick={() => setProjectListExpanded((value) => !value)} type="button">
                        {projectListExpanded ? "收起" : "显示更多"}
                      </button>
                    </div>
                  ) : null}
                </>
              )}
            </section>

            {currentProject ? (
              <>
                <section className="section">
                  <div className="sectionHeader"><h2>统一资料上传</h2><span className="badge">支持多文件</span></div>
                  <div className="uploadPanel">
                    <div>
                      <h3>{currentProject.project_name}</h3>
                      <p>系统将自动识别资料用途，上传时无需选择资料归属章节。</p>
                    </div>
                    <label className="uploadBox">
                      <span>选择项目资料</span>
                      <input
                        name="project_files"
                        type="file"
                        multiple
                        accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                        onChange={(event) => setSelectedFiles(Array.from(event.target.files ?? []))}
                      />
                    </label>
                    <div className="fileList">
                      {(selectedFiles.length ? selectedFiles : uploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
                    </div>
                    <div className="actions">
                      <button className="primaryButton" disabled={busy} onClick={uploadProjectFiles} type="button">统一上传项目资料</button>
                      <button className="secondaryButton" disabled={busy} onClick={analyzeProject} type="button">开始识别资料</button>
                    </div>
                    {uploadSuccess && <div className="uploadSuccess">上传成功，已上传 {uploadedFiles.length} 个文件</div>}
                  </div>
                  <div className="futureModules"><strong>M3/M4 为后续动态模块，本阶段不生成</strong><span>后续将根据真实设计参数、工程量、用钢量和工期规则动态生成。</span></div>
                </section>

                <section className="section">
                  <div className="sectionHeader"><h2>识别结果确认</h2><span className="badge">确认项目类型与模板</span></div>
                  {classification ? (
                    <>
                      <div className="resultGrid">
                        <article className="resultCard">
                          <span>项目类型</span>
                          <strong>{labelForProjectType(classification.detected_project_type)}</strong>
                          <p>置信度：{classification.confidence ? `${Math.round(classification.confidence * 100)}%` : "待返回"}；关键词：{classification.matched_keywords?.join("、") || "暂无"}</p>
                        </article>
                        <article className="resultCard">
                          <span>M1/M2 选用模板</span>
                          <strong>{firstTemplateName(classification.template_selection?.M1_M2)}</strong>
                          <p>用于行业背景、技术标准、项目概况与现场挑战的固化模板字段替换。</p>
                        </article>
                        <article className="resultCard">
                          <span>M5 推荐案例</span>
                          <strong>{recommendedCases[0]?.title ?? "暂无高匹配案例"}</strong>
                          <p>{recommendedCases[0]?.match_reason ?? "系统未返回高匹配案例时，请在人工确认时补充选择。"}</p>
                        </article>
                        <article className="resultCard">
                          <span>M6 固定模板</span>
                          <strong>{firstTemplateName(classification.template_selection?.M6)}</strong>
                          <p>默认使用企业背书与荣誉固定模板，可由后端补充替换字段。</p>
                        </article>
                      </div>
                      <div className="missingFields">
                        <strong>缺失字段</strong>
                        <div>{classification.missing_fields?.length ? classification.missing_fields.map((field) => <span key={field}>{field}</span>) : <span>暂无缺失字段</span>}</div>
                      </div>
                      <form className="confirmationGrid" onSubmit={(event) => { event.preventDefault(); submitClassificationReview(); }}>
                        <label>确认项目类型<select aria-label="确认项目类型" value={reviewForm.projectType} onChange={(event) => setReviewForm((value) => ({ ...value, projectType: event.target.value }))}>{projectTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                        <label>确认 M1/M2 模板<select aria-label="确认 M1/M2 模板" value={reviewForm.m1m2Template} onChange={(event) => setReviewForm((value) => ({ ...value, m1m2Template: event.target.value }))}>{m1m2Templates.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                        <label>确认 M5 案例<select aria-label="确认 M5 案例" value={reviewForm.caseId} onChange={(event) => setReviewForm((value) => ({ ...value, caseId: event.target.value }))}><option value="">暂不选择案例</option>{recommendedCases.map((item) => <option key={item.case_id} value={item.case_id}>{item.title}</option>)}</select></label>
                        <label>确认备注<input value={reviewForm.notes} onChange={(event) => setReviewForm((value) => ({ ...value, notes: event.target.value }))} placeholder="可填写模板或案例调整原因" /></label>
                        <button className="primaryButton" disabled={busy} type="submit">提交人工确认</button>
                      </form>
                      <div className="actions" style={{ marginTop: "1rem" }}>
                        <button className="secondaryButton" disabled={busy} onClick={saveToVectorStore} type="button">确认存入向量库</button>
                      </div>
                    </>
                  ) : (
                    <div className="emptyState compact"><h3>等待系统识别</h3><p>统一上传项目资料后，点击开始识别资料，即可在此确认项目类型、模板选择、案例选择和缺失字段。</p></div>
                  )}
                </section>

                <section className="section statusSection">
                  <div className="sectionHeader"><h2>生成状态</h2><div className="actions"><button className="primaryButton" disabled={busy} onClick={generate} type="button">启动生成</button><button className="secondaryButton" disabled={busy} onClick={downloadFinal} type="button">下载最终 PPTX</button></div></div>
                  <ol className="statusList">{statuses.map((status, index) => <li className={status === activeStatus ? "current" : ""} key={status}><span>{index + 1}</span>{status}</li>)}</ol>
                  <div className="historyBox"><strong>状态历史</strong><span>{statusHistory}</span></div>
                  <p className="messageLine">{message}</p>
                  <div className="downloadRow"><div><h3>最终文件</h3><p id="finalFileDesc">生成完成后可下载 PPTX</p></div><span className="badge">{activeStatus}</span></div>
                </section>
              </>
            ) : null}
          </>
        ) : null}

        {activeView === "create" ? (
          <section id="create" className="section">
            <div className="sectionHeader"><h2>新建项目</h2><span className="badge">基础信息</span></div>
            <form className="projectForm" onSubmit={createProject}>
              <label>项目名称<input name="project_name" placeholder="例如：某城市轨道交通声屏障改造项目" /></label>
              <label>项目所在地（可选）<input name="project_location" placeholder="例如：南京" /></label>
              <label>建设/业主单位（可选）<input name="owner_unit" placeholder="例如：某建设单位" /></label>
              <label>产品线（可选）<select aria-label="产品线" name="product_line" defaultValue="">
                <option value="">请选择产品线</option>
                <option value="轨道交通声屏障">轨道交通声屏障</option>
                <option value="轨交既有线改造">轨交既有线改造</option>
                <option value="公路声屏障">公路声屏障</option>
                <option value="铁路声屏障">铁路声屏障</option>
              </select></label>
              <button className="primaryButton" disabled={busy} type="submit">创建项目</button>
            </form>
          </section>
        ) : null}

        {activeView === "cases" ? (
          <section id="cases" className="section"><div className="sectionHeader"><h2>案例库管理</h2><button className="secondaryButton" type="button">新增案例</button></div><div className="emptyState compact"><h3>案例库为空</h3><p>添加历史项目案例后，系统会根据项目标签自动匹配相似案例。</p><button className="secondaryButton" type="button">添加第一个案例</button></div></section>
        ) : null}

        {activeView === "m1m2-test" ? (
          <section id="m1m2-test" className="section">
            <div className="sectionHeader">
              <h2>M1/M2选择测试</h2>
              <span className="badge">固定枚举识别</span>
            </div>
            <div className="testPanel">
              <div className="testInputs single">
                <label>测试项目名称<input value={m1m2TestProjectName} onChange={(event) => setM1m2TestProjectName(event.target.value)} /></label>
              </div>
              <label className="uploadBox">
                <span>上传测试资料</span>
                <input
                  name="m1m2_test_files"
                  type="file"
                  multiple
                  accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                  onChange={(event) => setM1m2TestFiles(Array.from(event.target.files ?? []))}
                />
              </label>
              <div className="fileList">
                {(m1m2TestFiles.length ? m1m2TestFiles : m1m2TestUploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
              </div>
              <button className="primaryButton" disabled={busy} onClick={runM1M2TemplateTest} type="button">识别 M1/M2 类型并选择模板</button>
              <p className="messageLine">{m1m2TestMessage}</p>
            </div>

            <div className="typeCheckGrid">
              {projectTypes.map((item) => (
                <label className={m1m2TestResult?.detected_project_type === item.value ? "typeCheck selected" : "typeCheck"} key={item.value}>
                  <input type="radio" checked={m1m2TestResult?.detected_project_type === item.value} readOnly />
                  <span>{item.label}</span>
                  <small>{item.value}</small>
                </label>
              ))}
            </div>

            <div className="resultGrid">
              <article className="resultCard">
                <span>识别到的项目类型</span>
                <strong>{labelForProjectType(m1m2TestResult?.detected_project_type)}</strong>
                <p>project_type：{m1m2TestResult?.detected_project_type ?? "待识别"}</p>
              </article>
              <article className="resultCard">
                <span>对应 PPT 模板</span>
                <strong>{firstTemplateName(m1m2TestResult?.template_selection?.M1_M2)}</strong>
                <p>只选择既有 M1/M2 固化模板，不动态生成整章内容。</p>
              </article>
              <article className="resultCard">
                <span>confidence</span>
                <strong>{m1m2TestResult?.confidence ? `${Math.round(m1m2TestResult.confidence * 100)}%` : "待识别"}</strong>
                <p>供前端人工确认时参考。</p>
              </article>
              <article className="resultCard">
                <span>matched_keywords</span>
                <strong>{m1m2TestResult?.matched_keywords?.join("、") || "待识别"}</strong>
                <p>命中关键词来自项目名称、文件名和解析文本。</p>
              </article>
            </div>
            <div className="evidencePanel">
              <div className="sectionHeader">
                <h3>判断依据</h3>
                <span className="badge">detection_evidence</span>
              </div>
              {m1m2TestResult?.detection_evidence?.length ? (
                <div className="evidenceList">
                  {m1m2TestResult.detection_evidence.map((item, index) => (
                    <article className="evidenceItem" key={`${item.keyword}-${item.source}-${index}`}>
                      <div>
                        <strong>{item.keyword || "关键词"}</strong>
                        <span>{item.source || "来源未知"}</span>
                      </div>
                      <p>{item.snippet || "未返回 snippet"}</p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="messageLine">未返回明确命中依据，请检查 PDF 是否可提取文本。</p>
              )}
            </div>
          </section>
        ) : null}

        {activeView === "m5-test" ? (
          <section id="m5-test" className="section">
            <div className="sectionHeader">
              <h2>M5选择测试</h2>
              <span className="badge">案例库匹配</span>
            </div>
            <div className="testPanel">
              <div className="testInputs single">
                <label>测试项目名称<input value={m5TestProjectName} onChange={(event) => setM5TestProjectName(event.target.value)} /></label>
              </div>
              <label className="uploadBox">
                <span>上传测试资料</span>
                <input
                  name="m5_test_files"
                  type="file"
                  multiple
                  accept=".ppt,.pptx,.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg"
                  onChange={(event) => setM5TestFiles(Array.from(event.target.files ?? []))}
                />
              </label>
              <div className="fileList">
                {(m5TestFiles.length ? m5TestFiles : m5TestUploadedFiles).map((file) => <span key={"name" in file ? file.name : file.file_id}>{"name" in file ? file.name : file.filename}</span>)}
              </div>
              <button className="primaryButton" disabled={busy} onClick={runM5CaseTest} type="button">分析并匹配案例</button>
              <p className="messageLine">{m5TestMessage}</p>
            </div>

            <div className="resultGrid">
              <article className="resultCard">
                <span>项目类型</span>
                <strong>{labelForProjectType(m5TestResult?.detected_project_type)}</strong>
                <p>用于筛选同类项目案例</p>
              </article>
              <article className="resultCard">
                <span>推荐案例数</span>
                <strong>{m5TestResult?.case_selection?.recommended_cases?.length ?? 0} 个</strong>
                <p>系统根据项目标签匹配相似案例</p>
              </article>
            </div>

            {m5TestResult?.case_selection?.recommended_cases && m5TestResult.case_selection.recommended_cases.length > 0 ? (
              <div className="evidencePanel">
                <div className="sectionHeader">
                  <h3>匹配结果</h3>
                  <span className="badge">recommended_cases</span>
                </div>
                <div className="evidenceList">
                  {m5TestResult.case_selection.recommended_cases.map((caseItem, index) => (
                    <article className="evidenceItem" key={caseItem.case_id ?? index}>
                      <div>
                        <strong>{caseItem.title || `案例 ${index + 1}`}</strong>
                        <span>case_id: {String(caseItem.case_id)}</span>
                      </div>
                      <p><strong>匹配理由：</strong>{caseItem.match_reason || "暂无匹配理由"}</p>
                      <div>
                        <strong>匹配标签：</strong>
                        {caseItem.matched_tags && caseItem.matched_tags.length > 0 ? (
                          caseItem.matched_tags.map((tag, tagIndex) => (
                            <span className="caseTag" key={tagIndex}>{tag}</span>
                          ))
                        ) : (
                          <span>暂无标签</span>
                        )}
                      </div>
                      {caseItem.source_path && (
                        <p className="sourcePath"><strong>来源路径：</strong>{caseItem.source_path}</p>
                      )}
                    </article>
                  ))}
                </div>
              </div>
            ) : (
              <div className="emptyState compact">
                <h3>暂无高匹配案例</h3>
                <p>{m5TestResult?.case_selection?.message || "系统未找到相似案例，可能原因：1) 案例库为空；2) 上传资料不完整；3) 项目类型与现有案例差异较大。"}</p>
              </div>
            )}

            {m5TestResult?.case_selection?.status && (
              <div className={m5TestResult.case_selection.status === "matched" ? "matchStatus matched" : "matchStatus"}>
                <strong>案例匹配状态：</strong>{m5TestResult.case_selection.status}
                {m5TestResult.case_selection.message && <span> - {m5TestResult.case_selection.message}</span>}
              </div>
            )}

            {m5TestResult?.detection_evidence && m5TestResult.detection_evidence.length > 0 && (
              <div className="evidencePanel spaced">
                <div className="sectionHeader">
                  <h3>判断依据</h3>
                  <span className="badge">detection_evidence</span>
                </div>
                <div className="evidenceList">
                  {m5TestResult.detection_evidence.map((item, index) => (
                    <article className="evidenceItem" key={`${item.keyword}-${item.source}-${index}`}>
                      <div>
                        <strong>{item.keyword || "关键词"}</strong>
                        <span>{item.source || "来源未知"}</span>
                      </div>
                      <p>{item.snippet || "未返回 snippet"}</p>
                    </article>
                  ))}
                </div>
              </div>
            )}
          </section>
        ) : null}

        {activeView === "document-parse-test" ? (
          <section id="document-parse-test" className="section">
            <div className="sectionHeader">
              <h2>文档解析测试</h2>
              <span className="badge">多格式解析验证</span>
            </div>
            <div className="testPanel">
              <label className="uploadBox">
                <span>选择测试文件</span>
                <input
                  name="document_parse_test_files"
                  type="file"
                  multiple
                  accept=".txt,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg,.dwg,.dxf"
                  onChange={(event) => setDocumentParseTestFiles(Array.from(event.target.files ?? []))}
                />
              </label>
              <div className="fileList">
                {documentParseTestFiles.map((file) => <span key={file.name}>{file.name}</span>)}
              </div>
              <button className="primaryButton" disabled={busy} onClick={runDocumentParseTest} type="button">开始解析测试</button>
              <p className="messageLine">{documentParseTestMessage}</p>
            </div>

            {documentParseTestResults.length > 0 ? (
              <div className="parseTestResults">
                {documentParseTestResults.map((result, index) => (
                  <article className="parseResultCard" key={index}>
                    <div className="parseResultHeader">
                      <strong>{result.filename}</strong>
                      <span className="badge">{result.suffix}</span>
                      <span className={`parseStatus ${result.parse_status}`}>{result.parse_status}</span>
                      {result.parse_status === "pending_enhancement" && <span className="badge warn">pending_enhancement</span>}
                      {result.parse_status === "pending_ocr" && <span className="badge warn">pending_ocr</span>}
                    </div>
                    <div className="parseResultMeta">
                      <span>资料角色: {result.document_role}</span>
                      <span>可服务模块: {result.assigned_modules.join(", ") || "暂无"}</span>
                      <span>Content-Type: {result.content_type}</span>
                    </div>
                    {result.error_message ? (
                      <div className={`parseError ${result.parse_status}`}>{result.error_message}</div>
                    ) : null}
                    {result.text ? (
                      <div className="parseTextPreview">
                        <strong>解析文本</strong>
                        <pre className="parseTextBox">{result.text.length > 2000 ? result.text.slice(0, 2000) + "\n...(已截断)" : result.text}</pre>
                        <div className="parseStats">
                          <span>字符数: {result.text.length}</span>
                          <span>行数: {result.sections?.length || result.text.split("\n").length}</span>
                        </div>
                      </div>
                    ) : null}
                    {result.slides && result.slides.length > 0 ? (
                      <div className="parseSlides">
                        <strong>结构化结果 ({result.slides.length} 项):</strong>
                        {result.slides.map((slide: DocumentParseSlide, slideIdx: number) => (
                          <div key={slideIdx} className={`slideItem ${slide.title ? "hasTitle" : ""}`}>
                            <div className="slideItemHeader">
                              <span className="slideIndex">{slideIdx + 1}</span>
                              {slide.sheet_name ? <span className="sheetName">{slide.sheet_name}</span> : null}
                              {slide.title ? <strong className="slideTitle">{slide.title}</strong> : null}
                              {slide.rows !== undefined ? <span className="slideMeta">行{slide.rows} × 列{slide.columns}</span> : null}
                            </div>
                            {slide.preview_rows && slide.preview_rows.length > 0 ? (
                              <div className="tableScrollWrapper">
                                <table className="previewTable">
                                  <tbody>
                                    {slide.preview_rows.slice(0, 10).map((row: string[], rowIdx: number) => (
                                      <tr key={rowIdx}>
                                        <td className="rowNum">{rowIdx + 1}</td>
                                        {row.map((cell: string, cellIdx: number) => <td key={cellIdx}>{cell}</td>)}
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            ) : null}
                            {slide.texts && slide.texts.length > 0 ? (
                              <div className="slideTexts">
                                {slide.texts.slice(0, 10).map((t: string, i: number) => <p key={i} className="slideTextItem">{t}</p>)}
                              </div>
                            ) : null}
                            {slide.text ? <p className="slideTextItem">{slide.text}</p> : null}
                          </div>
                        ))}
                      </div>
                    ) : null}
                    {result.sections && result.sections.length > 0 ? (
                      <div className="parseSections">
                        <strong>段落/行预览</strong>
                        <ul className="sectionsList">
                          {result.sections.slice(0, 20).map((sec: string, i: number) => <li key={i}>{sec}</li>)}
                        </ul>
                        {result.sections.length > 20 ? <p className="sectionsMore">... 共 {result.sections.length} 条</p> : null}
                      </div>
                    ) : null}
                  </article>
                ))}
              </div>
            ) : null}
          </section>
        ) : null}
      </section>
    </main>
  );
}
