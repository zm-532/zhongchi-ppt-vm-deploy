import json
import os
import shutil
import tempfile
from pathlib import Path


def build_project_ppt_preview(project_id: int, project: dict, output_root: Path) -> dict:
    """为项目生成或复用 PPT 预览图片，返回 slide 列表信息。

    Args:
        project_id: 项目 ID。
        project: 项目数据字典，需包含 final_ppt_path。
        output_root: 项目输出根目录，如 data/outputs/project_1/。

    Returns:
        包含 slide_count 和 slides 列表的字典。

    Raises:
        ValueError: 最终 PPTX 尚未生成。
        RuntimeError: PowerPoint COM 不可用。
    """
    final_ppt_path = project.get("final_ppt_path")
    if not final_ppt_path:
        raise ValueError("最终PPTX尚未生成")

    pptx_path = Path(final_ppt_path)
    if not pptx_path.exists():
        raise ValueError("最终PPTX文件不存在")

    preview_dir = output_root / "preview"
    manifest_path = preview_dir / "manifest.json"

    # 检查缓存是否有效
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            cached_size = manifest.get("pptx_size")
            cached_mtime = manifest.get("pptx_mtime")
            stat = pptx_path.stat()
            if cached_size == stat.st_size and abs(cached_mtime - stat.st_mtime) < 1.0:
                # 校验所有 PNG 文件真实存在
                slide_files = [preview_dir / s["filename"] for s in manifest["slides"]]
                if all(p.exists() and p.is_file() and p.suffix.lower() == ".png" for p in slide_files):
                    return {
                        "slide_count": manifest["slide_count"],
                        "slides": [
                            {
                                "index": s["index"],
                                "image_url": f"/api/projects/{project_id}/preview/slides/{s['filename']}",
                            }
                            for s in manifest["slides"]
                    ],
                }
        except (json.JSONDecodeError, KeyError, OSError):
            # manifest 损坏，重新生成
            pass

    # 清理旧预览目录
    if preview_dir.exists():
        shutil.rmtree(preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)

    # 导出 PNG
    slide_count, slide_files = _export_slides_to_png(pptx_path, preview_dir)

    # 写入 manifest
    stat = pptx_path.stat()
    manifest = {
        "pptx_path": str(pptx_path),
        "pptx_size": stat.st_size,
        "pptx_mtime": stat.st_mtime,
        "slide_count": slide_count,
        "slides": [
            {"index": i + 1, "filename": fname}
            for i, fname in enumerate(slide_files)
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "slide_count": slide_count,
        "slides": [
            {
                "index": s["index"],
                "image_url": f"/api/projects/{project_id}/preview/slides/{s['filename']}",
            }
            for s in manifest["slides"]
        ],
    }


def _export_slides_to_png(pptx_path: Path, preview_dir: Path) -> tuple[int, list[str]]:
    """使用 PowerPoint COM 将 PPTX 每页导出为 PNG。

    Args:
        pptx_path: 源 PPTX 文件路径。
        preview_dir: PNG 输出目录。

    Returns:
        (slide_count, slide_files) 元组。

    Raises:
        RuntimeError: 非 Windows 系统或 pywin32 不可用。
    """
    if os.name != "nt":
        raise RuntimeError("PPT 预览仅支持 Windows 系统（需要 PowerPoint）。仍可下载 PPTX。")

    try:
        import win32com.client  # type: ignore[import-not-found]
    except ImportError:
        raise RuntimeError("预览生成需要安装 pywin32 (pip install pywin32)。仍可下载 PPTX。")

    preview_dir.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="zhongchi_ppt_preview_"))
    local_pptx_path = work_dir / pptx_path.name
    shutil.copy2(pptx_path, local_pptx_path)

    app = None
    presentation = None
    try:
        app = win32com.client.DispatchEx("PowerPoint.Application")
        presentation = app.Presentations.Open(
            str(local_pptx_path.resolve()), ReadOnly=True, Untitled=False, WithWindow=False
        )
        slide_count = presentation.Slides.Count
        slide_files: list[str] = []
        for i in range(1, slide_count + 1):
            filename = f"slide-{i:03d}.png"
            temp_output_path = work_dir / filename
            final_output_path = preview_dir / filename
            presentation.Slides(i).Export(str(temp_output_path), "PNG", 1920, 1080)
            if not temp_output_path.exists():
                raise RuntimeError(f"PowerPoint 未成功导出预览图片：{filename}")
            shutil.copy2(temp_output_path, final_output_path)
            slide_files.append(filename)
        return slide_count, slide_files
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"PPT 预览生成失败：{exc}。仍可下载 PPTX。") from exc
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        shutil.rmtree(work_dir, ignore_errors=True)
