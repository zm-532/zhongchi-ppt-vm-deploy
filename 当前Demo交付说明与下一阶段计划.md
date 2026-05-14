# 中驰智能PPT Demo 当前交付说明与下一阶段计划

## 1. 当前状态说明

当前代码 Demo 已完成一条旧口径的端到端链路：用户创建项目后，按 `M1/M2/M5/M6` 上传材料，系统生成章节 PPT 并合并最终 PPTX。

但业务口径已经更新。后续代码改造必须以 `D:\中驰股份\技术文档.md` 和 `D:\中驰股份\计划.md` 为准：

- 前端不再按模块上传。
- 前端统一上传全部项目资料。
- 后端自动解析资料、归类资料、识别项目类型。
- `M1/M2` 根据项目类型选择固化模板并替换字段。
- `M5` 根据项目资料匹配案例。
- `M6` 使用固定企业背书模板。
- `M3/M4` 后续动态生成，本阶段不进入生成链路。

## 2. 当前 Demo 已实现能力

### 后端能力

- FastAPI 项目骨架。
- 项目创建、查询、列表接口。
- 旧版按模块文件上传接口。
- 本地 JSON Mock 存储，结构后续可替换 PostgreSQL。
- 任务状态查询接口。
- 人工确认接口。
- 最终 PPTX 下载接口。
- 旧版状态历史可观测。

### PPT 引擎能力

- 使用 python-pptx 生成旧版章节 PPT。
- 缺失字段使用 `[待补充：字段名]` 占位。
- 能合并最终 PPTX。
- 当前尚未真正接入 `code\ppt_engine\templates\solution_fixed_modules` 的模板复制和字段替换。

### 前端能力

- Next.js Demo 页面。
- 项目列表。
- 新建项目表单。
- 旧版上传区。
- 启动生成按钮。
- 人工确认按钮。
- 状态历史展示。
- 最终 PPTX 下载入口。

### 工作流与资产能力

- Mock 工作流骨架覆盖解析、匹配、大纲、确认、渲染、合并。
- 资产扫描工具已有初步分类能力。
- 当前素材匹配使用关键词/标签 fallback。
- pgvector 接口仍是后续增强方向。

## 3. 与最新口径的差距

当前代码需要后续 AI 重点修改：

- 前端旧版上传区需要改成统一多文件上传。
- 后端需要新增 `/api/projects/{project_id}/files` 统一上传接口。
- 文件记录需要从强制 `module_id` 改为后端解析后的 `document_role` 和 `assigned_modules`。
- 需要新增资料分析接口 `/api/projects/{project_id}/analyze`。
- 需要新增识别结果查询接口 `/api/projects/{project_id}/classification`。
- 需要新增识别结果确认接口 `/api/projects/{project_id}/classification/review`。
- 工作流需要增加资料分类、项目类型识别、模板选择、案例匹配节点。
- PPT 引擎需要接入真实固化模板，而不是重新画占位页。
- 测试需要改为覆盖统一上传和自动分类新流程。

## 4. 新版标准演示流程

1. 启动后端服务。
2. 启动前端服务。
3. 打开前端页面。
4. 新建项目。
5. 统一上传全部项目资料。
6. 点击“开始分析”或“识别资料”。
7. 查看系统识别结果：项目类型、M1/M2 模板、M5 推荐案例、M6 固定模板、缺失字段。
8. 人工确认或修正识别结果。
9. 点击“生成 PPT”。
10. 系统套用模板、替换字段、填充案例、合并最终文件。
11. 下载最终 PPTX。

新版 API 流程：

1. `POST /api/projects`
2. `POST /api/projects/{project_id}/files`
3. `POST /api/projects/{project_id}/analyze`
4. `GET /api/projects/{project_id}/classification`
5. `POST /api/projects/{project_id}/classification/review`
6. `POST /api/projects/{project_id}/generate`
7. `GET /api/projects/{project_id}/task`
8. `GET /api/projects/{project_id}/download`

旧版 `/api/projects/{project_id}/modules/{module_id}/files` 可保留兼容，但新版前端不再调用。

## 5. 本地运行方式

当前代码仍可按旧 Demo 方式运行。后续 AI 改造代码时，应保持这些启动方式尽量不变。

### 启动后端

```powershell
cd D:\中驰股份\code\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 启动前端

```powershell
cd D:\中驰股份\code\frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3001
```

访问地址：

```text
http://127.0.0.1:3001
```

默认后端地址：

```text
http://127.0.0.1:8000
```

## 6. 后续自动化验收方向

后续代码改造完成后，建议保留并更新以下验收命令：

### 后端验收

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest -v tests.test_api
```

重点覆盖：

- 创建项目。
- 统一上传多个文件。
- 上传时不传 `module_id`。
- analyze 生成 classification。
- review classification。
- generate 生成最终 PPTX。
- M3/M4 不参与当前生成。

### PPT 引擎验收

```powershell
cd D:\中驰股份\code\ppt_engine
uv run python -m unittest -v tests.test_renderer
```

重点覆盖：

- M1/M2 按项目类型选择模板。
- M5 按确认案例填充模板。
- M6 使用固定模板。
- 最终 PPTX 可打开。

### 工作流验收

```powershell
cd D:\中驰股份\code\workflow
uv run python -m unittest -v tests.test_workflow
```

重点覆盖：

- 资料解析节点。
- 资料分类节点。
- 项目类型识别节点。
- 模板选择节点。
- 案例匹配节点。
- 人工确认节点。

### 前端验收

```powershell
cd D:\中驰股份\code\frontend
npm test
npm run build
npm run test:e2e
```

重点覆盖：

- 页面不再出现“分模块上传材料”主流程。
- 支持统一多文件上传。
- 展示识别结果。
- 支持人工确认。
- 支持最终下载。

## 7. 下一阶段任务计划

| 计划时间 | 实际完成时间 | 工作事项 | 具体方法 | 完成情况 |
|---|---|---|---|---|
| 第1步 | 2026-05-13 | 文档口径修订 | 将文档统一改为“统一上传，后端自动分类、选模板、匹配案例” | 已完成 |
| 第2步 | 待定 | 前端改造 | 删除旧版上传区，新增统一上传和识别结果确认界面 | 未开始 |
| 第3步 | 待定 | 后端接口改造 | 新增统一上传、analyze、classification、classification review 接口 | 未开始 |
| 第4步 | 待定 | 数据模型改造 | 文件记录增加 document_role、assigned_modules、parse_status | 未开始 |
| 第5步 | 待定 | 工作流改造 | 增加资料分类、类型识别、模板选择、案例匹配节点 | 未开始 |
| 第6步 | 待定 | 模板引擎改造 | 接入 `PPT_TEMPLATE_ROOT=D:\中驰股份\code\ppt_engine\templates\solution_fixed_modules`，实现复制模板和字段替换 | 未开始 |
| 第7步 | 待定 | 案例匹配 | 用关键词/标签 fallback 先实现 M5 案例推荐 | 未开始 |
| 第8步 | 待定 | 测试更新 | 更新后端、前端、PPT 引擎、工作流测试 | 未开始 |
| 第9步 | 待定 | 演示验收 | 用中海寰宇等示例资料跑通新版流程 | 未开始 |

