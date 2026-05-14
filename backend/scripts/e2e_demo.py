import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    code_dir = Path(__file__).resolve().parents[2]
    data_dir = code_dir / "data"
    os.environ["ZHONGCHI_DATA_DIR"] = str(data_dir)

    client = TestClient(app)
    project = client.post(
        "/api/projects",
        json={
            "project_name": "中驰智能PPT端到端演示项目",
            "project_location": "南京",
            "owner_unit": "某建设单位",
            "product_line": "轨交既有线改造",
        },
    ).json()
    project_id = project["project_id"]

    for module_id in ["M1", "M2", "M5", "M6"]:
        response = client.post(
            f"/api/projects/{project_id}/modules/{module_id}/files",
            files={"file": (f"{module_id}_demo.pdf", f"{module_id} demo material".encode(), "application/pdf")},
        )
        response.raise_for_status()

    client.post(f"/api/projects/{project_id}/generate").raise_for_status()
    client.post(f"/api/projects/{project_id}/review", json={"approved": True, "notes": "端到端演示确认"}).raise_for_status()

    detail = client.get(f"/api/projects/{project_id}").json()
    download = client.get(f"/api/projects/{project_id}/download")
    download.raise_for_status()

    output_path = data_dir / "outputs" / "e2e_downloaded_final.pptx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(download.content)

    print(f"project_id={project_id}")
    print(f"final_ppt_path={detail['final_ppt_path']}")
    print(f"downloaded={output_path}")


if __name__ == "__main__":
    main()

