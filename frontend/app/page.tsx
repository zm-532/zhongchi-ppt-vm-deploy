"use client";

import { FormEvent, Fragment, useCallback, useEffect, useMemo, useState } from "react";

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

const productLineProjectTypeMap: Record<string, string> = {
  "轨道交通声屏障": "metro",
  "地铁声屏障": "metro",
  "轨交既有线改造": "existing_rail_transit",
  "公路声屏障": "highway",
  "铁路声屏障": "railway",
};

const M5_DEMO_CASE = { case_id: "m5_demo", title: "M5示例案例", match_reason: "演示全流程使用的固定 M5 案例模板。" };

const M3_FULL_SECTIONS = [
  { title: "项目基本情况", textField: "m3_basic_summary", imageField: "image:m3_basic" },
  { title: "项目线路图", textField: "m3_line_summary", imageField: "image:m3_line" },
  { title: "敏感点路段", textField: "m3_sensitive_points_summary", imageField: "image:m3_sensitive_points" },
  { title: "工程量统计", textField: "m3_quantity_summary", imageField: "image:m3_quantity" },
  { title: "结构形式", textField: "m3_structure_summary", imageField: "image:m3_structure" },
  { title: "现场踏勘", textField: "m3_site_survey_summary", imageField: "image:m3_site_survey" },
  { title: "现场勘察情况", textField: "m3_investigation_summary", imageField: "image:m3_investigation" },
  { title: "项目重难点分析", textField: "m3_risk_summary", imageField: "image:m3_risk" },
  { title: "重难点应对措施", textField: "m3_solution_summary", imageField: "image:m3_solution" },
];
const M3_SECTION_TITLE_ALIASES: Record<string, string> = {
  "现场勘查情况": "现场勘察情况",
};

function M3NamingHelpButton({ onOpen }: { onOpen: () => void }) {
  return (
    <button aria-label="查看 M3 图片命名规则" className="iconHelpButton" onClick={onOpen} type="button">?</button>
  );
}

type ViewId = "projects" | "create" | "cases" | "project-m3-materials" | "function-tests" | "m1m2-test" | "m3-full-test" | "m5-test" | "document-parse-test" | "llm-test";
type Project = {
  project_id: number;
  project_name: string;
  project_location?: string;
  owner_unit?: string;
  product_line?: string;
  task_status: string;
  status_history?: string[];
  final_ppt_path?: string;
  include_print_tail_page?: boolean;
  quality_report?: QualityReport;
};
type QualityReport = {
  passed?: boolean;
  severity?: "pass" | "warning" | "error" | string;
  errors?: string[];
  warnings?: string[];
  checks?: Array<{ name?: string; passed?: boolean; severity?: string; message?: string }>;
  checked_at?: string;
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
  classification_method?: string;
  llm_reasoning_summary?: string;
  fallback_reason?: string;
  template_selection?: {
    M1_M2?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
    M5?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
    M6?: { template_key?: string; template_path?: string; template_name?: string; template_filename?: string };
  };
  case_selection?: CaseSelection;
  missing_fields?: string[];
  files?: StoredFile[];
};
type TaskState = { project_id: number; task_status: string; status_history: string[]; quality_report?: QualityReport };
type ReviewForm = { projectType: string; m1m2Template: string; caseId?: string; m3Selection: string; includePrintTailPage: boolean; notes: string };
type RecommendedCase = { case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string };
type LlmTestResult = { ok: boolean; status_code: number; model: string; reply: string; error: string; configured: Record<string, boolean> };
type M3FullTestResult = { ok: boolean; pptx_path: string; download_url: string; slide_count: number; image_summary: Record<string, number>; table_summary?: Record<string, number> };
type CaseLibraryItem = { case_id: string | number; title: string; filename?: string; project_type?: string; source_path?: string; module_id?: string; source_type?: string };
type FullPptCaseItem = { case_id: string; project_id: number; title: string; filename: string; project_type?: string; source_path: string; source_type: "full_ppt"; stored_at: string; file_size: number; download_url: string };
type M3MaterialImage = { purpose: string; filename: string; content_type?: string; stored_path: string; description?: string; page_index?: number };
type M3MaterialTable = { purpose: string; filename: string; content_type?: string; stored_path: string; page_index?: number };
type M3MaterialsResult = {
  project_id: number;
  texts: Record<string, string>;
  images: M3MaterialImage[];
  tables?: M3MaterialTable[];
  page_texts?: Record<string, string[]>;
  text_completed_count: number;
  text_total_count: number;
  image_count: number;
  image_summary: Record<string, number>;
  table_count?: number;
  table_summary?: Record<string, number>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8010";
const PROJECT_LIST_PREVIEW_LIMIT = 5;
const PROJECT_LIST_PAGE_SIZE = 10;
const viewTitles: Record<ViewId, { title: string; description: string }> = {
  projects: { title: "我的项目", description: "创建项目、统一上传项目资料，并确认系统识别结果。" },
  create: { title: "新建项目", description: "填写基础信息后创建一个新的售前 PPT 项目。" },
  cases: { title: "案例库管理", description: "维护历史案例，供系统按项目标签推荐引用。" },
  "project-m3-materials": { title: "M3资料上传", description: "按 M3 九部分维护项目深化方案文字、图片和 Excel 表格资料。" },
  "function-tests": { title: "功能测试", description: "开发过程验证入口，收纳内部功能测试页面，普通前端用户无需使用。" },
  "m1m2-test": { title: "M1/M2选择测试", description: "上传测试资料，根据文件名和解析文本识别项目类型并选择对应 M1/M2 固化模板。" },
  "m3-full-test": { title: "M3完整测试", description: "按 M3 九部分测试文字与图片占位符替换，多图自动扩页。" },
  "m5-test": { title: "M5选择测试", description: "上传测试资料，根据项目标签从案例库匹配相似案例并显示匹配理由。" },
  "document-parse-test": { title: "文档解析测试", description: "用于测试不同格式资料的文本与结构化解析效果。" },
  "llm-test": { title: "大模型测试", description: "调用后端开发测试接口，验证当前 LLM 环境变量和中转站请求是否可用。" },
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

function projectTypeFromProductLine(productLine?: string) {
  return productLineProjectTypeMap[String(productLine || "").trim()] || "";
}

function firstTemplateName(item?: { template_path?: string; template_name?: string; template_key?: string; template_filename?: string }) {
  if (!item) return "待识别";
  return item.template_filename || item.template_name || item.template_path?.split(/[\\/]/).pop() || item.template_key || "待识别";
}

function getProjectStatusClass(status: string) {
  if (!status) return "status-idle";
  if (status === "完成") return "status-done";
  if (status === "待确认") return "status-review";
  if (status === "待上传") return "status-idle";
  if (status.includes("失败") || status.includes("错误")) return "status-error";
  if (status.includes("中")) return "status-running";
  return "status-idle";
}

function qualityReportLabel(report?: QualityReport) {
  if (!report) return "待检查";
  if (report.severity === "error" || report.passed === false) return "检查失败";
  if (report.severity === "warning" || (report.warnings?.length ?? 0) > 0) return "有风险";
  return "通过";
}

function formatStoredAt(value?: string) {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatFileSize(bytes?: number) {
  if (!bytes || bytes <= 0) return "未知大小";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function HomePage() {
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

  // PPT 预览
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewSlides, setPreviewSlides] = useState<{index: number; image_url: string}[]>([]);
  const [previewCurrentIndex, setPreviewCurrentIndex] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

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
  const m5FixedCases = useMemo(() => caseLibraryItems.filter((item) => item.source_type === "fixed_m5" && item.module_id === "M5"), [caseLibraryItems]);
  const canSaveFullPptCase = Boolean(currentProject?.final_ppt_path) && activeStatus === "完成";
  const productLineClassificationConflict = useMemo(() => {
    const preferredProjectType = projectTypeFromProductLine(currentProject?.product_line);
    const detectedProjectType = classification?.detected_project_type || "";
    if (!preferredProjectType || !detectedProjectType || preferredProjectType === detectedProjectType) return null;
    return {
      productLine: currentProject?.product_line || "",
      preferredProjectType,
      detectedProjectType,
    };
  }, [classification?.detected_project_type, currentProject?.product_line]);
  const hasMoreProjects = projects.length > PROJECT_LIST_PREVIEW_LIMIT;
  const totalProjectPages = Math.ceil(projects.length / PROJECT_LIST_PAGE_SIZE);
  const visibleProjects = projectListExpanded
    ? projects.slice((projectListPage - 1) * PROJECT_LIST_PAGE_SIZE, projectListPage * PROJECT_LIST_PAGE_SIZE)
    : projects.slice(0, PROJECT_LIST_PREVIEW_LIMIT);
  const m3FullAutoPreview = useMemo(() => {
    const normalize = (value: string) => value.trim().replace(/\s+/g, "");
    const parseImageKey = (value: string) => {
      const normalized = normalize(value);
      const match = normalized.match(/^(.+?)(?:-(\d+))?$/);
      if (!match) return null;
      const section = M3_FULL_SECTIONS.find((item) => item.title === match[1]);
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: match[2] ? Number(match[2]) : -1, label: normalized };
    };
    const parseTableKey = (value: string) => {
      const normalized = normalize(value);
      const aliased = Object.entries(M3_SECTION_TITLE_ALIASES).reduce((current, [alias, canonical]) => {
        const normalizedAlias = normalize(alias);
        const normalizedCanonical = normalize(canonical);
        if (current === normalizedAlias) return normalizedCanonical;
        if (current.startsWith(`${normalizedAlias}-`)) return `${normalizedCanonical}-${current.slice(normalizedAlias.length + 1)}`;
        return current;
      }, normalized);
      const section = M3_FULL_SECTIONS.find((item) => aliased === item.title || aliased.startsWith(`${item.title}-`));
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: -1, label: normalized };
    };
    const fileRows = m3FullTestBulkFiles.map((file) => {
      const nameWithoutExt = file.name.replace(/\.[^.]+$/, "");
      const isTable = /\.xlsx$/i.test(file.name);
      const parsed = isTable ? parseTableKey(nameWithoutExt) : parseImageKey(nameWithoutExt);
      return { filename: file.name, parsed, isTable };
    });
    const descriptionRows = m3FullTestDescriptions
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^([^:：]+)[:：](.*)$/);
        const parsed = match ? parseImageKey(match[1]) : null;
        return { line, parsed, valid: Boolean(match && parsed) };
      });
    const grouped = M3_FULL_SECTIONS.map((section) => ({
      ...section,
      files: fileRows
        .filter((row) => row.parsed?.imageField === section.imageField && !row.isTable)
        .sort((a, b) => (a.parsed?.order ?? 0) - (b.parsed?.order ?? 0)),
      tables: fileRows.filter((row) => row.parsed?.imageField === section.imageField && row.isTable),
      descriptions: descriptionRows.filter((row) => row.parsed?.imageField === section.imageField),
    })).filter((section) => section.files.length || section.tables.length || section.descriptions.length);
    return {
      grouped,
      unknownFiles: fileRows.filter((row) => !row.parsed).map((row) => row.filename),
      invalidDescriptions: descriptionRows.filter((row) => !row.valid).map((row) => row.line),
    };
  }, [m3FullTestBulkFiles, m3FullTestDescriptions]);
  const m3MaterialAutoPreview = useMemo(() => {
    const normalize = (value: string) => value.trim().replace(/\s+/g, "");
    const parseImageKey = (value: string) => {
      const normalized = normalize(value);
      const match = normalized.match(/^(.+?)(?:-(\d+))?$/);
      if (!match) return null;
      const section = M3_FULL_SECTIONS.find((item) => item.title === match[1]);
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: match[2] ? Number(match[2]) : -1, label: normalized };
    };
    const parseTableKey = (value: string) => {
      const normalized = normalize(value);
      const aliased = Object.entries(M3_SECTION_TITLE_ALIASES).reduce((current, [alias, canonical]) => {
        const normalizedAlias = normalize(alias);
        const normalizedCanonical = normalize(canonical);
        if (current === normalizedAlias) return normalizedCanonical;
        if (current.startsWith(`${normalizedAlias}-`)) return `${normalizedCanonical}-${current.slice(normalizedAlias.length + 1)}`;
        return current;
      }, normalized);
      const section = M3_FULL_SECTIONS.find((item) => aliased === item.title || aliased.startsWith(`${item.title}-`));
      if (!section) return null;
      return { title: section.title, imageField: section.imageField, order: -1, label: normalized };
    };
    const fileRows = m3MaterialBulkFiles.map((file) => {
      const nameWithoutExt = file.name.replace(/\.[^.]+$/, "");
      const isTable = /\.xlsx$/i.test(file.name);
      const parsed = isTable ? parseTableKey(nameWithoutExt) : parseImageKey(nameWithoutExt);
      return { filename: file.name, parsed, isTable };
    });
    const descriptionRows = m3MaterialDescriptions
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const match = line.match(/^([^:：]+)[:：](.*)$/);
        const parsed = match ? parseImageKey(match[1]) : null;
        return { line, parsed, valid: Boolean(match && parsed) };
      });
    const grouped = M3_FULL_SECTIONS.map((section) => ({
      ...section,
      files: fileRows
        .filter((row) => row.parsed?.imageField === section.imageField && !row.isTable)
        .sort((a, b) => (a.parsed?.order ?? 0) - (b.parsed?.order ?? 0)),
      tables: fileRows.filter((row) => row.parsed?.imageField === section.imageField && row.isTable),
      descriptions: descriptionRows.filter((row) => row.parsed?.imageField === section.imageField),
    })).filter((section) => section.files.length || section.tables.length || section.descriptions.length);
    return {
      grouped,
      unknownFiles: fileRows.filter((row) => !row.parsed).map((row) => row.filename),
      invalidDescriptions: descriptionRows.filter((row) => !row.valid).map((row) => row.line),
    };
  }, [m3MaterialBulkFiles, m3MaterialDescriptions]);

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
      setActiveView(
        nextView === "create" ||
        nextView === "cases" ||
        nextView === "project-m3-materials" ||
        nextView === "function-tests" ||
        nextView === "m1m2-test" ||
        nextView === "m5-test" ||
        nextView === "document-parse-test" ||
        nextView === "m3-full-test" ||
        nextView === "llm-test"
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
      // 只有在 caseId 从未设置过（undefined）时才用默认值初始化，
      // 一旦用户明确选择过（包括空字符串），就不再覆盖。
      const needsInitCaseId = value.caseId === undefined || value.caseId === null;
      let newCaseId = value.caseId;
      if (needsInitCaseId) {
        // 首次初始化：优先用后端确认的 caseId，其次用推荐列表第一个，均无则为空（暂不选择）
        newCaseId = confirmedCaseId !== undefined && confirmedCaseId !== null
          ? String(confirmedCaseId)
          : (recommendedCases[0]?.case_id !== undefined ? String(recommendedCases[0].case_id) : "");
      }

      return {
        ...value,
        projectType: value.projectType || defaultProjectType || "",
        m1m2Template: value.m1m2Template || templateKey || "",
        caseId: newCaseId,
        // m3Selection 不在 useEffect 中重置，保持用户选择或默认 "m3_template"
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
        (result.images || [])
          .filter((image) => image.description)
          .map((image) => {
            const section = M3_FULL_SECTIONS.find((item) => item.imageField === image.purpose);
            return section ? `${section.title}-${image.page_index || 1}：${image.description}` : "";
          })
          .filter(Boolean)
          .join("\n")
      );
      setM3MaterialsMessage("M3资料已加载，如需替换请重新批量上传图片或 Excel 表格。");
    } catch (error) {
      setM3MaterialsResult(null);
      setM3MaterialBulkFiles([]);
      setM3MaterialDescriptions("");
      setM3MaterialsMessage(error instanceof Error ? error.message : "M3资料加载失败");
    }
  }, []);

  useEffect(() => {
    if (!currentProject) {
      setM3MaterialsResult(null);
      setM3MaterialBulkFiles([]);
      setM3MaterialDescriptions("");
      return;
    }
    loadM3Materials(currentProject.project_id);
  }, [currentProject?.project_id, loadM3Materials]);

  function updateM3MaterialBulkFiles(files: File[]) {
    setM3MaterialBulkFiles(files);
    setM3MaterialsMessage("已选择新资料，保存后会替换已保存的 M3 图片和表格。");
  }

  async function saveM3Materials(returnToProjects = false) {
    if (!currentProject) return setM3MaterialsMessage("请先选择项目。");
    if (m3MaterialBulkFiles.length === 0) return setM3MaterialsMessage("请先批量上传按九类命名的 M3 图片或 Excel 表格。");
    const formData = new FormData();
    formData.append("descriptions", m3MaterialDescriptions);
    m3MaterialBulkFiles.forEach((file) => formData.append("files", file));

    setBusy(true);
    try {
      const result = await requestJson<M3MaterialsResult>(`/api/projects/${currentProject.project_id}/m3-materials`, {
        method: "POST",
        body: formData,
      });
      setM3MaterialsResult(result);
      setM3MaterialBulkFiles([]);
      setM3MaterialDescriptions(
        (result.images || [])
          .filter((image) => image.description)
          .map((image) => {
            const section = M3_FULL_SECTIONS.find((item) => item.imageField === image.purpose);
            return section ? `${section.title}-${image.page_index || 1}：${image.description}` : "";
          })
          .filter(Boolean)
          .join("\n")
      );
      setM3MaterialsMessage(`M3资料已保存：已填写 ${result.text_completed_count}/${result.text_total_count}，已上传 ${result.image_count} 张图片、${result.table_count || 0} 个表格。`);
      if (returnToProjects) {
        setActiveView("projects");
        window.location.hash = "projects";
        setMessage("M3资料已保存，可继续识别、确认或生成。");
      }
    } catch (error) {
      setM3MaterialsMessage(error instanceof Error ? error.message : "M3资料保存失败");
    } finally {
      setBusy(false);
    }
  }

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
      setShowClassificationDetails(false);
      setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
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
      setShowClassificationDetails(false);
      setCurrentProject(await requestJson<Project>(`/api/projects/${currentProject.project_id}`));
      // 重置 reviewForm 为新识别结果，确保 M5 默认选中新推荐案例
      const detectedType = result.confirmed_project_type || result.detected_project_type || "";
      const preferredProjectType = projectTypeFromProductLine(currentProject?.product_line);
      const defaultProjectType = preferredProjectType || detectedType;
      const templateKey = preferredProjectType || result.template_selection?.M1_M2?.template_key || detectedType;
      const newCaseId = result.case_selection?.confirmed_case_id != null
        ? String(result.case_selection.confirmed_case_id)
        : (result.case_selection?.recommended_cases?.[0]?.case_id != null ? String(result.case_selection.recommended_cases[0].case_id) : "");
      setReviewForm({ projectType: defaultProjectType, m1m2Template: templateKey, caseId: newCaseId, m3Selection: "m3_template", includePrintTailPage: false, notes: "" });
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
          include_print_tail_page: reviewForm.includePrintTailPage,
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

  async function saveFullPptCase() {
    if (!currentProject) return setMessage("请先创建项目。");
    if (!canSaveFullPptCase) return setMessage("请先完成 PPT 生成，再存入案例库。");
    setBusy(true);
    try {
      const saved = await requestJson<FullPptCaseItem>(
        `/api/projects/${currentProject.project_id}/full-ppt-case`,
        { method: "POST" },
      );
      await refreshFullPptCases();
      setCaseLibraryTab("full-ppt");
      setMessage(`已存入完整PPT案例库：${saved.title || saved.filename}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "存入案例库失败");
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

  function updateM3FullTestBulkFiles(files: File[]) {
    setM3FullTestBulkFiles(files);
    setM3FullTestResult(null);
    setM3FullTestMessage("已选择 M3 测试资料，系统将按文件名自动分类。");
  }

  async function runM3FullRenderTest() {
    if (!m3FullTestProjectName.trim()) return setM3FullTestMessage("请先填写项目名称。");
    if (m3FullTestBulkFiles.length === 0) return setM3FullTestMessage("请先批量上传按九类命名的 M3 图片或表格。");
    const formData = new FormData();
    formData.append("project_name", m3FullTestProjectName);
    formData.append("texts", JSON.stringify({}));
    formData.append("descriptions", m3FullTestDescriptions);
    m3FullTestBulkFiles.forEach((file) => formData.append("files", file));

    setBusy(true);
    setM3FullTestResult(null);
    try {
      const result = await requestJson<M3FullTestResult>("/api/test/m3-full-render", {
        method: "POST",
        body: formData,
      });
      setM3FullTestResult(result);
      setM3FullTestMessage(result.ok ? "M3 完整测试 PPTX 已生成，点击下载链接获取文件。" : "M3 完整测试失败。");
    } catch (error) {
      setM3FullTestMessage(error instanceof Error ? error.message : "M3 完整测试失败");
    } finally {
      setBusy(false);
    }
  }

  function downloadFinal() {
    if (!currentProject) return setMessage("请先创建项目。");
    window.location.href = `${API_BASE}/api/projects/${currentProject.project_id}/download`;
  }

  async function previewFinalPpt() {
    if (!currentProject) return setMessage("请先创建项目。");
    setPreviewLoading(true);
    setPreviewError("");
    try {
      const result = await requestJson<{slide_count: number; slides: {index: number; image_url: string}[]}>(
        `/api/projects/${currentProject.project_id}/preview`,
        { method: "POST" },
      );
      setPreviewSlides(result.slides);
      setPreviewCurrentIndex(0);
      setPreviewOpen(true);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "预览生成失败";
      setPreviewError(msg);
      setMessage(msg);
    } finally {
      setPreviewLoading(false);
    }
  }

  const pageTitle = viewTitles[activeView];
  const isFunctionTestView = activeView === "function-tests" || activeView === "m1m2-test" || activeView === "m3-full-test" || activeView === "m5-test" || activeView === "document-parse-test" || activeView === "llm-test";

  return (
    <main className="shell">
      {m3NamingHelpOpen ? (
        <div className="modalBackdrop" role="presentation" onMouseDown={() => setM3NamingHelpOpen(false)}>
          <div aria-modal="true" className="modalPanel" role="dialog" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modalHeader">
              <h2>M3图片命名规则</h2>
              <button aria-label="关闭命名规则弹窗" className="iconCloseButton" onClick={() => setM3NamingHelpOpen(false)} type="button">×</button>
            </div>
            <div className="namingRules">
              <p>总共有这九类：</p>
              <div className="ruleGrid">
                {M3_FULL_SECTIONS.map((section) => <span key={`rule-${section.imageField}`}>{section.title}</span>)}
              </div>
              <p>如果只有一张图，可以使用“项目基本情况.jpg”。</p>
              <p>多张图必须使用“项目基本情况-1.jpg”“项目基本情况-2.jpg”。</p>
              <p>描述文本按同样编号填写，例如“项目基本情况-1：第一张图片说明”。</p>
            </div>
          </div>
        </div>
      ) : null}
      {previewOpen ? (
        <div className="modalBackdrop" role="presentation" onMouseDown={() => setPreviewOpen(false)}>
          <div aria-modal="true" className="previewModalPanel" role="dialog" onMouseDown={(event) => event.stopPropagation()}>
            <div className="modalHeader">
              <h2>PPT 预览 ({previewCurrentIndex + 1} / {previewSlides.length})</h2>
              <button aria-label="关闭预览" className="iconCloseButton" onClick={() => setPreviewOpen(false)} type="button">&times;</button>
            </div>
            {previewError ? <div className="previewError">{previewError}</div> : null}
            <div className="previewBody">
              <button
                className="previewNavButton"
                disabled={previewCurrentIndex <= 0}
                onClick={() => setPreviewCurrentIndex((i) => Math.max(0, i - 1))}
                type="button"
              >&lsaquo;</button>
              <div className="previewImageContainer">
                {previewSlides.length > 0 ? (
                  <img
                    className="previewImage"
                    src={`${API_BASE}${previewSlides[previewCurrentIndex].image_url}`}
                    alt={`第 ${previewCurrentIndex + 1} 页`}
                  />
                ) : null}
              </div>
              <button
                className="previewNavButton"
                disabled={previewCurrentIndex >= previewSlides.length - 1}
                onClick={() => setPreviewCurrentIndex((i) => Math.min(previewSlides.length - 1, i + 1))}
                type="button"
              >&rsaquo;</button>
            </div>
            <div className="previewThumbnailStrip">
              {previewSlides.map((slide, idx) => (
                <button
                  key={slide.index}
                  className={`previewThumbnail${idx === previewCurrentIndex ? " previewThumbnailActive" : ""}`}
                  onClick={() => setPreviewCurrentIndex(idx)}
                  type="button"
                >
                  <img src={`${API_BASE}${slide.image_url}`} alt={`缩略图 ${slide.index}`} />
                  <span>{slide.index}</span>
                </button>
              ))}
            </div>
            <div className="previewFooter">
              <a className="primaryButton btn-xs" href={`${API_BASE}/api/projects/${currentProject?.project_id}/download`} download>下载 PPTX</a>
            </div>
          </div>
        </div>
      ) : null}
      <aside className="sidebar" aria-label="主导航">
        <div className="brand"><div className="brandMark" aria-hidden="true" /><div><strong>中驰售前PPT助手</strong></div></div>
        <nav className="sidebar-nav">
          <a className={activeView === "projects" ? "navItem active" : "navItem"} href="#projects">我的项目</a>
          <a className={activeView === "create" ? "navItem active" : "navItem"} href="#create">新建项目</a>
          <a className={activeView === "cases" ? "navItem active" : "navItem"} href="#cases">案例库管理</a>
          <a className={isFunctionTestView ? "navItem active" : "navItem"} href="#function-tests">功能测试</a>
        </nav>
      </aside>
      <section className="content">
        <header className="topbar"><div className="topbar-title-area"><h1>{pageTitle.title}</h1><p>{pageTitle.description}</p></div>{activeView === "projects" ? <div className="topbarActions"><button className="secondaryButton" onClick={toggleProjectManagement} type="button">{isManagingProjects ? "取消管理" : "管理项目"}</button><a className="primaryButton" href="#create">新建项目</a></div> : null}</header>

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
                      <span className={`project-status-badge ${getProjectStatusClass(project.task_status)}`}>{project.task_status}</span>
                    </label>
                  ) : (
                    <button className={currentProject?.project_id === project.project_id ? "projectItem selected" : "projectItem"} key={project.project_id} onClick={() => { setCurrentProject(project); setTask(null); setClassification(null); setShowClassificationDetails(false); setReviewForm({ projectType: "", m1m2Template: "", caseId: undefined, m3Selection: "m3_template", includePrintTailPage: false, notes: "" }); }} type="button"><strong>{project.project_name}</strong><span className={`project-status-badge ${getProjectStatusClass(project.task_status)}`}>{project.task_status}</span></button>
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
                        <div className="project-info-edit-panel">
                          <input
                            value={editForm.project_name}
                            onChange={(e) => setEditForm((f) => ({ ...f, project_name: e.target.value }))}
                            placeholder="项目名称"
                            className="project-info-edit-input"
                          />
                          <input
                            value={editForm.project_location}
                            onChange={(e) => setEditForm((f) => ({ ...f, project_location: e.target.value }))}
                            placeholder="项目所在地"
                            className="project-info-edit-input"
                          />
                          <input
                            value={editForm.owner_unit}
                            onChange={(e) => setEditForm((f) => ({ ...f, owner_unit: e.target.value }))}
                            placeholder="建设/业主单位"
                            className="project-info-edit-input"
                          />
                          <input
                            value={editForm.product_line}
                            onChange={(e) => setEditForm((f) => ({ ...f, product_line: e.target.value }))}
                            placeholder="产品线"
                            className="project-info-edit-input"
                          />
                          <div className="project-info-edit-actions">
                            <button className="primaryButton btn-xs" disabled={busy} onClick={updateProjectBasicInfo} type="button">保存</button>
                            <button className="secondaryButton btn-xs" disabled={busy} onClick={() => setIsEditingProject(false)} type="button">取消</button>
                          </div>
                        </div>
                      ) : (
                        <div className="project-info-header">
                          <h3>{currentProject.project_name}</h3>
                          <button
                            className="secondaryButton btn-xs-pad"
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
                  </div>
                  <div className="m3-material-entry">
                    <div>
                      <strong>M3资料上传</strong>
                      <span>用于项目深化方案 M3 章节生成</span>
                    </div>
                    <p className="m3-upload-summary"><strong>M3上传情况：</strong>已填写 {m3MaterialsResult?.text_completed_count ?? 0}/{m3MaterialsResult?.text_total_count ?? 9} 个部分，已上传 {m3MaterialsResult?.image_count ?? 0} 张图片</p>
                    <a className="secondaryButton" href="#project-m3-materials">进入M3资料上传</a>
                  </div>
                  {uploadSuccess && <div className="uploadSuccess">上传成功</div>}
                  <div className="upload-actions-bar">
                    <button className="primaryButton" disabled={busy} onClick={uploadProjectFiles} type="button">统一上传项目资料</button>
                    <button className="secondaryButton" disabled={busy} onClick={analyzeProject} type="button">开始识别资料</button>
                  </div>
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
                          <button className="secondaryButton btn-xs" onClick={() => setShowClassificationDetails((value) => !value)} type="button">{showClassificationDetails ? "收起分析依据" : "查看分析依据"}</button>
                        </article>
                        <article className="resultCard">
                          <span>M5 推荐案例</span>
                          <strong>{recommendedCases[0]?.title || recommendedCases[0]?.source_path?.split(/[\\/]/).pop() || "暂无推荐案例"}</strong>
                          <p>{recommendedCases[0]?.match_reason ?? "暂无推荐案例，可在下方人工确认中选择 M5 案例或暂不选择。"}</p>
                        </article>
                        <article className="resultCard">
                          <span>M6 固定模板</span>
                          <strong>{firstTemplateName(classification.template_selection?.M6)}</strong>
                          <p>默认使用企业背书与荣誉固定模板，可由后端补充替换字段。</p>
                        </article>
                      </div>
                      {showClassificationDetails ? (
                        <div className="evidencePanel">
                          <div className="sectionHeader">
                            <h3>M1/M2 分析依据</h3>
                            <span className="badge">classification_detail</span>
                          </div>
                          <div className="resultGrid">
                            <article className="resultCard">
                              <span>识别到的项目类型</span>
                              <strong>{labelForProjectType(classification.detected_project_type)}</strong>
                              <p>project_type：{classification.detected_project_type ?? "待识别"}</p>
                            </article>
                            <article className="resultCard">
                              <span>对应 PPT 模板</span>
                              <strong>{firstTemplateName(classification.template_selection?.M1_M2)}</strong>
                              <p>只选择既有 M1/M2 固化模板，不动态生成整章内容。</p>
                            </article>
                            <article className="resultCard">
                              <span>confidence</span>
                              <strong>{classification.confidence ? `${Math.round(classification.confidence * 100)}%` : "待识别"}</strong>
                              <p>供前端人工确认时参考。</p>
                            </article>
                            <article className="resultCard">
                              <span>matched_keywords</span>
                              <strong>{classification.matched_keywords?.join("、") || "待识别"}</strong>
                              <p>命中关键词来自项目名称、文件名和解析文本。</p>
                            </article>
                            <article className="resultCard">
                              <span>分类方式</span>
                              <strong>{classification.classification_method === "llm" ? "LLM" : classification.classification_method === "rule_fallback" ? "规则 fallback" : "待识别"}</strong>
                              <p>{classification.fallback_reason || "LLM 可用时优先使用模板画像判断。"}</p>
                            </article>
                            <article className="resultCard">
                              <span>LLM 判断理由</span>
                              <strong>{classification.llm_reasoning_summary || "暂无"}</strong>
                              <p>模型只判断模板类型，不动态生成 M1/M2 内容。</p>
                            </article>
                          </div>
                          <div className="sectionHeader">
                            <h3>判断依据</h3>
                            <span className="badge">detection_evidence</span>
                          </div>
                          {classification.detection_evidence?.length ? (
                            <div className="evidenceList">
                              {classification.detection_evidence.map((item, index) => (
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
                      ) : null}
                      {productLineClassificationConflict ? (
                        <p className="messageLine">
                          新建项目选择的产品线“{productLineClassificationConflict.productLine}”对应{labelForProjectType(productLineClassificationConflict.preferredProjectType)}，资料识别结果为{labelForProjectType(productLineClassificationConflict.detectedProjectType)}。已默认按产品线选择 M1/M2；如资料判断更准确，请在下方人工确认中修改。
                        </p>
                      ) : null}
                                            <form className="confirmationGrid" onSubmit={(event) => { event.preventDefault(); submitClassificationReview(); }}>
                        <label>确认项目类型<select aria-label="确认项目类型" value={reviewForm.projectType} onChange={(event) => { const nextType = event.target.value; setReviewForm((value) => ({ ...value, projectType: nextType, m1m2Template: nextType })); }}>{projectTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                        <label>确认 M1/M2 模板<select aria-label="确认 M1/M2 模板" value={reviewForm.m1m2Template} onChange={(event) => { const nextType = event.target.value; setReviewForm((value) => ({ ...value, projectType: nextType, m1m2Template: nextType })); }}>{m1m2Templates.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
                        <label>确认 M3 模块<select aria-label="确认 M3 模块" value={reviewForm.m3Selection} onChange={(event) => setReviewForm((value) => ({ ...value, m3Selection: event.target.value }))}><option value="m3_template">M3模板</option><option value="m3_skip">暂不选择</option></select></label>
                        <label>确认 M5 案例<select aria-label="确认 M5 案例" value={reviewForm.caseId ?? ""} onChange={(event) => setReviewForm((value) => ({ ...value, caseId: event.target.value }))}>{recommendedCases[0] ? <option value={String(recommendedCases[0].case_id)}>{recommendedCases[0].title || recommendedCases[0].case_id}</option> : null}{m5FixedCases.filter((item) => String(item.case_id) !== String(recommendedCases[0]?.case_id)).map((item) => <option key={item.case_id} value={item.case_id}>{item.filename || item.title}</option>)}<option value="">暂不选择案例</option></select></label>
                        <label className="checkboxField"><input checked={reviewForm.includePrintTailPage} onChange={(event) => setReviewForm((value) => ({ ...value, includePrintTailPage: event.target.checked }))} type="checkbox" />添加尾页打印版</label>
                        <button className="primaryButton" disabled={busy} type="submit">提交人工确认</button>
                      </form>
                    </>
                  ) : (
                    <div className="emptyState compact"><h3>等待系统识别</h3><p>统一上传项目资料后，点击开始识别资料，即可在此确认项目类型、模板选择、案例选择和缺失字段。</p></div>
                  )}
                </section>

                <section className="section statusSection">
                  <div className="sectionHeader"><h2>生成状态</h2><div className="actions"><button className="primaryButton btn-xs" disabled={busy} onClick={generate} type="button">启动生成</button></div></div>
                  <ol className="statusList">{statuses.map((status, index) => <li className={status === activeStatus ? "current" : (statuses.indexOf(status) < statuses.indexOf(activeStatus) ? "completed" : "pending")} key={status}><span>{index + 1}</span>{status}</li>)}</ol>
                  <div className="historyBox"><strong>状态历史</strong><span>{statusHistory}</span></div>
                  <p className="messageLine">{message}</p>
                  {qualityReport ? (
                    <div className="evidencePanel spaced qualityReportPanel">
                      <button
                        aria-expanded={qualityReportExpanded}
                        className="qualityReportSummary"
                        onClick={() => setQualityReportExpanded((value) => !value)}
                        type="button"
                      >
                        <span className="qualityReportTitle">
                          <strong>质量检查结果</strong>
                          <span className="badge">QAReviewAgent</span>
                        </span>
                        <span className="qualityReportMeta">
                          <strong>{qualityReportLabel(qualityReport)}</strong>
                          <span>{qualityReport.errors?.length ?? 0} 错误 / {qualityReport.warnings?.length ?? 0} 风险</span>
                        </span>
                        <span className="qualityReportToggle">{qualityReportExpanded ? "收起" : "展开详情"}</span>
                      </button>
                      {qualityReportExpanded ? (
                        <div className="qualityReportDetails">
                          <div className="qualityReportActions">
                            <button className="secondaryButton btn-xs" onClick={() => setQualityReportExpanded(false)} type="button">收起</button>
                          </div>
                          <div className="resultGrid">
                            <article className="resultCard">
                              <span>检查状态</span>
                              <strong>{qualityReportLabel(qualityReport)}</strong>
                              <p>第一版 QAReviewAgent 只做结果提示，不影响下载。</p>
                            </article>
                            <article className="resultCard">
                              <span>检查时间</span>
                              <strong>{qualityReport.checked_at || "未返回"}</strong>
                              <p>passed：{String(Boolean(qualityReport.passed))}；severity：{qualityReport.severity || "unknown"}</p>
                            </article>
                            <article className="resultCard">
                              <span>errors</span>
                              <strong>{qualityReport.errors?.length ?? 0} 项</strong>
                              <p>{(qualityReport.errors ?? []).slice(0, 3).join("；") || "未发现阻断级错误。"}</p>
                            </article>
                            <article className="resultCard">
                              <span>warnings</span>
                              <strong>{qualityReport.warnings?.length ?? 0} 项</strong>
                              <p>{(qualityReport.warnings ?? []).slice(0, 3).join("；") || "未发现提示级风险。"}</p>
                            </article>
                          </div>
                          <div className="qualityReportActions bottom">
                            <button className="secondaryButton btn-xs" onClick={() => setQualityReportExpanded(false)} type="button">收起</button>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  <div className="downloadRow"><div><h3>最终文件</h3><p id="finalFileDesc">生成完成后可下载、预览或存入完整PPT案例库</p></div><div className="downloadActions"><button className="secondaryButton btn-xs" disabled={busy || !canSaveFullPptCase} onClick={saveFullPptCase} type="button">存入案例库</button><button className="secondaryButton btn-xs" disabled={busy || previewLoading} onClick={previewFinalPpt} type="button">{previewLoading ? "生成预览中..." : "预览 PPT"}</button><button className="secondaryButton btn-xs" disabled={busy} onClick={downloadFinal} type="button">下载最终 PPTX</button><span className="badge">{activeStatus}</span></div></div>
                </section>
              </>
            ) : null}
          </>
        ) : null}

        {activeView === "project-m3-materials" ? (
          <section id="project-m3-materials" className="section">
            <div className="sectionHeader">
              <h2>M3资料上传</h2>
              <span className="badge">正式流程</span>
            </div>
            {currentProject ? (
              <div className="testPanel">
                <div className="m3-material-page-header">
                  <div>
                    <strong>{currentProject.project_name}</strong>
                    <span>已填写 {m3MaterialsResult?.text_completed_count ?? 0}/{m3MaterialsResult?.text_total_count ?? 9} 个部分，已上传 {m3MaterialsResult?.image_count ?? 0} 张图片 / {m3MaterialsResult?.table_count ?? 0} 个表格</span>
                  </div>
                  <a className="secondaryButton" href="#projects">返回我的项目</a>
                </div>
                <div className="evidenceItem">
                  <div>
                    <strong>批量 M3 资料自动分类</strong>
                    <span className="inlineTitle">文件名格式：项目基本情况-1.jpg / 现场勘查情况.xlsx <M3NamingHelpButton onOpen={() => setM3NamingHelpOpen(true)} /></span>
                  </div>
                  <label className="uploadBox uploadBoxSpaced">
                    <span>一次上传 M3 九类图片或 Excel 表格</span>
                    <input
                      name="project_m3_material_bulk_images"
                      type="file"
                      multiple
                      accept=".xlsx,.png,.jpg,.jpeg,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                      onChange={(event) => updateM3MaterialBulkFiles(Array.from(event.target.files ?? []))}
                    />
                  </label>
                  <div className="fileList">
                    {(m3MaterialBulkFiles.length
                      ? m3MaterialBulkFiles.map((file) => file.name)
                      : [...(m3MaterialsResult?.tables || []).map((table) => table.filename), ...(m3MaterialsResult?.images || []).map((image) => image.filename)]
                    ).map((name) => (
                      <span key={`project-m3-material-${name}`}>{name}</span>
                    ))}
                  </div>
                </div>
                <label>
                  批量描述文本（某个图片不需要描述可以不添加，如果添加，冒号前文字要与图片名一一对应）
                  <textarea
                    value={m3MaterialDescriptions}
                    onChange={(event) => {
                      setM3MaterialDescriptions(event.target.value);
                      setM3MaterialsMessage("M3资料描述有未保存修改。");
                    }}
                    rows={7}
                    placeholder={"项目基本情况-1：第一张图片说明\n项目基本情况-2：第二张图片说明\n项目线路图-1：线路图说明"}
                  />
                </label>
                {m3MaterialBulkFiles.length > 0 || m3MaterialDescriptions.trim() ? (
                  <div className="evidencePanel">
                    <div className="sectionHeader">
                      <h3>自动匹配预览</h3>
                      <span className="badge">保存时由后端校验</span>
                    </div>
                    {m3MaterialAutoPreview.grouped.length ? (
                      <div className="evidenceList">
                        {m3MaterialAutoPreview.grouped.map((section) => (
                          <article className="evidenceItem" key={`project-m3-auto-${section.imageField}`}>
                            <div>
                              <strong>{section.title}</strong>
                              <span>{section.tables.length} 个表格 / {section.files.length} 张图片 / {section.descriptions.length} 条描述</span>
                            </div>
                            <div className="fileList">
                              {section.tables.map((row) => <span key={`project-auto-table-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                              {section.files.map((row) => <span key={`project-auto-file-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                              {section.descriptions.map((row) => <span key={`project-auto-desc-${section.imageField}-${row.line}`}>{row.line}</span>)}
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="messageLine">尚未识别到可匹配的 M3 表格、图片或描述。</p>
                    )}
                    {m3MaterialAutoPreview.unknownFiles.length ? <p className="messageLine errorText">分类不明文件：{m3MaterialAutoPreview.unknownFiles.join("、")}</p> : null}
                    {m3MaterialAutoPreview.invalidDescriptions.length ? <p className="messageLine errorText">描述格式或分类异常：{m3MaterialAutoPreview.invalidDescriptions.join("；")}</p> : null}
                  </div>
                ) : null}
                <div className="evidenceList">
                  {M3_FULL_SECTIONS.map((section) => {
                    const savedImages = (m3MaterialsResult?.images || []).filter((image) => image.purpose === section.imageField);
                    const savedTables = (m3MaterialsResult?.tables || []).filter((table) => table.purpose === section.imageField);
                    if (!savedImages.length && !savedTables.length) return null;
                    return (
                      <article className="evidenceItem" key={`project-saved-${section.textField}`}>
                        <div>
                          <strong>{section.title}</strong>
                          <span>{savedTables.length} 个已保存表格 / {savedImages.length} 张已保存图片</span>
                        </div>
                        <div className="fileList">
                          {savedTables.map((table) => <span key={`${section.imageField}-saved-table-${table.stored_path}`}>{table.filename}</span>)}
                          {savedImages.map((image) => <span key={`${section.imageField}-saved-${image.stored_path}`}>{image.filename}{image.description ? `：${image.description}` : ""}</span>)}
                        </div>
                      </article>
                    );
                  })}
                </div>
                <div className="upload-actions-bar">
                  <button className="primaryButton" disabled={busy} onClick={() => saveM3Materials(false)} type="button">保存M3资料</button>
                  <button className="primaryButton" disabled={busy} onClick={() => saveM3Materials(true)} type="button">保存并返回我的项目</button>
                  <a className="secondaryButton" href="#projects">返回我的项目</a>
                </div>
                <p className="messageLine" style={m3MaterialsMessage && m3MaterialsMessage.includes("失败") ? {color: "#e74c3c"} : {}}>{m3MaterialsMessage}</p>
              </div>
            ) : (
              <div className="emptyState compact"><h3>请先选择项目</h3><p>回到我的项目页面选择一个项目后，再进入 M3资料上传。</p><a className="secondaryButton" href="#projects">返回我的项目</a></div>
            )}
          </section>
        ) : null}

        {activeView === "create" ? (
          <section id="create" className="section">
            <div className="sectionHeader"><h2>新建项目</h2><span className="badge">基础信息</span></div>
            <form className="projectForm" onSubmit={createProject}>
              <label>项目名称*<input name="project_name" placeholder="例如：某城市轨道交通声屏障改造项目" /></label>
              <label>项目所在地*<input name="project_location" placeholder="例如：南京" /></label>
              <label>建设/业主单位*<input name="owner_unit" placeholder="例如：某建设单位" /></label>
              <label>产品线*<select aria-label="产品线" name="product_line" defaultValue="">
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
          <section id="cases" className="section">
            <div className="sectionHeader"><h2>案例库管理</h2><button className="secondaryButton" disabled type="button">新增案例</button></div>
            <div className="caseLibraryTabs" role="tablist" aria-label="案例库分类">
              <button className={caseLibraryTab === "m5" ? "caseLibraryTab active" : "caseLibraryTab"} onClick={() => setCaseLibraryTab("m5")} role="tab" type="button">M5案例库</button>
              <button className={caseLibraryTab === "full-ppt" ? "caseLibraryTab active" : "caseLibraryTab"} onClick={() => setCaseLibraryTab("full-ppt")} role="tab" type="button">完整PPT案例库</button>
            </div>
            {caseLibraryTab === "m5" ? (
              m5FixedCases.length > 0 ? (
                <div className="evidenceList">
                  {m5FixedCases.map((item) => (
                    <article className="evidenceItem" key={item.case_id}>
                      <div>
                        <strong>{item.filename || item.title}</strong>
                        <span>case_id: {String(item.case_id)}</span>
                      </div>
                      {item.project_type ? <p>项目类型：{item.project_type}</p> : null}
                    </article>
                  ))}
                </div>
              ) : (
                <div className="cases-empty-panel">
                  <h3 className="cases-empty-title">暂未发现 M5 案例文件</h3>
                  <p className="cases-empty-desc">请检查 ppt_engine/templates/solution_fixed_modules/M5 目录下是否存在 .pptx 案例文件。</p>
                  <div className="cases-capability-list">
                    <div className="cases-capability-item">历史项目案例归档</div>
                    <div className="cases-capability-item">项目标签与场景匹配</div>
                    <div className="cases-capability-item">M5 推荐案例辅助生成</div>
                  </div>
                </div>
              )
            ) : (
              fullPptCases.length > 0 ? (
                <div className="evidenceList">
                  {fullPptCases.map((caseItem) => (
                    <article className="evidenceItem fullPptCaseItem" key={caseItem.case_id}>
                      <div>
                        <strong>{caseItem.title || caseItem.filename}</strong>
                        <span>{caseItem.filename}</span>
                        <span>{formatFileSize(caseItem.file_size)}</span>
                      </div>
                      <p>项目类型：{labelForProjectType(caseItem.project_type)}；存入时间：{formatStoredAt(caseItem.stored_at)}</p>
                      <p className="sourcePath">case_id: {caseItem.case_id}</p>
                      <div className="caseItemActions">
                        <a className="secondaryButton btn-xs" href={`${API_BASE}/api/cases/full-ppt/${caseItem.case_id}/download`} download>下载 PPTX</a>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="cases-empty-panel">
                  <h3 className="cases-empty-title">暂未保存完整PPT案例</h3>
                  <p className="cases-empty-desc">在项目完整生成后，点击最终文件区域的“存入案例库”，即可在这里查看和下载。</p>
                  <div className="cases-capability-list">
                    <div className="cases-capability-item">完整PPT归档</div>
                    <div className="cases-capability-item">按项目保留最新版本</div>
                    <div className="cases-capability-item">案例库下载复用</div>
                  </div>
                </div>
              )
            )}
          </section>
        ) : null}

        {activeView === "function-tests" ? (
          <section id="function-tests" className="section">
            <div className="sectionHeader">
              <h2>功能测试</h2>
              <span className="badge">开发过程验证入口</span>
            </div>
            <div className="test-hub-grid">
              <article className="test-hub-card">
                <div className="test-hub-card-header">
                  <strong>M1/M2选择测试</strong>
                  <span className="test-hub-badge">模板识别</span>
                </div>
                <p className="test-hub-desc">验证项目类型识别与 M1/M2 固化模板选择。</p>
                <a className="secondaryButton test-hub-action" href="#m1m2-test">打开测试</a>
              </article>
              <article className="test-hub-card">
                <div className="test-hub-card-header">
                  <strong>M3完整测试</strong>
                  <span className="test-hub-badge">M3完整</span>
                </div>
                <p className="test-hub-desc">按九个部分测试 M3 文字与图片替换，多图自动扩页。</p>
                <a className="secondaryButton test-hub-action" href="#m3-full-test">打开测试</a>
              </article>
              <article className="test-hub-card">
                <div className="test-hub-card-header">
                  <strong>M5选择测试</strong>
                  <span className="test-hub-badge">案例匹配</span>
                </div>
                <p className="test-hub-desc">验证项目标签、案例库匹配与推荐理由。</p>
                <a className="secondaryButton test-hub-action" href="#m5-test">打开测试</a>
              </article>
              <article className="test-hub-card">
                <div className="test-hub-card-header">
                  <strong>文档解析测试</strong>
                  <span className="test-hub-badge">解析验证</span>
                </div>
                <p className="test-hub-desc">验证上传资料解析状态、资料角色和模块分配。</p>
                <a className="secondaryButton test-hub-action" href="#document-parse-test">打开测试</a>
              </article>
              <article className="test-hub-card">
                <div className="test-hub-card-header">
                  <strong>大模型测试</strong>
                  <span className="test-hub-badge">LLM</span>
                </div>
                <p className="test-hub-desc">通过后端读取环境变量并调用配置好的接口。</p>
                <a className="secondaryButton test-hub-action" href="#llm-test">打开测试</a>
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
              <article className="resultCard">
                <span>分类方式</span>
                <strong>{m1m2TestResult?.classification_method === "llm" ? "LLM" : m1m2TestResult?.classification_method === "rule_fallback" ? "规则 fallback" : "待识别"}</strong>
                <p>{m1m2TestResult?.fallback_reason || "LLM 可用时优先使用模板画像判断。"}</p>
              </article>
              <article className="resultCard">
                <span>LLM 判断理由</span>
                <strong>{m1m2TestResult?.llm_reasoning_summary || "暂无"}</strong>
                <p>模型只判断模板类型，不动态生成 M1/M2 内容。</p>
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
              <div className="flowStatusPanel">
                <div className="sectionHeader">
                  <h3>完整流程状态</h3>
                </div>
                <div className="flowStatusSteps">
                  <div className="flowStatusStep">
                    <span className={m1m2TestResult ? "flowStatusDot done" : "flowStatusDot"} />
                    <span>① 分析识别</span>
                  </div>
                  <div className="flowStatusStep">
                    <span className={m1m2TestReviewStatus === "success" ? "flowStatusDot done" : m1m2TestReviewStatus === "error" ? "flowStatusDot error" : "flowStatusDot"} />
                    <span>② 人工确认</span>
                    {m1m2TestReviewStatus === "success" && <span className="flowStatusText done">已确认</span>}
                    {m1m2TestReviewStatus === "error" && <span className="flowStatusText error">确认失败</span>}
                  </div>
                  <div className="flowStatusStep">
                    <span className={m1m2TestGenerateStatus === "success" ? "flowStatusDot done" : m1m2TestGenerateStatus === "error" ? "flowStatusDot error" : m1m2TestGenerateStatus === "starting" ? "flowStatusDot running" : "flowStatusDot"} />
                    <span>③ 启动生成</span>
                    {m1m2TestGenerateStatus === "success" && <span className="flowStatusText done">{m1m2TestTaskStatus}</span>}
                    {m1m2TestGenerateStatus === "error" && <span className="flowStatusText error">生成失败</span>}
                    {m1m2TestGenerateStatus === "starting" && <span className="flowStatusText running">进行中...</span>}
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
              <div className="flowStatusPanel">
                <div className="sectionHeader">
                  <h3>完整流程状态</h3>
                </div>
                <div className="flowStatusSteps">
                  <div className="flowStatusStep">
                    <span className={m5TestResult ? "flowStatusDot done" : "flowStatusDot"} />
                    <span>① 分析识别</span>
                  </div>
                  <div className="flowStatusStep">
                    <span className={m5TestReviewStatus === "success" ? "flowStatusDot done" : m5TestReviewStatus === "error" ? "flowStatusDot error" : "flowStatusDot"} />
                    <span>② 人工确认</span>
                    {m5TestReviewStatus === "success" && <span className="flowStatusText done">已确认</span>}
                    {m5TestReviewStatus === "error" && <span className="flowStatusText error">确认失败</span>}
                  </div>
                  <div className="flowStatusStep">
                    <span className={m5TestGenerateStatus === "success" ? "flowStatusDot done" : m5TestGenerateStatus === "error" ? "flowStatusDot error" : m5TestGenerateStatus === "starting" ? "flowStatusDot running" : "flowStatusDot"} />
                    <span>③ 启动生成</span>
                    {m5TestGenerateStatus === "success" && <span className="flowStatusText done">{m5TestTaskStatus}</span>}
                    {m5TestGenerateStatus === "error" && <span className="flowStatusText error">生成失败</span>}
                    {m5TestGenerateStatus === "starting" && <span className="flowStatusText running">进行中...</span>}
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
                <div className="resultGrid">
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
                  <div className="doc-parse-table-wrapper">
                    <h3 className="doc-parse-table-title">
                      文件解析详情（共 {docParseTestResult.files.length} 个文件）
                    </h3>
                    <table className="doc-parse-table">
                      <thead>
                        <tr className="doc-parse-table-header-row">
                          <th className="doc-parse-table-header-cell">文件名</th>
                          <th className="doc-parse-table-header-cell">解析状态</th>
                          <th className="doc-parse-table-header-cell">资料角色</th>
                          <th className="doc-parse-table-header-cell">服务模块</th>
                          <th className="doc-parse-table-header-cell">解析文本</th>
                        </tr>
                      </thead>
                      <tbody>
                        {docParseTestResult.files.map((f, idx) => (
                          <Fragment key={idx}>
                            <tr className="doc-parse-table-row">
                              <td className="doc-parse-table-cell">{f.filename}</td>
                              <td className="doc-parse-table-cell">
                                <span className={`parseStatus ${f.parse_status}`}>{f.parse_status}</span>
                                {f.parse_status === "pending_enhancement" && <span className="badge warn doc-parse-status-extra">待增强</span>}
                                {f.parse_status === "pending_ocr" && <span className="badge warn doc-parse-status-extra">待OCR</span>}
                                {f.parse_status === "failed" && <span className="badge warn doc-parse-status-extra">失败</span>}
                              </td>
                              <td className="doc-parse-table-cell text-muted">{f.document_role || "未知"}</td>
                              <td className="doc-parse-table-cell text-muted">{(f.assigned_modules || []).join(", ") || "未分配"}</td>
                              <td className="doc-parse-table-cell">
                                {f.parse_status === "parsed" ? (
                                  f.text_preview ? (
                                    <button
                                      className="btn-doc-action"
                                      onClick={() => toggleDocParseTestFileExpanded(f.file_id)}
                                      type="button"
                                    >
                                      {docParseTestExpandedFiles[f.file_id] ? "收起" : "查看文本"}
                                    </button>
                                  ) : (
                                    <span className="doc-parse-loading-text">解析成功，无文本内容</span>
                                  )
                                ) : f.error_message ? (
                                  <span className="doc-parse-error-text" title={f.error_message}>{f.error_message.length > 30 ? f.error_message.slice(0, 30) + "…" : f.error_message}</span>
                                ) : (
                                  <span className="doc-parse-loading-text">暂无解析文本</span>
                                )}
                              </td>
                            </tr>
                            {docParseTestExpandedFiles[f.file_id] ? (
                              <tr key={`${idx}-text`}>
                                <td colSpan={5} className="doc-parse-expanded-cell">
                                  {docParseTestLoadingFullText[f.file_id] ? (
                                    <span className="doc-parse-loading-text">加载中…</span>
                                  ) : (
                                    <pre className="doc-parse-expanded-pre">
                                      {docParseTestFullTextMap[f.file_id] || "（空）"}
                                    </pre>
                                  )}
                                </td>
                              </tr>
                            ) : null}
                            {f.parse_status === "parsed" && f.text_preview && !docParseTestExpandedFiles[f.file_id] ? (
                              <tr key={`${idx}-preview`}>
                                <td colSpan={5} className="doc-parse-preview-cell">
                                  <span className="doc-parse-preview-label">文本预览：</span>
                                  <span className="doc-parse-preview-text">{f.text_preview}{f.text_preview.length >= 1500 ? "…" : ""}</span>
                                </td>
                              </tr>
                            ) : null}
                          </Fragment>
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

        {activeView === "m3-full-test" ? (
          <section id="m3-full-test" className="section">
            <div className="sectionHeader">
              <h2>M3完整测试</h2>
              <span className="badge">独立测试</span>
            </div>
            <div className="testPanel">
              <div className="testInputs single">
                <label>项目名称<input value={m3FullTestProjectName} onChange={(event) => setM3FullTestProjectName(event.target.value)} /></label>
              </div>
              <div className="evidenceItem">
                <div>
                  <strong>批量 M3 资料自动分类</strong>
                  <span className="inlineTitle">文件名格式：项目基本情况-1.jpg / 敏感点路段.xlsx <M3NamingHelpButton onOpen={() => setM3NamingHelpOpen(true)} /></span>
                </div>
                <label className="uploadBox uploadBoxSpaced">
                  <span>一次上传 M3 九类图片或 Excel 表格</span>
                  <input
                    name="m3_full_test_bulk_images"
                    type="file"
                    multiple
                    accept=".xlsx,.png,.jpg,.jpeg,image/png,image/jpeg,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    onChange={(event) => updateM3FullTestBulkFiles(Array.from(event.target.files ?? []))}
                  />
                </label>
                <div className="fileList">
                  {m3FullTestBulkFiles.map((file) => <span key={`m3-bulk-${file.name}`}>{file.name}</span>)}
                </div>
              </div>
              <label>
                批量描述文本（某个图片不需要描述可以不添加，如果添加，冒号前文字要与图片名一一对应）
                <textarea
                  value={m3FullTestDescriptions}
                  onChange={(event) => {
                    setM3FullTestDescriptions(event.target.value);
                    setM3FullTestResult(null);
                    setM3FullTestMessage("已更新描述文本，请执行 M3 完整测试。");
                  }}
                  rows={7}
                  placeholder={"项目基本情况-1：第一张图片说明\n项目基本情况-2：第二张图片说明\n项目线路图-1：线路图说明"}
                />
              </label>
              {m3FullTestBulkFiles.length > 0 || m3FullTestDescriptions.trim() ? (
                <div className="evidencePanel">
                  <div className="sectionHeader">
                    <h3>自动匹配预览</h3>
                    <span className="badge">按后端规则校验为准</span>
                  </div>
                  {m3FullAutoPreview.grouped.length ? (
                    <div className="evidenceList">
                      {m3FullAutoPreview.grouped.map((section) => (
                        <article className="evidenceItem" key={`m3-auto-${section.imageField}`}>
                          <div>
                            <strong>{section.title}</strong>
                            <span>{section.tables.length} 个表格 / {section.files.length} 张图片 / {section.descriptions.length} 条描述</span>
                          </div>
                          <div className="fileList">
                            {section.tables.map((row) => <span key={`auto-table-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                            {section.files.map((row) => <span key={`auto-file-${section.imageField}-${row.filename}`}>{row.filename}</span>)}
                            {section.descriptions.map((row) => <span key={`auto-desc-${section.imageField}-${row.line}`}>{row.line}</span>)}
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="messageLine">尚未识别到可匹配的 M3 表格、图片或描述。</p>
                  )}
                  {m3FullAutoPreview.unknownFiles.length ? <p className="messageLine errorText">分类不明文件：{m3FullAutoPreview.unknownFiles.join("、")}</p> : null}
                  {m3FullAutoPreview.invalidDescriptions.length ? <p className="messageLine errorText">描述格式或分类异常：{m3FullAutoPreview.invalidDescriptions.join("；")}</p> : null}
                </div>
              ) : null}
              <button className="primaryButton" disabled={busy} onClick={runM3FullRenderTest} type="button">执行 M3 完整测试</button>
              <p className="messageLine" style={m3FullTestMessage && m3FullTestMessage.includes("失败") ? {color: "#e74c3c"} : {}}>{m3FullTestMessage}</p>
            </div>

            {m3FullTestResult && m3FullTestResult.ok ? (
              <div className="resultGrid">
                <article className="resultCard">
                  <span>渲染状态</span>
                  <strong>成功</strong>
                  <p>页数：{m3FullTestResult.slide_count} 页</p>
                </article>
                <article className="resultCard wide">
                  <span>下载链接</span>
                  <strong>M3 完整测试 PPTX 已生成</strong>
                  <p>
                    <a href={`${API_BASE}${m3FullTestResult.download_url}`} download>点击下载生成的 M3 完整测试 PPTX</a>
                  </p>
                </article>
                <article className="resultCard">
                  <span>图片数量</span>
                  <strong>{Object.values(m3FullTestResult.image_summary || {}).reduce((sum, count) => sum + count, 0)} 张</strong>
                  <p>多张图片会自动扩展对应部分页面。</p>
                </article>
                <article className="resultCard">
                  <span>表格数量</span>
                  <strong>{Object.values(m3FullTestResult.table_summary || {}).reduce((sum, count) => sum + count, 0)} 个</strong>
                  <p>同一部分内表格页会排在图片页之前。</p>
                </article>
              </div>
            ) : null}
          </section>
        ) : null}

      </section>
    </main>
  );
}
