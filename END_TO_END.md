# 中驰智能PPT Demo 端到端验收说明

本文档用于阶段 7 端到端演示验收。所有命令均在 `D:\中驰股份\code` 下的子目录执行。

## 1. 启动后端

```powershell
cd D:\中驰股份\code\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端提供：

- 项目创建/查询。
- 统一上传全部项目资料。
- 后端自动解析资料、识别项目类型、判断资料可服务模块。
- M1/M2 模板选择。
- M5 案例匹配。
- M6 企业背书模板选择。
- 人工确认。
- 章节 PPTX 渲染。
- 最终 PPTX 合并。
- 最终 PPTX 下载。

## 2. 启动前端

```powershell
cd D:\中驰股份\code\frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3001
```

访问：

```text
http://127.0.0.1:3001
```

当前前端已接入后端 API，可在页面中完成创建项目、统一上传项目资料、启动分析、人工确认、生成并下载最终 PPTX。默认后端地址为：

```text
http://127.0.0.1:8010
```

如需修改地址，启动前端前设置：

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010'
```

## 3. 自动化验收命令

后端端到端验收：

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest -v tests.test_api
```

生成一份可人工打开检查的演示 PPTX：

```powershell
cd D:\中驰股份\code\backend
uv run python scripts\e2e_demo.py
```

脚本会把下载结果保存到：

```text
D:\中驰股份\code\data\outputs\e2e_downloaded_final.pptx
```

PPT 引擎验收：

```powershell
cd D:\中驰股份\code\ppt_engine
uv run python -m unittest -v tests.test_renderer
```

工作流验收：

```powershell
cd D:\中驰股份\code\workflow
uv run python -m unittest -v tests.test_workflow
```

资产工具验收：

```powershell
cd D:\中驰股份\code\asset_tools
uv run python -m unittest -v tests.test_assets
uv run python -m asset_tools.cli 'D:\中驰股份\SR智能PPT拆分' --output 'D:\中驰股份\code\data\assets\assets_catalog.json'
```

前端验收：

```powershell
cd D:\中驰股份\code\frontend
npm test
.\node_modules\.bin\tsc.cmd --noEmit
npm run test:e2e
```

## 4. 后端 API 演示流程

1. `POST /api/projects` 创建项目。
2. `POST /api/projects/{project_id}/files` 统一上传全部项目资料，不要求前端传 `module_id`。
3. `POST /api/projects/{project_id}/analyze` 后端解析资料、识别项目类型、判断资料可服务模块，并推荐 M1/M2 模板和 M5 案例。
4. `POST /api/projects/{project_id}/classification/review` 提交人工确认结果。
5. `POST /api/projects/{project_id}/generate` 按确认结果生成章节 PPTX，并合并最终 PPTX。
6. `GET /api/projects/{project_id}/download` 下载最终 PPTX。

旧版 `POST /api/projects/{project_id}/modules/{module_id}/files` 分模块上传接口仍保留为兼容旧 Demo，不作为新版主流程。

自动化测试已覆盖统一上传、资料分析、人工确认、生成、下载等关键链路；其中旧版分模块上传闭环测试仅用于兼容性验证，不代表新版主流程。

浏览器端到端测试 `tests/e2e.spec.ts` 已覆盖前端真实点击链路，并验证最终 PPTX 下载事件。

## 5. 当前边界

- 工作流仍为纯 Python Mock 骨架，尚未替换为真实 LangGraph。
- pgvector 为预留接口，当前使用关键词/标签 fallback。
- LLM 和 Embedding 默认使用 Mock/fallback。
- `M3/M4` 只作为后续动态模块，不生成章节。
- 当前真实资产扫描结果中 `M1=0`，M1 演示使用 Mock/fallback 大纲。
