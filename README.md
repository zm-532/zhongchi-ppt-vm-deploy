# 中驰智能PPT Demo

本目录是中驰售前 PPT 生成平台的代码工作区。当前主流程是：创建项目、统一上传项目资料、系统解析和识别、人工确认项目类型与模板、生成并下载最终 PPTX。

## 目录职责

- `frontend/`：Next.js 前端，包含正式流程页面和开发功能测试入口。
- `backend/`：FastAPI 后端，负责项目、文件、分析、确认、生成和下载 API。
- `ppt_engine/`：PPTX 模板复制、字段替换、章节渲染和合并。
- `asset_tools/`：案例和素材扫描、标签提取、索引辅助工具。
- `workflow/`：后续可替换为 LangGraph 的工作流骨架。
- `docker/`：PostgreSQL、pgvector 等本地开发配置。
- `data/`：本地上传、解析文本、输出 PPTX 和案例库数据。

## 当前正式流程

1. 用户创建项目并填写基础信息。
2. 用户统一上传项目资料，不需要选择资料属于哪个章节。
3. 后端解析文件，识别资料角色、项目类型、M1/M2 模板和 M5 推荐案例。
4. M1/M2 项目类型识别使用模板画像 + LLM 优先 + 规则 fallback，结果可在前端“查看分析依据”中查看。
5. 用户确认项目类型、M1/M2 模板、M3 是否生成、M5 案例。
6. 后端按 `M1/M2 -> M3 -> M5 -> M6` 生成并合并 PPTX；M4 暂不参与当前生成链路。
7. 用户下载最终 PPTX。

## 启动

后端默认建议运行在 `http://127.0.0.1:8010`，与前端默认 API 地址一致。

```powershell
cd D:\中驰股份\code\backend
uv run uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload
```

前端：

```powershell
cd D:\中驰股份\code\frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3001
```

访问：

```text
http://127.0.0.1:3001
```

如需覆盖后端地址：

```powershell
$env:NEXT_PUBLIC_API_BASE_URL='http://127.0.0.1:8010'
```

## 常用验证

只跑相关测试，不跑全量测试。

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest tests.test_api -v

cd D:\中驰股份\code\frontend
npm test -- static-structure.test.mjs
.\node_modules\.bin\tsc.cmd --noEmit
```

M3 或 PPT 引擎专项验证：

```powershell
cd D:\中驰股份\code\ppt_engine
uv run python -m unittest tests.test_m3_image_renderer tests.test_m3_renderer -v
uv run python -m unittest tests.test_renderer -v
```

当前 Windows/Codex 桌面环境中，除非明确需要生产构建，不要把 `npm run build` 作为快速验证命令。

## 功能测试入口

前端“功能测试”是开发验证入口，不是普通用户主流程。当前包括：

- M1/M2 选择测试。
- M5 案例匹配测试。
- 文档解析测试。
- 大模型连接测试。
- M3 文字替换测试。
- M3 图片替换测试。
- M3 完整测试。

功能测试使用独立输出目录或真实项目测试链路，具体边界见 `技术文档.md`。
