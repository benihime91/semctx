# semctx

[![Codecov](https://codecov.io/gh/benihime91/semctx/graph/badge.svg)](https://app.codecov.io/gh/benihime91/semctx) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A semantic codebase discovery and search CLI. It provides repository discovery, indexed semantic search, and blast-radius analysis.

> [!NOTE]
> This project start as a full rewrite of the [Context+ project](https://github.com/ForLoopCodes/contextplus) into a native Python CLI.

## Table of contents

- [Installation](#installation)
  - [Embedding providers](#embedding-providers)
  - [Using SKILL.md with AI agents](#using-skillmd-with-ai-agents)
    - [Cursor](#cursor)
    - [OpenCode](#opencode)
    - [Codex](#codex-openai)
    - [Claude Code](#claude-code)
- [Quick Start](#quick-start)
  - [First commands](#first-commands)
  - [Scope model](#scope-model)
- [Supported Languages](#supported-languages)
- [Supported Commands](#supported-commands)
  - [Discovery (Tree & Skeleton)](#discovery-tree-skeleton)
  - [Semantic Search](#semantic-search)
  - [Index lifecycle](#index-lifecycle)
  - [Blast radius](#blast-radius)
- [Development checks](#development-checks)

## Installation

This section covers the full setup path: install the `semctx` CLI, configure **embedding providers** (including Ollama, Gemini, and Vertex env vars), then **install the agent skill** so Cursor, OpenCode, Codex, or Claude Code pick up `SKILL.md` from the right path. **Quick Start** is only first commands and scope.

Install `semctx` as a `uv` tool from GitHub:

```bash
# Install from the GitHub repo
uv tool install git+https://github.com/benihime91/semctx.git

# Install a tagged release
uv tool install git+https://github.com/benihime91/semctx.git@v0.1.0
```

### Embedding providers

`semctx` treats `--model provider/model` as the canonical embedding selector for embedding-aware commands (via `litellm`). Use the full provider-prefixed string everywhere you override embeddings.

Supported examples:

- `ollama/nomic-embed-text-v2-moe:latest`
- `gemini/gemini-embedding-2-preview`
- `vertex_ai/gemini-embedding-2-preview`

| Provider example                        | Required setup                                                                                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ollama/nomic-embed-text-v2-moe:latest` | Install Ollama, start the local Ollama service, and pull the embedding model before running `semctx`.                                                               |
| `gemini/gemini-embedding-2-preview`     | Export `GEMINI_API_KEY` in the shell, CI job, or agent runtime that will execute `semctx`.                                                                          |
| `vertex_ai/gemini-embedding-2-preview`  | Export `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, and `VERTEX_LOCATION`. Use a runtime with semctx's LiteLLM and Google auth dependencies available. |

For `vertex_ai`, semctx normalizes an unset or `global` `VERTEX_LOCATION` to `us-central1` for LiteLLM's Vertex path.

If you expect an AI agent to call semctx repeatedly, do not leave the default model implicit. Put the chosen `provider/model` and its setup notes in `SKILL.md`, then have the agent use that default unless the task explicitly asks for another model.

```bash
# Local Ollama embeddings
semctx --target-dir "backend/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"
semctx --target-dir "backend/" --cache-dir ".semctx" search-code "retry policy" --model "ollama/nomic-embed-text-v2-moe:latest"

# Vertex AI embeddings (use a separate cache dir if you switch providers)
semctx --target-dir "backend/" --cache-dir ".semctx-vertex" index init --model "vertex_ai/gemini-embedding-2-preview"
semctx --target-dir "backend/" --cache-dir ".semctx-vertex" search-code "retry policy" --model "vertex_ai/gemini-embedding-2-preview"
```

Install commands and environment variables for each backend are in the sections below — **three separate collapsibles**, each **collapsed by default** on GitHub (expand the one you need).

**Ollama embeddings** — install, `ollama pull`, optional `OLLAMA_API_BASE`

### Ollama embeddings

If your default `--model` uses the `ollama/` prefix (for example `ollama/nomic-embed-text-v2-moe:latest`), install and run [Ollama](https://ollama.com/) on the same machine (or network-reachable host) that will execute `semctx`, then pull the **exact** embedding model name you pass to `--model`:

```bash
# Install Ollama (see https://ollama.com/download for installers and package managers)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the embedding weights semctx will request via LiteLLM
ollama pull nomic-embed-text-v2-moe:latest
```

Keep the Ollama daemon running while indexing or searching (`ollama serve` runs in the background on most installs). No API key is required for a local server on the default address.

Optional environment variables (only when your Ollama API is not on the default host or port):

```bash
# LiteLLM / semctx: override the Ollama OpenAI-compatible base URL if needed
export OLLAMA_API_BASE="http://127.0.0.1:11434"
```

**Gemini embeddings** — `GEMINI_API_KEY`

### Gemini embeddings

If your default `--model` uses the `gemini/` prefix, set an API key in every shell, CI job, or agent runtime that runs `semctx`:

```bash
export GEMINI_API_KEY="your-api-key"
```

**Vertex AI embeddings** — `GOOGLE_`\_ / `VERTEX\__` env vars

### Vertex AI embeddings

If your default `--model` uses the `vertex_ai/` prefix, point LiteLLM at Google Cloud with application-default credentials (or a service account) plus project and region. `semctx` maps these into the env names LiteLLM expects; unset or `global` `VERTEX_LOCATION` is normalized to `us-central1`.

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project"
export VERTEX_LOCATION="us-central1"
```

### Using `SKILL.md` with AI agents

> [!WARNING]
> After you install the skill, edit the `SKILL.md` you copied into your tool’s skill directory and **align it with your current preferences**: default `--model` (`provider/model`), embedding **provider** choice, `--cache-dir` convention, and any provider-specific environment variables or setup notes. The upstream file uses placeholders; agents will not reliably call `semctx` until those sections match your runtime.

This repo’s root `SKILL.md` is the canonical agent guide. Most tools expect **one directory per skill** with a `SKILL.md` inside (not a lone file in the repo root). Download the latest upstream copy like this, then move it into the path your tool lists below:

```bash
curl -fsSL -o /tmp/semctx-SKILL.md https://raw.githubusercontent.com/benihime91/semctx/refs/heads/main/SKILL.md
```

On every platform, after the file is in place, edit **Default model configuration** (and any provider env notes) so they match the user’s embedding backend—placeholders will not work for real runs.

Shared expectations for agents:

- make `semctx` available on `PATH`
- prefer `semctx --json` for programmatic and agent-driven calls
- pass `--target-dir` to define the content scope for indexing and search
- pass `--cache-dir` to control where `index.db` and embedding artifacts live
- configure a default model in the skill (or in `AGENTS.md` / `CLAUDE.md` where applicable), then pass overrides only as `--model provider/model`

Your AI agents should use that configured default model for `index init`, `index refresh`, `search-code`, and `search-identifiers` unless you explicitly override it with `--model provider/model`.

#### Cursor

<details>
<summary>Cursor</summary>
- **Project (committed):** `.cursor/skills/<skill-name>/SKILL.md` — for example `.cursor/skills/semctx/SKILL.md`.
- **Personal:** `~/.cursor/skills/<skill-name>/SKILL.md` so the skill applies across workspaces.

Copy or move `/tmp/semctx-SKILL.md` into that `SKILL.md` path (create the folders first). Cursor loads project skills from `.cursor/skills/`; see Cursor’s **create-skill** / Agent Skills docs for layout and frontmatter conventions.

</details>

#### OpenCode

<details>
<summary>OpenCode</summary>
OpenCode discovers standard layout skills from several locations (see [Agent skills](https://opencode.ai/docs/skills/)):

- **Project:** `.opencode/skills/<skill-name>/SKILL.md` (recommended), or compatible trees `.claude/skills/<skill-name>/SKILL.md`, `.agents/skills/<skill-name>/SKILL.md` under the repo.
- **Global:** `~/.config/opencode/skills/<skill-name>/SKILL.md`, or `~/.claude/skills/`, `~/.agents/skills/` for user-wide skills.

Place the downloaded `SKILL.md` under a new folder such as `semctx`. OpenCode loads skills on demand via its `skill` tool; if a skill does not appear, confirm the directory name, frontmatter `name` / `description`, and `[opencode.json` skill permissions](https://opencode.ai/docs/skills/).

</details>

#### Codex (OpenAI)

<details>
<summary>Codex (OpenAI)</summary>
Codex uses the Agent Skills layout for reusable workflows (see [Customization: skills](https://developers.openai.com/codex/concepts/customization/) and [Create a skill](https://developers.openai.com/codex/skills/create-skill)):

- **Project (team):** `.agents/skills/<skill-name>/SKILL.md` in the repository.
- **Personal:** `~/.agents/skills/<skill-name>/SKILL.md` for defaults on your machine.

Copy the downloaded file into `SKILL.md` inside that folder. For durable repo-wide instructions (build commands, conventions, **when** to call semctx), also maintain a root `**AGENTS.md`\*\*; Codex reads it automatically in addition to skills. In the CLI you can scaffold with `/init`, then merge in semctx-specific guidance.

</details>

#### Claude Code

<details>
<summary>Claude Code</summary>
Claude Code loads skills from project or user scope (see [Explore the `.claude` directory](https://code.claude.com/docs/en/claude-directory)):

- **Project (committed):** `.claude/skills/<skill-name>/SKILL.md`.
- **Personal:** `~/.claude/skills/<skill-name>/SKILL.md`.

Optional: add or extend root `**CLAUDE.md`\*\* for session-wide project context (build, architecture) alongside the skill. After installing, run `/skills` in a session to confirm the skill is listed.

</details>

## Quick Start

`index`, `search-code`, and `search-identifiers` need a working embedding backend. Complete [Installation](#installation) (including [Embedding providers](#embedding-providers)) first, then run [First commands](#first-commands).

### First commands

Explore a repository subtree and its semantics:

```bash
# Build the local index for the directory you want to search
semctx --target-dir "backend/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"

# View the structural tree of that directory
semctx tree backend/ --depth-limit 2

# Search indexed code and docs by meaning
semctx --target-dir "backend/" --cache-dir ".semctx" search-code "user authentication" --model "ollama/nomic-embed-text-v2-moe:latest"
```

Use `--json` before the command when you want machine-readable output:

```bash
semctx --json tree backend/ --depth-limit 2
semctx --json --target-dir "backend/" --cache-dir ".semctx" search-code "user authentication" --model "ollama/nomic-embed-text-v2-moe:latest"
```

### Scope model

- `--target-dir` is the only content scope. It is the directory whose files are indexed and searched.
- `--cache-dir` is only where `semctx` stores `index.db` and related artifacts.
- `--depth-limit` is optional narrowing for traversal-heavy commands. It does not change scope identity.

If you want to search only `backend/`, point `--target-dir` at `backend/`. Files outside that directory, such as a repo-root `README.md`, are outside scope.

## Supported Languages

`semctx` uses [tree-sitter](https://tree-sitter.github.io/tree-sitter/) grammars to parse files and extract symbols for discovery, chunking, indexing, and blast-radius analysis.

| Language   | Extensions    | Extracted symbols                                                               |
| ---------- | ------------- | ------------------------------------------------------------------------------- |
| Python     | `.py`         | functions, classes                                                              |
| TypeScript | `.ts`, `.tsx` | functions, classes, interfaces, types, enums, `const` bindings                  |
| JavaScript | `.js`, `.jsx` | functions, classes, `const` bindings                                            |
| Go         | `.go`         | functions, methods, struct and interface types                                  |
| Rust       | `.rs`         | functions, structs, enums, traits, impl blocks, types, consts, modules, statics |
| Kotlin     | `.kt`, `.kts` | functions, classes, interfaces, objects, properties                             |

Files with other extensions are still indexed as plain text for semantic search when included in scope, but symbol-level features (tree, skeleton, blast-radius, symbol-aligned chunks) apply only to the languages above.

## Supported Commands

`semctx` is organized into several capability areas. The currently supported commands and subcommands are:

- **Discovery:** `tree`, `skeleton`
- **Index Lifecycle:** `index` (`init`, `status`, `refresh`, `clear`)
- **Semantic Search:** `search-code`, `search-identifiers`
- **Analysis:** `blast-radius`

| Command              | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| `tree`               | View the structural tree of a directory including symbols       |
| `skeleton`           | View the API surface of a file without its full body            |
| `index`              | Build, inspect, refresh, or clear the local SQLite search index |
| `search-code`        | Search the codebase by semantic meaning                         |
| `search-identifiers` | Search functions and classes by semantic intent                 |
| `blast-radius`       | Trace symbol usage across the codebase                          |

### Discovery (Tree & Skeleton)

Understand file structure and API surfaces without reading full implementations.

```bash
# Show file headers, functions, and classes
semctx tree backend/ --include-symbols

# View the API surface of a specific file
semctx skeleton backend/payments/service.py
```

### Semantic Search

Search your indexed codebase by meaning. Embeddings are provided via `litellm` and cached locally to avoid redundant API calls.

```bash
# Find files related to a concept
semctx --target-dir "backend/" --cache-dir ".semctx" search-code "how are transactions signed" --model "ollama/nomic-embed-text-v2-moe:latest"

# Search by identifier intent
semctx --target-dir "backend/" --cache-dir ".semctx" search-identifiers "password hashing" --model "ollama/nomic-embed-text-v2-moe:latest"
```

Normal search runs recover the local index when the safe fix is obvious:

- Missing index: `search-code` and `search-identifiers` automatically build it first.
- Stale index from file changes: both commands automatically run an incremental refresh.
- Incompatible index metadata: search stops and tells you to run `semctx index refresh --full`.

You can still manage lifecycle state explicitly with the `index` commands when you want to inspect or control the rebuild step yourself.

Choose a `provider/model`, set up the provider environment, and use consistent `--model` and `--cache-dir` values as described in [Embedding providers](#embedding-providers) under Installation.

### Index Lifecycle

The indexed search flow is explicit. Use `--target-dir` to choose what content belongs in the index and `--cache-dir` to choose where the index artifacts live:

```bash
# Create the SQLite index for backend/
semctx --target-dir "backend/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"

# Inspect whether the index is ready, stale, or needs rebuild
semctx --target-dir "backend/" --cache-dir ".semctx" index status --model "ollama/nomic-embed-text-v2-moe:latest"

# Apply incremental updates for added, changed, or removed files
semctx --target-dir "backend/" --cache-dir ".semctx" index refresh --model "ollama/nomic-embed-text-v2-moe:latest"

# Rebuild from scratch when metadata changes require it
semctx --target-dir "backend/" --cache-dir ".semctx" index refresh --full --model "ollama/nomic-embed-text-v2-moe:latest"

# Remove the local index database
semctx --cache-dir ".semctx" index clear
```

Lifecycle behavior:

- `index init` discovers supported code plus v1 markdown/text files under `target_dir`, chunks them, computes embeddings, and stores the SQLite index in `cache_dir`.
- `index status` reports whether the index exists, whether it is stale, and whether a full rebuild is required, using the canonical `provider/model` selector in human-facing output.
- A **stale** index means file-level changes were detected and `index refresh` can update only the changed set.
- A **rebuild required** status means structural metadata changed, such as provider/model or ignore-fingerprint changes, so you must run `index refresh --full`.
- Search commands reuse that lifecycle policy automatically: they auto-build missing indexes, auto-refresh stale ones, and still stop on rebuild-required states.
- `index clear` deletes the local index in `cache_dir` so the next search or refresh starts from a clean state.

### Blast Radius

Trace symbol usage across your codebase before deleting or refactoring.

```bash
# Find every usage of 'fetch_embedding' outside of its defining file
semctx blast-radius fetch_embedding src/semctx/core/embeddings.py
```

## Development checks

Install dev dependencies and wire up the local git hooks:

```bash
uv sync --dev
pre-commit install
```

Validate the hook config or run the approved fast-core profile on demand:

```bash
pre-commit validate-config
pre-commit run --all-files
ruff check src/semctx
ty check src/semctx
python -m compileall "src/semctx"
```

The pre-commit profile stays intentionally small: fast file-hygiene hooks, Astral's official `uv-lock` hook, plus local `ruff check src/semctx`, `ty check src/semctx`, and `python -m compileall "src/semctx"` checks.
