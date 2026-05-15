"""Tests for vector store."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Set up environment before imports
os.environ["ZHONGCHI_VECTOR_DSN"] = ""  # Disable vector store by default

from app.vector_service import ChunkMetadata, PgVectorConfig, PgVectorStore, get_vector_store


class PgVectorStoreDisabledTest(unittest.TestCase):
    """Test PgVectorStore when pgvector is not available (ZHONGCHI_VECTOR_DSN not set)."""

    def setUp(self):
        # Ensure vector DSN is not set
        os.environ.pop("ZHONGCHI_VECTOR_DSN", None)

    def test_is_available_false_without_dsn(self):
        store = PgVectorStore()
        self.assertFalse(store.is_available())

    def test_is_available_false_with_empty_dsn(self):
        os.environ["ZHONGCHI_VECTOR_DSN"] = ""
        store = PgVectorStore()
        self.assertFalse(store.is_available())

    def test_search_raises_not_implemented_when_disabled(self):
        store = PgVectorStore()
        with self.assertRaises(NotImplementedError) as context:
            store.search(module_id="M1", embedding=[0.1] * 1536)
        self.assertIn("关键词/标签 fallback", str(context.exception))

    def test_upsert_raises_not_implemented_when_disabled(self):
        store = PgVectorStore()
        chunks = ["test chunk"]
        embeddings = [[0.1] * 1536]
        metadata = [
            ChunkMetadata(
                filename="test.txt",
                source_path="/test/test.txt",
                document_role="test",
                assigned_modules=["M1"],
                chunk_index=0,
            )
        ]
        with self.assertRaises(NotImplementedError) as context:
            store.upsert(chunks, embeddings, metadata)
        self.assertIn("关键词/标签 fallback", str(context.exception))

    def test_delete_project_chunks_returns_zero_when_disabled(self):
        store = PgVectorStore()
        result = store.delete_project_chunks(project_id=1)
        self.assertEqual(result, 0)


class PgVectorStoreConfigTest(unittest.TestCase):
    """Test PgVectorStore configuration."""

    def test_custom_config_used(self):
        config = PgVectorConfig(enabled=True, dsn="postgresql://localhost/test", table_name="custom_table")
        store = PgVectorStore(config)
        self.assertTrue(store.is_available())
        self.assertEqual(store.config.table_name, "custom_table")

    def test_env_table_name_used(self):
        os.environ["ZHONGCHI_VECTOR_DSN"] = "postgresql://localhost/test"
        os.environ["ZHONGCHI_VECTOR_TABLE"] = "custom_emb"
        try:
            store = PgVectorStore()
            self.assertEqual(store.config.table_name, "custom_emb")
        finally:
            os.environ.pop("ZHONGCHI_VECTOR_TABLE", None)
            os.environ.pop("ZHONGCHI_VECTOR_DSN", None)

    def test_env_embedding_dim_used(self):
        os.environ["ZHONGCHI_VECTOR_DSN"] = "postgresql://localhost/test"
        os.environ["ZHONGCHI_EMBEDDING_DIM"] = "2048"
        try:
            store = PgVectorStore()
            self.assertEqual(store.config.embedding_dimension, 2048)
        finally:
            os.environ.pop("ZHONGCHI_EMBEDDING_DIM", None)
            os.environ.pop("ZHONGCHI_VECTOR_DSN", None)

    def test_table_name_sanitized_removes_invalid_chars(self):
        """Verify table_name is sanitized to only safe SQL identifier characters."""
        os.environ["ZHONGCHI_VECTOR_DSN"] = "postgresql://localhost/test"
        os.environ["ZHONGCHI_VECTOR_TABLE"] = "zhongchi'; DROP TABLE users; --"
        try:
            store = PgVectorStore()
            # Only A-Za-z0-9_ should remain
            self.assertEqual(store.config.table_name, "zhongchiDROPTABLEusers")
            self.assertNotIn("'", store.config.table_name)
            self.assertNotIn(";", store.config.table_name)
        finally:
            os.environ.pop("ZHONGCHI_VECTOR_TABLE", None)
            os.environ.pop("ZHONGCHI_VECTOR_DSN", None)

    def test_table_name_fallback_to_default_on_empty(self):
        """Verify empty table_name falls back to default."""
        os.environ["ZHONGCHI_VECTOR_DSN"] = "postgresql://localhost/test"
        os.environ["ZHONGCHI_VECTOR_TABLE"] = "   "
        try:
            store = PgVectorStore()
            self.assertEqual(store.config.table_name, "zhongchi_embeddings")
        finally:
            os.environ.pop("ZHONGCHI_VECTOR_TABLE", None)
            os.environ.pop("ZHONGCHI_VECTOR_DSN", None)


class ChunkMetadataTest(unittest.TestCase):
    def test_metadata_creation(self):
        meta = ChunkMetadata(
            filename="test.pdf",
            source_path="/docs/test.pdf",
            document_role="tender",
            assigned_modules=["M1", "M2"],
            chunk_index=3,
            project_id=5,
            file_id=10,
        )
        self.assertEqual(meta.filename, "test.pdf")
        self.assertEqual(meta.doc_type, "project")
        self.assertEqual(meta.chunk_index, 3)

    def test_asset_metadata_with_extra_fields(self):
        meta = ChunkMetadata(
            filename="m1_asset.txt",
            source_path="/assets/m1_asset.txt",
            document_role="asset_material",
            assigned_modules=["M1"],
            chunk_index=0,
            doc_type="asset",
            asset_id=42,
            module_id="M1",
            title="行业政策素材",
            tags=["行业", "政策"],
        )
        self.assertEqual(meta.doc_type, "asset")
        self.assertEqual(meta.asset_id, 42)
        self.assertEqual(meta.module_id, "M1")


class PgVectorStoreUpsertSqlTest(unittest.TestCase):
    """Test that upsert SQL uses correct conflict target including asset_id."""

    def test_upsert_sql_includes_asset_id_in_conflict_target(self):
        """Verify ON CONFLICT includes asset_id to avoid collisions between asset chunks."""
        # Mock the connection to capture the SQL
        executed_sqls = []

        class MockCursor:
            def __init__(self):
                self.calls = []

            def execute(self, sql, params=None):
                executed_sqls.append((sql, params))
                # Simulate successful upsert
                self.rowcount = 1

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        class MockConnection:
            def cursor(self):
                return MockCursor()

            def commit(self):
                pass

            def rollback(self):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        config = PgVectorConfig(
            enabled=True,
            dsn="postgresql://localhost/test",
            table_name="zhongchi_embeddings",
        )
        store = PgVectorStore(config)

        # Patch _get_connection to return our mock
        with patch.object(store, "_get_connection", return_value=MockConnection()):
            with patch.object(store, "_ensure_table"):  # Skip table creation
                store.upsert(
                    chunks=["test chunk"],
                    embeddings=[[0.1] * 1536],
                    metadata=[
                        ChunkMetadata(
                            filename="asset.txt",
                            source_path="/path/asset.txt",
                            document_role="asset",
                            assigned_modules=["M1"],
                            chunk_index=0,
                            project_id=0,
                            file_id=0,
                            doc_type="asset",
                            asset_id=5,
                        )
                    ],
                )

        self.assertGreater(len(executed_sqls), 0)
        upsert_sql = executed_sqls[0][0]

        # Verify the conflict target includes asset_id
        self.assertIn("ON CONFLICT (project_id, file_id, doc_type, chunk_index, asset_id)", upsert_sql)
        # Verify the VALUES list includes asset_id (between file_id and title)
        self.assertIn("asset_id", upsert_sql)


if __name__ == "__main__":
    unittest.main()