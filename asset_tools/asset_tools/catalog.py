from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ALLOWED_MODULE_IDS = ("M1", "M2", "M5", "M6")

MODULE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "M1": ("行业", "政策", "标准", "技术标准", "产品趋势", "规范", "背景"),
    "M2": ("项目概况", "项目基本情况", "概况", "现场", "挑战", "客户痛点", "痛点", "工况", "问题"),
    "M5": ("案例", "同类型", "历史项目", "解决成效", "技术难点", "相似项目"),
    "M6": ("企业", "资质", "荣誉", "CNAS", "专利", "产能", "背书", "生产", "质量保障", "质量保证", "原材料", "检测计划"),
}

DYNAMIC_MODULE_KEYWORDS = ("M3", "M4", "定制化设计", "工程量", "施工周期", "工期测算", "技术深化", "图纸深化", "实施方案", "施工总体部署", "实施预排", "措施费")

TEXT_EXTENSIONS = {".txt", ".md", ".json", ".csv"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | {".ppt", ".pptx", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg"}


@dataclass(frozen=True)
class AssetRecord:
    asset_id: int
    module_id: str
    title: str
    text: str
    tags: list[str]
    source_path: str
    asset_type: str = "material"
    embedding_status: str = "fallback_keyword"


class AssetCatalog:
    def __init__(self, assets: list[dict[str, Any]] | list[AssetRecord] | None = None):
        self.assets = [asset if isinstance(asset, AssetRecord) else AssetRecord(**asset) for asset in (assets or [])]

    def filter_by_module(self, module_id: str) -> list[AssetRecord]:
        validate_module_id(module_id)
        return [asset for asset in self.assets if asset.module_id == module_id]

    def to_jsonable(self) -> list[dict[str, Any]]:
        return [asdict(asset) for asset in self.assets]

    def save_json(self, output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_jsonable(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path


def validate_module_id(module_id: str) -> None:
    if module_id not in ALLOWED_MODULE_IDS:
        raise ValueError("module_id 只允许 M1/M2/M5/M6，M3/M4 为后续动态模块。")


def classify_module(text: str) -> str | None:
    normalized = text.upper()
    if any(keyword.upper() in normalized for keyword in DYNAMIC_MODULE_KEYWORDS):
        dynamic_only = not any(
            keyword.upper() in normalized
            for module_id, keywords in MODULE_KEYWORDS.items()
            for keyword in ((module_id,) + keywords)
        )
        if dynamic_only:
            return None

    scores: dict[str, int] = {}
    for module_id, keywords in MODULE_KEYWORDS.items():
        score = 0
        if module_id in normalized:
            score += 3
        for keyword in keywords:
            if keyword.upper() in normalized:
                score += 1
        if score:
            scores[module_id] = score

    if not scores:
        return None
    return sorted(scores.items(), key=lambda item: (-item[1], ALLOWED_MODULE_IDS.index(item[0])))[0][0]


def extract_tags(module_id: str, text: str) -> list[str]:
    validate_module_id(module_id)
    tags = [keyword for keyword in MODULE_KEYWORDS[module_id] if keyword.upper() in text.upper()]
    return tags or [module_id]


def read_asset_text(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="gbk", errors="ignore")
    return path.stem


def scan_asset_directory(root: str | Path) -> list[AssetRecord]:
    root_path = Path(root)
    if not root_path.exists():
        raise FileNotFoundError(f"素材目录不存在：{root_path}")

    records: list[AssetRecord] = []
    for path in sorted(item for item in root_path.rglob("*") if item.is_file()):
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        text = f"{path.stem} {read_asset_text(path)}"
        module_id = classify_module(text)
        if module_id is None:
            continue
        records.append(
            AssetRecord(
                asset_id=len(records) + 1,
                module_id=module_id,
                title=path.stem,
                text=text[:2000],
                tags=extract_tags(module_id, text),
                source_path=str(path),
                asset_type=path.suffix.lower().lstrip(".") or "material",
            )
        )
    return sorted(records, key=lambda asset: (ALLOWED_MODULE_IDS.index(asset.module_id), asset.source_path))
