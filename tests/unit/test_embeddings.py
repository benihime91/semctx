# Embedding fetch unit tests.
# FEATURE: Vertex fallback preserves provider-specific safety.
import os
import sys
from types import SimpleNamespace

import pytest

from semctx.core.embedding_provider import resolve_embedding_provider
from semctx.core.embeddings import fetch_embeddings


def test_fetch_embeddings_applies_vertex_env_overrides_only_during_call(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "project-from-google")
  monkeypatch.setenv("VERTEX_LOCATION", "global")
  monkeypatch.setenv("VERTEXAI_PROJECT", "existing-project")
  monkeypatch.setenv("VERTEXAI_LOCATION", "existing-location")
  monkeypatch.delenv("VERTEX_AI_PROJECT", raising=False)
  monkeypatch.delenv("VERTEX_AI_LOCATION", raising=False)
  captured_env: dict[str, str | None] = {}

  def fake_embedding(*, model: str, input: list[str]) -> SimpleNamespace:
    assert model == "vertex_ai/gemini-embedding-2-preview"
    assert input == ["alpha"]
    captured_env.update(
      {
        "VERTEXAI_PROJECT": os.environ.get("VERTEXAI_PROJECT"),
        "VERTEXAI_LOCATION": os.environ.get("VERTEXAI_LOCATION"),
        "VERTEX_AI_PROJECT": os.environ.get("VERTEX_AI_PROJECT"),
        "VERTEX_AI_LOCATION": os.environ.get("VERTEX_AI_LOCATION"),
      }
    )
    return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 2.0])])

  monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(embedding=fake_embedding))

  vectors = fetch_embeddings(["alpha"], resolve_embedding_provider("vertex_ai"))

  assert vectors == [[1.0, 2.0]]
  assert captured_env == {
    "VERTEXAI_PROJECT": "existing-project",
    "VERTEXAI_LOCATION": "existing-location",
    "VERTEX_AI_PROJECT": "existing-project",
    "VERTEX_AI_LOCATION": "existing-location",
  }
  assert os.environ.get("VERTEXAI_PROJECT") == "existing-project"
  assert os.environ.get("VERTEXAI_LOCATION") == "existing-location"
  assert os.environ.get("VERTEX_AI_PROJECT") is None
  assert os.environ.get("VERTEX_AI_LOCATION") is None


def test_fetch_embeddings_uses_single_item_vertex_fallback(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  calls: list[list[str]] = []

  def fake_embedding(*, model: str, input: list[str]) -> SimpleNamespace:
    calls.append(input)
    assert model == "vertex_ai/gemini-embedding-2-preview"
    return SimpleNamespace(data=[SimpleNamespace(embedding=[float(len(input[0]))])])

  monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(embedding=fake_embedding))

  vectors = fetch_embeddings(
    ["alpha", "beta"],
    resolve_embedding_provider("vertex_ai"),
  )

  assert calls == [["alpha"], ["beta"]]
  assert vectors == [[5.0], [4.0]]


def test_fetch_embeddings_preserves_batch_length_validation_for_non_vertex(
  monkeypatch: pytest.MonkeyPatch,
) -> None:
  def fake_embedding(*, model: str, input: list[str]) -> SimpleNamespace:
    assert model == "ollama/nomic-embed-text-v2-moe:latest"
    assert input == ["alpha", "beta"]
    return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0])])

  monkeypatch.setitem(sys.modules, "litellm", SimpleNamespace(embedding=fake_embedding))

  with pytest.raises(
    ValueError,
    match="Embedding response length did not match the input length.",
  ):
    fetch_embeddings(["alpha", "beta"], resolve_embedding_provider("ollama"))
