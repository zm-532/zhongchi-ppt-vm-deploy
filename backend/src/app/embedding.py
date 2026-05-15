"""Embedding provider interface and implementations."""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Optional

import httpx


class EmbeddingProvider(ABC):
    """Abstract embedding provider interface."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per input text)
        """
        raise NotImplementedError

    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimension."""
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic hash-based embedding for testing without network or model dependencies.

    Produces fixed-dimension vectors from stable hash of input text.
    """

    DEFAULT_DIMENSION = 1536

    def __init__(self, dimension: Optional[int] = None):
        self._dimension = dimension or self.DEFAULT_DIMENSION

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            # Use SHA-256 for stable, deterministic hash
            hash_bytes = hashlib.sha256(text.encode("utf-8")).digest()
            # Convert hash bytes to floats in [-1, 1]
            values: list[float] = []
            for i in range(self._dimension):
                byte_val = hash_bytes[i % len(hash_bytes)]
                values.append((byte_val / 127.5) - 1.0)
            vectors.append(values)
        return vectors

    def dimensions(self) -> int:
        return self._dimension


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """
    OpenRouter-compatible embedding provider.

    Requires OPENROUTER_API_KEY and uses nvidia/llama-nemotron-embed-vl-1b-v2:free
    by default. Falls back to HashEmbeddingProvider if API key is not configured.
    """

    DEFAULT_MODEL = "nvidia/llama-nemotron-embed-vl-1b-v2:free"
    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_DIMENSION = 1536
    BATCH_SIZE = 32  # OpenRouter free tier rate limit mitigation

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        dimension: Optional[int] = None,
    ):
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self._model = model or os.environ.get("ZHONGCHI_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        self._base_url = base_url or os.environ.get("ZHONGCHI_EMBEDDING_BASE_URL", self.DEFAULT_BASE_URL)
        self._dimension = dimension or int(os.environ.get("ZHONGCHI_EMBEDDING_DIM", self.DEFAULT_DIMENSION))
        self._inferred_dim: Optional[int] = None

    def is_available(self) -> bool:
        """Return True only if API key is configured."""
        return bool(self._api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.is_available():
            raise RuntimeError(
                "OpenRouter embedding provider requires OPENROUTER_API_KEY environment variable. "
                "Falling back to HashEmbeddingProvider is recommended for testing."
            )

        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            embeddings = self._embed_batch(batch)
            all_embeddings.extend(embeddings)
        return all_embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "input": texts,  # OpenAI-compatible "input" field (array for batch)
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{self._base_url}/embeddings", json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"OpenRouter embedding API error: {response.status_code} {response.text}. "
                    f"Check ZHONGCHI_EMBEDDING_MODEL and ZHONGCHI_EMBEDDING_BASE_URL."
                )
            data = response.json()

        embeddings: list[list[float]] = []
        # Support both OpenAI-compatible response format: { "data": [{ "embedding": [...] }] }
        data_items = data.get("data", [])
        for item in data_items:
            embedding = item.get("embedding", [])
            if self._inferred_dim is None and embedding:
                self._inferred_dim = len(embedding)
            embeddings.append(embedding)

        return embeddings

    def dimensions(self) -> int:
        if self._inferred_dim:
            return self._inferred_dim
        return self._dimension


def create_embedding_provider(provider_type: Optional[str] = None) -> EmbeddingProvider:
    """
    Create an embedding provider based on configuration.

    Args:
        provider_type: "openrouter" to use OpenRouter, None defaults to HashEmbeddingProvider
                      unless ZHONGCHI_EMBEDDING_PROVIDER=openrouter is set.

    Returns:
        An EmbeddingProvider instance
    """
    env_provider = os.environ.get("ZHONGCHI_EMBEDDING_PROVIDER", "").lower()

    if provider_type == "openrouter" or env_provider == "openrouter":
        openrouter_provider = OpenRouterEmbeddingProvider()
        if openrouter_provider.is_available():
            return openrouter_provider
        # Fall through to hash if API key not configured

    return HashEmbeddingProvider()