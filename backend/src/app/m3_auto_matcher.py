from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class M3Section:
    title: str
    text_field: str
    image_field: str


@dataclass(frozen=True)
class M3AutoRenderPayload:
    texts: dict[str, str]
    images_by_purpose: dict[str, list[bytes]]
    page_texts: dict[str, list[str]]
    ordered_images: list[dict[str, object]]


M3_AUTO_SECTIONS = (
    M3Section("项目基本情况", "m3_basic_summary", "image:m3_basic"),
    M3Section("项目线路图", "m3_line_summary", "image:m3_line"),
    M3Section("敏感点路段", "m3_sensitive_points_summary", "image:m3_sensitive_points"),
    M3Section("工程量统计", "m3_quantity_summary", "image:m3_quantity"),
    M3Section("结构形式", "m3_structure_summary", "image:m3_structure"),
    M3Section("现场踏勘", "m3_site_survey_summary", "image:m3_site_survey"),
    M3Section("现场勘察情况", "m3_investigation_summary", "image:m3_investigation"),
    M3Section("项目重难点分析", "m3_risk_summary", "image:m3_risk"),
    M3Section("重难点应对措施", "m3_solution_summary", "image:m3_solution"),
)

_SECTIONS_BY_TITLE = {section.title: section for section in M3_AUTO_SECTIONS}
_KEY_PATTERN = re.compile(r"^(?P<title>.+?)(?:-(?P<index>\d+))?$")
_DESCRIPTION_PATTERN = re.compile(r"^(?P<key>[^:：]+)[:：](?P<text>.*)$")


def _normalize_key_text(value: str) -> str:
    return re.sub(r"\s+", "", value.strip())


def _parse_m3_key(raw_key: str, *, source_label: str) -> tuple[M3Section, int | None]:
    key = _normalize_key_text(raw_key)
    match = _KEY_PATTERN.match(key)
    if not match:
        raise ValueError(f"{source_label}格式错误：{raw_key}")

    title = match.group("title")
    section = _SECTIONS_BY_TITLE.get(title)
    if section is None:
        if source_label == "图片":
            raise ValueError(f"无法识别图片分类：{raw_key}")
        raise ValueError(f"无法识别描述分类：{raw_key}")

    index_text = match.group("index")
    return section, int(index_text) if index_text else None


def _parse_description_lines(descriptions: str) -> dict[tuple[str, int | None], str]:
    parsed: dict[tuple[str, int | None], str] = {}
    for line_no, raw_line in enumerate((descriptions or "").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        match = _DESCRIPTION_PATTERN.match(line)
        if not match:
            raise ValueError(f"描述格式错误：第 {line_no} 行缺少冒号")
        section, index = _parse_m3_key(match.group("key"), source_label="描述")
        key = (section.image_field, index)
        if key in parsed:
            raise ValueError(f"描述编号重复：{match.group('key')}")
        parsed[key] = match.group("text").strip()
    return parsed


def build_m3_auto_render_payload(
    filenames: list[str],
    blobs: list[bytes],
    descriptions: str,
) -> M3AutoRenderPayload:
    if len(filenames) != len(blobs):
        raise ValueError("图片文件数量和内容数量必须一致")

    grouped: dict[str, dict[int | None, tuple[str, bytes]]] = {}
    for filename, blob in zip(filenames, blobs):
        stem = Path(filename).stem
        section, index = _parse_m3_key(stem, source_label="图片")
        bucket = grouped.setdefault(section.image_field, {})
        if index is None and None in bucket:
            raise ValueError(f"{section.title} 存在多个未编号图片，请补充 -1/-2")
        if index is not None and index in bucket:
            raise ValueError(f"{section.title} 图片编号重复：-{index}")
        bucket[index] = (filename, blob)

    parsed_descriptions = _parse_description_lines(descriptions)
    image_keys = {
        (image_field, index)
        for image_field, indexed_items in grouped.items()
        for index in indexed_items
    }
    for image_field, index in parsed_descriptions:
        if (image_field, index) not in image_keys:
            section_title = next(
                section.title for section in M3_AUTO_SECTIONS if section.image_field == image_field
            )
            suffix = "" if index is None else f"-{index}"
            raise ValueError(f"描述没有对应图片：{section_title}{suffix}")

    texts = {section.text_field: "" for section in M3_AUTO_SECTIONS}
    images_by_purpose: dict[str, list[bytes]] = {}
    page_texts: dict[str, list[str]] = {}
    ordered_images: list[dict[str, object]] = []

    for section in M3_AUTO_SECTIONS:
        indexed_items = grouped.get(section.image_field, {})
        if not indexed_items:
            continue
        ordered_indices = sorted(indexed_items, key=lambda value: (-1 if value is None else value))
        images_by_purpose[section.image_field] = [indexed_items[index][1] for index in ordered_indices]
        page_texts[section.image_field] = [
            parsed_descriptions.get((section.image_field, index), "")
            for index in ordered_indices
        ]
        for position, index in enumerate(ordered_indices, start=1):
            filename, blob = indexed_items[index]
            ordered_images.append(
                {
                    "purpose": section.image_field,
                    "filename": filename,
                    "blob": blob,
                    "description": parsed_descriptions.get((section.image_field, index), ""),
                    "page_index": position,
                }
            )
        texts[section.text_field] = page_texts[section.image_field][0] if page_texts[section.image_field] else ""

    return M3AutoRenderPayload(
        texts=texts,
        images_by_purpose=images_by_purpose,
        page_texts=page_texts,
        ordered_images=ordered_images,
    )
