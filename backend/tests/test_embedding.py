"""Tests for embedding providers."""

import os
import unittest

from app.embedding import (
    HashEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    create_embedding_provider,
)


class HashEmbeddingTest(unittest.TestCase):
    def test_hash_embedding_returns_correct_dimension(self):
        provider = HashEmbeddingProvider(dimension=1536)
        self.assertEqual(provider.dimensions(), 1536)

    def test_hash_embedding_returns_fixed_dimension(self):
        provider = HashEmbeddingProvider(dimension=256)
        embeddings = provider.embed(["test text"])
        self.assertEqual(len(embeddings[0]), 256)

    def test_hash_embedding_is_deterministic(self):
        provider = HashEmbeddingProvider()
        text = "This is a test string"
        result1 = provider.embed([text])
        result2 = provider.embed([text])
        self.assertEqual(result1, result2)

    def test_hash_embedding_different_texts_different_vectors(self):
        provider = HashEmbeddingProvider()
        result1 = provider.embed(["text one"])
        result2 = provider.embed(["text two"])
        self.assertNotEqual(result1, result2)

    def test_hash_embedding_single_and_batch_consistent(self):
        provider = HashEmbeddingProvider()
        single = provider.embed(["single text"])
        batch = provider.embed(["single text"])
        self.assertEqual(single, batch)

    def test_hash_embedding_values_in_range(self):
        provider = HashEmbeddingProvider()
        embeddings = provider.embed(["some test content"])
        for val in embeddings[0]:
            self.assertGreaterEqual(val, -1.0)
            self.assertLessEqual(val, 1.0)

    def test_hash_embedding_empty_list(self):
        provider = HashEmbeddingProvider()
        result = provider.embed([])
        self.assertEqual(result, [])


class OpenRouterProviderTest(unittest.TestCase):
    def test_openrouter_not_available_without_api_key(self):
        # Ensure no API key in environment
        old_key = os.environ.pop("OPENROUTER_API_KEY", None)
        try:
            provider = OpenRouterEmbeddingProvider()
            self.assertFalse(provider.is_available())
        finally:
            if old_key:
                os.environ["OPENROUTER_API_KEY"] = old_key

    def test_openrouter_is_available_with_api_key(self):
        old_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        try:
            provider = OpenRouterEmbeddingProvider()
            self.assertTrue(provider.is_available())
        finally:
            if old_key is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = old_key


class CreateProviderTest(unittest.TestCase):
    def test_default_creates_hash_provider(self):
        # Ensure no openrouter config
        old_env = os.environ.get("ZHONGCHI_EMBEDDING_PROVIDER")
        old_key = os.environ.get("OPENROUTER_API_KEY")
        if "ZHONGCHI_EMBEDDING_PROVIDER" in os.environ:
            del os.environ["ZHONGCHI_EMBEDDING_PROVIDER"]
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
        try:
            provider = create_embedding_provider()
            self.assertIsInstance(provider, HashEmbeddingProvider)
        finally:
            if old_env is not None:
                os.environ["ZHONGCHI_EMBEDDING_PROVIDER"] = old_env
            if old_key is not None:
                os.environ["OPENROUTER_API_KEY"] = old_key

    def test_openrouter_type_creates_openrouter_provider(self):
        old_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["OPENROUTER_API_KEY"] = "test-key"
        try:
            provider = create_embedding_provider("openrouter")
            self.assertIsInstance(provider, OpenRouterEmbeddingProvider)
        finally:
            if old_key is None:
                os.environ.pop("OPENROUTER_API_KEY", None)
            else:
                os.environ["OPENROUTER_API_KEY"] = old_key

    def test_env_openrouter_falls_back_to_hash_without_key(self):
        old_provider = os.environ.get("ZHONGCHI_EMBEDDING_PROVIDER")
        old_key = os.environ.get("OPENROUTER_API_KEY")
        os.environ["ZHONGCHI_EMBEDDING_PROVIDER"] = "openrouter"
        if "OPENROUTER_API_KEY" in os.environ:
            del os.environ["OPENROUTER_API_KEY"]
        try:
            provider = create_embedding_provider()
            # Falls back to hash when API key is missing
            self.assertIsInstance(provider, HashEmbeddingProvider)
        finally:
            if old_provider is None:
                os.environ.pop("ZHONGCHI_EMBEDDING_PROVIDER", None)
            else:
                os.environ["ZHONGCHI_EMBEDDING_PROVIDER"] = old_provider
            if old_key is not None:
                os.environ["OPENROUTER_API_KEY"] = old_key


if __name__ == "__main__":
    unittest.main()