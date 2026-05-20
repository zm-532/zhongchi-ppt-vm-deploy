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

const M3_ACTIVE_REPLACEMENT_FIELDS = [
  "m3_basic_summary",
  "m3_quantity_summary",
  "m3_site_survey_summary",
  "m3_risk_summary",
  "m3_solution_summary",
];

type ViewId = "projects" | "create" | "cases" | "function-tests" | "m1m2-test" | "m5-test" | "document-parse-test" | "llm-test" | "m3-test";
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
type StoredFile = { file_id: number; filename: string; content_type?: string; document_role?: string; assigned_modules?: string[]; parse_status?: string; text_preview?: string; error_message?: string };
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
  files?: StoredFile[];
};
type TaskState = { project_id: number; task_status: string; status_history: string[] };
type ReviewForm = { projectType: string; m1m2Template: string; caseId?: string; m3Selection: string; notes: string };
type RecommendedCase = { case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string };
type LlmTestResult = { ok: boolean; status_code: number; model: string; reply: string; error: string; configured: Record<string, boolean> };

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8010";
const PROJECT_LIST_PREVIEW_LIMIT = 5;
const PROJECT_LIST_PAGE_SIZE = 10;
const viewTitles: Record<ViewId, { title: string; description: string }> = {
  projects: { title: "我的项目", description: "创建项目、统一上传项目资料，并确认系统识别结果。" },
  create: { title: "新建项目", description: "填写基础信息后创建一个新的售前 PPT 项目。" },
  cases: { title: "案例库管理", description: "维护历史案例，供系统按项目标签推荐引用。" },
  "function-tests": { title: "功能测试", description: "开发过程验证入口，收纳内部功能测试页面，普通前端用户无需使用。" },
  "m1m2-test": { title: "M1/M2选择测试", description: "上传测试资料，根据文件名和解析文本识别项目类型并选择对应 M1/M2 固化模板。" },
  "m5-test": { title: "M5选择测试", description: "上传测试资料，根据项目标签从案例库匹配相似案例并显示匹配理由。" },
  "document-parse-test": { title: "文档解析测试", description: "用于测试不同格式资料的文本与结构化解析效果。" },
  "llm-test": { title: "大模型测试", description: "调用后端开发测试接口，验证当前 LLM 环境变量和中转站请求是否可用。" },
  "m3-test": { title: "M3文字替换测试", description: "将模拟资料文本替换到 M3 项目深化方案模板，验证独立 M3 文字替换功能。" },
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
  const [reviewForm, setReviewForm] = useState<ReviewForm>({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", notes: "" });
  const [m1m2TestFiles, setM1m2TestFiles] = useState<File[]>([]);
  const [m1m2TestProjectName, setM1m2TestProjectName] = useState("M1/M2选择测试项目");
  const [m1m2TestResult, setM1m2TestResult] = useState<ClassificationResult | null>(null);
  const [m1m2TestUploadedFiles, setM1m2TestUploadedFiles] = useState<StoredFile[]>([]);
  const [m1m2TestMessage, setM1m2TestMessage] = useState("请选择一个或多个资料文件后开始测试。");
  // M1/M2 完整流程状态：analyze → review → generate
  const [m1m2TestReviewStatus, setM1m2TestReviewStatus] = useState<"idle" | "success" | "error">("idle");
  const [m1m2TestGenerateStatus, setM1m2TestGenerateStatus] = useState<"idle" | "starting" | "success" | "error">("idle");
  const [m1m2TestTaskStatus, setM1m2TestTaskStatus] = useState<string>("");
  const [m5TestFiles, setM5TestFiles] = useState<File[]>([]);
  const [m5TestProjectName, setM5TestProjectName] = useState("M5案例匹配测试项目");
  const [m5TestResult, setM5TestResult] = useState<ClassificationResult | null>(null);
  const [m5TestUploadedFiles, setM5TestUploadedFiles] = useState<StoredFile[]>([]);
  const [m5TestMessage, setM5TestMessage] = useState("请上传项目资料，系统将根据案例库匹配相似案例。");
  const [m5TestReviewStatus, setM5TestReviewStatus] = useState<"idle" | "success" | "error">("idle");
  const [m5TestGenerateStatus, setM5TestGenerateStatus] = useState<"idle" | "starting" | "success" | "error">("idle");
  const [m5TestTaskStatus, setM5TestTaskStatus] = useState<string>("");

  // Document Parse Test - now uses real project flow (analyze via real project API, not /api/document-parse-test)
  const [docParseTestFiles, setDocumentParseTestFiles] = useState<File[]>([]);
  const [docParseTestProjectId, setDocParseTestProjectId] = useState<number | null>(null);
  const [docParseTestResult, setDocParseTestResult] = useState<ClassificationResult | null>(null);
  const [docParseTestMessage, setDocumentParseTestMessage] = useState("请上传文件以测试解析效果。");
  const [docParseTestFullTextMap, setDocParseTestFullTextMap] = useState<Record<number, string>>({});
  const [docParseTestLoadingFullText, setDocParseTestLoadingFullText] = useState<Record<number, boolean>>({});
  const [docParseTestExpandedFiles, setDocParseTestExpandedFiles] = useState<Record<number, boolean>>({});
  const [llmTestPrompt, setLlmTestPrompt] = useState("请用一句话回复：LLM连接成功，并说明你收到了中驰售前PPT助手的页面测试请求。");
  const [llmTestResult, setLlmTestResult] = useState<LlmTestResult | null>(null);
  const [llmTestMessage, setLlmTestMessage] = useState("点击按钮后将通过后端调用大模型测试接口。");

  // M3 Text Replacement Test
  const [m3TestProjectName, setM3TestProjectName] = useState("南京地铁3号线声屏障改造工程");
  const [m3TestProjectLocation, setM3TestProjectLocation] = useState("南京");
  const [m3TestOwnerUnit, setM3TestOwnerUnit] = useState("南京地铁集团");
  const [m3TestProductLine, setM3TestProductLine] = useState("轨道交通声屏障");
  const [m3TestSources, setM3TestSources] = useState(
    "项目位于南京地铁3号线既有线区间，涉及多个敏感点路段，全线约15公里。\n现场踏勘发现施工窗口受限，部分区段需要桥下吊装，采用全封闭声屏障结构形式。\n工程量统计：声屏障长度约12km，护栏吸声板约2000㎡。\n风险分析：工期紧张，夜间施工风压控制是重难点，需要工装TEKLA定位和抗风支架防松动措施。"
  );
  const [m3TestResult, setM3TestResult] = useState<{ok: boolean; pptx_path: string; download_url: string; replacements: Record<string, string>} | null>(null);
  const [m3TestMessage, setM3TestMessage] = useState("请填写项目信息和模拟资料文本，点击按钮开始 M3 文字替换测试。");

  // 项目基础信息编辑
  const [isEditingProject, setIsEditingProject] = useState(false);
  const [editForm, setEditForm] = useState({ project_name: "", project_location: "", owner_unit: "", product_line: "" });

  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("请先创建项目，再统一上传项目资料。");
  const [projectListExpanded, setProjectListExpanded] = useState(false);
  const [projectListPage, setProjectListPage] = useState(1);
  const [isManagingProjects, setIsManagingProjects] = useState(false);
  const [selectedProjectIds, setSelectedProjectIds] = useState<number[]>([]);
  const activeStatus = task?.task_status ?? currentProject?.task_status ?? "待上传";
  const recommendedCases = useMemo(() => classification?.case_selection?.recommended_cases ?? [], [classification]);
  const hasMoreProjects = projects.length > PROJECT_LIST_PREVIEW_LIMIT;
  const totalProjectPages = Math.ceil(projects.length / PROJECT_LIST_PAGE_SIZE);
  const visibleProjects = projectListExpanded
    ? projects.slice((projectListPage - 1) * PROJECT_LIST_PAGE_SIZE, projectListPage * PROJECT_LIST_PAGE_SIZE)
    : projects.slice(0, PROJECT_LIST_PREVIEW_LIMIT);

  const statusHistory = useMemo(
    () => (task?.status_history ?? currentProject?.status_history ?? ["待上传"]).join(" -> "),
    [currentProject, task],
  );

  useEffect(() => {
    function syncViewFromHash() {
      const nextView = window.location.hash.replace("#", "");
      setActiveView(
        nextView === "create" ||
        nextView === "cases" ||
        nextView === "function-tests" ||
        nextView === "m1m2-test" ||
        nextView === "m5-test" ||
        nextView === "document-parse-test" ||
        nextView === "llm-test" ||
        nextView === "m3-test"
          ? nextView
          : "projects"
      );
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
      .catch(() => setMessage("后端未连接，请确认 FastAPI 运行在 127.0.0.1:8010。"));
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
        // m3Selection 不在 useEffect 中重置，保持用户选择或默认 "m3_template"
        m3Selection: value.m3Selection || "m3_template",
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
      setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", notes: "" });
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
          m3_selection: reviewForm.m3Selection,
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
      const newTotalPages = Math.ceil(remainingProjects.length / PROJECT_LIST_PAGE_SIZE);
      if (projectListPage > newTotalPages) setProjectListPage(Math.max(1, newTotalPages));
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

  async function updateProjectBasicInfo() {
    if (!currentProject) return;
    setBusy(true);
    try {
      const updated = await requestJson<Project>(
        `/api/projects/${currentProject.project_id}`,
        { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(editForm) },
      );
      setCurrentProject(updated);
      setProjects((items) => items.map((p) => (p.project_id === updated.project_id ? updated : p)));
      setIsEditingProject(false);
      setMessage("项目信息已更新，若已生成 PPT，请重新启动生成以应用最新字段。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "更新项目信息失败");
    } finally {
      setBusy(false);
    }
  }

  async function runM1M2TemplateTest() {
    if (m1m2TestFiles.length === 0) return setM1m2TestMessage("请先选择一个或多个测试资料文件。");
    setBusy(true);
    setM1m2TestResult(null);
    setM1m2TestUploadedFiles([]);
    setM1m2TestReviewStatus("idle");
    setM1m2TestGenerateStatus("idle");
    setM1m2TestTaskStatus("");
    try {
      // 1. 创建临时项目
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
      // 2. 上传文件
      const body = new FormData();
      m1m2TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      setM1m2TestUploadedFiles(stored);
      // 3. 调用 analyze（真实业务流程入口）
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM1m2TestResult(result);
      setProjects((items) => [project, ...items]);
      setM1m2TestMessage("已完成：上传文件 + 分析识别。下一步：提交人工确认...");

      // 4. 提交人工确认（使用检测到的项目类型和模板）
      const detectedType = result.detected_project_type || result.confirmed_project_type || "metro";
      const templateKey = result.template_selection?.M1_M2?.template_key || detectedType;
      try {
        await requestJson(`/api/projects/${project.project_id}/classification/review`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirmed_project_type: detectedType,
            template_selection: {
              M1_M2: { template_key: templateKey },
              M5: result.template_selection?.M5,
              M6: result.template_selection?.M6,
            },
            confirmed_case_id: null,
            notes: "M1/M2 测试视图自动确认",
          }),
        });
        setM1m2TestReviewStatus("success");
        setM1m2TestMessage("已完成：上传 + 分析 + 人工确认。下一步：启动生成...");
      } catch (reviewError) {
        setM1m2TestReviewStatus("error");
        setM1m2TestMessage("已完成分析(review 失败: " + (reviewError instanceof Error ? reviewError.message : "未知错误") + ")。可手动在\"我的项目\"中继续。");
        setBusy(false);
        return;
      }

      // 5. 启动生成
      setM1m2TestGenerateStatus("starting");
      try {
        await requestJson(`/api/projects/${project.project_id}/generate`, { method: "POST" });
        // 查询任务状态
        const taskState = await requestJson<{ task_status: string; status_history: string[] }>(`/api/projects/${project.project_id}/task`);
        setM1m2TestTaskStatus(taskState.task_status || "生成中");
        setM1m2TestGenerateStatus("success");
        setM1m2TestMessage("完整流程完成: 上传 -> 分析 -> 确认 -> 生成已启动(状态: " + taskState.task_status + ")。");
      } catch (generateError) {
        setM1m2TestGenerateStatus("error");
        setM1m2TestMessage("已完成分析+确认，但启动生成失败: " + (generateError instanceof Error ? generateError.message : "未知错误") + "。");
      }
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
    setM5TestReviewStatus("idle");
    setM5TestGenerateStatus("idle");
    setM5TestTaskStatus("");
    try {
      // 1. 创建临时项目
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
      // 2. 上传文件
      const body = new FormData();
      m5TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      setM5TestUploadedFiles(stored);
      // 3. 调用 analyze（真实业务流程入口）
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM5TestResult(result);
      setProjects((items) => [project, ...items]);
      const cases = result.case_selection?.recommended_cases;
      if (!cases || cases.length === 0) {
        // 完整流程测试未覆盖：分析阶段无推荐案例，review/generate 步骤被跳过
        setM5TestReviewStatus("idle");
        setM5TestGenerateStatus("idle");
        setM5TestMessage("分析完成但未找到推荐案例。完整流程测试未覆盖 review/generate 步骤。需使用包含匹配关键词的 fixture 文件重试。");
        setBusy(false);
        return;
      }
      setM5TestMessage("分析完成，找到 " + cases.length + " 个推荐案例。下一步: 提交人工确认...");

      // 4. 提交人工确认（带上推荐案例中第一个）
      const detectedType = result.detected_project_type || result.confirmed_project_type || "metro";
      const firstCase = cases[0];
      const confirmedCaseId = firstCase?.case_id != null ? String(firstCase.case_id) : null;
      try {
        await requestJson(`/api/projects/${project.project_id}/classification/review`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            confirmed_project_type: detectedType,
            template_selection: {
              M1_M2: result.template_selection?.M1_M2,
              M5: result.template_selection?.M5,
              M6: result.template_selection?.M6,
            },
            confirmed_case_id: confirmedCaseId,
            notes: "M5 测试视图自动确认并选用推荐案例",
          }),
        });
        setM5TestReviewStatus("success");
        setM5TestMessage("已完成: 上传 + 分析 + 确认(选用案例: " + (firstCase?.title || confirmedCaseId) + ")。下一步: 启动生成...");
      } catch (reviewError) {
        setM5TestReviewStatus("error");
        setM5TestMessage("已完成分析(review 失败: " + (reviewError instanceof Error ? reviewError.message : "未知错误") + ")。");
        setBusy(false);
        return;
      }

      // 5. 启动生成
      setM5TestGenerateStatus("starting");
      try {
        await requestJson(`/api/projects/${project.project_id}/generate`, { method: "POST" });
        const taskState = await requestJson<{ task_status: string; status_history: string[] }>(`/api/projects/${project.project_id}/task`);
        setM5TestTaskStatus(taskState.task_status || "生成中");
        setM5TestGenerateStatus("success");
        setM5TestMessage("完整流程完成: 上传 -> 分析 -> 确认(含案例) -> 生成已启动(状态: " + taskState.task_status + ")。");
      } catch (generateError) {
        setM5TestGenerateStatus("error");
        setM5TestMessage("已完成分析+确认，但启动生成失败: " + (generateError instanceof Error ? generateError.message : "未知错误") + "。");
      }
    } catch (error) {
      setM5TestMessage(error instanceof Error ? error.message : "M5 案例匹配测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function runDocumentParseTest() {
    if (docParseTestFiles.length === 0) return setDocumentParseTestMessage("请先选择要测试的文件。");
    setBusy(true);
    setDocParseTestResult(null);
    setDocParseTestProjectId(null);
    try {
      // 1. 创建临时项目（与真实业务流程一致：必须先有项目才能上传和分析）
      const project = await requestJson<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_name: "文档解析测试项目",
          project_location: "",
          owner_unit: "",
          product_line: "",
        }),
      });
      setDocParseTestProjectId(project.project_id);
      // 2. 上传到真实项目（走 POST /api/projects/{id}/files，与主流程完全一致）
      const body = new FormData();
      docParseTestFiles.forEach((file) => body.append("files", file));
      await requestJson(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      // 3. 调用 analyze（真实业务流程：经过 document_analysis.analyze_document + _detect_project_type + match_cases 全流程）
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      // 4. 从 classification 结果中提取每个文件的解析信息
      //    classification.files 中每个文件记录了 parse_status、document_role、assigned_modules、filename 等
      setDocParseTestResult(result);
      const parsedFiles = result.files ?? [];
      const successCount = parsedFiles.filter((f) => f.parse_status === "parsed").length;
      const pendingCount = parsedFiles.filter((f) => f.parse_status === "pending_enhancement").length;
      const failedCount = parsedFiles.filter((f) => f.parse_status === "failed").length;
      setDocumentParseTestMessage(
        "解析完成, 共 " + parsedFiles.length + " 个文件(成功: " + successCount + ", 待增强: " + pendingCount + ", 失败: " + failedCount + "). " + "项目类型: " + labelForProjectType(result.detected_project_type) + "; 匹配关键词: " + (result.matched_keywords?.join(", ") || "暂无") + "."
      );
    } catch (error) {
      setDocumentParseTestMessage(error instanceof Error ? error.message : "解析测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function loadDocParseTestFullText(fileId: number) {
    if (!docParseTestProjectId) return;
    setDocParseTestLoadingFullText((prev) => ({ ...prev, [fileId]: true }));
    try {
      const result = await requestJson<{ text: string; error_message: string }>(
        `/api/projects/${docParseTestProjectId}/files/${fileId}/parsed-text`,
      );
      setDocParseTestFullTextMap((prev) => ({ ...prev, [fileId]: result.text || result.error_message || "" }));
    } catch {
      setDocParseTestFullTextMap((prev) => ({ ...prev, [fileId]: "加载失败" }));
    } finally {
      setDocParseTestLoadingFullText((prev) => ({ ...prev, [fileId]: false }));
    }
  }

  function toggleDocParseTestFileExpanded(fileId: number) {
    setDocParseTestExpandedFiles((prev) => {
      const isExpanding = !prev[fileId];
      if (isExpanding && !docParseTestFullTextMap[fileId]) {
        loadDocParseTestFullText(fileId);
      }
      return { ...prev, [fileId]: isExpanding };
    });
  }

  async function runLlmConnectionTest() {
    const prompt = llmTestPrompt.trim();
    if (!prompt) return setLlmTestMessage("请先填写测试提示词。");
    setBusy(true);
    setLlmTestResult(null);
    try {
      const result = await requestJson<LlmTestResult>("/api/dev/llm-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      setLlmTestResult(result);
      setLlmTestMessage(result.ok ? "大模型调用成功。" : `大模型调用失败：${result.error || result.status_code}`);
    } catch (error) {
      setLlmTestMessage(error instanceof Error ? error.message : "大模型测试失败");
    } finally {
      setBusy(false);
    }
  }

  async function runM3RenderTest() {
    if (!m3TestProjectName.trim()) return setM3TestMessage("请先填写项目名称。");
    setBusy(true);
    setM3TestResult(null);
    try {
      const result = await requestJson<{ok: boolean; pptx_path: string; download_url: string; replacements: Record<string, string>}>(
        "/api/test/m3-render",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project_name: m3TestProjectName,
            project_location: m3TestProjectLocation,
            owner_unit: m3TestOwnerUnit,
            product_line: m3TestProductLine,
            parsed_sources: m3TestSources.split("\n").filter((s) => s.trim()),
          }),
        }
      );
      setM3TestResult(result);
      setM3TestMessage(result.ok ? "M3 PPTX 已生成，点击下载链接获取文件。" : "M3 渲染失败，请检查后端日志。");
    } catch (error) {
      setM3TestMessage(error instanceof Error ? error.message : "M3 测试失败");
    } finally {
      setBusy(false);
    }
  }

  function downloadFinal() {
    if (!currentProject) return setMessage("请先创建项目。");
    window.location.href = `${API_BASE}/api/projects/${currentProject.project_id}/download`;
  }

  const pageTitle = viewTitles[activeView];
  const isFunctionTestView = activeView === "function-tests" || activeView === "m1m2-test" || activeView === "m5-test" || activeView === "document-parse-test" || activeView === "llm-test" || activeView === "m3-test";

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="主导航">
        <div className="brand"><div className="brandMark" aria-hidden="true" /><div><strong>中驰售前PPT助手</strong></div></div>
        <nav>
          <a className={activeView === "projects" ? "navItem active" : "navItem"} href="#projects">我的项目</a>
          <a className={activeView === "create" ? "navItem active" : "navItem"} href="#create">新建项目</a>
          <a className={activeView === "cases" ? "navItem active" : "navItem"} href="#cases">案例库管理</a>
          <a className={isFunctionTestView ? "navItem active" : "navItem"} href="#function-tests">功能测试</a>
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
                      <span>{projectListExpanded ? `第 ${projectListPage} / ${totalProjectPages} 页，共 ${projects.length} 个项目` : `已显示前 ${PROJECT_LIST_PREVIEW_LIMIT} 个，共 ${projects.length} 个项目`}</span>
                      <div className="projectListFooterActions">
                        {projectListExpanded && totalProjectPages > 1 ? (
                          <>
                            <button className="secondaryButton" disabled={projectListPage <= 1} onClick={() => setProjectListPage((p) => Math.max(1, p - 1))} type="button">上一页</button>
                            <button className="secondaryButton" disabled={projectListPage >= totalProjectPages} onClick={() => setProjectListPage((p) => Math.min(totalProjectPages, p + 1))} type="button">下一页</button>
                          </>
                        ) : null}
                        <button className="secondaryButton" onClick={() => { setProjectListExpanded((expanded) => !expanded); setProjectListPage(1); }} type="button">
                          {projectListExpanded ? "收起" : "显示更多"}
                        </button>
                      </div>
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
                      {isEditingProject ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "6px", padding: "10px", border: "1px solid var(--line)", borderRadius: "6px" }}>
                          <input
                            value={editForm.project_name}
                            onChange={(e) => setEditForm((f) => ({ ...f, project_name: e.target.value }))}
                            placeholder="项目名称"
                            style={{ padding: "4px 8px", fontSize: "13px" }}
                          />
                          <input
                            value={editForm.project_location}
                            onChange={(e) => setEditForm((f) => ({ ...f, project_location: e.target.value }))}
                            placeholder="项目所在地"
                            style={{ padding: "4px 8px", fontSize: "13px" }}
                          />
                          <input
                            value={editForm.owner_unit}
                            onChange={(e) => setEditForm((f) => ({ ...f, owner_unit: e.target.value }))}
                            placeholder="建设/业主单位"
                            style={{ padding: "4px 8px", fontSize: "13px" }}
                          />
                          <input
                            value={editForm.product_line}
                            onChange={(e) => setEditForm((f) => ({ ...f, product_line: e.target.value }))}
                            placeholder="产品线"
                            style={{ padding: "4px 8px", fontSize: "13px" }}
                          />
                          <div style={{ display: "flex", gap: "6px" }}>
                            <button className="primaryButton" style={{ fontSize: "12px", padding: "4px 12px" }} disabled={busy} onClick={updateProjectBasicInfo} type="button">保存</button>
                            <button className="secondaryButton" style={{ fontSize: "12px", padding: "4px 12px" }} disabled={busy} onClick={() => setIsEditingProject(false)} type="button">取消</button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <h3>{currentProject.project_name}</h3>
                          <button
                            className="secondaryButton"
                            style={{ fontSize: "12px", padding: "2px 10px" }}
                            onClick={() => {
                              setEditForm({
                                project_name: currentProject.project_name || "",
                                project_location: currentProject.project_location || "",
                                owner_unit: currentProject.owner_unit || "",
                                product_line: currentProject.product_line || "",
                              });
                              setIsEditingProject(true);
                            }}
                            type="button"
                          >
                            编辑基础信息
                          </button>
                        </div>
                      )}
                      <p>系统将自动识别资料用途，上传时无需选择资料归属章节。</p>
                      <p className="uploadHint">支持格式：.ppt / .pptx / .pdf / .doc / .docx / .xls / .xlsx / .png / .jpg / .jpeg</p>
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
                  <div className="futureModules"><strong>M3 已接入正式生成，M4 暂不生成</strong><span>M3 目前使用模板级文字替换，不做图片替换；M4 后续再接入。</span></div>
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
                        <label>确认 M3 模块<select aria-label="确认 M3 模块" value={reviewForm.m3Selection} onChange={(event) => setReviewForm((value) => ({ ...value, m3Selection: event.target.value }))}><option value="m3_template">M3模板</option><option value="m3_skip">暂不选择</option></select></label>
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
                  <div className="sectionHeader"><h2>生成状态</h2><div className="actions"><button className="primaryButton" disabled={busy} onClick={generate} type="button">启动生成</button></div></div>
                  <ol className="statusList">{statuses.map((status, index) => <li className={status === activeStatus ? "current" : ""} key={status}><span>{index + 1}</span>{status}</li>)}</ol>
                  <div className="historyBox"><strong>状态历史</strong><span>{statusHistory}</span></div>
                  <p className="messageLine">{message}</p>
                  <div className="downloadRow"><div><h3>最终文件</h3><p id="finalFileDesc">生成完成后可下载 PPTX</p></div><div className="downloadActions"><button className="secondaryButton" disabled={busy} onClick={downloadFinal} type="button">下载最终 PPTX</button><span className="badge">{activeStatus}</span></div></div>
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
              <label>项目所在地（可选，建议填写）<input name="project_location" placeholder="例如：南京" /></label>
              <label>建设/业主单位（可选，建议填写）<input name="owner_unit" placeholder="例如：某建设单位" /></label>
              <label>产品线（可选，建议填写）<select aria-label="产品线" name="product_line" defaultValue="">
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

        {activeView === "function-tests" ? (
          <section id="function-tests" className="section">
            <div className="sectionHeader">
              <h2>功能测试</h2>
              <span className="badge">开发过程验证入口</span>
            </div>
            <div className="resultGrid">
              <article className="resultCard">
                <span>模板识别</span>
                <strong>M1/M2选择测试</strong>
                <p>验证项目类型识别与 M1/M2 固化模板选择。</p>
                <a className="secondaryButton" href="#m1m2-test">打开测试</a>
              </article>
              <article className="resultCard">
                <span>案例匹配</span>
                <strong>M5选择测试</strong>
                <p>验证项目标签、案例库匹配与推荐理由。</p>
                <a className="secondaryButton" href="#m5-test">打开测试</a>
              </article>
              <article className="resultCard">
                <span>资料解析</span>
                <strong>文档解析测试</strong>
                <p>验证上传资料解析状态、资料角色和模块分配。</p>
                <a className="secondaryButton" href="#document-parse-test">打开测试</a>
              </article>
              <article className="resultCard">
                <span>LLM 连通性</span>
                <strong>大模型测试</strong>
                <p>通过后端读取环境变量并调用配置好的接口。</p>
                <a className="secondaryButton" href="#llm-test">打开测试</a>
              </article>
              <article className="resultCard">
                <span>M3 文字替换</span>
                <strong>M3文字替换测试</strong>
                <p>将模拟资料文本替换到 M3 项目深化方案模板。</p>
                <a className="secondaryButton" href="#m3-test">打开测试</a>
              </article>
            </div>
          </section>
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

            {/* 完整流程状态：analyze → review → generate */}
            {m1m2TestResult ? (
              <div className="flowStatusPanel" style={{ marginTop: "18px", padding: "14px", border: "1px solid var(--line)", borderRadius: "8px", background: "var(--surface-soft)" }}>
                <div className="sectionHeader">
                  <h3>完整流程状态</h3>
                </div>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m1m2TestResult ? "var(--success)" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>① 分析识别</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m1m2TestReviewStatus === "success" ? "var(--success)" : m1m2TestReviewStatus === "error" ? "#e74c3c" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>② 人工确认</span>
                    {m1m2TestReviewStatus === "success" && <span style={{ fontSize: "12px", color: "var(--success)" }}>✅</span>}
                    {m1m2TestReviewStatus === "error" && <span style={{ fontSize: "12px", color: "#e74c3c" }}>❌</span>}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m1m2TestGenerateStatus === "success" ? "var(--success)" : m1m2TestGenerateStatus === "error" ? "#e74c3c" : m1m2TestGenerateStatus === "starting" ? "var(--accent)" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>③ 启动生成</span>
                    {m1m2TestGenerateStatus === "success" && <span style={{ fontSize: "12px", color: "var(--success)" }}>✅ {m1m2TestTaskStatus}</span>}
                    {m1m2TestGenerateStatus === "error" && <span style={{ fontSize: "12px", color: "#e74c3c" }}>❌</span>}
                    {m1m2TestGenerateStatus === "starting" && <span style={{ fontSize: "12px", color: "var(--accent)" }}>进行中...</span>}
                  </div>
                </div>
              </div>
            ) : null}
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

            {/* 完整流程状态：analyze → review → generate */}
            {m5TestResult ? (
              <div className="flowStatusPanel" style={{ marginTop: "18px", padding: "14px", border: "1px solid var(--line)", borderRadius: "8px", background: "var(--surface-soft)" }}>
                <div className="sectionHeader">
                  <h3>完整流程状态</h3>
                </div>
                <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginTop: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m5TestResult ? "var(--success)" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>① 分析识别</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m5TestReviewStatus === "success" ? "var(--success)" : m5TestReviewStatus === "error" ? "#e74c3c" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>② 人工确认</span>
                    {m5TestReviewStatus === "success" && <span style={{ fontSize: "12px", color: "var(--success)" }}>✅</span>}
                    {m5TestReviewStatus === "error" && <span style={{ fontSize: "12px", color: "#e74c3c" }}>❌</span>}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ width: "20px", height: "20px", borderRadius: "50%", background: m5TestGenerateStatus === "success" ? "var(--success)" : m5TestGenerateStatus === "error" ? "#e74c3c" : m5TestGenerateStatus === "starting" ? "var(--accent)" : "var(--line)", display: "inline-block" }} />
                    <span style={{ fontSize: "13px" }}>③ 启动生成</span>
                    {m5TestGenerateStatus === "success" && <span style={{ fontSize: "12px", color: "var(--success)" }}>✅ {m5TestTaskStatus}</span>}
                    {m5TestGenerateStatus === "error" && <span style={{ fontSize: "12px", color: "#e74c3c" }}>❌</span>}
                    {m5TestGenerateStatus === "starting" && <span style={{ fontSize: "12px", color: "var(--accent)" }}>进行中...</span>}
                  </div>
                </div>
              </div>
            ) : null}
          </section>
        ) : null}

        {activeView === "document-parse-test" ? (
          <section id="document-parse-test" className="section">
            <div className="sectionHeader">
              <h2>文档解析测试</h2>
              <span className="badge">真实流程验证</span>
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
                {docParseTestFiles.map((file) => <span key={file.name}>{file.name}</span>)}
              </div>
              <button className="primaryButton" disabled={busy} onClick={runDocumentParseTest} type="button">开始解析测试</button>
              <p className="messageLine">{docParseTestMessage}</p>
            </div>

            {docParseTestResult ? (
              <div className="parseTestResults">
                <div className="resultGrid" style={{ marginTop: "18px" }}>
                  <article className="resultCard">
                    <span>项目类型</span>
                    <strong>{labelForProjectType(docParseTestResult.detected_project_type)}</strong>
                    <p>置信度: {docParseTestResult.confidence ? `${Math.round(docParseTestResult.confidence * 100)}%` : "N/A"}</p>
                  </article>
                  <article className="resultCard">
                    <span>匹配关键词</span>
                    <strong>{docParseTestResult.matched_keywords?.join("、") || "暂无"}</strong>
                    <p>用于判断向量相关性</p>
                  </article>
                  <article className="resultCard">
                    <span>M1/M2 模板</span>
                    <strong>{firstTemplateName(docParseTestResult.template_selection?.M1_M2)}</strong>
                    <p>模板选择结果</p>
                  </article>
                  <article className="resultCard">
                    <span>M5 案例数</span>
                    <strong>{docParseTestResult.case_selection?.recommended_cases?.length ?? 0} 个</strong>
                    <p>{docParseTestResult.case_selection?.status || ""}</p>
                  </article>
                </div>
                {docParseTestResult.files && docParseTestResult.files.length > 0 ? (
                  <div style={{ marginTop: "18px" }}>
                    <h3 style={{ fontSize: "14px", color: "var(--primary-dark)", marginBottom: "10px" }}>
                      文件解析详情（共 {docParseTestResult.files.length} 个文件）
                    </h3>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "var(--surface-soft)" }}>
                          <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>文件名</th>
                          <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>解析状态</th>
                          <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>资料角色</th>
                          <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>服务模块</th>
                          <th style={{ padding: "8px 12px", textAlign: "left", borderBottom: "1px solid var(--line)", fontSize: "12px", color: "var(--muted)" }}>解析文本</th>
                        </tr>
                      </thead>
                      <tbody>
                        {docParseTestResult.files.map((f, idx) => (
                          <>
                            <tr key={idx} style={{ borderBottom: "1px solid var(--line)" }}>
                              <td style={{ padding: "8px 12px", fontSize: "13px" }}>{f.filename}</td>
                              <td style={{ padding: "8px 12px" }}>
                                <span className={`parseStatus ${f.parse_status}`}>{f.parse_status}</span>
                                {f.parse_status === "pending_enhancement" && <span className="badge warn" style={{ marginLeft: "6px" }}>待增强</span>}
                                {f.parse_status === "pending_ocr" && <span className="badge warn" style={{ marginLeft: "6px" }}>待OCR</span>}
                                {f.parse_status === "failed" && <span className="badge warn" style={{ marginLeft: "6px" }}>失败</span>}
                              </td>
                              <td style={{ padding: "8px 12px", fontSize: "13px", color: "var(--muted)" }}>{f.document_role || "未知"}</td>
                              <td style={{ padding: "8px 12px", fontSize: "13px", color: "var(--muted)" }}>{(f.assigned_modules || []).join(", ") || "未分配"}</td>
                              <td style={{ padding: "8px 12px", fontSize: "12px" }}>
                                {f.parse_status === "parsed" ? (
                                  f.text_preview ? (
                                    <button
                                      style={{ fontSize: "11px", padding: "2px 8px", background: "var(--surface-soft)", border: "1px solid var(--line)", borderRadius: "4px", cursor: "pointer" }}
                                      onClick={() => toggleDocParseTestFileExpanded(f.file_id)}
                                      type="button"
                                    >
                                      {docParseTestExpandedFiles[f.file_id] ? "收起" : "查看文本"}
                                    </button>
                                  ) : (
                                    <span style={{ color: "var(--muted)", fontSize: "12px" }}>解析成功，无文本内容</span>
                                  )
                                ) : f.error_message ? (
                                  <span style={{ color: "#e74c3c", fontSize: "12px" }} title={f.error_message}>{f.error_message.length > 30 ? f.error_message.slice(0, 30) + "…" : f.error_message}</span>
                                ) : (
                                  <span style={{ color: "var(--muted)", fontSize: "12px" }}>暂无解析文本</span>
                                )}
                              </td>
                            </tr>
                            {docParseTestExpandedFiles[f.file_id] ? (
                              <tr key={`${idx}-text`}>
                                <td colSpan={5} style={{ padding: "8px 12px", background: "var(--surface-soft)", borderBottom: "1px solid var(--line)" }}>
                                  {docParseTestLoadingFullText[f.file_id] ? (
                                    <span style={{ fontSize: "12px", color: "var(--muted)" }}>加载中…</span>
                                  ) : (
                                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: "12px", maxHeight: "300px", overflowY: "auto", background: "var(--bg)", padding: "8px", borderRadius: "4px", border: "1px solid var(--line)" }}>
                                      {docParseTestFullTextMap[f.file_id] || "（空）"}
                                    </pre>
                                  )}
                                </td>
                              </tr>
                            ) : null}
                            {f.parse_status === "parsed" && f.text_preview && !docParseTestExpandedFiles[f.file_id] ? (
                              <tr key={`${idx}-preview`}>
                                <td colSpan={5} style={{ padding: "4px 12px 8px 12px", borderBottom: "1px solid var(--line)", background: "var(--surface-soft)" }}>
                                  <span style={{ fontSize: "11px", color: "var(--muted)" }}>文本预览：</span>
                                  <span style={{ fontSize: "12px", color: "var(--text)", display: "block", marginTop: "2px" }}>{f.text_preview}{f.text_preview.length >= 1500 ? "…" : ""}</span>
                                </td>
                              </tr>
                            ) : null}
                          </>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>
        ) : null}

        {activeView === "llm-test" ? (
          <section id="llm-test" className="section">
            <div className="sectionHeader">
              <h2>大模型测试</h2>
              <span className="badge">页面调用验证</span>
            </div>
            <div className="testPanel">
              <label>
                测试提示词
                <textarea
                  value={llmTestPrompt}
                  onChange={(event) => setLlmTestPrompt(event.target.value)}
                  rows={4}
                />
              </label>
              <button className="primaryButton" disabled={busy} onClick={runLlmConnectionTest} type="button">调用大模型测试</button>
              <p className="messageLine">{llmTestMessage}</p>
            </div>

            {llmTestResult ? (
              <div className="resultGrid">
                <article className="resultCard">
                  <span>调用状态</span>
                  <strong>{llmTestResult.ok ? "成功" : "失败"}</strong>
                  <p>HTTP status：{llmTestResult.status_code || "无响应"}</p>
                </article>
                <article className="resultCard">
                  <span>模型</span>
                  <strong>{llmTestResult.model || "未返回"}</strong>
                  <p>由后端读取 ZHONGCHI_LLM_MODEL。</p>
                </article>
                <article className="resultCard wide">
                  <span>模型回复</span>
                  <strong>{llmTestResult.reply || "无回复"}</strong>
                  <p>{llmTestResult.error ? `错误信息：${llmTestResult.error}` : "后端不会向前端返回 API Key。"}</p>
                </article>
                <article className="resultCard">
                  <span>配置检查</span>
                  <strong>{llmTestResult.configured?.base_url && llmTestResult.configured?.api_key && llmTestResult.configured?.model ? "完整" : "缺失"}</strong>
                  <p>base_url：{String(Boolean(llmTestResult.configured?.base_url))}；api_key：{String(Boolean(llmTestResult.configured?.api_key))}；model：{String(Boolean(llmTestResult.configured?.model))}</p>
                </article>
              </div>
            ) : null}
          </section>
        ) : null}

        {activeView === "m3-test" ? (
          <section id="m3-test" className="section">
            <div className="sectionHeader">
              <h2>M3文字替换测试</h2>
              <span className="badge">独立测试</span>
            </div>
            <div className="testPanel">
              <div className="testInputs">
                <label>项目名称<input value={m3TestProjectName} onChange={(event) => setM3TestProjectName(event.target.value)} /></label>
                <label>项目所在地<input value={m3TestProjectLocation} onChange={(event) => setM3TestProjectLocation(event.target.value)} /></label>
                <label>建设/业主单位<input value={m3TestOwnerUnit} onChange={(event) => setM3TestOwnerUnit(event.target.value)} /></label>
                <label>产品线<input value={m3TestProductLine} onChange={(event) => setM3TestProductLine(event.target.value)} /></label>
              </div>
              <label>
                模拟资料文本（多行，每行一段）
                <textarea
                  value={m3TestSources}
                  onChange={(event) => setM3TestSources(event.target.value)}
                  rows={6}
                  placeholder="每行一段资料文本，用于 M3 字段提取测试..."
                />
              </label>
              <button className="primaryButton" disabled={busy} onClick={runM3RenderTest} type="button">执行 M3 文字替换测试</button>
              <p className="messageLine" style={m3TestMessage && m3TestMessage.includes("失败") ? {color: "#e74c3c"} : {}}>{m3TestMessage}</p>
            </div>

            {m3TestResult && m3TestResult.ok ? (
              <div className="resultGrid">
                <article className="resultCard">
                  <span>渲染状态</span>
                  <strong>成功</strong>
                  <p>文件路径：{m3TestResult.pptx_path || "无"}</p>
                </article>
                {m3TestResult.download_url ? (
                  <article className="resultCard wide">
                    <span>下载链接</span>
                    <strong>M3 PPTX 已生成</strong>
                    <p>
                      <a href={`${API_BASE}${m3TestResult.download_url}`} download>点击下载生成的 M3 PPTX</a>
                    </p>
                  </article>
                ) : null}
              </div>
            ) : null}

            {m3TestResult && m3TestResult.ok && m3TestResult.replacements && Object.keys(m3TestResult.replacements).length > 0 ? (
              <div style={{ marginTop: "16px" }}>
                <h3 style={{ fontSize: "14px", color: "var(--primary-dark)", marginBottom: "8px" }}>字段替换摘要</h3>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                  <thead>
                    <tr style={{ background: "var(--surface-soft)" }}>
                      <th style={{ padding: "6px 10px", textAlign: "left", borderBottom: "1px solid var(--line)" }}>字段</th>
                      <th style={{ padding: "6px 10px", textAlign: "left", borderBottom: "1px solid var(--line)" }}>替换值</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(m3TestResult.replacements)
                      .filter(([key]) => M3_ACTIVE_REPLACEMENT_FIELDS.includes(key))
                      .map(([key, value]) => (
                      <tr key={key} style={{ borderBottom: "1px solid var(--line)" }}>
                        <td style={{ padding: "6px 10px", color: "var(--muted)" }}>{key}</td>
                        <td style={{ padding: "6px 10px", wordBreak: "break-word" }}>{String(value).slice(0, 120)}{String(value).length > 120 ? "…" : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>
        ) : null}
      </section>
    </main>
  );
}
