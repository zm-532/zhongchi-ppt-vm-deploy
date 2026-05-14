# workflow

工作流编排目录。

后续串联模块解析、素材匹配、章节大纲、人工确认、章节渲染和最终合并流程。

## 当前阶段能力

本阶段提供一个可替换为 LangGraph 的 Python 工作流骨架，节点边界与技术文档保持一致：

1. `load_project`
2. `prepare_modules`
3. `parse_module_files`
4. `extract_module_tags`
5. `retrieve_module_assets`
6. `match_cases`
7. `generate_module_outlines`
8. `human_review`
9. `render_chapter_ppts`
10. `merge_ppt`
11. `quality_check`

当前实现只处理 `M1/M2/M5/M6`。`M3/M4` 为后续动态模块，输入中出现时会被拒绝。

LLM 和 Embedding 默认使用 Mock fallback：

- `use_mock_llm=True`
- `use_mock_embedding=True`

## 运行测试

```powershell
cd D:\中驰股份\code\workflow
uv run python -m unittest -v tests.test_workflow
```

## 代码入口

```python
from workflow.engine import WorkflowEngine, build_workflow_engine
```
