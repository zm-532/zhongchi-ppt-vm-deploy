"""Vector store implementation using pgvector."""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field


def _sanitize_table_name(name: str) -> str:
    """只允许 [A-Za-z_][A-Za-z0-9_]*，非法时返回空字符串。"""
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", name)
    if cleaned and re.match(r"^[A-Za-z_]", cleaned):
        return cleaned
    return ""

try:
    import psycopg

    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    psycopg = None


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk stored in the vector database."""

    filename: str
    source_path: str
    document_role: str
    assigned_modules: list[str]
    chunk_index: int
    project_id: int = 0
    file_id: int = 0
    doc_type: str = "project"  # "project" or "asset"
    # Asset-specific fields
    asset_id: int = 0
    module_id: str = ""
    title: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PgVectorConfig:
    """Configuration for pgvector connection."""

    enabled: bool = False
    dsn: str = ""
    table_name: str = "zhongchi_embeddings"
    embedding_dimension: int = 1536


class PgVectorStore:
    """
    pgvector-based vector store for project and asset embeddings.

    When ZHONGCHI_VECTOR_DSN is not configured, is_available() returns False
    and all operations raise NotImplementedError to trigger keyword fallback.
    """

    def __init__(self, config: PgVectorConfig | None = None):
        if config is None:
            dsn = os.environ.get("ZHONGCHI_VECTOR_DSN", "")
            table_name = os.environ.get("ZHONGCHI_VECTOR_TABLE", "zhongchi_embeddings")
            table_name = _sanitize_table_name(table_name) or "zhongchi_embeddings"
            embedding_dim_str = os.environ.get("ZHONGCHI_EMBEDDING_DIM", "")
            try:
                embedding_dim = int(embedding_dim_str) if embedding_dim_str else 1536
            except (ValueError, TypeError):
                embedding_dim = 1536
            embedding_dim = max(1, min(embedding_dim, 4096))
            config = PgVectorConfig(
                enabled=bool(dsn),
                dsn=dsn,
                table_name=table_name,
                embedding_dimension=embedding_dim,
            )
        else:
            safe_table = _sanitize_table_name(config.table_name) or "zhongchi_embeddings"
            safe_dim = max(1, min(int(config.embedding_dimension), 4096))
            if safe_table != config.table_name or safe_dim != config.embedding_dimension:
                config = PgVectorConfig(
                    enabled=config.enabled,
                    dsn=config.dsn,
                    table_name=safe_table,
                    embedding_dimension=safe_dim,
                )
        self.config = config

    def is_available(self) -> bool:
        """Return True if pgvector DSN is configured."""
        return self.config.enabled and bool(self.config.dsn)

    def _get_connection(self):
        """Get a psycopg connection from the DSN pool."""
        if not PSYCOPG_AVAILABLE:
            raise RuntimeError(
                "psycopg is required for pgvector operations. Install with: uv pip install psycopg[binary]"
            )
        return psycopg.connect(self.config.dsn)

    def _ensure_table(self) -> None:
        """Create the embeddings table if it doesn't exist."""
        if not self.is_available():
            raise NotImplementedError("pgvector 未启用，请使用关键词/标签 fallback 完成素材匹配。")

        # Ensure pgvector extension exists before creating vector column
        create_ext_sql = "CREATE EXTENSION IF NOT EXISTS vector"

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.config.table_name} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            chunk_text TEXT NOT NULL,
            embedding vector({self.config.embedding_dimension}) NOT NULL,
            module_id VARCHAR(10) NOT NULL,
            doc_type VARCHAR(20) NOT NULL DEFAULT 'project',
            filename VARCHAR(500),
            source_path VARCHAR(1000),
            document_role VARCHAR(100),
            assigned_modules VARCHAR(500),
            chunk_index INTEGER DEFAULT 0,
            project_id INTEGER DEFAULT 0,
            file_id INTEGER DEFAULT 0,
            asset_id INTEGER DEFAULT 0,
            title VARCHAR(500),
            tags VARCHAR(1000),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT unique_chunk UNIQUE (project_id, file_id, doc_type, chunk_index, asset_id)
        )
        """
        create_updated_at_sql = f"""
        ALTER TABLE {self.config.table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        """

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_ext_sql)
                cur.execute(create_table_sql)
                cur.execute(create_updated_at_sql)
            conn.commit()

    def upsert(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadata: list[ChunkMetadata],
    ) -> int:
        """
        Insert or update embedding chunks into the vector store.

        Args:
            chunks: List of text chunks
            embeddings: Corresponding embedding vectors
            metadata: List of chunk metadata

        Returns:
            Number of chunks successfully upserted

        Raises:
            NotImplementedError: If pgvector is not available
            ValueError: If input lists have mismatched lengths
        """
        if not self.is_available():
            raise NotImplementedError("pgvector 未启用，请使用关键词/标签 fallback 完成素材匹配。")

        if len(chunks) != len(embeddings) or len(chunks) != len(metadata):
            raise ValueError("chunks, embeddings, and metadata must have the same length")

        if not chunks:
            return 0

        # Ensure table exists
        self._ensure_table()

        inserted = 0
        with self._get_connection() as conn:
            for chunk_text, embedding, meta in zip(chunks, embeddings, metadata):
                assigned_modules_str = ",".join(meta.assigned_modules) if meta.assigned_modules else ""
                tags_str = ",".join(meta.tags) if meta.tags else ""
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

                upsert_sql = f"""
                INSERT INTO {self.config.table_name}
                (chunk_text, embedding, module_id, doc_type, filename, source_path,
                 document_role, assigned_modules, chunk_index, project_id, file_id,
                 asset_id, title, tags, updated_at)
                VALUES (
                    %s, %s::vector, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
                )
                ON CONFLICT (project_id, file_id, doc_type, chunk_index, asset_id)
                DO UPDATE SET
                    chunk_text = EXCLUDED.chunk_text,
                    embedding = EXCLUDED.embedding,
                    module_id = EXCLUDED.module_id,
                    updated_at = CURRENT_TIMESTAMP
                """
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            upsert_sql,
                            (
                                chunk_text,
                                embedding_str,
                                meta.module_id or meta.assigned_modules[0] if meta.assigned_modules else "",
                                meta.doc_type,
                                meta.filename,
                                meta.source_path,
                                meta.document_role,
                                assigned_modules_str,
                                meta.chunk_index,
                                meta.project_id,
                                meta.file_id,
                                meta.asset_id,
                                meta.title,
                                tags_str,
                            ),
                        )
                        inserted += 1
                except Exception as exc:
                    conn.rollback()
                    raise RuntimeError(f"Failed to upsert chunk: {exc}") from exc
            conn.commit()

        return inserted

    def search(
        self,
        module_id: str,
        embedding: list[float],
        doc_type: str | None = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Search for similar chunks by embedding vector.

        Args:
            module_id: Filter by module ID (required)
            embedding: Query embedding vector
            doc_type: Optional filter by document type ("project" or "asset")
            top_k: Maximum number of results to return

        Returns:
            List of matching chunk records with metadata and similarity scores

        Raises:
            NotImplementedError: If pgvector is not available
        """
        if not self.is_available():
            raise NotImplementedError("pgvector 未启用，请使用关键词/标签 fallback 完成素材匹配。")

        top_k = max(1, min(int(top_k), 100))

        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        # Build params in SQL placeholder order: embedding, module_id, [doc_type], embedding
        params: list = [embedding_str, module_id]
        doc_type_clause = ""
        if doc_type is not None:
            doc_type_clause = " AND doc_type = %s"
            params.append(doc_type)
        params.append(embedding_str)  # for ORDER BY

        search_sql = f"""
        SELECT
            id, chunk_text, module_id, doc_type, filename, source_path,
            document_role, assigned_modules, chunk_index, project_id, file_id,
            asset_id, title, tags,
            (embedding <=> %s::vector) AS distance
        FROM {self.config.table_name}
        WHERE module_id = %s{doc_type_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT {top_k}
        """

        results: list[dict] = []
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(search_sql, params)
                for row in cur.fetchall():
                    results.append(
                        {
                            "id": row[0],
                            "chunk_text": row[1],
                            "module_id": row[2],
                            "doc_type": row[3],
                            "filename": row[4],
                            "source_path": row[5],
                            "document_role": row[6],
                            "assigned_modules": row[7].split(",") if row[7] else [],
                            "chunk_index": row[8],
                            "project_id": row[9],
                            "file_id": row[10],
                            "asset_id": row[11],
                            "title": row[12],
                            "tags": row[13].split(",") if row[13] else [],
                            "distance": row[14],
                        }
                    )
        return results

    def delete_project_chunks(self, project_id: int) -> int:
        """Delete all chunks for a given project_id."""
        if not self.is_available():
            return 0

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM {self.config.table_name} WHERE project_id = %s", (project_id,))
                deleted = cur.rowcount
            conn.commit()
        return deleted if deleted is not None else 0

