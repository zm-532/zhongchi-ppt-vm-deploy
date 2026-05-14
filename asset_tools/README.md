# asset_tools

资产工具目录。

后续扫描和整理 `SR智能PPT拆分` 中的素材，按 M1/M2/M5/M6 分类，并预留 pgvector 或关键词/标签匹配能力。

## 当前阶段能力

- 扫描素材目录中的 PPTX/PDF/Office/图片/文本文件。
- 按关键词和标签分类到 `M1/M2/M5/M6`。
- 排除 `M3/M4` 相关动态模块内容。
- 生成本地资产索引 JSON。
- 提供关键词/标签 fallback 匹配器。
- 预留 pgvector 配置和接口；未启用时明确提示使用 fallback。

## 扫描真实素材

```powershell
cd D:\中驰股份\code\asset_tools
uv run python -m asset_tools.cli 'D:\中驰股份\SR智能PPT拆分' --output 'D:\中驰股份\code\data\assets\assets_catalog.json'
```

当前规则基于文件名和可直接读取的文本内容分类。对于 PPTX 深层页面文本抽取、截图预览、Embedding 入库，后续阶段可继续增强。

## 运行测试

```powershell
cd D:\中驰股份\code\asset_tools
uv run python -m unittest -v tests.test_assets
```
