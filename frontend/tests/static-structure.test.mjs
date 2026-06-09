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
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const pageSource = () => readFileSync(new URL("../app/page.tsx", import.meta.url), "utf8");
const repoRoot = new URL("../../", import.meta.url);

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
    "查看分析依据",
    "案例库管理",
    "功能测试",
    "M1/M2选择测试",
    "M1/M2 选用模板",
    "M5 推荐案例",
    "M6 固定模板",
    "生成状态",
    "下载最终 PPTX",
    "M3资料上传",
    "M3完整测试",
  ].forEach((text) => assert.match(source, new RegExp(text)));
});

test("[静态] page.tsx 将开发测试收纳到功能测试入口并包含大模型测试", () => {
  const source = pageSource();
  [
    'type ViewId = "projects" | "create" | "cases" | "project-m3-materials" | "function-tests"',
    "#function-tests",
    "功能测试",
    "开发过程验证入口",
    "M1/M2选择测试",
    "M3完整测试",
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
  assert.doesNotMatch(source, /href="#m3-test"/);
  assert.doesNotMatch(source, /href="#m3-image-test"/);

  const order = ["#m1m2-test", "#m3-full-test", "#m5-test", "#document-parse-test", "#llm-test"];
  const positions = order.map((text) => source.indexOf(text));
  positions.forEach((position) => assert.notEqual(position, -1));
  assert.deepEqual([...positions].sort((a, b) => a - b), positions);
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
    "分类方式",
    "LLM 判断理由",
    "classification_method",
    "llm_reasoning_summary",
    "fallback_reason",
    "判断依据",
    "detection_evidence",
    "snippet",
    "confidence",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  assert.doesNotMatch(source, /m1m2TestProductLine/);
  assert.match(source, /product_line: ""/);
});

test("[静态] 项目文档收敛为根 README 和技术文档", () => {
  const rootPath = (name) => new URL(name, repoRoot);

  // 旧文档路径应不存在
  const oldDocs = [
    "END_TO_END.md",
    "asset_tools/README.md",
    "backend/README.md",
    "data/README.md",
    "docker/README.md",
    "frontend/README.md",
    "ppt_engine/README.md",
    "workflow/README.md",
    "计划.md",
    "文本解析入库与向量库构建计划.md",
  ];
  for (const doc of oldDocs) {
    assert.ok(!existsSync(rootPath(doc)), `旧文档 ${doc} 应已移除`);
  }

  // 正式文档应存在
  assert.ok(existsSync(rootPath("README.md")), "根 README.md 应存在");
  assert.ok(existsSync(rootPath("技术文档.md")), "技术文档.md 应存在");
});

test("[静态] 根文档和页面元信息不再保留旧流程口径", () => {
  const readRoot = (name) => readFileSync(new URL(name, repoRoot), "utf8");
  const source = `${readRoot("README.md")}\n${readRoot("技术文档.md")}\n${readFileSync(new URL("../app/layout.tsx", import.meta.url), "utf8")}`;
  [
    "上传 M1/M2/M5/M6",
    "M3/M4 不生成",
    "END_TO_END",
    "127.0.0.1:8000",
    "按模块上传材料",
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
  assert.match(source, /统一上传项目资料/);
  assert.match(source, /M1\/M2 LLM 分类器/);
  assert.match(source, /查看分析依据/);
});

test("[静态] 正式识别结果确认页包含 M1/M2 分析依据展开入口", () => {
  const source = pageSource();
  [
    "showClassificationDetails",
    "setShowClassificationDetails",
    "查看分析依据",
    "收起分析依据",
    "分类方式",
    "LLM 判断理由",
    "fallback_reason",
    "detection_evidence",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] 生成状态区展示 QAReviewAgent 质量检查结果", () => {
  const source = pageSource();
  [
    "quality_report",
    "qualityReport",
    "qualityReportExpanded",
    "setQualityReportExpanded",
    "质量检查结果",
    "QAReviewAgent",
    "展开详情",
    "收起",
    "不影响下载",
    "检查失败",
    "有风险",
    "通过",
    "errors",
    "warnings",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
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
    "/m3-materials",
    "NEXT_PUBLIC_API_BASE_URL",
    "fetch(",
    // M3 完整测试接口
    "/api/test/m3-full-render",
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

test("[静态] 创建项目表单为单列布局且必填项用星号标注", () => {
  const pageSourceText = pageSource();
  const styles = readFileSync(new URL("../app/styles.css", import.meta.url), "utf8");

  assert.match(pageSourceText, /项目名称\*/);
  assert.match(pageSourceText, /项目所在地\*/);
  assert.match(pageSourceText, /建设\/业主单位\*/);
  assert.match(pageSourceText, /产品线\*/);
  assert.doesNotMatch(pageSourceText, /项目所在地（可选，建议填写）/);
  assert.doesNotMatch(pageSourceText, /建设\/业主单位（可选，建议填写）/);
  assert.doesNotMatch(pageSourceText, /产品线（可选，建议填写）/);
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

test("[静态] page.tsx 不再包含 M3 文字/图片拆分测试入口", () => {
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
    "#m3-image-test",
    "M3图片替换测试",
    "m3ImageTestProjectName",
    "m3ImageTestFiles",
    "m3ImageTestPurposes",
    "m3ImageTestResult",
    "m3ImageTestMessage",
    "runM3ImageRenderTest",
    "/api/test/m3-image-render",
    "执行 M3 图片替换测试",
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] page.tsx 包含 M3 完整测试视图的 UI 元素", () => {
  const source = pageSource();
  [
    "#m3-full-test",
    "M3完整测试",
    "m3FullTestProjectName",
    "m3FullTestBulkFiles",
    "m3FullTestDescriptions",
    "m3FullTestResult",
    "m3FullTestMessage",
    "runM3FullRenderTest",
    "/api/test/m3-full-render",
    "执行 M3 完整测试",
    "批量 M3 资料自动分类",
    "批量描述文本",
    "自动匹配预览",
    "m3NamingHelpOpen",
    "M3图片命名规则",
    "命名规则",
    "如果只有一张图，可以使用“项目基本情况.jpg”",
    "多张图必须使用“项目基本情况-1.jpg”“项目基本情况-2.jpg”",
    "项目基本情况",
    "项目线路图",
    "敏感点路段",
    "工程量统计",
    "结构形式",
    "现场踏勘",
    "现场勘察情况",
    "项目重难点分析",
    "重难点应对措施",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  [
    "手动上传 fallback",
    "未选择批量图片时生效",
    "m3FullTestFiles",
    "updateM3FullTestText",
    "updateM3FullTestFiles",
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] page.tsx 包含正式流程 M3资料上传独立页面", () => {
  const source = pageSource();
  [
    "#project-m3-materials",
    "project-m3-materials",
    "M3资料上传",
    "用于项目深化方案 M3 章节生成",
    "保存M3资料",
    "保存并返回我的项目",
    "返回我的项目",
    "m3MaterialBulkFiles",
    "m3MaterialDescriptions",
    "m3MaterialAutoPreview",
    "m3MaterialsResult",
    "m3MaterialsMessage",
    "loadM3Materials",
    "saveM3Materials",
    "/api/projects/${currentProject.project_id}/m3-materials",
    "project_m3_material_bulk_images",
    "批量 M3 资料自动分类",
    "批量描述文本",
    "自动匹配预览",
    "项目基本情况",
    "项目线路图",
    "敏感点路段",
    "工程量统计",
    "结构形式",
    "现场踏勘",
    "现场勘察情况",
    "项目重难点分析",
    "重难点应对措施",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));

  [
    "m3MaterialTexts",
    "m3MaterialFiles",
    "updateM3MaterialText",
    "updateM3MaterialFiles",
    "project_m3_material_${section.textField}",
    "上传{section.title}图片",
  ].forEach((text) => assert.doesNotMatch(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] 统一资料上传页将上传成功提示放在 M3 上传情况之后", () => {
  const source = pageSource();

  assert.match(source, /M3上传情况/);
  assert.match(source, /<div className="uploadSuccess">上传成功<\/div>/);
  assert.doesNotMatch(source, /上传成功，已上传 \{uploadedFiles\.length\} 个文件/);

  const uploadPanelPosition = source.indexOf('className="uploadPanel"');
  const m3EntryPosition = source.indexOf('className="m3-material-entry"');
  const successPosition = source.indexOf('className="uploadSuccess"');

  assert.notEqual(uploadPanelPosition, -1);
  assert.notEqual(m3EntryPosition, -1);
  assert.notEqual(successPosition, -1);
  assert.ok(uploadPanelPosition < m3EntryPosition);
  assert.ok(m3EntryPosition < successPosition);
});

test("[静态] 人工确认表单中 M3 在 M5 前面且包含 M5 案例选择", () => {
  const source = pageSource();
  assert.match(source, /确认 M3 模块[\s\S]*确认 M5 案例/);
  assert.match(source, /暂不选择案例/);
  assert.match(source, /caseLibraryItems/);
  assert.match(source, /m5FixedCases/);
});

test("[静态] page.tsx 支持完整PPT存入案例库和案例库分组展示", () => {
  const source = pageSource();
  [
    "存入案例库",
    "完整PPT案例库",
    "M5案例库",
    "saveFullPptCase",
    "refreshFullPptCases",
    "fullPptCases",
    "caseLibraryTab",
    "/api/projects/${currentProject.project_id}/full-ppt-case",
    "/api/cases/full-ppt",
    "/api/cases/full-ppt/${caseItem.case_id}/download",
  ].forEach((text) => assert.match(source, new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))));
});

test("[静态] 人工确认表单支持选择尾页打印版", () => {
  const source = pageSource();
  assert.match(source, /includePrintTailPage: boolean/);
  assert.match(source, /includePrintTailPage: false/);
  assert.match(source, /type="checkbox"/);
  assert.match(source, /include_print_tail_page: reviewForm\.includePrintTailPage/);
});

test("[静态] 人工确认界面隐藏备注和向量库按钮", () => {
  const source = pageSource();
  assert.doesNotMatch(source, /确认备注/);
  assert.doesNotMatch(source, /确认存入向量库/);
  assert.match(source, /添加尾页打印版/);
});

test("[静态] analyzeProject 成功后重置 reviewForm 为新识别结果", () => {
  const source = pageSource();
  // analyzeProject 内必须在 setClassification 之后调用 setReviewForm
  assert.match(source, /async function analyzeProject[\s\S]*setReviewForm/);
  // 重置逻辑必须使用 recommended_cases 初始化 caseId
  assert.match(source, /recommended_cases[\s\S]*?caseId/);
});

test("[静态] M1/M2 人工确认默认优先使用新建项目产品线映射", () => {
  const source = pageSource();
  assert.match(source, /productLineProjectTypeMap/);
  assert.match(source, /轨道交通声屏障["']:\s*["']metro/);
  assert.match(source, /轨交既有线改造["']:\s*["']existing_rail_transit/);
  assert.match(source, /公路声屏障["']:\s*["']highway/);
  assert.match(source, /铁路声屏障["']:\s*["']railway/);
  assert.match(source, /projectTypeFromProductLine\(currentProject\?\.product_line\)/);
  assert.match(source, /preferredProjectType \|\| detectedType/);
});

test("[静态] 产品线和资料识别冲突时人工确认区显示提示", () => {
  const source = pageSource();
  assert.match(source, /productLineClassificationConflict/);
  assert.match(source, /新建项目选择的产品线/);
  assert.match(source, /资料识别结果为/);
  assert.match(source, /已默认按产品线选择/);
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
