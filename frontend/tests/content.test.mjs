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
