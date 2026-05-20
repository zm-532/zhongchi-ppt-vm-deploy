/**
 * 静态结构检查测试
 *
 * 本文件中的所有测试都是源码结构/文案存在性检查（Static Structure Checks）。
 * 它们通过 readFileSync 读取源代码，然后用正则匹配验证特定字符串是否出现在源码中。
 *
 * 这些测试：
 * - 不执行任何代码
 * - 不调用任何 API
 * - 不验证任何 DOM 结构
 * - 不验证任何用户交互行为
 * - 不验证任何业务流程
 *
 * 因此，即使所有测试通过，也不能证明：
 * - 上传资料功能可用
 * - 识别资料功能可用
 * - 人工确认功能可用
 * - 生成 PPT 功能可用
 * - 下载功能可用
 *
 * 如需验证真实业务流程，请运行 Playwright e2e 测试：
 *   npm run test:e2e
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = () => readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

// ============================================================================
// 源码静态检查 - UI 结构存在性
// ============================================================================

/**
 * [静态检查] 源码中包含主要 UI section 的文本标记
 * 不验证这些 section 在运行时是否正确渲染
 */
test("[静态] page.tsx 源码中包含主要 workflow section 的文本标记", () => {
  const source = pageSource();
  [
    "我的项目",
    "新建项目",
    "统一资料上传",
    "系统将自动识别资料用途",
    "识别结果确认",
    "确认项目类型与模板",
    "案例库管理",
    "功能测试",
    "M1/M2选择测试",
    "M1/M2 选用模板",
    "M5 推荐案例",
    "M6 固定模板",
    "缺失字段",
    "M3 已接入正式生成",
    "M4 暂不生成",
    "生成状态",
    "下载最终 PPTX",
    // M3 入口
    "M3文字替换测试",
    "M3 文字替换测试",
  ].forEach((text) => assert.match(source, new RegExp(text)));
});

test("[静态] page.tsx 将开发测试收纳到功能测试入口并包含大模型测试", () => {
  const source = pageSource();
  [
    'type ViewId = "projects" | "create" | "cases" | "function-tests"',
    "#function-tests",
    "功能测试",
    "开发过程验证入口",
    "M1/M2选择测试",
    "M5选择测试",
    "文档解析测试",
    "大模型测试",
    "runLlmConnectionTest",
    "/api/dev/llm-test",
    "llmTestPrompt",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  assert.doesNotMatch(source, /href="#m1m2-test">M1\/M2选择测试/);
  assert.doesNotMatch(source, /href="#m5-test">M5选择测试/);
  assert.doesNotMatch(source, /href="#document-parse-test">文档解析测试/);
});

test("[静态] page.tsx 源码中包含 M1/M2 测试视图的关键 UI 元素标记", () => {
  const source = pageSource();
  [
    "#m1m2-test",
    "M1/M2选择测试",
    "上传测试资料",
    "识别 M1/M2 类型并选择模板",
    "识别到的项目类型",
    "对应 PPT 模板",
    "matched_keywords",
    "判断依据",
    "detection_evidence",
    "snippet",
    "confidence",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  assert.doesNotMatch(source, /m1m2TestProductLine/);
  assert.match(source, /product_line: ""/);
});

test("[静态] page.tsx 使用侧边栏视图结构和正确的品牌文案", () => {
  const source = pageSource();
  assert.match(source, /中驰售前PPT助手/);
  assert.doesNotMatch(source, /<span>Demo 工作台<\/span>/);
  assert.match(source, /activeView === "projects"/);
  assert.match(source, /activeView === "create"/);
  assert.match(source, /activeView === "cases"/);
});

test("[静态] page.tsx 源码中没有描述'完整PPT自动拆分'的文本", () => {
  const source = pageSource();
  [
    ["完整", "PPT", "自动", "拆分"].join(""),
    ["上传", "完整", "PPT", "后", "自动", "拆分"].join(""),
    ["上传", "一份", "完整", "PPT"].join(""),
    ["自动", "拆成", "M1-M6"].join(""),
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text)));
});

test("[静态] page.tsx 不再要求用户按模块上传资料", () => {
  const source = pageSource();
  [
    "分模块上传材料",
    "上传 M1/M2/M5/M6 材料",
    "前端选择资料属于 M 几",
    "/modules/${moduleId}/files",
    "/api/projects/${currentProject.project_id}/modules/",
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  assert.match(source, /name="project_files"/);
  assert.match(source, /multiple/);
  assert.doesNotMatch(source, /name="M3"/);
  assert.doesNotMatch(source, /name="M4"/);
});

test("[静态] page.tsx 调用了所需的 backend API 端点字符串", () => {
  const source = pageSource();
  [
    "/api/projects",
    "/files",
    "/analyze",
    "/classification",
    "/classification/review",
    "/generate",
    "/task",
    "/download",
    "NEXT_PUBLIC_API_BASE_URL",
    "fetch(",
    // M3 测试接口
    "/api/test/m3-render",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] page.tsx 保留 case_id 为字符串格式和默认端口配置", () => {
  const source = pageSource();
  assert.match(source, /http:\/\/127\.0\.0\.1:8010/);
  assert.doesNotMatch(source, /Number\(reviewForm\.caseId\)/);
  assert.match(source, /confirmed_case_id: reviewForm\.caseId \|\| null/);
  assert.match(source, /caseId: undefined/);
});

test("[静态] page.tsx 包含项目列表展开/收起控制逻辑", () => {
  const source = pageSource();
  assert.match(source, /PROJECT_LIST_PREVIEW_LIMIT = 5/);
  assert.match(source, /PROJECT_LIST_PAGE_SIZE = 10/);
  assert.match(source, /visibleProjects/);
  assert.match(source, /projectListPage/);
  assert.match(source, /totalProjectPages/);
  assert.match(source, /projects\.slice\(0, PROJECT_LIST_PREVIEW_LIMIT\)/);
  assert.match(source, /显示更多/);
  assert.match(source, /收起/);
  assert.match(source, /setProjectListExpanded\(\(expanded\) => !expanded\)/);
  assert.match(source, /上一页/);
  assert.match(source, /下一页/);
  assert.match(source, /第 \$\{projectListPage\} \/ /);
});

test("[静态] page.tsx 支持多选项目管理删除功能", () => {
  const source = pageSource();
  [
    "管理项目",
    "取消管理",
    "删除选中",
    "selectedProjectIds",
    "toggleProjectSelection",
    "deleteSelectedProjects",
    'method: "DELETE"',
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] 创建项目表单为单列布局且标注可选字段", () => {
  const pageSourceText = pageSource();
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");

  assert.match(pageSourceText, /项目所在地（可选，建议填写）/);
  assert.match(pageSourceText, /建设\/业主单位（可选，建议填写）/);
  assert.match(pageSourceText, /产品线（可选，建议填写）/);
  assert.match(styles, /\.projectForm\s*{\s*display: grid;\s*grid-template-columns: minmax\(0, 1fr\);/);
});

test("[静态] page.tsx 调用完整 demo workflow 的 API 端点字符串", () => {
  const source = pageSource();
  [
    "use client",
    "/api/projects",
    "/files",
    "/analyze",
    "/classification",
    "/classification/review",
    "/generate",
    "/task",
    "/download",
    "fetch(",
    "FormData",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] page.tsx 包含编辑已有项目基础信息的功能", () => {
  const source = pageSource();
  assert.match(source, /编辑基础信息/);
  // PATCH 请求：method 在 requestJson 第二个参数中，URL 中含 project_id
  assert.match(source, /method: "PATCH"/);
  assert.match(source, /\/api\/projects\/\$\{currentProject\.project_id\}/);
  assert.match(source, /updateProjectBasicInfo/);
  assert.match(source, /isEditingProject/);
  assert.match(source, /setIsEditingProject/);
});

test("[静态] page.tsx 包含文档解析测试视图的 UI 元素（使用真实项目流程）", () => {
  const source = pageSource();
  [
    "选择测试文件",
    "开始解析测试",
    "docParseTestFiles",
    "docParseTestMessage",
    "docParseTestResult",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] page.tsx 包含 M3 文字替换测试视图的 UI 元素", () => {
  const source = pageSource();
  [
    "#m3-test",
    "M3文字替换测试",
    "m3TestProjectName",
    "m3TestProjectLocation",
    "m3TestOwnerUnit",
    "m3TestProductLine",
    "m3TestSources",
    "m3TestResult",
    "m3TestMessage",
    "runM3RenderTest",
    "/api/test/m3-render",
    "执行 M3 文字替换测试",
    "M3 PPTX 已生成",
    // replacements 摘要展示
    "字段替换摘要",
    "Object.entries(m3TestResult.replacements)",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] styles.css 中解析结果卡片包含文本换行相关的 CSS 类", () => {
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");

  assert.match(styles, /\.parseTextBox\s*\{/);
  assert.match(styles, /white-space:\s*pre-wrap/);
  assert.match(styles, /overflow-wrap:\s*anywhere/);
  assert.match(styles, /word-break:\s*break-word/);
  assert.match(styles, /max-width:\s*100%/);
  assert.match(styles, /overflow-x:\s*hidden/);
  assert.match(styles, /max-height:\s*\d+px/);
  assert.match(styles, /overflow-y:\s*auto/);
  assert.match(styles, /\.parseResultCard\s*\{[^}]*overflow:\s*hidden/);
});

// NOTE: tests 14 and 16 (slides/sections/table rendering and xlsx/pptx distinction)
// have been removed because the old detailed parse-result UI (which used these elements)
// was replaced with a simpler table-based file list view in the document-parse-test section.
// The real analyze flow (via /api/projects/{id}/analyze) returns classification results
// with per-file parse_status/document_role/assigned_modules, which are displayed in a table.
