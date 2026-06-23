"""临时诊断脚本：检查 static-structure.test.mjs 中失败断言的实际匹配情况。"""
import re
import pathlib

app = pathlib.Path("../frontend/app")
src = "".join(p.read_text(encoding="utf-8") + "\n" for p in app.rglob("*") if p.suffix in (".ts", ".tsx"))
styles = pathlib.Path("../frontend/app/styles.css").read_text(encoding="utf-8")


def check(label, pattern, source, should_match=True):
    found = bool(re.search(pattern, source))
    if should_match:
        status = "OK " if found else "MISS"
    else:
        status = "ABSENT(good)" if not found else "PRESENT(bad)"
    print(f"  {status}  {label}: {pattern!r}")


print("=== TEST1: workflow section 文本标记 ===")
t1 = ["我的项目", "新建项目", "统一资料上传", "系统将自动识别资料用途", "识别结果确认",
      "确认项目类型与模板", "查看分析依据", "案例库管理", "功能测试", "M1/M2选择测试",
      "M1/M2 选用模板", "M5 推荐案例", "M6 固定模板", "生成状态", "下载最终 PPTX",
      "M3资料上传", "M3完整测试"]
for s in t1:
    check("t1", s, src)

print("\n=== TEST2: 功能测试收纳 ===")
t2 = [
    'type ViewId = "projects" | "create" | "cases" | "project-m3-materials" | "function-tests"',
    "#function-tests", "功能测试", "开发过程验证入口", "M1/M2选择测试", "M3完整测试",
    "M5选择测试", "文档解析测试", "大模型测试", "runLlmConnectionTest", "/api/dev/llm-test",
    "llmTestPrompt",
]
for s in t2:
    check("t2", re.escape(s), src)

print("\n=== TEST2: doesNotMatch (应不存在) ===")
d2 = [r'href="#m1m2-test">M1/M2选择测试', r'href="#m5-test">M5选择测试',
      r'href="#document-parse-test">文档解析测试', r'href="#m3-test"', r'href="#m3-image-test"']
for s in d2:
    check("t2-dnm", s, src, should_match=False)

order = ["#m1m2-test", "#m3-full-test", "#m5-test", "#document-parse-test", "#llm-test"]
pos = [src.find(t) for t in order]
print(f"\n  order positions: {pos}")
print(f"  order ok: {sorted(pos) == pos and all(p != -1 for p in pos)}")

print("\n=== TEST6: 分析依据展开入口 ===")
t6 = ["showClassificationDetails", "setShowClassificationDetails", "查看分析依据",
      "收起分析依据", "分类方式", "LLM 判断理由", "fallback_reason", "detection_evidence"]
for s in t6:
    check("t6", re.escape(s), src)

print("\n=== TEST15: 创建项目表单单列布局 ===")
t15_match = ["项目名称\\*", "项目所在地\\*", "建设\\/业主单位\\*", "产品线\\*"]
for s in t15_match:
    check("t15", s, src)
t15_dnm = ["项目所在地（可选，建议填写）", "建设\\/业主单位（可选，建议填写）", "产品线（可选，建议填写）"]
for s in t15_dnm:
    check("t15-dnm", s, src, should_match=False)
print("\n  styles projectForm grid:")
check("t15-css", r'\.projectForm\s*\{\s*display: grid;\s*grid-template-columns: minmax\(0, 1fr\);', styles)
