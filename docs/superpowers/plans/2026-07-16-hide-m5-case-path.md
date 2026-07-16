# M5 案例库隐藏路径与 Case ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 M5 案例库只展示案例名称和项目类型，不展示路径、case_id 或空状态中的目录信息。

**Architecture:** 保留后端接口和 `CaseLibraryItem` 数据结构不变，只调整 `CaseLibraryView` 的 M5 页签 JSX。使用现有 Node 静态结构测试锁定展示边界，确保完整 PPT 案例库现有 case_id 展示不受影响。

**Tech Stack:** Next.js、React、TypeScript、Node.js `node:test`

---

## 文件结构

- Modify: `frontend/tests/static-structure.test.mjs`：增加 M5 案例库敏感字段不渲染的源码结构回归测试。
- Modify: `frontend/app/views/CaseLibraryView.tsx`：移除 M5 条目路径与 case_id，并改写空状态提示。

## TDL

| 计划时间 | 实际完成时间 | 工作事项 | 具体方法 | 完成情况 |
|---|---|---|---|---|
| 2026-07-16 | — | 添加回归测试 | 对 `CaseLibraryView.tsx` 做定向源码断言 | 未开始 |
| 2026-07-16 | — | 隐藏 M5 路径与 case_id | 仅删除 M5 页签对应 JSX，保留数据和 React key | 未开始 |
| 2026-07-16 | — | 相关验证 | 只运行新增静态测试及 TypeScript 检查 | 未开始 |

### Task 1: 添加失败的 M5 展示边界测试

**Files:**
- Modify: `frontend/tests/static-structure.test.mjs`
- Test: `frontend/tests/static-structure.test.mjs`

- [ ] **Step 1: 增加定向源码读取和失败测试**

在测试文件的源码读取辅助变量处增加：

```js
const caseLibraryViewSource = () => readFileSync(new URL("../app/views/CaseLibraryView.tsx", import.meta.url), "utf8");
```

增加测试：

```js
test("[静态] M5案例库不展示路径和case_id", () => {
  const source = caseLibraryViewSource();
  const m5Section = source.slice(source.indexOf('{caseLibraryTab === "m5"'), source.indexOf(") : (", source.indexOf('{caseLibraryTab === "m5"')));

  assert.doesNotMatch(m5Section, /case_id:/);
  assert.doesNotMatch(m5Section, /item\.source_path/);
  assert.doesNotMatch(m5Section, /ppt_engine\/templates\/solution_fixed_modules\/M5/);
  assert.match(m5Section, /item\.filename \|\| item\.title/);
  assert.match(m5Section, /labelForProjectType\(item\.project_type\)/);
});
```

- [ ] **Step 2: 定向运行测试并确认失败**

Run:

```powershell
node --test --test-name-pattern="M5案例库不展示路径和case_id" tests/static-structure.test.mjs
```

Working directory: `frontend`

Expected: FAIL，失败原因是 M5 区域仍包含 `case_id:`、`item.source_path` 或具体目录路径。

### Task 2: 最小化修改 M5 案例库展示

**Files:**
- Modify: `frontend/app/views/CaseLibraryView.tsx:51-70`
- Test: `frontend/tests/static-structure.test.mjs`

- [ ] **Step 1: 删除 M5 条目中的 case_id 文本**

将：

```tsx
<div>
  <strong>{item.filename || item.title}</strong>
  <span>case_id: {String(item.case_id)}</span>
</div>
```

改为：

```tsx
<div>
  <strong>{item.filename || item.title}</strong>
</div>
```

保留 `<article ... key={item.case_id}>`，因为 React 列表仍需要稳定 key，该属性不会显示给用户。

- [ ] **Step 2: 删除 M5 条目中的路径文本**

将：

```tsx
<div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
  {item.project_type ? <span className="badge">{labelForProjectType(item.project_type)}</span> : null}
  {item.source_path ? <span className="sourcePath">{item.source_path}</span> : null}
</div>
```

改为：

```tsx
<div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 4 }}>
  {item.project_type ? <span className="badge">{labelForProjectType(item.project_type)}</span> : null}
</div>
```

- [ ] **Step 3: 改写 M5 空状态文案**

将：

```tsx
<p className="cases-empty-desc">请检查 ppt_engine/templates/solution_fixed_modules/M5 目录下是否存在 .pptx 案例文件。</p>
```

改为：

```tsx
<p className="cases-empty-desc">当前案例库暂无可用案例，请联系管理员导入案例文件。</p>
```

- [ ] **Step 4: 定向运行新增测试并确认通过**

Run:

```powershell
node --test --test-name-pattern="M5案例库不展示路径和case_id" tests/static-structure.test.mjs
```

Working directory: `frontend`

Expected: PASS，1 个匹配测试通过。

### Task 3: 相关范围验证

**Files:**
- Verify: `frontend/app/views/CaseLibraryView.tsx`
- Verify: `frontend/tests/static-structure.test.mjs`

- [ ] **Step 1: 运行静态结构测试文件**

Run:

```powershell
node --test tests/static-structure.test.mjs
```

Working directory: `frontend`

Expected: PASS，0 failures。

- [ ] **Step 2: 运行 TypeScript 类型检查**

Run:

```powershell
npx tsc --noEmit
```

Working directory: `frontend`

Expected: exit code 0，无 TypeScript 错误。

- [ ] **Step 3: 核对定向差异**

Run:

```powershell
git diff -- frontend/app/views/CaseLibraryView.tsx frontend/tests/static-structure.test.mjs
```

Expected: 仅包含 M5 展示移除、空状态文案和对应测试；完整 PPT 案例库代码不变。
