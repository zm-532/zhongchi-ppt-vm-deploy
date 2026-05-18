/**
 * @deprecated
 *
 * 此文件已废弃，功能测试已迁移到：
 *   - static-structure.test.mjs  (源码静态结构检查，不是功能测试)
 *   - e2e.spec.ts                (Playwright 端到端测试，覆盖真实业务流程)
 *
 * ============================================================
 * 如果你正在运行 `npm test`，请注意：
 * ============================================================
 * content.test.mjs 是源码字符串匹配检查，不是功能测试。
 * 即使所有断言通过，也不能证明以下功能可用：
 *   - 上传资料
 *   - 识别资料（analyze）
 *   - 人工确认（review）
 *   - 生成 PPT（generate）
 *   - 下载最终 PPTX
 *
 * 如需验证真实业务流程，请运行：
 *   npm run test:e2e
 *
 * 此文件保留用于兼容性目的，不会被删除。
 * 运行 `node --test tests/static-structure.test.mjs` 来执行静态结构检查。
 */

import test from "node:test";

// Stub: 明确告知 content.test.mjs 已废弃，不执行任何检查
// 如需执行静态结构检查，请运行 static-structure.test.mjs
test("content.test.mjs is deprecated", () => {
  // NO-OP - see deprecation notice above
});