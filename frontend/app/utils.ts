import { API_BASE, projectTypes, productLineProjectTypeMap } from "./constants";
import type { QualityReport } from "./constants";

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) throw new Error(await response.text());
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function labelForProjectType(value?: string) {
  return projectTypes.find((item) => item.value === value)?.label ?? value ?? "待识别";
}

export function projectTypeFromProductLine(productLine?: string) {
  return productLineProjectTypeMap[String(productLine || "").trim()] || "";
}

export function firstTemplateName(item?: { template_path?: string; template_name?: string; template_key?: string; template_filename?: string }) {
  if (!item) return "待识别";
  return item.template_filename || item.template_name || item.template_path?.split(/[\\/]/).pop() || item.template_key || "待识别";
}

export function getProjectStatusClass(status: string) {
  if (!status) return "status-idle";
  if (status === "完成") return "status-done";
  if (status === "待确认") return "status-review";
  if (status === "待上传") return "status-idle";
  if (status.includes("失败") || status.includes("错误")) return "status-error";
  if (status.includes("中")) return "status-running";
  return "status-idle";
}

export function qualityReportLabel(report?: QualityReport) {
  if (!report) return "待检查";
  if (report.severity === "error" || report.passed === false) return "检查失败";
  if (report.severity === "warning" || (report.warnings?.length ?? 0) > 0) return "有风险";
  return "通过";
}

export function formatStoredAt(value?: string) {
  if (!value) return "未记录";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

export function formatFileSize(bytes?: number) {
  if (!bytes || bytes <= 0) return "未知大小";
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
