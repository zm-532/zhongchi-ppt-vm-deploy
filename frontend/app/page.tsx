"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  API_BASE,
  M3_FULL_SECTIONS,
  PROJECT_LIST_PAGE_SIZE,
  PROJECT_LIST_PREVIEW_LIMIT,
  viewTitles,
} from "./constants";
import type {
  CaseLibraryItem,
  ClassificationResult,
  FullPptCaseItem,
  LlmTestResult,
  M3FullTestResult,
  M3MaterialsResult,
  Project,
  ReviewForm,
  StoredFile,
  TaskState,
  ViewId,
} from "./constants";
import { requestJson, labelForProjectType, projectTypeFromProductLine } from "./utils";
import { useM3AutoPreview } from "./useM3AutoPreview";

import { ToastProvider, useToast } from "./components/Toast";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { M3NamingHelpModal } from "./components/M3NamingHelpModal";
import { PreviewModal } from "./components/PreviewModal";
import { ProjectsView } from "./views/ProjectsView";
import { CreateProjectView } from "./views/CreateProjectView";
import { CaseLibraryView } from "./views/CaseLibraryView";
import { M3MaterialsView } from "./views/M3MaterialsView";
import { FunctionTestsView } from "./views/FunctionTestsView";
import { M1M2TestView } from "./views/M1M2TestView";
import { M3FullTestView } from "./views/M3FullTestView";
import { M5TestView } from "./views/M5TestView";
import { DocParseTestView } from "./views/DocParseTestView";
import { LlmTestView } from "./views/LlmTestView";

const FUNCTION_TEST_VIEWS: ViewId[] = ["m1m2-test", "m3-full-test", "m5-test", "document-parse-test", "llm-test"];

function AppShell() {
  const toast = useToast();
  const [activeView, setActiveView] = useState<ViewId>("projects");
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [task, setTask] = useState<TaskState | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [uploadedFiles, setUploadedFiles] = useState<StoredFile[]>([]);
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  const [showClassificationDetails, setShowClassificationDetails] = useState(false);
  const [qualityReportExpanded, setQualityReportExpanded] = useState(false);
  const [reviewForm, setReviewForm] = useState<ReviewForm>({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
  const [caseLibraryItems, setCaseLibraryItems] = useState<CaseLibraryItem[]>([]);
  const [fullPptCases, setFullPptCases] = useState<FullPptCaseItem[]>([]);
  const [caseLibraryTab, setCaseLibraryTab] = useState<"m5" | "full-ppt">("m5");
  const [m1m2TestFiles, setM1m2TestFiles] = useState<File[]>([]);
  const [m1m2TestProjectName, setM1m2TestProjectName] = useState("M1/M2选择测试项目");
  const [m1m2TestResult, setM1m2TestResult] = useState<ClassificationResult | null>(null);
  const [m1m2TestUploadedFiles, setM1m2TestUploadedFiles] = useState<StoredFile[]>([]);
  const [m1m2TestMessage, setM1m2TestMessage] = useState("请选择一个或多个资料文件后开始测试。");
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
  const [m3FullTestProjectName, setM3FullTestProjectName] = useState("M3完整测试项目");
  const [m3FullTestBulkFiles, setM3FullTestBulkFiles] = useState<File[]>([]);
  const [m3FullTestDescriptions, setM3FullTestDescriptions] = useState("");
  const [m3FullTestResult, setM3FullTestResult] = useState<M3FullTestResult | null>(null);
  const [m3FullTestMessage, setM3FullTestMessage] = useState("请批量上传按九类命名的图片，并填写可选描述文本。");
  const [m3MaterialBulkFiles, setM3MaterialBulkFiles] = useState<File[]>([]);
  const [m3MaterialDescriptions, setM3MaterialDescriptions] = useState("");
  const [m3MaterialsResult, setM3MaterialsResult] = useState<M3MaterialsResult | null>(null);
  const [m3MaterialsMessage, setM3MaterialsMessage] = useState("进入页面后批量上传按九类命名的 M3 图片或 Excel 表格，并填写可选描述。");
  const [m3NamingHelpOpen, setM3NamingHelpOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSlides, setPreviewSlides] = useState<{index: number; image_url: string}[]>([]);
  const [previewCurrentIndex, setPreviewCurrentIndex] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [isEditingProject, setIsEditingProject] = useState(false);
  const [editForm, setEditForm] = useState({ project_name: "", project_location: "", owner_unit: "", product_line: "" });
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("请先创建项目，再统一上传项目资料。");
  const [projectListExpanded, setProjectListExpanded] = useState(false);
  const [projectListPage, setProjectListPage] = useState(1);
  const [isManagingProjects, setIsManagingProjects] = useState(false);
  const [selectedProjectIds, setSelectedProjectIds] = useState<number[]>([]);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [navTestExpanded, setNavTestExpanded] = useState(false);

  const activeStatus = task?.task_status ?? currentProject?.task_status ?? "待上传";
  const recommendedCases = useMemo(() => classification?.case_selection?.recommended_cases ?? [], [classification]);
  const m5FixedCases = useMemo(() => caseLibraryItems.filter((item) => item.source_type === "fixed_m5" && item.module_id === "M5"), [caseLibraryItems]);
  const canSaveFullPptCase = Boolean(currentProject?.final_ppt_path) && activeStatus === "完成";
  const productLineClassificationConflict = useMemo(() => {
    const preferredProjectType = projectTypeFromProductLine(currentProject?.product_line);
    const detectedProjectType = classification?.detected_project_type || "";
    if (!preferredProjectType || !detectedProjectType || preferredProjectType === detectedProjectType) return null;
    return { productLine: currentProject?.product_line || "", preferredProjectType, detectedProjectType };
  }, [classification?.detected_project_type, currentProject?.product_line]);
  const hasMoreProjects = projects.length > PROJECT_LIST_PREVIEW_LIMIT;
  const totalProjectPages = Math.ceil(projects.length / PROJECT_LIST_PAGE_SIZE);
  const visibleProjects = projectListExpanded
    ? projects.slice((projectListPage - 1) * PROJECT_LIST_PAGE_SIZE, projectListPage * PROJECT_LIST_PAGE_SIZE)
    : projects.slice(0, PROJECT_LIST_PREVIEW_LIMIT);

  const m3FullAutoPreview = useM3AutoPreview(m3FullTestBulkFiles, m3FullTestDescriptions);
  const m3MaterialAutoPreview = useM3AutoPreview(m3MaterialBulkFiles, m3MaterialDescriptions);

  const statusHistory = useMemo(
    () => (task?.status_history ?? currentProject?.status_history ?? ["待上传"]).join(" -> "),
    [currentProject, task],
  );
  const qualityReport = task?.quality_report ?? currentProject?.quality_report;

  const refreshFullPptCases = useCallback(async () => {
    try {
      const items = await requestJson<FullPptCaseItem[]>("/api/cases/full-ppt");
      setFullPptCases(items);
    } catch {
      setFullPptCases([]);
    }
  }, []);

  useEffect(() => {
    function syncViewFromHash() {
      const nextView = window.location.hash.replace("#", "");
      const validViews: ViewId[] = ["create", "cases", "project-m3-materials", "function-tests", ...FUNCTION_TEST_VIEWS];
      setActiveView(validViews.includes(nextView as ViewId) ? nextView as ViewId : "projects");
    }
    syncViewFromHash();
    window.addEventListener("hashchange", syncViewFromHash);
    return () => window.removeEventListener("hashchange", syncViewFromHash);
  }, []);

  useEffect(() => {
    if (FUNCTION_TEST_VIEWS.includes(activeView)) {
      setNavTestExpanded(true);
    }
  }, [activeView]);

  useEffect(() => {
    requestJson<Project[]>("/api/projects")
      .then((items) => { setProjects(items); if (items[0]) setCurrentProject(items[0]); })
      .catch(() => toast.error("后端未连接，请确认 FastAPI 运行在 127.0.0.1:8010。"));
  }, []);

  useEffect(() => {
    requestJson<CaseLibraryItem[]>("/api/cases")
      .then((items) => setCaseLibraryItems(items))
      .catch(() => setCaseLibraryItems([]));
    refreshFullPptCases();
  }, [refreshFullPptCases]);

  useEffect(() => {
    const detectedType = classification?.confirmed_project_type || classification?.detected_project_type || "";
    const preferredProjectType = projectTypeFromProductLine(currentProject?.product_line);
    const defaultProjectType = preferredProjectType || detectedType;
    const templateKey = preferredProjectType || classification?.template_selection?.M1_M2?.template_key || detectedType;
    const confirmedCaseId = classification?.case_selection?.confirmed_case_id;
    setReviewForm((value) => {
      const needsInitCaseId = value.caseId === undefined || value.caseId === null;
      let newCaseId = value.caseId;
      if (needsInitCaseId) {
        newCaseId = confirmedCaseId !== undefined && confirmedCaseId !== null
          ? String(confirmedCaseId)
          : (recommendedCases[0]?.case_id !== undefined ? String(recommendedCases[0].case_id) : "");
      }
      return {
        ...value,
        projectType: value.projectType || defaultProjectType || "",
        m1m2Template: value.m1m2Template || templateKey || "",
        caseId: newCaseId,
        m3Selection: value.m3Selection || "m3_template",
      };
    });
  }, [classification, currentProject?.product_line, recommendedCases]);

  const loadM3Materials = useCallback(async (projectId: number) => {
    try {
      const result = await requestJson<M3MaterialsResult>(`/api/projects/${projectId}/m3-materials`);
      setM3MaterialsResult(result);
      setM3MaterialBulkFiles([]);
      setM3MaterialDescriptions(
        (result.images || []).filter((image) => image.description).map((image) => {
          const section = M3_FULL_SECTIONS.find((item) => item.imageField === image.purpose);
          return section ? `${section.title}-${image.page_index || 1}：${image.description}` : "";
        }).filter(Boolean).join("\n")
      );
      setM3MaterialsMessage("M3资料已加载，如需替换请重新批量上传图片或 Excel 表格。");
    } catch (error) {
      setM3MaterialsResult(null); setM3MaterialBulkFiles([]); setM3MaterialDescriptions("");
      setM3MaterialsMessage(error instanceof Error ? error.message : "M3资料加载失败");
    }
  }, []);

  useEffect(() => {
    if (!currentProject) { setM3MaterialsResult(null); setM3MaterialBulkFiles([]); setM3MaterialDescriptions(""); return; }
    loadM3Materials(currentProject.project_id);
  }, [currentProject?.project_id, loadM3Materials]);

  function updateM3MaterialBulkFiles(files: File[]) {
    setM3MaterialBulkFiles(files);
    setM3MaterialsMessage("已选择新资料，保存后会替换已保存的 M3 图片和表格。");
  }

  async function saveM3Materials(returnToProjects = false) {
    if (!currentProject) return toast.error("请先选择项目。");
    if (m3MaterialBulkFiles.length === 0) return toast.error("请先批量上传按九类命名的 M3 图片或 Excel 表格。");
    const formData = new FormData();
    formData.append("descriptions", m3MaterialDescriptions);
    m3MaterialBulkFiles.forEach((file) => formData.append("files", file));
    setBusy(true);
    try {
      const result = await requestJson<M3MaterialsResult>(`/api/projects/${currentProject.project_id}/m3-materials`, { method: "POST", body: formData });
      setM3MaterialsResult(result);
      setM3MaterialBulkFiles([]);
      setM3MaterialDescriptions(
        (result.images || []).filter((image) => image.description).map((image) => {
          const section = M3_FULL_SECTIONS.find((item) => item.imageField === image.purpose);
          return section ? `${section.title}-${image.page_index || 1}：${image.description}` : "";
        }).filter(Boolean).join("\n")
      );
      toast.success(`M3资料已保存：已填写 ${result.text_completed_count}/${result.text_total_count}，已上传 ${result.image_count} 张图片、${result.table_count || 0} 个表格。`);
      if (returnToProjects) { setActiveView("projects"); window.location.hash = "projects"; toast.info("M3资料已保存，可继续识别、确认或生成。"); }
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "M3资料保存失败");
    } finally { setBusy(false); }
  }

  async function createProject(event: FormEvent<HTMLFormElement>, isValid: boolean) {
    if (!isValid) return;
    event.preventDefault();
    setBusy(true);
    try {
      const formData = new FormData(event.currentTarget);
      const project = await requestJson<Project>("/api/projects", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_name: formData.get("project_name") || "中驰智能PPT演示项目", project_location: formData.get("project_location") || "", owner_unit: formData.get("owner_unit") || "", product_line: formData.get("product_line") || "" }),
      });
      setProjects((items) => [project, ...items]);
      setCurrentProject(project); setTask(null); setUploadedFiles([]); setUploadSuccess(false);
      setClassification(null); setShowClassificationDetails(false);
      setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
      setActiveView("projects"); window.location.hash = "projects";
      toast.success(`项目已创建：${project.project_name}`);
    } catch (error) { toast.error(error instanceof Error ? error.message : "创建项目失败"); } finally { setBusy(false); }
  }

  async function uploadProjectFiles() {
    if (!currentProject) return toast.error("请先创建项目。");
    if (selectedFiles.length === 0) return toast.error("请先选择需要上传的项目资料。");
    setBusy(true);
    try {
      const body = new FormData();
      selectedFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[] | StoredFile>(`/api/projects/${currentProject.project_id}/files`, { method: "POST", body });
      setUploadedFiles(Array.isArray(stored) ? stored : [stored]);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      setSelectedFiles([]); setUploadSuccess(true);
      toast.success("项目资料已统一上传，可点击开始识别资料。");
    } catch (error) { toast.error(error instanceof Error ? error.message : "统一上传失败"); } finally { setBusy(false); }
  }

  async function analyzeProject() {
    if (!currentProject) return toast.error("请先创建项目。");
    setBusy(true);
    try {
      await requestJson(`/api/projects/${currentProject.project_id}/analyze`, { method: "POST" });
      const result = await requestJson<ClassificationResult>(`/api/projects/${currentProject.project_id}/classification`);
      setClassification(result); setShowClassificationDetails(false);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      const detectedType = result.confirmed_project_type || result.detected_project_type || "";
      const preferredProjectType = projectTypeFromProductLine(currentProject?.product_line);
      const defaultProjectType = preferredProjectType || detectedType;
      const templateKey = preferredProjectType || result.template_selection?.M1_M2?.template_key || detectedType;
      const newCaseId = result.case_selection?.confirmed_case_id != null ? String(result.case_selection.confirmed_case_id) : (result.case_selection?.recommended_cases?.[0]?.case_id != null ? String(result.case_selection.recommended_cases[0].case_id) : "");
      setReviewForm({ projectType: defaultProjectType, m1m2Template: templateKey, caseId: newCaseId, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
      toast.success("识别结果已返回，请确认项目类型、模板与案例。");
    } catch (error) { toast.error(error instanceof Error ? error.message : "资料识别失败"); } finally { setBusy(false); }
  }

  async function submitClassificationReview() {
    if (!currentProject) return toast.error("请先创建项目。");
    setBusy(true);
    try {
      await requestJson(`/api/projects/${currentProject.project_id}/classification/review`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirmed_project_type: reviewForm.projectType, template_selection: { M1_M2: { template_key: reviewForm.m1m2Template }, M5: classification?.template_selection?.M5, M6: classification?.template_selection?.M6 }, confirmed_case_id: reviewForm.caseId || null, m3_selection: reviewForm.m3Selection, include_print_tail_page: reviewForm.includePrintTailPage, notes: reviewForm.notes || "前端人工确认" }),
      });
      const latest = await requestJson<ClassificationResult>(`/api/projects/${currentProject.project_id}/classification`);
      setClassification(latest);
      const caseMsg = reviewForm.caseId ? "" : "（本次不使用 M5 案例）";
      toast.success(`人工确认已提交${caseMsg}，可启动最终生成。`);
    } catch (error) { toast.error(error instanceof Error ? error.message : "人工确认失败"); } finally { setBusy(false); }
  }

  async function generate() {
    if (!currentProject) return toast.error("请先创建项目。");
    setBusy(true);
    try {
      await requestJson<TaskState>(`/api/projects/${currentProject.project_id}/generate`, { method: "POST" });
      const latest = await requestJson<TaskState>(`/api/projects/${currentProject.project_id}/task`);
      setTask(latest); setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      toast.success(`生成任务已启动，当前状态：${latest.task_status}`);
    } catch (error) { toast.error(error instanceof Error ? error.message : "启动生成失败"); } finally { setBusy(false); }
  }

  async function saveFullPptCase() {
    if (!currentProject) return toast.error("请先创建项目。");
    if (!canSaveFullPptCase) return toast.error("请先完成 PPT 生成，再存入案例库。");
    setBusy(true);
    try {
      const saved = await requestJson<FullPptCaseItem>(`/api/projects/${currentProject.project_id}/full-ppt-case`, { method: "POST" });
      await refreshFullPptCases(); setCaseLibraryTab("full-ppt");
      toast.success(`已存入完整PPT案例库：${saved.title || saved.filename}`);
    } catch (error) { toast.error(error instanceof Error ? error.message : "存入案例库失败"); } finally { setBusy(false); }
  }

  function toggleProjectManagement() { setIsManagingProjects((value) => !value); setSelectedProjectIds([]); }
  function toggleProjectSelection(projectId: number) { setSelectedProjectIds((ids) => (ids.includes(projectId) ? ids.filter((id) => id !== projectId) : [...ids, projectId])); }

  function requestDeleteProjects() {
    if (selectedProjectIds.length === 0) return toast.error("请先选择要删除的项目。");
    setConfirmDeleteOpen(true);
  }

  async function deleteSelectedProjects() {
    setConfirmDeleteOpen(false);
    if (selectedProjectIds.length === 0) return;
    setBusy(true);
    try {
      const idsToDelete = [...selectedProjectIds];
      await Promise.all(idsToDelete.map((projectId) => requestJson(`/api/projects/${projectId}`, { method: "DELETE" })));
      const remainingProjects = projects.filter((project) => !idsToDelete.includes(project.project_id));
      setProjects(remainingProjects); setSelectedProjectIds([]);
      const newTotalPages = Math.ceil(remainingProjects.length / PROJECT_LIST_PAGE_SIZE);
      if (projectListPage > newTotalPages) setProjectListPage(Math.max(1, newTotalPages));
      if (currentProject && idsToDelete.includes(currentProject.project_id)) { setCurrentProject(remainingProjects[0] ?? null); setTask(null); setClassification(null); }
      toast.success(`已删除 ${idsToDelete.length} 个项目。`);
    } catch (error) { toast.error(error instanceof Error ? error.message : "删除项目失败"); } finally { setBusy(false); }
  }

  async function updateProjectBasicInfo() {
    if (!currentProject) return;
    setBusy(true);
    try {
      const updated = await requestJson<Project>(`/api/projects/${currentProject.project_id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(editForm) });
      setCurrentProject(updated); setProjects((items) => items.map((p) => (p.project_id === updated.project_id ? updated : p)));
      setIsEditingProject(false); toast.success("项目信息已更新，若已生成 PPT，请重新启动生成以应用最新字段。");
    } catch (error) { toast.error(error instanceof Error ? error.message : "更新项目信息失败"); } finally { setBusy(false); }
  }

  async function runM1M2TemplateTest() {
    if (m1m2TestFiles.length === 0) return setM1m2TestMessage("请先选择一个或多个测试资料文件。");
    setBusy(true); setM1m2TestResult(null); setM1m2TestUploadedFiles([]); setM1m2TestReviewStatus("idle"); setM1m2TestGenerateStatus("idle"); setM1m2TestTaskStatus("");
    try {
      const project = await requestJson<Project>("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_name: m1m2TestProjectName || "M1/M2选择测试项目", project_location: "", owner_unit: "", product_line: "" }) });
      const body = new FormData(); m1m2TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      setM1m2TestUploadedFiles(stored);
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM1m2TestResult(result); setProjects((items) => [project, ...items]);
      setM1m2TestMessage("已完成：上传文件 + 分析识别。下一步：提交人工确认...");
      const detectedType = result.detected_project_type || result.confirmed_project_type || "metro";
      const templateKey = result.template_selection?.M1_M2?.template_key || detectedType;
      try {
        await requestJson(`/api/projects/${project.project_id}/classification/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed_project_type: detectedType, template_selection: { M1_M2: { template_key: templateKey }, M5: result.template_selection?.M5, M6: result.template_selection?.M6 }, confirmed_case_id: null, notes: "M1/M2 测试视图自动确认" }) });
        setM1m2TestReviewStatus("success"); setM1m2TestMessage("已完成：上传 + 分析 + 人工确认。下一步：启动生成...");
      } catch (reviewError) { setM1m2TestReviewStatus("error"); setM1m2TestMessage("已完成分析(review 失败: " + (reviewError instanceof Error ? reviewError.message : "未知错误") + ")。可手动在\"我的项目\"中继续。"); setBusy(false); return; }
      setM1m2TestGenerateStatus("starting");
      try {
        await requestJson(`/api/projects/${project.project_id}/generate`, { method: "POST" });
        const taskState = await requestJson<{ task_status: string; status_history: string[] }>(`/api/projects/${project.project_id}/task`);
        setM1m2TestTaskStatus(taskState.task_status || "生成中"); setM1m2TestGenerateStatus("success");
        setM1m2TestMessage("完整流程完成: 上传 -> 分析 -> 确认 -> 生成已启动(状态: " + taskState.task_status + ")。");
      } catch (generateError) { setM1m2TestGenerateStatus("error"); setM1m2TestMessage("已完成分析+确认，但启动生成失败: " + (generateError instanceof Error ? generateError.message : "未知错误") + "。"); }
    } catch (error) { setM1m2TestMessage(error instanceof Error ? error.message : "M1/M2 选择测试失败"); } finally { setBusy(false); }
  }

  async function runM5CaseTest() {
    if (m5TestFiles.length === 0) return setM5TestMessage("请先选择一个或多个测试资料文件。");
    setBusy(true); setM5TestResult(null); setM5TestUploadedFiles([]); setM5TestReviewStatus("idle"); setM5TestGenerateStatus("idle"); setM5TestTaskStatus("");
    try {
      const project = await requestJson<Project>("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_name: m5TestProjectName || "M5案例匹配测试项目", project_location: "", owner_unit: "", product_line: "" }) });
      const body = new FormData(); m5TestFiles.forEach((file) => body.append("files", file));
      const stored = await requestJson<StoredFile[]>(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      setM5TestUploadedFiles(stored);
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setM5TestResult(result); setProjects((items) => [project, ...items]);
      const cases = result.case_selection?.recommended_cases;
      if (!cases || cases.length === 0) { setM5TestReviewStatus("idle"); setM5TestGenerateStatus("idle"); setM5TestMessage("分析完成但未找到推荐案例。完整流程测试未覆盖 review/generate 步骤。需使用包含匹配关键词的 fixture 文件重试。"); setBusy(false); return; }
      setM5TestMessage("分析完成，找到 " + cases.length + " 个推荐案例。下一步: 提交人工确认...");
      const detectedType = result.detected_project_type || result.confirmed_project_type || "metro";
      const firstCase = cases[0]; const confirmedCaseId = firstCase?.case_id != null ? String(firstCase.case_id) : null;
      try {
        await requestJson(`/api/projects/${project.project_id}/classification/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed_project_type: detectedType, template_selection: { M1_M2: result.template_selection?.M1_M2, M5: result.template_selection?.M5, M6: result.template_selection?.M6 }, confirmed_case_id: confirmedCaseId, notes: "M5 测试视图自动确认并选用推荐案例" }) });
        setM5TestReviewStatus("success"); setM5TestMessage("已完成: 上传 + 分析 + 确认(选用案例: " + (firstCase?.title || confirmedCaseId) + ")。下一步: 启动生成...");
      } catch (reviewError) { setM5TestReviewStatus("error"); setM5TestMessage("已完成分析(review 失败: " + (reviewError instanceof Error ? reviewError.message : "未知错误") + ")。"); setBusy(false); return; }
      setM5TestGenerateStatus("starting");
      try {
        await requestJson(`/api/projects/${project.project_id}/generate`, { method: "POST" });
        const taskState = await requestJson<{ task_status: string; status_history: string[] }>(`/api/projects/${project.project_id}/task`);
        setM5TestTaskStatus(taskState.task_status || "生成中"); setM5TestGenerateStatus("success");
        setM5TestMessage("完整流程完成: 上传 -> 分析 -> 确认(含案例) -> 生成已启动(状态: " + taskState.task_status + ")。");
      } catch (generateError) { setM5TestGenerateStatus("error"); setM5TestMessage("已完成分析+确认，但启动生成失败: " + (generateError instanceof Error ? generateError.message : "未知错误") + "。"); }
    } catch (error) { setM5TestMessage(error instanceof Error ? error.message : "M5 案例匹配测试失败"); } finally { setBusy(false); }
  }

  async function runDocumentParseTest() {
    if (docParseTestFiles.length === 0) return setDocumentParseTestMessage("请先选择要测试的文件。");
    setBusy(true); setDocParseTestResult(null); setDocParseTestProjectId(null);
    try {
      const project = await requestJson<Project>("/api/projects", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ project_name: "文档解析测试项目", project_location: "", owner_unit: "", product_line: "" }) });
      setDocParseTestProjectId(project.project_id);
      const body = new FormData(); docParseTestFiles.forEach((file) => body.append("files", file));
      await requestJson(`/api/projects/${project.project_id}/files`, { method: "POST", body });
      const result = await requestJson<ClassificationResult>(`/api/projects/${project.project_id}/analyze`, { method: "POST" });
      setDocParseTestResult(result);
      const parsedFiles = result.files ?? [];
      const successCount = parsedFiles.filter((f) => f.parse_status === "parsed").length;
      const pendingCount = parsedFiles.filter((f) => f.parse_status === "pending_enhancement").length;
      const failedCount = parsedFiles.filter((f) => f.parse_status === "failed").length;
      setDocumentParseTestMessage("解析完成, 共 " + parsedFiles.length + " 个文件(成功: " + successCount + ", 待增强: " + pendingCount + ", 失败: " + failedCount + "). " + "项目类型: " + labelForProjectType(result.detected_project_type) + "; 匹配关键词: " + (result.matched_keywords?.join(", ") || "暂无") + ".");
    } catch (error) { setDocumentParseTestMessage(error instanceof Error ? error.message : "解析测试失败"); } finally { setBusy(false); }
  }

  async function loadDocParseTestFullText(fileId: number) {
    if (!docParseTestProjectId) return;
    setDocParseTestLoadingFullText((prev) => ({ ...prev, [fileId]: true }));
    try {
      const result = await requestJson<{ text: string; error_message: string }>(`/api/projects/${docParseTestProjectId}/files/${fileId}/parsed-text`);
      setDocParseTestFullTextMap((prev) => ({ ...prev, [fileId]: result.text || result.error_message || "" }));
    } catch { setDocParseTestFullTextMap((prev) => ({ ...prev, [fileId]: "加载失败" })); } finally { setDocParseTestLoadingFullText((prev) => ({ ...prev, [fileId]: false })); }
  }

  function toggleDocParseTestFileExpanded(fileId: number) {
    setDocParseTestExpandedFiles((prev) => {
      const isExpanding = !prev[fileId];
      if (isExpanding && !docParseTestFullTextMap[fileId]) loadDocParseTestFullText(fileId);
      return { ...prev, [fileId]: isExpanding };
    });
  }

  async function runLlmConnectionTest() {
    const prompt = llmTestPrompt.trim();
    if (!prompt) return setLlmTestMessage("请先填写测试提示词。");
    setBusy(true); setLlmTestResult(null);
    try {
      const result = await requestJson<LlmTestResult>("/api/dev/llm-test", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prompt }) });
      setLlmTestResult(result); setLlmTestMessage(result.ok ? "大模型调用成功。" : `大模型调用失败：${result.error || result.status_code}`);
    } catch (error) { setLlmTestMessage(error instanceof Error ? error.message : "大模型测试失败"); } finally { setBusy(false); }
  }

  function updateM3FullTestBulkFiles(files: File[]) { setM3FullTestBulkFiles(files); setM3FullTestResult(null); setM3FullTestMessage("已选择 M3 测试资料，系统将按文件名自动分类。"); }

  async function runM3FullRenderTest() {
    if (!m3FullTestProjectName.trim()) return setM3FullTestMessage("请先填写项目名称。");
    if (m3FullTestBulkFiles.length === 0) return setM3FullTestMessage("请先批量上传按九类命名的 M3 图片或表格。");
    const formData = new FormData();
    formData.append("project_name", m3FullTestProjectName); formData.append("texts", JSON.stringify({})); formData.append("descriptions", m3FullTestDescriptions);
    m3FullTestBulkFiles.forEach((file) => formData.append("files", file));
    setBusy(true); setM3FullTestResult(null);
    try {
      const result = await requestJson<M3FullTestResult>("/api/test/m3-full-render", { method: "POST", body: formData });
      setM3FullTestResult(result); setM3FullTestMessage(result.ok ? "M3 完整测试 PPTX 已生成，点击下载链接获取文件。" : "M3 完整测试失败。");
    } catch (error) { setM3FullTestMessage(error instanceof Error ? error.message : "M3 完整测试失败"); } finally { setBusy(false); }
  }

  function downloadFinal() {
    if (!currentProject) return toast.error("请先创建项目。");
    window.location.href = `${API_BASE}/api/projects/${currentProject.project_id}/download`;
  }

  async function previewFinalPpt() {
    if (!currentProject) return toast.error("请先创建项目。");
    setPreviewLoading(true); setPreviewError("");
    try {
      const result = await requestJson<{slide_count: number; slides: {index: number; image_url: string}[]}>(`/api/projects/${currentProject.project_id}/preview`, { method: "POST" });
      setPreviewSlides(result.slides); setPreviewCurrentIndex(0); setPreviewOpen(true);
    } catch (error) { const msg = error instanceof Error ? error.message : "预览生成失败"; setPreviewError(msg); toast.error(msg); } finally { setPreviewLoading(false); }
  }

  async function handleSelectProject(project: Project) {
    setCurrentProject(project);
    setTask(null); setClassification(null); setShowClassificationDetails(false);
    setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
    setUploadSuccess(false);
    try {
      const [cls, taskState] = await Promise.allSettled([
        requestJson<ClassificationResult>(`/api/projects/${project.project_id}/classification`),
        requestJson<TaskState>(`/api/projects/${project.project_id}/task`),
      ]);
      if (cls.status === "fulfilled") {
        setClassification(cls.value);
        const detectedType = cls.value.confirmed_project_type || cls.value.detected_project_type || "";
        const preferredProjectType = projectTypeFromProductLine(project.product_line);
        const defaultProjectType = preferredProjectType || detectedType;
        const templateKey = preferredProjectType || cls.value.template_selection?.M1_M2?.template_key || detectedType;
        const confirmedCaseId = cls.value.case_selection?.confirmed_case_id;
        const newCaseId = confirmedCaseId != null ? String(confirmedCaseId) : (cls.value.case_selection?.recommended_cases?.[0]?.case_id != null ? String(cls.value.case_selection.recommended_cases[0].case_id) : "");
        setReviewForm({ projectType: defaultProjectType, m1m2Template: templateKey, caseId: newCaseId, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
      }
      if (taskState.status === "fulfilled") setTask(taskState.value);
    } catch { /* silent */ }
  }

  const pageTitle = viewTitles[activeView];
  const isFunctionTestView = activeView === "function-tests" || FUNCTION_TEST_VIEWS.includes(activeView);

  return (
    <main className="shell">
      {confirmDeleteOpen ? (
        <ConfirmDialog
          title="确认删除项目"
          message={`确定要删除选中的 ${selectedProjectIds.length} 个项目吗？此操作不可撤销。`}
          confirmText="确认删除"
          danger
          onConfirm={deleteSelectedProjects}
          onCancel={() => setConfirmDeleteOpen(false)}
        />
      ) : null}
      {m3NamingHelpOpen ? <M3NamingHelpModal onClose={() => setM3NamingHelpOpen(false)} /> : null}
      {previewOpen ? <PreviewModal slides={previewSlides} currentIndex={previewCurrentIndex} onIndexChange={setPreviewCurrentIndex} onClose={() => setPreviewOpen(false)} error={previewError} currentProject={currentProject} /> : null}
      <aside className="sidebar" aria-label="主导航">
        <div className="brand"><div className="brandMark" aria-hidden="true" /><div><strong>中驰售前PPT助手</strong></div></div>
        <nav className="sidebar-nav">
          <a className={activeView === "projects" ? "navItem active" : "navItem"} href="#projects">我的项目</a>
          <a className={activeView === "create" ? "navItem active" : "navItem"} href="#create">新建项目</a>
          <a className={activeView === "cases" ? "navItem active" : "navItem"} href="#cases">案例库</a>
          <a className={`navItem navItem-expandable${isFunctionTestView ? " active" : ""}`} onClick={() => setNavTestExpanded(!navTestExpanded)} style={{ cursor: "pointer" }}>
            功能测试
            <span className={`nav-arrow${navTestExpanded ? " expanded" : ""}`}>&rsaquo;</span>
          </a>
          {navTestExpanded ? (
            <div className="navSubList">
              <a className={`navSubItem${activeView === "m1m2-test" ? " active" : ""}`} href="#m1m2-test">M1/M2选择测试</a>
              <a className={`navSubItem${activeView === "m3-full-test" ? " active" : ""}`} href="#m3-full-test">M3完整测试</a>
              <a className={`navSubItem${activeView === "m5-test" ? " active" : ""}`} href="#m5-test">M5选择测试</a>
              <a className={`navSubItem${activeView === "document-parse-test" ? " active" : ""}`} href="#document-parse-test">文档解析测试</a>
              <a className={`navSubItem${activeView === "llm-test" ? " active" : ""}`} href="#llm-test">大模型测试</a>
            </div>
          ) : null}
        </nav>
      </aside>
      <section className="content">
        <header className="topbar"><div className="topbar-title-area"><h1>{pageTitle.title}</h1><p>{pageTitle.description}</p></div>{activeView === "projects" ? <div className="topbarActions"><button className="secondaryButton" onClick={toggleProjectManagement} type="button">{isManagingProjects ? "取消管理" : "管理项目"}</button><a className="primaryButton" href="#create">新建项目</a></div> : null}</header>

        {activeView === "projects" ? <ProjectsView projects={projects} currentProject={currentProject} setCurrentProject={handleSelectProject} task={task} setTask={setTask} classification={classification} setClassification={setClassification} showClassificationDetails={showClassificationDetails} setShowClassificationDetails={setShowClassificationDetails} qualityReportExpanded={qualityReportExpanded} setQualityReportExpanded={setQualityReportExpanded} reviewForm={reviewForm} setReviewForm={setReviewForm} recommendedCases={recommendedCases} m5FixedCases={m5FixedCases} canSaveFullPptCase={canSaveFullPptCase} productLineClassificationConflict={productLineClassificationConflict} hasMoreProjects={hasMoreProjects} totalProjectPages={totalProjectPages} visibleProjects={visibleProjects} projectListExpanded={projectListExpanded} setProjectListExpanded={setProjectListExpanded} projectListPage={projectListPage} setProjectListPage={setProjectListPage} isManagingProjects={isManagingProjects} selectedProjectIds={selectedProjectIds} activeStatus={activeStatus} statusHistory={statusHistory} qualityReport={qualityReport} message={message} busy={busy} uploadSuccess={uploadSuccess} selectedFiles={selectedFiles} setSelectedFiles={setSelectedFiles} uploadedFiles={uploadedFiles} isEditingProject={isEditingProject} setIsEditingProject={setIsEditingProject} editForm={editForm} setEditForm={setEditForm} m3MaterialsResult={m3MaterialsResult} previewLoading={previewLoading} m3MaterialAutoPreview={m3MaterialAutoPreview} toggleProjectManagement={toggleProjectManagement} toggleProjectSelection={toggleProjectSelection} deleteSelectedProjects={requestDeleteProjects} uploadProjectFiles={uploadProjectFiles} analyzeProject={analyzeProject} submitClassificationReview={submitClassificationReview} generate={generate} saveFullPptCase={saveFullPptCase} previewFinalPpt={previewFinalPpt} downloadFinal={downloadFinal} updateProjectBasicInfo={updateProjectBasicInfo} setM3NamingHelpOpen={setM3NamingHelpOpen} /> : null}

        {activeView === "project-m3-materials" ? <M3MaterialsView currentProject={currentProject} m3MaterialsResult={m3MaterialsResult} m3MaterialBulkFiles={m3MaterialBulkFiles} m3MaterialDescriptions={m3MaterialDescriptions} setM3MaterialDescriptions={setM3MaterialDescriptions} m3MaterialsMessage={m3MaterialsMessage} m3MaterialAutoPreview={m3MaterialAutoPreview} busy={busy} updateM3MaterialBulkFiles={updateM3MaterialBulkFiles} saveM3Materials={saveM3Materials} setM3NamingHelpOpen={setM3NamingHelpOpen} /> : null}

        {activeView === "create" ? <CreateProjectView busy={busy} onSubmit={createProject} /> : null}

        {activeView === "cases" ? <CaseLibraryView caseLibraryTab={caseLibraryTab} setCaseLibraryTab={setCaseLibraryTab} m5FixedCases={m5FixedCases} fullPptCases={fullPptCases} /> : null}

        {activeView === "function-tests" ? <FunctionTestsView /> : null}

        {activeView === "m1m2-test" ? <M1M2TestView m1m2TestProjectName={m1m2TestProjectName} setM1m2TestProjectName={setM1m2TestProjectName} m1m2TestFiles={m1m2TestFiles} setM1m2TestFiles={setM1m2TestFiles} m1m2TestUploadedFiles={m1m2TestUploadedFiles} m1m2TestMessage={m1m2TestMessage} m1m2TestResult={m1m2TestResult} m1m2TestReviewStatus={m1m2TestReviewStatus} m1m2TestGenerateStatus={m1m2TestGenerateStatus} m1m2TestTaskStatus={m1m2TestTaskStatus} busy={busy} runM1M2TemplateTest={runM1M2TemplateTest} /> : null}

        {activeView === "m5-test" ? <M5TestView m5TestProjectName={m5TestProjectName} setM5TestProjectName={setM5TestProjectName} m5TestFiles={m5TestFiles} setM5TestFiles={setM5TestFiles} m5TestUploadedFiles={m5TestUploadedFiles} m5TestMessage={m5TestMessage} m5TestResult={m5TestResult} m5TestReviewStatus={m5TestReviewStatus} m5TestGenerateStatus={m5TestGenerateStatus} m5TestTaskStatus={m5TestTaskStatus} busy={busy} runM5CaseTest={runM5CaseTest} /> : null}

        {activeView === "document-parse-test" ? <DocParseTestView docParseTestFiles={docParseTestFiles} setDocParseTestFiles={setDocumentParseTestFiles} docParseTestMessage={docParseTestMessage} docParseTestResult={docParseTestResult} docParseTestExpandedFiles={docParseTestExpandedFiles} docParseTestLoadingFullText={docParseTestLoadingFullText} docParseTestFullTextMap={docParseTestFullTextMap} busy={busy} runDocumentParseTest={runDocumentParseTest} toggleDocParseTestFileExpanded={toggleDocParseTestFileExpanded} /> : null}

        {activeView === "llm-test" ? <LlmTestView llmTestPrompt={llmTestPrompt} setLlmTestPrompt={setLlmTestPrompt} llmTestMessage={llmTestMessage} llmTestResult={llmTestResult} busy={busy} runLlmConnectionTest={runLlmConnectionTest} /> : null}

        {activeView === "m3-full-test" ? <M3FullTestView m3FullTestProjectName={m3FullTestProjectName} setM3FullTestProjectName={setM3FullTestProjectName} m3FullTestBulkFiles={m3FullTestBulkFiles} m3FullTestDescriptions={m3FullTestDescriptions} setM3FullTestDescriptions={setM3FullTestDescriptions} m3FullTestMessage={m3FullTestMessage} m3FullTestResult={m3FullTestResult} m3FullAutoPreview={m3FullAutoPreview} busy={busy} updateM3FullTestBulkFiles={updateM3FullTestBulkFiles} runM3FullRenderTest={runM3FullRenderTest} setM3NamingHelpOpen={setM3NamingHelpOpen} /> : null}

      </section>
    </main>
  );
}

export default function HomePage() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  );
}
