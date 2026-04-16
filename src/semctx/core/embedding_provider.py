"""Embedding provider resolution helpers."""

import os
from dataclasses import dataclass, field

from beartype import beartype


_DEFAULT_MODELS = {
  "ollama": "nomic-embed-text-v2-moe:latest",
  "gemini": "gemini-embedding-2-preview",
  "vertex_ai": "gemini-embedding-2-preview",
}

VERTEX_SAFE_DEFAULT_LOCATION = "us-central1"


@beartype
@dataclass(frozen=True)
class EmbeddingProviderConfig:
  """Describe one resolved embedding provider configuration."""

  provider_name: str
  model: str
  litellm_model: str
  cache_namespace: str
  env_overrides: dict[str, str] = field(default_factory=dict)


@beartype
def resolve_embedding_provider(name: str, model: str | None = None) -> EmbeddingProviderConfig:
  """Resolve a supported provider name and model into config."""
  provider_name = name.strip().lower()
  if provider_name not in _DEFAULT_MODELS:
    raise ValueError(f"Unsupported embedding provider: {name}")
  resolved_model = model.strip() if isinstance(model, str) else _DEFAULT_MODELS[provider_name]
  if not resolved_model:
    raise ValueError("Embedding model cannot be empty.")
  return EmbeddingProviderConfig(
    provider_name=provider_name,
    model=resolved_model,
    litellm_model=f"{provider_name}/{resolved_model}",
    cache_namespace=f"{provider_name}_{_slugify(resolved_model)}",
    env_overrides=(get_vertex_env_overrides() if provider_name == "vertex_ai" else {}),
  )


@beartype
def get_vertex_env_overrides() -> dict[str, str]:
  """Normalize user Vertex settings into LiteLLM-compatible env vars."""
  project = _first_env_value("VERTEXAI_PROJECT", "VERTEX_AI_PROJECT", "GOOGLE_CLOUD_PROJECT")
  location = _normalize_vertex_location(_first_env_value("VERTEXAI_LOCATION", "VERTEX_AI_LOCATION", "VERTEX_LOCATION"))
  credentials = _first_env_value("GOOGLE_APPLICATION_CREDENTIALS")
  overrides: dict[str, str] = {
    "VERTEXAI_LOCATION": location,
    "VERTEX_AI_LOCATION": location,
  }
  if project:
    overrides["VERTEXAI_PROJECT"] = project
    overrides["VERTEX_AI_PROJECT"] = project
  if credentials:
    overrides["GOOGLE_APPLICATION_CREDENTIALS"] = credentials
  return overrides


@beartype
def coerce_embedding_provider(
  provider: EmbeddingProviderConfig | str,
) -> EmbeddingProviderConfig:
  """Normalize either a config object or provider string."""
  if isinstance(provider, EmbeddingProviderConfig):
    return provider
  raw_model = provider.strip()
  if not raw_model:
    raise ValueError("Embedding model cannot be empty.")
  provider_name, model_name = _split_provider_model(raw_model)
  if provider_name is None:
    return EmbeddingProviderConfig(
      provider_name="raw",
      model=raw_model,
      litellm_model=raw_model,
      cache_namespace=_slugify(raw_model),
      env_overrides={},
    )
  return resolve_embedding_provider(provider_name, model_name)


@beartype
def resolve_requested_embedding_provider(
  provider_name: str | None,
  model: str | None,
  default_provider: str | None = None,
) -> EmbeddingProviderConfig:
  """Resolve CLI provider/model inputs with provider-prefixed models as canonical."""
  raw_model = model.strip() if isinstance(model, str) else ""
  if raw_model:
    resolved_from_model = coerce_embedding_provider(raw_model)
    if resolved_from_model.provider_name != "raw":
      return resolved_from_model
    resolved_provider_name = (provider_name.strip() if isinstance(provider_name, str) else "") or (default_provider.strip() if isinstance(default_provider, str) else "")
    if not resolved_provider_name:
      raise ValueError("Embedding provider is required when --model does not include provider/model.")
    return resolve_embedding_provider(resolved_provider_name, raw_model)
  resolved_provider_name = (provider_name.strip() if isinstance(provider_name, str) else "") or (default_provider.strip() if isinstance(default_provider, str) else "")
  if not resolved_provider_name:
    raise ValueError("Embedding provider or model is required.")
  return resolve_embedding_provider(resolved_provider_name)


def _first_env_value(*names: str) -> str:
  """Return the first non-empty environment value for the given names."""
  for name in names:
    value = os.getenv(name, "").strip()
    if value:
      return value
  return ""


def _normalize_vertex_location(location: str) -> str:
  """Return a deterministic Vertex-safe location."""
  normalized = location.strip().lower()
  if not normalized or normalized == "global":
    return VERTEX_SAFE_DEFAULT_LOCATION
  return normalized


def _split_provider_model(value: str) -> tuple[str | None, str | None]:
  """Split a provider/model string when the provider is supported."""
  if "/" not in value:
    return None, None
  provider_name, model_name = value.split("/", maxsplit=1)
  normalized_provider = provider_name.strip().lower()
  if normalized_provider not in _DEFAULT_MODELS:
    return None, None
  return normalized_provider, model_name.strip() or None


def _slugify(value: str) -> str:
  """Build a filesystem-safe cache namespace fragment."""
  return value.replace("/", "_").replace(":", "_").replace(" ", "_")
