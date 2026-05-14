# 中驰智能PPT Demo 端到端验收说明

本文档用于阶段 7 端到端演示验收。所有命令均在 `D:\中驰股份\code` 下的子目录执行。

## 1. 启动后端

```powershell
cd D:\中驰股份\code\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

后端提供：

- 项目创建/查询。
- M1/M2/M5/M6 分模块上传。
- Mock 大纲生成。
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

当前前端已接入后端 API，可在页面中完成创建项目、M1/M2/M5/M6 分模块上传、启动生成、人工确认和下载最终 PPTX。默认后端地址为：

```text
http://127.0.0.1:8000
```

如需修改地址，启动前端前设置：

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8000'
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
npm run build
npm run test:e2e
```

## 4. 后端 API 演示流程

1. `POST /api/projects` 创建项目。
2. `POST /api/projects/{project_id}/modules/M1/files` 上传 M1 材料。
3. `POST /api/projects/{project_id}/modules/M2/files` 上传 M2 材料。
4. `POST /api/projects/{project_id}/modules/M5/files` 上传 M5 材料。
5. `POST /api/projects/{project_id}/modules/M6/files` 上传 M6 材料。
6. `POST /api/projects/{project_id}/generate` 生成 Mock 章节大纲，状态进入 `待确认`。
7. `POST /api/projects/{project_id}/review` 提交人工确认，系统渲染章节 PPTX 并合并最终 PPTX。
8. `GET /api/projects/{project_id}/download` 下载最终 PPTX。

自动化测试 `test_end_to_end_generate_review_and_download_final_pptx` 已覆盖以上闭环，并验证最终 PPTX 可被 `python-pptx` 打开。

浏览器端到端测试 `tests/e2e.spec.ts` 已覆盖前端真实点击链路，并验证最终 PPTX 下载事件。

## 5. 当前边界

- 工作流仍为纯 Python Mock 骨架，尚未替换为真实 LangGraph。
- pgvector 为预留接口，当前使用关键词/标签 fallback。
- LLM 和 Embedding 默认使用 Mock/fallback。
- `M3/M4` 只作为后续动态模块，不生成章节。
- 当前真实资产扫描结果中 `M1=0`，M1 演示使用 Mock/fallback 大纲。
