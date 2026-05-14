import { expect, test } from "@playwright/test";
import path from "node:path";

test("user can create project, upload unified files, confirm classification, generate, and download final pptx", async ({ page }) => {
  await page.goto("/");

  const uniqueName = `前端端到端项目 ${Date.now()}`;
  await page.getByPlaceholder("例如：某城市轨道交通声屏障改造项目").fill(uniqueName);
  await page.getByPlaceholder("例如：南京").fill("南京");
  await page.getByPlaceholder("例如：某建设单位").fill("某建设单位");
  await page.getByRole("combobox", { name: "产品线" }).selectOption("轨交既有线改造");
  await page.getByRole("button", { name: "创建项目" }).click();
  await expect(page.getByText(`项目已创建：${uniqueName}`)).toBeVisible();

  await page.locator('input[name="project_files"]').setInputFiles([
    path.join(process.cwd(), "tests", "fixtures", "M1_demo.pdf"),
    path.join(process.cwd(), "tests", "fixtures", "M2_demo.pdf"),
    path.join(process.cwd(), "tests", "fixtures", "M5_demo.pdf"),
    path.join(process.cwd(), "tests", "fixtures", "M6_demo.pdf"),
  ]);
  await page.getByRole("button", { name: "统一上传项目资料" }).click();
  await expect(page.getByText("项目资料已统一上传。")).toBeVisible();

  await page.getByRole("button", { name: "开始识别资料" }).click();
  await expect(page.getByText("识别结果已返回，请确认项目类型、模板与案例。")).toBeVisible();
  await expect(page.getByText("M1/M2 选用模板")).toBeVisible();
  await expect(page.getByText("M5 推荐案例")).toBeVisible();
  await expect(page.getByText("M6 固定模板")).toBeVisible();

  await page.getByRole("combobox", { name: "确认项目类型" }).selectOption("existing_rail_transit");
  await page.getByRole("button", { name: "提交人工确认" }).click();
  await expect(page.getByText("人工确认已提交，可启动最终生成。")).toBeVisible();

  await page.getByRole("button", { name: "启动生成" }).click();
  await expect(page.getByText("生成任务已启动")).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "下载最终 PPTX" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/\.pptx$/);
});
