# 中驰智能PPT Demo 代码目录

本目录用于存放本项目所有代码、脚本、配置和本地开发数据目录。

当前阶段仅建立项目骨架，不实现业务逻辑。

## 目录职责

- `frontend/`: Next.js 前端项目。
- `backend/`: FastAPI 后端项目，后续使用 uv 管理 Python 环境。
- `workflow/`: LangGraph 或等价可替换工作流编排代码。
- `ppt_engine/`: python-pptx 章节 PPT 生成与最终 PPTX 合并引擎。
- `asset_tools/`: 历史素材扫描、分类、标签和向量入库工具。
- `docker/`: PostgreSQL、pgvector 等本地开发配置。
- `data/`: Demo 本地文件存储目录。

## 端到端验收

见 `END_TO_END.md`。
