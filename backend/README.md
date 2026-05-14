# backend

FastAPI 后端目录。

后续实现项目 API、模块上传 API、任务状态 API、人工确认 API、资产/案例查询 API 和下载接口。

## 当前阶段能力

- 项目创建、列表、详情接口。
- M1/M2/M5/M6 分模块文件上传接口。
- `module_id` 白名单校验。
- Mock 生成任务状态和模块状态接口。
- 人工确认接口。
- 人工确认通过后调用 PPT 引擎生成 M1/M2/M5/M6 章节 PPTX，并合并最终 PPTX。
- 资产和案例查询接口。
- 最终 PPTX 下载接口。
- 本地 JSON Mock 存储，后续可替换为 PostgreSQL。

## 运行

```powershell
cd D:\中驰股份\code\backend
uv run uvicorn app.main:app --reload
```

## 测试

```powershell
cd D:\中驰股份\code\backend
uv run python -m unittest -v tests.test_api
```
