# 中驰智能PPT Demo 代码目录

本目录用于存放本项目所有代码、脚本、配置和本地开发数据目录。

当前阶段以 Demo 闭环和功能测试为主。正式生成流程与开发测试入口必须隔离，尤其是 M3 文字替换测试、M3 图片替换测试和完整 PPT 生成流程不能互相影响。

## 目录职责

- `frontend/`: Next.js 前端项目。
- `backend/`: FastAPI 后端项目，后续使用 uv 管理 Python 环境。
- `workflow/`: LangGraph 或等价可替换工作流编排代码。
- `ppt_engine/`: python-pptx 章节 PPT 生成与最终 PPTX 合并引擎。
- `asset_tools/`: 历史素材扫描、分类、标签和向量入库工具。
- `docker/`: PostgreSQL、pgvector 等本地开发配置。
- `data/`: Demo 本地文件存储目录。

## M3 图片替换独立测试

M3 图片替换当前只作为前端“功能测试”中的独立入口存在，不接入正式 PPT 生成流程。

- 前端入口：`功能测试 -> M3图片替换测试`，hash 为 `#m3-image-test`。
- 后端接口：`POST /api/test/m3-image-render`。
- 输出目录：`data/outputs/m3_image_test/`。
- 专用模板：`ppt_engine/templates/solution_fixed_modules/M3_项目深化方案模板_图片替换测试.pptx`。
- 正式 M3/文字测试模板：`ppt_engine/templates/solution_fixed_modules/M3_项目深化方案模板.pptx`，不得因图片测试修改。

图片用途固定为 5 类：

| 中文用途 | 后端字段名 |
|---|---|
| 项目建设范围图 | `project_scope_map` |
| 项目线路图 | `project_line_map` |
| 踏勘路线/点位图 | `survey_route_map` |
| 现场踏勘照片组 | `site_survey_photos` |
| 重难点证据图 | `key_difficulty_evidence` |

模板制作要求：

- 图片测试模板必须是独立复制件，不能直接修改正式 M3 模板。
- 图片占位符应使用矩形/图片槽位承载 `{{image:...}}` 文本。
- 占位符应放在最终图片应显示的位置和尺寸上。
- 不要把占位框叠在旧图片上方作为遮罩；应清掉旧图，只保留可替换槽位。
- 如果使用 PowerPoint 文本框或矩形内文字，需关闭“根据文字调整形状大小/Resize shape to fit text”，否则占位槽高度会被文字锁住。
- 后端会读取占位槽的 `left/top/width/height`，删除占位槽，并把上传图片按同样位置尺寸插入。

## 相关验证

只跑相关测试，不跑全量测试：

```powershell
cd D:\中驰股份\code\ppt_engine
uv run python -m unittest tests.test_m3_image_renderer tests.test_m3_renderer -v

cd D:\中驰股份\code\backend
uv run python -m unittest tests.test_m3_image_api -v

cd D:\中驰股份\code\frontend
npm test -- static-structure.test.mjs
.\node_modules\.bin\tsc.cmd --noEmit
```

除非明确需要生产构建，不要把 `npm run build` 作为前端快速验证命令。

## 端到端验收

见 `END_TO_END.md`。
