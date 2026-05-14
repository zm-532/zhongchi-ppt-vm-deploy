# ppt_engine

PPT 引擎目录。

后续使用 python-pptx 生成 M1/M2/M5/M6 章节 PPT，并按 M1 -> M2 -> M5 -> M6 合并最终 PPTX。

## 当前阶段能力

- 使用 `python-pptx` 生成可编辑 PPTX。
- 支持 `M1/M2/M5/M6` 四个章节。
- 按 `M1 -> M2 -> M5 -> M6` 顺序合并最终 PPTX。
- 缺失字段以 `[待补充：字段名]` 展示。
- 拒绝生成 `M3/M4`，这两个模块为后续动态模块。

## 运行测试

```powershell
cd D:\中驰股份\code\ppt_engine
uv run python -m unittest -v tests.test_renderer
```

## 代码入口

```python
from ppt_engine.renderer import render_chapter_ppt, render_final_ppt
```
