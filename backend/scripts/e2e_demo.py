# -*- coding: utf-8 -*-
"""新版 e2e 演示脚本，使用统一上传流程。

流程：POST /api/projects → /files → /analyze → /classification/review → /generate → /download
"""
import os
import sys
from pathlib import Path

# 在 import app.main 之前设置环境变量，使 case_matcher.py 能读到 ZHONGCHI_SR_PPT_SPLIT_DIR
_code_dir = Path(__file__).resolve().parents[2]
_data_dir = _code_dir / "data"
_sr_split_dir = _code_dir.parent / "SR智能PPT拆分"
os.environ["ZHONGCHI_DATA_DIR"] = str(_data_dir)
os.environ["ZHONGCHI_SR_PPT_SPLIT_DIR"] = str(_sr_split_dir)

from fastapi.testclient import TestClient

from app.main import app


DEMO_PROJECT = {
    "project_name": "南京地铁3号线声屏障改造工程",
    "project_location": "南京",
    "owner_unit": "南京地铁集团有限公司",
    "product_line": "轨交既有线改造",
}

# 演示用文本内容：包含线路名称、现场痛点、施工场景关键词
# 用于触发 M1/M2 规则识别字段（line_name / site_pain_points / construction_scenario）
DEMO_FILE_CONTENT = (
    "南京地铁3号线声屏障改造工程施工组织设计\n"
    "\n"
    "一、项目概况\n"
    "南京地铁3号线是南京市重要的轨道交通干线，本项目为3号线沿线声屏障改造工程。\n"
    "既有线运营期间施工，施工窗口受限，主要集中在夜间天窗点进行作业。\n"
    "沿线噪声问题突出，居民投诉频繁，需要采取降噪措施。\n"
    "\n"
    "二、施工难点\n"
    "1. 工期紧张：受运营影响，每天施工窗口短\n"
    "2. 噪声治理：夜间施工需严格控制降噪标准\n"
    "3. 既有线改造：必须在运营状态下进行，安全要求高\n"
    "\n"
    "三、主要施工内容\n"
    "地铁轨道交通声屏障加装工程，涉及全线约15公里的既有线改造。\n"
).encode("utf-8")


def main() -> None:
    data_dir = Path(os.environ["ZHONGCHI_DATA_DIR"])
    client = TestClient(app)

    # 1. 创建项目
    project = client.post("/api/projects", json=DEMO_PROJECT).json()
    project_id = project["project_id"]
    print(f"项目已创建: project_id={project_id}")

    # 2. 统一上传项目资料（包含可触发规则识别和案例匹配的文本）
    files = {
        "files": (
            "南京地铁3号线声屏障改造工程施工组织设计.txt",
            DEMO_FILE_CONTENT,
            "text/plain",
        )
    }
    uploaded = client.post(f"/api/projects/{project_id}/files", files=files)
    uploaded.raise_for_status()
    print(f"文件已上传: {len(uploaded.json())} 个")

    # 3. 分析项目
    classification = client.post(f"/api/projects/{project_id}/analyze")
    classification.raise_for_status()
    result = classification.json()
    detected_type = result.get("detected_project_type", "metro")
    print(f"项目已分析: detected_project_type={detected_type}")

    # 4. 读取推荐案例，取第一个匹配案例
    recommended_cases = result.get("case_selection", {}).get("recommended_cases", [])
    if not recommended_cases:
        print("错误：未匹配到 M5 案例，请检查上传资料和案例库")
        print("提示：ZHONGCHI_SR_PPT_SPLIT_DIR 需指向包含历史案例的目录")
        sys.exit(1)

    selected_case = recommended_cases[0]
    confirmed_case_id = selected_case.get("case_id")
    case_title = selected_case.get("title", "")
    print(f"匹配到案例: case_id={confirmed_case_id} title={case_title[:40]}")

    # 5. 人工确认（使用检测到的项目类型和选中的案例）
    confirmed = client.post(
        f"/api/projects/{project_id}/classification/review",
        json={
            "confirmed_project_type": detected_type,
            "template_selection": result.get("template_selection", {}),
            "confirmed_case_id": confirmed_case_id,
            "notes": "端到端演示确认",
        },
    )
    confirmed.raise_for_status()
    print(f"分类已确认: confirmed_project_type={detected_type}, confirmed_case_id={confirmed_case_id}")

    # 6. 生成 PPT（classification_status 已是 "reviewed"，走 generate_reviewed_project）
    generate = client.post(f"/api/projects/{project_id}/generate")
    generate.raise_for_status()
    print("PPT 已生成")

    # 7. 下载最终 PPT
    detail = client.get(f"/api/projects/{project_id}").json()
    download = client.get(f"/api/projects/{project_id}/download")
    download.raise_for_status()

    output_path = data_dir / "outputs" / "e2e_downloaded_final.pptx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(download.content)

    print(f"project_id={project_id}")
    print(f"final_ppt_path={detail.get('final_ppt_path', '')}")
    print(f"selected_case_title={case_title}")
    print(f"downloaded={output_path}")


if __name__ == "__main__":
    main()