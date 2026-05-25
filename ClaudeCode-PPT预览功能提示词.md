# Claude Code 提示词：实现 PPT 下载前预览功能

请在仓库 `D:\中驰股份\code` 中实现“PPT 下载前预览”功能。

## 背景

这是一个中驰售前 PPT 助手项目，已有完整 PPT 生成和下载流程。当前完整流程生成最终 PPTX 后，只能通过下载按钮获取文件，领导希望在下载前能先在网页里预览 PPT 内容。

已知现状：

- 后端 FastAPI 代码主要在 `backend/src/app/`。
- 前端页面主要在 `frontend/app/page.tsx` 和 `frontend/app/styles.css`。
- PPT 引擎主要在 `ppt_engine/ppt_engine/renderer.py`。
- 后端已有下载接口：`GET /api/projects/{project_id}/download`。
- 项目生成完成后，项目数据里已有 `final_ppt_path` 字段。
- PPT 引擎里已有 Windows PowerPoint COM 合并逻辑，依赖 `pywin32`，可以沿用同类能力做 PPT 导出图片。
- 不要改动现有完整生成流程和下载流程，预览功能应作为旁路能力添加。

## 目标

实现一个“预览 PPT”功能：用户生成最终 PPTX 后，在下载按钮旁点击“预览 PPT”，后端把最终 PPTX 导出为每页 PNG，前端用网页内弹窗展示预览图。预览失败不能影响原有 PPTX 下载。

## 功能要求

1. 后端新增 PPT 预览生成能力
   - 读取当前项目的 `final_ppt_path`。
   - 如果项目不存在，返回 404。
   - 如果最终 PPTX 尚未生成或文件不存在，返回清晰错误。
   - 使用 Windows PowerPoint COM 打开最终 PPTX，并导出每一页为 PNG。
   - 建议使用 PowerPoint COM 的 `Presentation.Export(output_dir, "PNG", width, height)`。
   - 导出的图片存放在项目输出目录下，例如：`data/outputs/project_{project_id}/preview/`。
   - 图片文件名统一整理为稳定格式，例如 `slide-001.png`、`slide-002.png`。
   - 生成一个 `manifest.json`，记录 PPTX 文件路径、文件大小、修改时间、页数、图片列表。

2. 后端新增预览 API
   - 新增 `POST /api/projects/{project_id}/preview`。
   - 该接口负责生成或复用预览图片，并返回：

```json
{
  "project_id": 1,
  "slide_count": 12,
  "slides": [
    {
      "index": 1,
      "image_url": "/api/projects/1/preview/slides/slide-001.png"
    }
  ]
}
```

   - 新增 `GET /api/projects/{project_id}/preview/slides/{filename}`。
   - 该接口只允许读取对应项目 preview 目录内的 PNG 文件，必须防止路径穿越。
   - 如果 PowerPoint COM 或 `pywin32` 不可用，返回清晰错误信息，例如“预览生成失败：当前环境无法调用 PowerPoint，仍可下载 PPTX”。

3. 预览缓存规则
   - 如果 `manifest.json` 存在，且记录的 PPTX 文件大小和修改时间与当前最终 PPTX 一致，则直接复用已有 PNG。
   - 如果最终 PPTX 变化，则清理旧 preview 目录中的旧 PNG，重新导出。
   - 不要因为预览缓存失败影响项目生成或下载。

4. 前端新增预览入口
   - 在最终文件区域，也就是当前“下载最终 PPTX”按钮附近，增加“预览 PPT”按钮。
   - 点击后调用 `POST /api/projects/{project_id}/preview`。
   - 请求过程中显示加载状态。
   - 成功后打开网页内弹窗，不要跳转页面，不要影响用户已经输入的内容。
   - 弹窗内容包括：
     - 当前页大图。
     - 页码，例如 `3 / 12`。
     - 上一页、下一页按钮。
     - 缩略图列表，点击缩略图可跳转。
     - 关闭按钮。
     - 可以保留“下载最终 PPTX”按钮入口。
   - 如果预览生成失败，展示错误提示，但下载按钮仍可使用。

5. UI 要求
   - 弹窗应为网页内 modal，不要打开新窗口。
   - 大图区域应适配常见桌面屏幕，不要溢出页面。
   - 缩略图可横向滚动。
   - 按钮和状态文案使用中文。
   - 保持现有页面风格，不做无关视觉重构。

## 技术约束

- 只处理 PPT 预览相关功能，不做无关重构。
- 修改前先阅读现有代码，遵循项目已有 API、状态管理、样式命名和错误处理模式。
- 保留用户已有的无关改动，不要回滚。
- 不要修改 M3 批量上传、命名分类、描述匹配等已经完成的功能，除非是预览按钮所在页面必须轻微接入。
- Python 环境和依赖默认使用 uv。
- 不要引入重量级新依赖，优先复用现有 `pywin32` 和 PowerPoint COM。
- 不要把 `npm run build` 作为常规验证命令。

## 建议实现步骤

1. 阅读现有代码
   - 查看 `backend/src/app/main.py` 中项目下载接口和路由组织方式。
   - 查看 `backend/src/app/storage.py` 中 `final_ppt_path` 的写入和项目输出目录结构。
   - 查看 `ppt_engine/ppt_engine/renderer.py` 中 PowerPoint COM 合并逻辑，复用它的环境判断、打开/关闭 PowerPoint 的方式。
   - 查看 `frontend/app/page.tsx` 中最终文件区域和 `downloadFinal()` 的实现。
   - 查看 `frontend/app/styles.css` 中现有弹窗、按钮、下载区域样式。

2. 编写后端预览服务
   - 建议新增一个聚焦文件，例如 `backend/src/app/ppt_preview.py`。
   - 在里面实现：
     - `build_project_ppt_preview(project_id, project, output_root) -> dict`
     - PowerPoint COM 导出函数。
     - manifest 读写。
     - 缓存有效性判断。
     - preview 目录清理。
   - PowerPoint 对象必须在 `finally` 中关闭 `presentation` 并 `Quit()`，避免残留 PowerPoint 进程。

3. 接入后端 API
   - 在 `backend/src/app/main.py` 新增预览接口。
   - `POST /api/projects/{project_id}/preview` 调用预览服务。
   - `GET /api/projects/{project_id}/preview/slides/{filename}` 返回 `FileResponse`。
   - 读取图片时必须解析真实路径，确认图片仍在当前项目 preview 目录下。

4. 编写后端测试
   - 不要依赖真实 PowerPoint，使用 monkeypatch/mock 替代导出函数。
   - 覆盖：
     - 项目不存在。
     - 最终 PPTX 不存在。
     - 首次生成预览成功。
     - PPTX 未变化时复用缓存。
     - PPTX 变化时重新生成。
     - slide 图片接口防路径穿越。
     - PowerPoint COM 不可用时返回清晰错误。

5. 前端接入
   - 在 `frontend/app/page.tsx` 增加预览状态：
     - 是否正在生成预览。
     - 预览图片列表。
     - 当前页索引。
     - 弹窗是否打开。
     - 错误信息。
   - 在最终文件区域增加“预览 PPT”按钮。
   - 实现 `previewFinalPpt()` 调用后端 API。
   - 实现 modal 预览 UI。
   - 图片地址使用后端返回的 `image_url`，拼接现有 `API_BASE`。

6. 前端样式
   - 在 `frontend/app/styles.css` 增加或复用 modal 样式。
   - 大图区域限制最大宽高。
   - 缩略图列表横向滚动。
   - 当前缩略图有明显选中态。

## 验证要求

只跑相关测试和检查，不跑全量测试，不跑生产 build。

后端建议：

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest tests.test_ppt_preview -v
```

如果预览 API 测试放进现有项目 API 测试文件，则只运行相关测试文件，例如：

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest tests.test_project_preview_api -v
```

前端建议：

```powershell
cd D:\中驰股份\code\frontend
npm test
.\node_modules\.bin\tsc.cmd --noEmit
```

不要运行：

```powershell
npm run build
```

除非用户明确要求验证生产构建。

## 交付要求

完成后请用中文汇报：

1. 修改了哪些文件。
2. 新增了哪些接口。
3. 前端怎么操作预览。
4. 运行了哪些测试或检查，结果如何。
5. 如果没有真实 PowerPoint 环境无法做端到端导出，请说明后端 mock 测试已覆盖哪些内容，以及真实环境还需要手工验证什么。

## 验收标准

- 完整 PPT 生成完成后，页面出现或可使用“预览 PPT”按钮。
- 点击“预览 PPT”后，可以在网页内弹窗查看每页 PPT 图片。
- 可以上一页、下一页、点击缩略图切换。
- 关闭弹窗后，页面当前项目状态和用户输入不丢失。
- 下载最终 PPTX 仍按原逻辑可用。
- 预览失败时只提示错误，不影响下载。
- 只修改预览相关逻辑，不破坏 M3 上传和完整流程。
