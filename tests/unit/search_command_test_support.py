# Search command unit-test helpers.
# FEATURE: Shared fixtures for search command tests.
from pathlib import Path
from typing import Callable

import pytest


def write_project(root_dir: Path) -> None:
  (root_dir / "app").mkdir(parents=True)
  (root_dir / "src").mkdir(parents=True)
  (root_dir / "app" / "main.py").write_text(
    'class Greeter:\n    def greet(self) -> str:\n        return "hi"\n',
    encoding="utf-8",
  )
  (root_dir / "src" / "widget.ts").write_text(
    "export function buildWidget(id: string): string {\n  return id;\n}\n",
    encoding="utf-8",
  )


def use_real_index_recovery(
  monkeypatch: pytest.MonkeyPatch,
  command_module: object,
  ensure_search_ready_index: Callable[..., object],
) -> None:
  monkeypatch.setattr(
    command_module,
    "ensure_search_ready_index",
    lambda **kwargs: ensure_search_ready_index(
      **kwargs,
      fetcher=fake_fetch_embeddings,
    ),
  )


def fake_fetch_embeddings(texts: list[str], model: object) -> list[list[float]]:
  del model
  return [[float(index + 1), float(len(text))] for index, text in enumerate(texts)]
