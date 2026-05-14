from __future__ import annotations

from dataclasses import dataclass

from .catalog import AssetCatalog, AssetRecord, validate_module_id


@dataclass(frozen=True)
class MatchResult:
    asset_id: int
    module_id: str
    title: str
    score: int
    tags: list[str]
    source_path: str


def tokenize(text: str) -> set[str]:
    raw_tokens = text.replace("，", " ").replace("。", " ").replace(",", " ").split()
    tokens = {token.strip().lower() for token in raw_tokens if token.strip()}
    for keyword in ("行业政策", "技术标准", "同类型案例", "解决成效", "客户痛点", "企业背书"):
        if keyword.lower() in text.lower():
            tokens.add(keyword.lower())
    return tokens


class KeywordAssetMatcher:
    def __init__(self, catalog: AssetCatalog):
        self.catalog = catalog

    def match(self, module_id: str, query: str, top_k: int = 5) -> list[MatchResult]:
        validate_module_id(module_id)
        query_tokens = tokenize(query)
        results: list[MatchResult] = []
        for asset in self.catalog.filter_by_module(module_id):
            score = self._score(asset, query_tokens)
            if score > 0:
                results.append(
                    MatchResult(
                        asset_id=asset.asset_id,
                        module_id=asset.module_id,
                        title=asset.title,
                        score=score,
                        tags=asset.tags,
                        source_path=asset.source_path,
                    )
                )
        return sorted(results, key=lambda item: (-item.score, item.asset_id))[:top_k]

    def _score(self, asset: AssetRecord, query_tokens: set[str]) -> int:
        haystack = tokenize(" ".join([asset.title, asset.text, " ".join(asset.tags)]))
        exact_hits = len(query_tokens & haystack)
        substring_hits = sum(1 for token in query_tokens if token and token in f"{asset.title} {asset.text}".lower())
        tag_hits = sum(2 for tag in asset.tags if tag.lower() in query_tokens)
        return exact_hits + substring_hits + tag_hits

