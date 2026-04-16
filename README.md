# semctx

A semantic codebase discovery and search CLI.

`semctx` is a Python port of the core Context+ product. It provides repository discovery, indexed semantic search, and blast-radius analysis.

## Installation

Use `uv` for local development, or install `semctx` as a tool from GitHub:

```bash
# Local development: run directly in the project
uv run semctx --help

# Install from the GitHub repo
uv tool install git+https://github.com/benihime91/semctx.git

# Install a tagged release
uv tool install git+https://github.com/benihime91/semctx.git@v0.1.0
```

## Required: choose a default embedding model

Before you use indexed semctx commands through an LLM or AI agent, choose a
default embedding provider/model and make sure that provider is actually ready
in the runtime where the agent will call semctx.

This is required because `search-code`, `search-identifiers`, and the `index`
commands depend on embeddings. If the default model is unclear or the provider
environment is missing, agent-driven semctx calls will be unreliable.

### Supported provider/model examples

Use full `provider/model` strings with the shipped CLI:

- `ollama/nomic-embed-text-v2-moe:latest`
- `gemini/text-embedding-004`
- `vertex_ai/gemini-embedding-2-preview`

### Provider requirements

| Provider example                        | Required setup                                                                                                                                                      |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ollama/nomic-embed-text-v2-moe:latest` | Install Ollama, start the local Ollama service, and pull the embedding model before running `semctx`.                                                               |
| `gemini/text-embedding-004`             | Export `GEMINI_API_KEY` in the shell, CI job, or agent runtime that will execute `semctx`.                                                                          |
| `vertex_ai/gemini-embedding-2-preview`  | Export `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`, and `VERTEX_LOCATION`. Use a runtime with semctx's LiteLLM and Google auth dependencies available. |

For `vertex_ai`, semctx normalizes an unset or `global` `VERTEX_LOCATION` to
`us-central1` for LiteLLM's Vertex path.

### After install, customize `SKILL.md`

`SKILL.md` is the agent-facing guide. After installation, edit its
`Default model configuration` section and replace the placeholders with your
real defaults.

At minimum, set:

- your default `--model provider/model`
- your default `--cache-dir` convention
- the provider-specific requirements your agent runtime already satisfies

Your AI agents should use that configured default model for `index init`,
`index refresh`, `search-code`, and `search-identifiers` unless you explicitly
override it with `--model provider/model`.

### Using `SKILL.md` with AI agents

If your agent platform supports repo-local skill or instruction files, point it
at `SKILL.md` in the repository root.

The exact wiring depends on the agent framework, but the intended setup is:

- make `semctx` available on `PATH`, or run it through `uv run semctx`
- prefer `semctx --json` for programmatic and agent-driven calls
- pass `--target-dir` to define the content scope for indexing and search
- pass `--cache-dir` to control where `index.db` and embedding artifacts live
- configure a default model in `SKILL.md`, then pass overrides only as `--model provider/model`

Minimal agent-friendly examples:

```bash
# Search a scoped directory with machine-readable output
uv run semctx --json --target-dir "src/" --cache-dir ".semctx" search-code "index lifecycle" --model "ollama/nomic-embed-text-v2-moe:latest"

# Search identifiers the same way
uv run semctx --json --target-dir "src/" --cache-dir ".semctx" search-identifiers "build index metadata" --model "vertex_ai/gemini-embedding-2-preview"
```

## Development Checks

Install dev dependencies and wire up the local git hooks:

```bash
uv sync --dev
uv run pre-commit install
```

Validate the hook config or run the approved fast-core profile on demand:

```bash
uv run pre-commit validate-config
uv run pre-commit run --all-files
uv run ruff check src/semctx
uv run ty check src/semctx
uv run python -m compileall "src/semctx"
```

The pre-commit profile stays intentionally small: fast file-hygiene hooks, Astral's official `uv-lock` hook, plus local `ruff check src/semctx`, `ty check src/semctx`, and `python -m compileall "src/semctx"` checks.

## Quick Start

Explore your repository structure and semantics:

```bash
# Build the local index for the directory you want to search
uv run semctx --target-dir "src/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"

# View the structural tree of that directory
uv run semctx tree src/ --depth-limit 2

# Search indexed code and docs by meaning
uv run semctx --target-dir "src/" --cache-dir ".semctx" search-code "user authentication" --model "ollama/nomic-embed-text-v2-moe:latest"
```

Use `--json` before the command when you want machine-readable output:

```bash
uv run semctx --json tree src/ --depth-limit 2
uv run semctx --json --target-dir "src/" --cache-dir ".semctx" search-code "user authentication" --model "ollama/nomic-embed-text-v2-moe:latest"
```

### Scope Model

- `--target-dir` is the only content scope. It is the directory whose files are indexed and searched.
- `--cache-dir` is only where `semctx` stores `index.db` and related artifacts.
- `--depth-limit` is optional narrowing for traversal-heavy commands. It does not change scope identity.

If you want to search only `src/`, point `--target-dir` at `src/`. Files outside `src/`, such as a repo-root `README.md`, are outside scope.

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
uv run semctx tree src/ --include-symbols

# View the API surface of a specific file
uv run semctx skeleton src/semctx/core/embeddings.py
```

### Semantic Search

Search your indexed codebase by meaning. Embeddings are provided via `litellm` and cached locally to avoid redundant API calls.

```bash
# Find files related to a concept
uv run semctx --target-dir "src/" --cache-dir ".semctx" search-code "how are transactions signed" --model "ollama/nomic-embed-text-v2-moe:latest"

# Search by identifier intent
uv run semctx --target-dir "src/" --cache-dir ".semctx" search-identifiers "password hashing" --model "ollama/nomic-embed-text-v2-moe:latest"
```

Normal search runs recover the local index when the safe fix is obvious:

- Missing index: `search-code` and `search-identifiers` automatically build it first.
- Stale index from file changes: both commands automatically run an incremental refresh.
- Incompatible index metadata: search stops and tells you to run `semctx index refresh --full`.

You can still manage lifecycle state explicitly with the `index` commands when you want to inspect or control the rebuild step yourself.

#### Embedding providers

`semctx` treats `--model provider/model` as the canonical embedding selector for embedding-aware commands. Use the full provider-prefixed model string everywhere you override embeddings.

If you expect an AI agent to call semctx repeatedly, do not leave the default
model implicit. Put the chosen `provider/model` and its setup notes in
`SKILL.md`, then have the agent use that default unless the task explicitly
asks for another model.

```bash
# Local Ollama embeddings
uv run semctx --target-dir "src/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"
uv run semctx --target-dir "src/" --cache-dir ".semctx" search-code "retry policy" --model "ollama/nomic-embed-text-v2-moe:latest"

# Vertex AI embeddings
uv run semctx --target-dir "src/" --cache-dir ".semctx-vertex" index init --model "vertex_ai/gemini-embedding-2-preview"
uv run semctx --target-dir "src/" --cache-dir ".semctx-vertex" search-code "retry policy" --model "vertex_ai/gemini-embedding-2-preview"
```

Provider notes:

- `ollama` requires a running local Ollama service and the selected model pulled locally.
- `gemini` requires `GEMINI_API_KEY`.
- `vertex_ai` requires Google auth env vars and a runtime with Google auth support.

For `gemini`, set:

```bash
export GEMINI_API_KEY="your-api-key"
```

For `vertex_ai`, set the Google and Vertex environment variables before running indexed search:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export GOOGLE_CLOUD_PROJECT="your-gcp-project"
export VERTEX_LOCATION="us-central1"
```

`semctx` maps those values into the Vertex names LiteLLM expects. If `VERTEX_LOCATION` is unset or set to `global`, it falls back to `us-central1`.

### Index Lifecycle

The indexed search flow is explicit. Use `--target-dir` to choose what content belongs in the index and `--cache-dir` to choose where the index artifacts live:

```bash
# Create the SQLite index for src/
uv run semctx --target-dir "src/" --cache-dir ".semctx" index init --model "ollama/nomic-embed-text-v2-moe:latest"

# Inspect whether the index is ready, stale, or needs rebuild
uv run semctx --target-dir "src/" --cache-dir ".semctx" index status --model "ollama/nomic-embed-text-v2-moe:latest"

# Apply incremental updates for added, changed, or removed files
uv run semctx --target-dir "src/" --cache-dir ".semctx" index refresh --model "ollama/nomic-embed-text-v2-moe:latest"

# Rebuild from scratch when metadata changes require it
uv run semctx --target-dir "src/" --cache-dir ".semctx" index refresh --full --model "ollama/nomic-embed-text-v2-moe:latest"

# Remove the local index database
uv run semctx --cache-dir ".semctx" index clear
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
uv run semctx blast-radius fetch_embedding src/semctx/core/embeddings.py
```
