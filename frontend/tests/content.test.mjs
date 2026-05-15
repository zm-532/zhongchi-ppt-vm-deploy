import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const pageSource = () => readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");

test("frontend page exposes required demo workflow sections", () => {
  const source = pageSource();

  [
    "我的项目",
    "新建项目",
    "统一资料上传",
    "系统将自动识别资料用途",
    "识别结果确认",
    "确认项目类型与模板",
    "案例库管理",
    "M1/M2选择测试",
    "M1/M2 选用模板",
    "M5 推荐案例",
    "M6 固定模板",
    "缺失字段",
    "后续动态模块",
    "生成状态",
    "下载最终 PPTX",
  ].forEach((text) => assert.match(source, new RegExp(text)));
});

test("frontend exposes an m1 m2 template selection test tool", () => {
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

test("frontend separates sidebar views and uses presales assistant branding", () => {
  const source = pageSource();

  assert.match(source, /中驰售前PPT助手/);
  assert.doesNotMatch(source, /<span>Demo 工作台<\/span>/);
  assert.match(source, /activeView === "projects"/);
  assert.match(source, /activeView === "create"/);
  assert.match(source, /activeView === "cases"/);
});

test("frontend does not describe the product as full-ppt auto splitting", () => {
  const source = pageSource();

  [
    ["完整", "PPT", "自动", "拆分"].join(""),
    ["上传", "完整", "PPT", "后", "自动", "拆分"].join(""),
    ["上传", "一份", "完整", "PPT"].join(""),
    ["自动", "拆成", "M1-M6"].join(""),
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text)));
});

test("frontend no longer asks users to upload by module", () => {
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

test("frontend wires required backend API calls", () => {
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
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("frontend preserves case id strings and uses backend default port", () => {
  const source = pageSource();

  assert.match(source, /http:\/\/127\.0\.0\.1:8000/);
  assert.doesNotMatch(source, /Number\(reviewForm\.caseId\)/);
  assert.match(source, /confirmed_case_id: reviewForm\.caseId \|\| null/);
  assert.match(source, /caseId: undefined/);
});

test("frontend limits long project lists with expand and collapse controls", () => {
  const source = pageSource();

  assert.match(source, /PROJECT_LIST_PREVIEW_LIMIT = 10/);
  assert.match(source, /visibleProjects/);
  assert.match(source, /projects\.slice\(0, PROJECT_LIST_PREVIEW_LIMIT\)/);
  assert.match(source, /显示更多/);
  assert.match(source, /收起/);
});

test("frontend supports multi-select project management deletion", () => {
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

test("create project form is single-column and marks optional fields", () => {
  const pageSourceText = pageSource();
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");

  assert.match(pageSourceText, /项目所在地（可选）/);
  assert.match(pageSourceText, /建设\/业主单位（可选）/);
  assert.match(pageSourceText, /产品线（可选）/);
  assert.match(styles, /\.projectForm\s*{\s*display: grid;\s*grid-template-columns: minmax\(0, 1fr\);/);
});

test("frontend calls backend api for the full demo workflow", () => {
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

test("frontend exposes a document parse test view", () => {
  const source = pageSource();

  [
    "#document-parse-test",
    "文档解析测试",
    "用于测试不同格式资料的文本与结构化解析效果",
    "/api/document-parse-test",
    "runDocumentParseTest",
    "parseStatus",
    "parseResultCard",
    "pending_enhancement",
    "pending_ocr",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("frontend document parse test view includes required UI elements", () => {
  const source = pageSource();

  [
    "选择测试文件",
    "开始解析测试",
    "documentParseTestFiles",
    "documentParseTestResults",
    "documentParseTestMessage",
    "parseResultHeader",
    "parseResultMeta",
    "parseError",
    "parseTextPreview",
    "parseSlides",
    "preview_rows",
    "slideItem",
    "parseStats",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("frontend parse test result card has CSS classes for text wrapping and scrolling", () => {
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

test("frontend parse test renders structured slides, sections, and table preview", () => {
  const source = pageSource();

  // slide structure rendering
  assert.match(source, /parseSlides/);
  assert.match(source, /slideItemHeader/);
  assert.match(source, /slideIndex/);
  assert.match(source, /sheetName/);
  assert.match(source, /slideTitle/);
  assert.match(source, /slideMeta/);
  assert.match(source, /tableScrollWrapper/);
  assert.match(source, /previewTable/);
  assert.match(source, /rowNum/);
  assert.match(source, /slideTexts/);
  assert.match(source, /slideTextItem/);

  // sections rendering
  assert.match(source, /parseSections/);
  assert.match(source, /sectionsList/);
  assert.match(source, /sectionsMore/);

  // stats row
  assert.match(source, /parseStats/);
});

test("frontend parse test result card header and meta layout", () => {
  const source = pageSource();
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");

  // parseResultHeader uses flex-wrap
  assert.match(styles, /\.parseResultHeader\s*\{[^}]*display:\s*flex/);
  assert.match(styles, /\.parseResultHeader\s*\{[^}]*flex-wrap:\s*wrap/);

  // parseResultMeta uses flex-wrap and badge-style spans
  assert.match(styles, /\.parseResultMeta\s*\{[^}]*display:\s*flex/);
  assert.match(styles, /\.parseResultMeta\s*\{[^}]*flex-wrap:\s*wrap/);

  // meta items are chip/badge style
  assert.match(styles, /\.parseResultMeta\s+span\s*\{/);
  assert.match(styles, /border-radius:\s*999px/);
});

test("frontend parse test distinguishes xlsx sheets from pptx slides in display", () => {
  const source = pageSource();

  // xlsx shows sheet_name + rows/columns metadata
  assert.match(source, /sheet_name\?/);
  assert.match(source, /rows.*columns/);

  // pptx shows slideIndex + title + texts
  assert.match(source, /slide_index\?/);
  assert.match(source, /title\?/);
  assert.match(source, /texts\?/);
});
