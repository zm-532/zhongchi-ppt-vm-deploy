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

type ViewId = "projects" | "create" | "cases" | "m1m2-test" | "m5-test";
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
type ReviewForm = { projectType: string; m1m2Template: string; caseId: string; notes: string };
type RecommendedCase = { case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
const viewTitles: Record<ViewId, { title: string; description: string }> = {
  projects: { title: "我的项目", description: "创建项目、统一上传项目资料，并确认系统识别结果。" },
  create: { title: "新建项目", description: "填写基础信息后创建一个新的售前 PPT 项目。" },
  cases: { title: "案例库管理", description: "维护历史案例，供系统按项目标签推荐引用。" },
  "m1m2-test": { title: "M1/M2选择测试", description: "上传测试资料，根据文件名和解析文本识别项目类型并选择对应 M1/M2 固化模板。" },
  "m5-test": { title: "M5选择测试", description: "上传测试资料，根据项目标签从案例库匹配相似案例并显示匹配理由。" },
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(await response.text());
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
  const [reviewForm, setReviewForm] = useState<ReviewForm>({ projectType: "", m1m2Template: "", caseId: "", notes: "" });
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
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("请先创建项目，再统一上传项目资料。");
  const activeStatus = task?.task_status ?? currentProject?.task_status ?? "待上传";
  const recommendedCases = useMemo(() => classification?.case_selection?.recommended_cases ?? [], [classification]);

  const statusHistory = useMemo(
    () => (task?.status_history ?? currentProject?.status_history ?? ["待上传"]).join(" -> "),
    [currentProject, task],
  );

  useEffect(() => {
    function syncViewFromHash() {
      const nextView = window.location.hash.replace("#", "");
      setActiveView(nextView === "create" || nextView === "cases" || nextView === "m1m2-test" || nextView === "m5-test" ? nextView : "projects");
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
    const firstCaseId = recommendedCases[0]?.case_id;
    setReviewForm((value) => ({
      ...value,
      projectType: value.projectType || detectedType,
      m1m2Template: value.m1m2Template || templateKey || "",
      caseId: value.caseId || String(confirmedCaseId ?? firstCaseId ?? ""),
    }));
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
        }),
      });
      setProjects((items) => [project, ...items]);
      setTask(null);
      setUploadedFiles([]);
      setClassification(null);
      setReviewForm({ projectType: "", m1m2Template: "", caseId: "", notes: "" });
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
      setMessage("项目资料已统一上传。");
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
          confirmed_case_id: reviewForm.caseId ? Number(reviewForm.caseId) : null,
          notes: reviewForm.notes || "前端人工确认",
        }),
      });
      const latest = await requestJson<ClassificationResult>(`/api/projects/${currentProject.project_id}/classification`);
      setClassification(latest);
      setMessage("人工确认已提交，可启动最终生成。");
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
        </nav>
      </aside>
      <section className="content">
        <header className="topbar"><div><h1>{pageTitle.title}</h1><p>{pageTitle.description}</p></div>{activeView === "projects" ? <a className="primaryButton" href="#create">新建项目</a> : null}</header>

        {activeView === "projects" ? (
          <>
            <section id="projects" className="section">
              <div className="sectionHeader"><h2>项目列表</h2><span className="badge">{projects.length ? `${projects.length} 个项目` : "Demo 数据"}</span></div>
              {projects.length === 0 ? <div className="emptyState"><div className="emptyIcon" aria-hidden="true">+</div><h3>还没有任何项目</h3><p>点击右上角新建项目，填写基础信息后即可进入资料上传。</p><a className="secondaryButton" href="#create">创建第一个项目</a></div> : (
                <div className="projectList">{projects.map((project) => <button className={currentProject?.project_id === project.project_id ? "projectItem selected" : "projectItem"} key={project.project_id} onClick={() => { setCurrentProject(project); setTask(null); setClassification(null); }} type="button"><strong>{project.project_name}</strong><span>{project.task_status}</span></button>)}</div>
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
                  <div className="downloadRow"><div><h3>最终文件</h3><p>生成完成后可下载按 M1/M2 → M5 → M6 合并的 PPTX；M3/M4 不参与当前生成链路。</p></div><span className="badge">{activeStatus}</span></div>
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
              <label>项目所在地<input name="project_location" placeholder="例如：南京" /></label>
              <label>建设/业主单位<input name="owner_unit" placeholder="例如：某建设单位" /></label>
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
                            <span key={tagIndex} style={{ marginLeft: "4px", padding: "2px 8px", background: "#eef6ff", borderRadius: "4px", fontSize: "12px" }}>{tag}</span>
                          ))
                        ) : (
                          <span>暂无标签</span>
                        )}
                      </div>
                      {caseItem.source_path && (
                        <p style={{ fontSize: "12px", color: "#65748b", marginTop: "4px" }}><strong>来源路径：</strong>{caseItem.source_path}</p>
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
              <div style={{ marginTop: "12px", padding: "8px 12px", background: m5TestResult.case_selection.status === "matched" ? "#eef6ff" : "#fff8e6", borderRadius: "6px", fontSize: "13px" }}>
                <strong>案例匹配状态：</strong>{m5TestResult.case_selection.status}
                {m5TestResult.case_selection.message && <span> - {m5TestResult.case_selection.message}</span>}
              </div>
            )}

            {m5TestResult?.detection_evidence && m5TestResult.detection_evidence.length > 0 && (
              <div className="evidencePanel" style={{ marginTop: "16px" }}>
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
      </section>
    </main>
  );
}
