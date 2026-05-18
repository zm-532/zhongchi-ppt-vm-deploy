# -*- coding: utf-8 -*-
"""检查 M1/M2 模板是否已有占位符。"""
from pptx import Presentation
from pathlib import Path
import re

TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates" / "solution_fixed_modules"

M1_M2_TEMPLATES = [
    "公路全封闭声屏障（M1_&_M2）.pptx",
    "轨道交通地铁全封闭声屏障（M1_&_M2）.pptx",
    "铁路_&_轨道交通既有线声屏障_（M1_&_M2）.pptx",
    "铁路声屏障行业背景与技术发展（M1_&_M2）.pptx",
]

PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def check_template(filename: str) -> dict:
    path = TEMPLATE_ROOT / filename
    prs = Presentation(str(path))
    all_texts = []
    placeholders_found = set()
    has_project_info = False

    for slide in prs.slides:
        for shape in slide.shapes:
            if not hasattr(shape, "text"):
                continue
            text = shape.text or ""
            all_texts.append(text)
            if "项目生成信息" in text:
                has_project_info = True
            for m in PLACEHOLDER_PATTERN.finditer(text):
                placeholders_found.add(m.group(1))

    return {
        "filename": filename,
        "slide_count": len(prs.slides),
        "has_placeholders": bool(placeholders_found),
        "placeholders": sorted(placeholders_found),
        "has_project_info_page": has_project_info,
    }


if __name__ == "__main__":
    for tmpl in M1_M2_TEMPLATES:
        result = check_template(tmpl)
        print(f"=== {result['filename']} ===")
        print(f"  Slides: {result['slide_count']}")
        print(f"  Has placeholders: {result['has_placeholders']}")
        if result["placeholders"]:
            print(f"  Placeholders: {result['placeholders']}")
        print(f"  Has 项目生成信息: {result['has_project_info_page']}")
        print()