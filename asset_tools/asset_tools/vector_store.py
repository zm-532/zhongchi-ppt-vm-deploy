from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PgVectorConfig:
    enabled: bool = False
    dsn: str = ""
    table_name: str = "asset_embeddings"
    embedding_dimension: int = 1536


class PgVectorStore:
    def __init__(self, config: PgVectorConfig):
        self.config = config

    def is_available(self) -> bool:
        return self.config.enabled and bool(self.config.dsn)

    def search(self, module_id: str, embedding: list[float], top_k: int = 5):
        if not self.is_available():
            raise NotImplementedError("pgvector 未启用，请使用关键词/标签 fallback 完成素材匹配。")
        raise NotImplementedError("pgvector 查询将在数据库接入阶段实现。")

