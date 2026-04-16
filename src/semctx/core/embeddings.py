"""Embedding helpers."""

import hashlib
import json
import os
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from beartype import beartype

from semctx.core.embedding_provider import (
    EmbeddingProviderConfig,
    coerce_embedding_provider,
)

EmbeddingRequest = str | EmbeddingProviderConfig
EmbeddingFetcher = Callable[[list[str], EmbeddingRequest], list[list[float]]]


@beartype
def fetch_embeddings(texts: list[str], model: EmbeddingRequest) -> list[list[float]]:
    """Fetch embeddings for uncached texts."""
    if not texts:
        return []
    provider = coerce_embedding_provider(model)
    from litellm import embedding

    with _temporary_env(provider.env_overrides):
        if provider.provider_name == "vertex_ai":
            return _fetch_vertex_embeddings(texts, provider.litellm_model, embedding)
        response = embedding(model=provider.litellm_model, input=texts)
    vectors = _extract_embedding_vectors(response)
    if len(vectors) != len(texts):
        raise ValueError("Embedding response length did not match the input length.")
    return vectors


@beartype
def get_cached_embeddings(
    cache_dir: Path,
    model: EmbeddingRequest,
    texts: list[str],
    fetcher: EmbeddingFetcher = fetch_embeddings,
) -> list[list[float]]:
    """Load embeddings from cache and fetch any misses."""
    if not texts:
        return []
    provider = coerce_embedding_provider(model)
    resolved_cache_dir = (cache_dir / "embeddings" / provider.cache_namespace).resolve()
    resolved_cache_dir.mkdir(parents=True, exist_ok=True)
    vectors_by_text: dict[str, list[float]] = {}
    missing_texts: list[str] = []
    for text in dict.fromkeys(texts):
        cache_path = _build_cache_path(resolved_cache_dir, text)
        if cache_path.exists():
            vectors_by_text[text] = _read_cached_embedding(cache_path)
            continue
        missing_texts.append(text)
    if missing_texts:
        fetched_vectors = fetcher(missing_texts, model)
        if len(fetched_vectors) != len(missing_texts):
            raise ValueError(
                "Embedding fetcher returned an unexpected number of vectors."
            )
        for text, vector in zip(missing_texts, fetched_vectors, strict=True):
            normalized_vector = _normalize_embedding(vector)
            _write_cached_embedding(
                _build_cache_path(resolved_cache_dir, text), normalized_vector
            )
            vectors_by_text[text] = normalized_vector
    return [vectors_by_text[text] for text in texts]


@beartype
def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for two vectors."""
    if len(left) != len(right):
        raise ValueError("Cosine similarity requires vectors of equal length.")
    dot_product = sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=True)
    )
    left_norm = sum(value * value for value in left) ** 0.5
    right_norm = sum(value * value for value in right) ** 0.5
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot_product / (left_norm * right_norm)


@contextmanager
def _temporary_env(overrides: dict[str, str]):
    """Apply environment overrides only within the wrapped scope."""
    previous = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
                continue
            os.environ[key] = value


def _build_cache_path(cache_dir: Path, text: str) -> Path:
    """Build the cache path for one input text."""
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return cache_dir / f"{text_hash}.json"


def _fetch_vertex_embeddings(
    texts: list[str],
    litellm_model: str,
    embedding: Callable[..., Any],
) -> list[list[float]]:
    """Fetch Vertex embeddings one text at a time."""
    vectors: list[list[float]] = []
    for text in texts:
        response = embedding(model=litellm_model, input=[text])
        response_vectors = _extract_embedding_vectors(response)
        if len(response_vectors) != 1:
            raise ValueError(
                "Vertex embedding response length did not match the single input length."
            )
        vectors.append(response_vectors[0])
    return vectors


def _extract_embedding_vectors(response: object) -> list[list[float]]:
    """Extract all embedding vectors from a LiteLLM response payload."""
    response_data = getattr(response, "data", None)
    if not isinstance(response_data, list):
        raise ValueError("Embedding response did not contain a data list.")
    return [_extract_embedding_vector(item) for item in response_data]


def _extract_embedding_vector(item: object) -> list[float]:
    """Extract one embedding vector from a LiteLLM response item."""
    embedding = (
        _get_dict_embedding(item)
        if isinstance(item, dict)
        else getattr(item, "embedding", None)
    )
    return _normalize_embedding(embedding)


def _get_dict_embedding(item: dict[Any, Any]) -> object:
    """Read an embedding value from a dictionary payload."""
    return item.get("embedding")


def _normalize_embedding(vector: object) -> list[float]:
    """Normalize a vector to a float list."""
    if not isinstance(vector, list | tuple):
        raise ValueError("Embedding vector must be a list or tuple.")
    normalized: list[float] = []
    for value in vector:
        if not isinstance(value, int | float | str):
            raise ValueError(f"Unsupported embedding value: {value!r}")
        normalized.append(float(value))
    return normalized


def _read_cached_embedding(cache_path: Path) -> list[float]:
    """Read one cached embedding vector from disk."""
    payload = json.loads(cache_path.read_text())
    if not isinstance(payload, dict) or not isinstance(payload.get("embedding"), list):
        raise ValueError(f"Invalid embedding cache payload: {cache_path}")
    return _normalize_embedding(payload["embedding"])


def _write_cached_embedding(cache_path: Path, vector: list[float]) -> None:
    """Write one embedding vector to disk."""
    cache_path.write_text(json.dumps({"embedding": vector}))
