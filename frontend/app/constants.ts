// ── 常量 ──

export const statuses = ["待上传", "资料解析中", "类型识别中", "案例匹配中", "待确认", "生成中", "合并中", "完成"];

export const projectTypes = [
  { value: "highway", label: "公路" },
  { value: "railway", label: "铁路" },
  { value: "metro", label: "轨道交通/地铁" },
  { value: "existing_rail_transit", label: "铁路/轨交既有线" },
];

export const m1m2Templates = [
  { value: "highway", label: "公路全封闭声屏障（M1_&_M2）.pptx" },
  { value: "metro", label: "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx" },
  { value: "existing_rail_transit", label: "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx" },
  { value: "railway", label: "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx" },
];

export const productLineProjectTypeMap: Record<string, string> = {
  "轨道交通声屏障": "metro",
  "地铁声屏障": "metro",
  "轨交既有线改造": "existing_rail_transit",
  "公路声屏障": "highway",
  "铁路声屏障": "railway",
};

export const M5_DEMO_CASE = { case_id: "m5_demo", title: "M5示例案例", match_reason: "演示全流程使用的固定 M5 案例模板。" };

export const M3_FULL_SECTIONS = [
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

export const M3_SECTION_TITLE_ALIASES: Record<string, string> = {
  "现场勘查情况": "现场勘察情况",
};

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8010";
export const PROJECT_LIST_PREVIEW_LIMIT = 5;
export const PROJECT_LIST_PAGE_SIZE = 10;

export const viewTitles: Record<ViewId, { title: string; description: string }> = {
  projects: { title: "我的项目", description: "创建项目、统一上传项目资料，并确认系统识别结果。" },
  create: { title: "新建项目", description: "填写基础信息后创建一个新的售前 PPT 项目。" },
  cases: { title: "案例库", description: "浏览历史案例，供系统按项目标签推荐引用。" },
  "project-m3-materials": { title: "M3资料上传", description: "按 M3 九部分维护项目深化方案文字、图片和 Excel 表格资料。" },
  "function-tests": { title: "功能测试", description: "开发过程验证入口，收纳内部功能测试页面，普通前端用户无需使用。" },
  "m1m2-test": { title: "M1/M2选择测试", description: "上传测试资料，根据文件名和解析文本识别项目类型并选择对应 M1/M2 固化模板。" },
  "m3-full-test": { title: "M3完整测试", description: "按 M3 九部分测试文字与图片占位符替换，多图自动扩页。" },
  "m5-test": { title: "M5选择测试", description: "上传测试资料，根据项目标签从案例库匹配相似案例并显示匹配理由。" },
  "document-parse-test": { title: "文档解析测试", description: "用于测试不同格式资料的文本与结构化解析效果。" },
  "llm-test": { title: "大模型测试", description: "调用后端开发测试接口，验证当前 LLM 环境变量和中转站请求是否可用。" },
};

// ── 类型 ──

export type ViewId = "projects" | "create" | "cases" | "project-m3-materials" | "function-tests" | "m1m2-test" | "m3-full-test" | "m5-test" | "document-parse-test" | "llm-test";

export type Project = {
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

export type QualityReport = {
  passed?: boolean;
  severity?: "pass" | "warning" | "error" | string;
  errors?: string[];
  warnings?: string[];
  checks?: Array<{ name?: string; passed?: boolean; severity?: string; message?: string }>;
  checked_at?: string;
};

export type StoredFile = { file_id: number; filename: string; content_type?: string; document_role?: string; assigned_modules?: string[]; parse_status?: string; text_preview?: string; error_message?: string };

export type CaseSelection = {
  recommended_cases?: Array<{ case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string }>;
  confirmed_case_id?: number | string | null;
  status?: string;
  message?: string;
};

export type ClassificationResult = {
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

export type TaskState = { project_id: number; task_status: string; status_history: string[]; quality_report?: QualityReport };
export type ReviewForm = { projectType: string; m1m2Template: string; caseId?: string; m3Selection: string; includePrintTailPage: boolean; notes: string };
export type RecommendedCase = { case_id: number | string; title: string; match_reason?: string; matched_tags?: string[]; source_path?: string };
export type LlmTestResult = { ok: boolean; status_code: number; model: string; reply: string; error: string; configured: Record<string, boolean> };
export type M3FullTestResult = { ok: boolean; pptx_path: string; download_url: string; slide_count: number; image_summary: Record<string, number>; table_summary?: Record<string, number> };
export type CaseLibraryItem = { case_id: string | number; title: string; filename?: string; project_type?: string; source_path?: string; module_id?: string; source_type?: string };
export type FullPptCaseItem = { case_id: string; project_id: number; title: string; filename: string; project_type?: string; source_path: string; source_type: "full_ppt"; stored_at: string; file_size: number; download_url: string };
export type M3MaterialImage = { purpose: string; filename: string; content_type?: string; stored_path: string; description?: string; page_index?: number };
export type M3MaterialTable = { purpose: string; filename: string; content_type?: string; stored_path: string; page_index?: number };
export type M3MaterialsResult = {
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
