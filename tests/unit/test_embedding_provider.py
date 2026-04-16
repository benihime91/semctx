# Embedding provider unit tests.
# FEATURE: Ollama and Gemini provider resolution.
from pathlib import Path

import pytest

from semctx.core.embedding_provider import (
    EmbeddingProviderConfig,
    coerce_embedding_provider,
    get_vertex_env_overrides,
    resolve_requested_embedding_provider,
    resolve_embedding_provider,
)
from semctx.core.embeddings import get_cached_embeddings


def test_resolve_embedding_provider_supports_ollama_and_gemini() -> None:
    ollama = resolve_embedding_provider("ollama")
    gemini = resolve_embedding_provider("gemini")

    assert ollama == EmbeddingProviderConfig(
        provider_name="ollama",
        model="nomic-embed-text-v2-moe:latest",
        litellm_model="ollama/nomic-embed-text-v2-moe:latest",
        cache_namespace="ollama_nomic-embed-text-v2-moe_latest",
        env_overrides={},
    )
    assert gemini == EmbeddingProviderConfig(
        provider_name="gemini",
        model="gemini-embedding-2-preview",
        litellm_model="gemini/gemini-embedding-2-preview",
        cache_namespace="gemini_gemini-embedding-2-preview",
        env_overrides={},
    )


def test_resolve_embedding_provider_uses_explicit_model_override() -> None:
    provider = resolve_embedding_provider("gemini", "custom-model")

    assert provider.model == "custom-model"
    assert provider.litellm_model == "gemini/custom-model"
    assert provider.cache_namespace == "gemini_custom-model"
    assert provider.env_overrides == {}


def test_resolve_embedding_provider_supports_vertex_ai(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "app-dashtoon")
    monkeypatch.setenv("VERTEX_LOCATION", "global")

    provider = resolve_embedding_provider("vertex_ai")

    assert provider.provider_name == "vertex_ai"
    assert provider.model == "gemini-embedding-2-preview"
    assert provider.litellm_model == "vertex_ai/gemini-embedding-2-preview"
    assert provider.cache_namespace == "vertex_ai_gemini-embedding-2-preview"
    assert provider.env_overrides["VERTEXAI_PROJECT"] == "app-dashtoon"
    assert provider.env_overrides["VERTEX_AI_PROJECT"] == "app-dashtoon"
    assert provider.env_overrides["VERTEXAI_LOCATION"] == "us-central1"
    assert provider.env_overrides["VERTEX_AI_LOCATION"] == "us-central1"


def test_resolve_embedding_provider_keeps_vertex_model_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERTEXAI_PROJECT", "project-123")
    monkeypatch.setenv("VERTEXAI_LOCATION", "europe-west4")

    provider = resolve_embedding_provider("vertex_ai", "custom-vertex-model")

    assert provider.model == "custom-vertex-model"
    assert provider.litellm_model == "vertex_ai/custom-vertex-model"
    assert provider.env_overrides["VERTEXAI_PROJECT"] == "project-123"
    assert provider.env_overrides["VERTEXAI_LOCATION"] == "europe-west4"


def test_get_vertex_env_overrides_normalizes_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VERTEX_AI_PROJECT", "alias-project")
    monkeypatch.setenv("VERTEX_AI_LOCATION", "global")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/creds.json")

    overrides = get_vertex_env_overrides()

    assert overrides == {
        "VERTEXAI_PROJECT": "alias-project",
        "VERTEX_AI_PROJECT": "alias-project",
        "VERTEXAI_LOCATION": "us-central1",
        "VERTEX_AI_LOCATION": "us-central1",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/creds.json",
    }


def test_coerce_embedding_provider_keeps_legacy_raw_models() -> None:
    provider = coerce_embedding_provider("text-embedding-3-small")

    assert provider.provider_name == "raw"
    assert provider.model == "text-embedding-3-small"
    assert provider.litellm_model == "text-embedding-3-small"
    assert provider.env_overrides == {}


def test_resolve_requested_embedding_provider_uses_provider_prefixed_model() -> None:
    provider = resolve_requested_embedding_provider(
        provider_name=None,
        model="vertex_ai/gemini-embedding-2-preview",
        default_provider="ollama",
    )

    assert provider.provider_name == "vertex_ai"
    assert provider.model == "gemini-embedding-2-preview"
    assert provider.litellm_model == "vertex_ai/gemini-embedding-2-preview"


def test_resolve_requested_embedding_provider_prefers_model_prefix_over_provider() -> (
    None
):
    provider = resolve_requested_embedding_provider(
        provider_name="ollama",
        model="vertex_ai/custom-model",
        default_provider="ollama",
    )

    assert provider.provider_name == "vertex_ai"
    assert provider.model == "custom-model"


def test_get_cached_embeddings_uses_provider_config_cache_namespace(
    tmp_path: Path,
) -> None:
    provider = resolve_embedding_provider("ollama", "custom-model")
    captured_models: list[EmbeddingProviderConfig | str] = []

    def fake_fetch_embeddings(
        texts: list[str], model: EmbeddingProviderConfig | str
    ) -> list[list[float]]:
        captured_models.append(model)
        return [[float(index + 1)] for index, _ in enumerate(texts)]

    vectors = get_cached_embeddings(
        cache_dir=tmp_path,
        model=provider,
        texts=["alpha", "beta"],
        fetcher=fake_fetch_embeddings,
    )

    assert vectors == [[1.0], [2.0]]
    assert captured_models == [provider]
    assert (tmp_path / "embeddings" / "ollama_custom-model").exists() is True


def test_resolve_embedding_provider_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        resolve_embedding_provider("unknown")
