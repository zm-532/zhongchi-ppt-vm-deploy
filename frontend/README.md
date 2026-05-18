# frontend

Next.js 前端目录。

后续实现项目列表、新建项目、M1/M2/M5/M6 分模块上传、生成状态展示和最终 PPTX 下载。

## 当前阶段能力

- 后台管理型单页 Demo，并接入 FastAPI 后端接口。
- 项目列表空状态。
- 新建项目基础表单。
- M1/M2/M5/M6 分模块上传区。
- M3/M4 标记为后续动态模块。
- 生成状态展示。
- 最终 PPTX 下载入口。
- 案例库管理空状态。
- 创建、上传、生成、人工确认和下载均调用后端 API。

默认 API 地址为 `http://127.0.0.1:8010`，可通过 `NEXT_PUBLIC_API_BASE_URL` 覆盖。

## 运行

```powershell
cd D:\中驰股份\code\frontend
npm install
npm run dev
```

## 验证

```powershell
cd D:\中驰股份\code\frontend
npm test
npm run build
npm run test:e2e
```
