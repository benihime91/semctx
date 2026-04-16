---
name: semctx
description: >-
  Semantic codebase discovery, search, and impact analysis CLI. Use when
  exploring unfamiliar repositories, finding code by meaning, locating symbol
  definitions or usages, tracing blast radius before refactors, or when the
  user mentions semctx, code search, codebase indexing, or symbol tracing.
---

# semctx — Semantic Code Context CLI

`semctx` is a local CLI that indexes a codebase into a SQLite database with
embeddings, then provides semantic + lexical search over code chunks and
identifiers, directory tree rendering, file skeleton views, and symbol
blast-radius analysis.

Always use `--json` when calling semctx programmatically — it produces
stable, machine-readable output. Parse the JSON to extract paths, line ranges,
scores, and snippets. For indexed search flows, also pass explicit
`--target-dir` and `--cache-dir` so scope and artifact location are
deterministic.

## Running

```bash
# If installed as a uv tool
semctx <command> [options]
```

## Global Options

| Flag                | Default                | Purpose                             |
| ------------------- | ---------------------- | ----------------------------------- |
| `--json`            | off                    | Emit JSON instead of human text     |
| `--target-dir PATH` | cwd                    | Content scope for index/search      |
| `--cache-dir PATH`  | `<target-dir>/.semctx` | Index DB + embedding cache location |

## Required setup: default model configuration

> [!INFO]
> Keep **this `SKILL.md`** aligned with your current preferences: default `--model` (`provider/model`), embedding **provider**, `--cache-dir` convention, and provider-specific environment variables or notes. If you copied this file from upstream, replace placeholders whenever your team changes backends or defaults so agents do not run `semctx` with stale embed settings.

Before an AI agent uses `search-code`, `search-identifiers`, or `index`
commands, the user must edit this file and replace the placeholders below with
their real default model choice and provider-specific setup.

If this section is left unconfigured, agent-driven semctx calls are likely to
fail or use the wrong embedding backend.

### User-filled defaults

```md
## semctx default model configuration

- Default model: `provider/model`
- Default cache-dir: `<target-dir>/.semctx/`
- Notes for agents: `Use this default model for index init, index refresh, search-code, and search-identifiers unless the user explicitly overrides it.`

### Provider-specific requirements

- `ollama/...`
  - Install and run Ollama locally.
  - Pull the embedding model before using semctx.
  - Example: `ollama/nomic-embed-text-v2-moe:latest`

- `gemini/...`
  - Export `GEMINI_API_KEY` in the shell or agent runtime.
  - Example: `gemini/text-embedding-004`

- `vertex_ai/...`
  - Ensure the runtime includes semctx's LiteLLM + Google auth dependencies.
  - Export `GOOGLE_APPLICATION_CREDENTIALS`.
  - Export `GOOGLE_CLOUD_PROJECT`.
  - Export `VERTEX_LOCATION`.
  - Example: `vertex_ai/gemini-embedding-2-preview`
```

### Supported provider examples

| Provider example                        | What the user must set up                                             |
| --------------------------------------- | --------------------------------------------------------------------- |
| `ollama/nomic-embed-text-v2-moe:latest` | Install Ollama, start the local service, and pull the embedding model |
| `gemini/text-embedding-004`             | Set `GEMINI_API_KEY` in the runtime environment                       |
| `vertex_ai/gemini-embedding-2-preview`  | Provide Google auth env vars and a runtime with Google auth support   |

### Agent rule

Agents should treat the user-filled default model in this file as the standard
embedding configuration for indexed semctx commands. Only pass a different
`--model provider/model` when the user explicitly asks for an override or when
the task requires a different cache/model combination.

---

## Commands

### 1. `tree` — Directory context tree

Renders the project tree with file headers and parsed symbols. Automatically
degrades detail when output exceeds the token budget.

```bash
semctx tree [TARGET_PATH] [--depth-limit N] [--include-symbols/--no-symbols] [--max-tokens N]
```

| Arg / Option        | Default | Notes                           |
| ------------------- | ------- | ------------------------------- |
| `TARGET_PATH`       | `.`     | Relative path to inspect        |
| `--depth-limit`     | `2`     | Max directory depth             |
| `--include-symbols` | on      | Toggle symbol listing per file  |
| `--max-tokens`      | `20000` | Approximate output token budget |

**JSON payload keys**: `command`, `root`, `target_path`, `depth_limit`,
`directories`, `files[]` (each with `path`, `language`, `header_lines`,
`symbols`), `include_symbols`, `max_tokens`.

**When to use**: Orient yourself in a new repo. Get a quick map of directory
structure and top-level symbols without reading every file.

### 2. `skeleton` — Single-file overview

Shows the header lines and parsed symbols for one file.

```bash
semctx skeleton FILE_PATH
```

**JSON payload keys**: `command`, `file` with `path`, `language`,
`header_lines`, `symbols`.

**When to use**: Quickly understand a file's API surface (imports, classes,
functions) before reading its full source.

### 3. `index` — Build and maintain the search index

Subcommands that manage the local SQLite index at `<cache-dir>/index.db`.

```bash
semctx index init   [--model PROVIDER/MODEL] [--target-dir PATH] [--depth-limit N]
semctx index status [--model PROVIDER/MODEL] [--target-dir PATH] [--depth-limit N]
semctx index refresh [--model PROVIDER/MODEL] [--target-dir PATH] [--depth-limit N] [--full]
semctx index clear
```

| Subcommand | Purpose                                                  |
| ---------- | -------------------------------------------------------- |
| `init`     | Build a fresh index from scratch                         |
| `status`   | Show indexed file count, model, staleness                |
| `refresh`  | Incrementally update; `--full` forces a complete rebuild |
| `clear`    | Delete the index database                                |

The `--model` flag accepts `provider/model` strings (e.g.
`ollama/nomic-embed-text-v2-moe:latest`, `gemini/text-embedding-004`,
`vertex_ai/gemini-embedding-2-preview`).

**Auto-index**: `search-code` and `search-identifiers` automatically run
`init` or `refresh` when needed, so explicit index management is optional
unless you want control over model selection or timing.

### 4. `search-code` — Semantic code chunk search

Finds relevant code chunks using combined cosine-similarity and field-weighted
lexical scoring.

```bash
semctx search-code QUERY [--top-k N] [--model PROVIDER/MODEL] [--target-dir PATH] [--depth-limit N]
```

| Arg / Option    | Default       | Notes                             |
| --------------- | ------------- | --------------------------------- |
| `QUERY`         | required      | Natural-language or keyword query |
| `--top-k`       | `5`           | Max results                       |
| `--model`       | index default | Override embedding model          |
| `--target-dir`  | `.`           | Scope the search root             |
| `--depth-limit` | `8`           | Directory depth limit             |

**JSON payload keys**: `command`, `query`, `matches[]` (each with
`relative_path`, `start_line`, `end_line`, `score`, `semantic_score`,
`lexical_score`, `snippet`), `model`, `provider`, `top_k`, `target_dir`,
`depth_limit`.

**When to use**: Find implementations, patterns, or logic by describing what
you're looking for in plain English. Preferred over grep when you don't know
exact variable/function names.

### 5. `search-identifiers` — Semantic symbol search

Searches indexed identifier documents (functions, classes, variables) with
semantic + lexical ranking.

```bash
semctx search-identifiers QUERY [--top-k N] [--model PROVIDER/MODEL] [--target-dir PATH] [--depth-limit N]
```

Options are identical to `search-code`.

**JSON payload keys**: same as `search-code`, plus each match includes `kind`,
`name`, `signature`, `line_start`, `line_end`.

**When to use**: Find a specific function, class, or symbol by name or
description. Use instead of `search-code` when looking for declarations rather
than usage patterns.

### 6. `blast-radius` — Symbol usage tracing

Scans the repo for external usages of a symbol defined in a specific file.

```bash
semctx blast-radius SYMBOL_NAME FILE_CONTEXT [--depth-limit N]
```

| Arg / Option    | Default  | Notes                              |
| --------------- | -------- | ---------------------------------- |
| `SYMBOL_NAME`   | required | Exact symbol name                  |
| `FILE_CONTEXT`  | required | Relative path to the defining file |
| `--depth-limit` | `99`     | Directory depth limit              |

**JSON payload keys**: `command`, `symbol_name`, `file_context`, `depth_limit`,
`definition` (line info or null), `usages[]` (each with file, line, snippet).

**When to use**: Before renaming or refactoring a symbol, check how many files
reference it and where. Essential for assessing change impact.

---

## Workflows

### Explore an unfamiliar repo

```bash
semctx --json tree --depth-limit 3
semctx --json skeleton backend/app.py
```

Parse the JSON `files[]` array to identify key modules, then `skeleton` the
most important ones.

### Find and understand code

```bash
semctx --json --target-dir "backend/" --cache-dir ".semctx" search-code "user authentication middleware" --top-k 5
```

Read the `matches[].relative_path` and `start_line`/`end_line` to locate
relevant source. Use the `snippet` field for a quick preview.

### Find a specific symbol

```bash
semctx --json --target-dir "backend/" --cache-dir ".semctx" search-identifiers "database connection pool" --top-k 3
```

Each match includes `kind` (function/class/variable), `name`, and `signature`.

### Assess refactoring impact

```bash
semctx --json blast-radius "process_payment" "backend/payments/service.py"
```

Check `usages[]` length and file distribution to gauge the blast radius.

### Chained workflow: discover, search, trace

```bash
# 1. Get the lay of the land
semctx --json tree --depth-limit 2

# 2. Search for the feature area
semctx --json --target-dir "backend/" --cache-dir ".semctx" search-code "payment processing" --top-k 5

# 3. Find the key function
semctx --json --target-dir "backend/" --cache-dir ".semctx" search-identifiers "process_payment" --top-k 3

# 4. Check what breaks if you change it
semctx --json blast-radius "process_payment" "backend/payments/service.py"
```

---

## Error Handling

JSON errors have this shape:

```json
{
  "command": "search-code",
  "error": "index_not_found",
  "message": "No index found. Run `semctx index init` first."
}
```

Common error codes:

- `index_not_found` — run `semctx index init`
- `full_rebuild_required` — run `semctx index refresh --full`

Non-zero exit code accompanies all errors.

---

## Embedding Providers

The `--model` flag uses `provider/model` format:

| Provider    | Example                                 | Notes                                                                           |
| ----------- | --------------------------------------- | ------------------------------------------------------------------------------- |
| `ollama`    | `ollama/nomic-embed-text-v2-moe:latest` | Requires a running local Ollama service and the embedding model pulled locally  |
| `gemini`    | `gemini/text-embedding-004`             | Requires `GEMINI_API_KEY`                                                       |
| `vertex_ai` | `vertex_ai/gemini-embedding-2-preview`  | Requires Google auth env vars plus a runtime with LiteLLM + Google auth support |

If `--model` is omitted, the index uses whatever model it was originally built
with. For reliable agent use, users should still configure and document their
preferred default model in the `Default model configuration` section above so
the agent knows which provider/model to use when it has to build or refresh an
index.

For `ollama`, make sure:

- Ollama is installed
- the Ollama service is running
- the chosen embedding model is pulled locally

For `gemini`, set:

- `GEMINI_API_KEY`

For `vertex_ai`, set:

- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_PROJECT`
- `VERTEX_LOCATION`

For `vertex_ai`, also make sure the runtime environment includes semctx's
Google-auth-capable dependency set. If you manage your own environment instead
of using the published semctx install, include the LiteLLM dependency and
Google auth support before using Vertex embeddings.

If `VERTEX_LOCATION` is unset or set to `global`, semctx normalizes it to
`us-central1` for LiteLLM's Vertex path.

---

## Key Behaviors

- The index lives at `<target-dir>/.semctx/index.db` by default.
- `.gitignore` and `.ignore` files control which files are walked and indexed.
- Search commands auto-init/refresh the index when safe; they fail with
  `full_rebuild_required` if schema or metadata is incompatible.
- Embedding results are cached on disk under `.semctx/embeddings/` to avoid
  redundant API calls.
- `target_dir` is the only content scope for indexed search; files outside it
  are not indexed or returned.
- `tree` automatically reduces detail (drops symbols, then headers) when output
  would exceed `--max-tokens`.
