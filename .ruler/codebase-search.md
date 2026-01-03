

When you need to call tools from the shell, follow these rules.

## Core Principles

- Prefer deterministic, non-interactive commands so runs are reproducible.
- Always check tool capabilities before assuming flags: run `<tool> --help` when first using it in a session.
- Default to pipelines that produce stable output (`--jsonl`, `--json` + `jq`, `sort`, `head`).

---

## File Operations

- Find files by file name: `fd <pattern>`
- Find files with path name: `fd -p <file-path>`
- List files in a directory: `fd . <directory>`
- Find files with extension and pattern: `fd -e <extension> <pattern>`

---

## Codebase Search (De-conflicted)

### 0) Discover the search interface (required)

- Always run: `ck --help`

### 1) Default search tool: `ck`

Use `ck` as the primary entry point for codebase search.

- Exact / literal matches:
  - Use `ck --regex` (or the equivalent described in `ck --help`)
- Conceptual / meaning-based matches:
  - Use `ck --sem`
- Best of both (recommended when unsure):
  - Use `ck --hybrid`
- Tooling / automation output:
  - Prefer `ck --jsonl` when you plan to post-process results.

Notes:

- If `ck` indicates it needs setup (e.g., indexing), follow the instructions shown by `ck` for your repo.

### 2) Structural search tool: `ast-grep` (use when structure matters)

Use `ast-grep` when you need syntax-aware matching (AST-level), such as:

- Find a specific language construct (e.g., a function shape, call pattern, import form)
- Avoid false positives common in text search
- Prepare for safe refactors/codemods

Common commands:

- Find code structure:
  - `ast-grep --lang <language> -p '<pattern>'`
- List matching files (then cap output):
  - `ast-grep -l --lang <language> -p '<pattern>' | head -n 10`

### 3) How to choose (the actual “de-conflict” rule)

- If your query is **conceptual** (“where is error handling done?”) → start with `ck --sem` or `ck --hybrid`.
- If your query is **literal** (“find `fooBar(` calls”) → use `ck --regex` (or `ck --hybrid` if you want nearby conceptual hits).
- If your query is **structural** (“find `try { ... } catch (e) { ... }` with a specific call inside”) → use `ast-grep`.
- If you start with `ck` and the results are broad/noisy, narrow to files/modules, then re-run with:
  - `ck` again (more specific query), or
  - `ast-grep` (to enforce structure).

---

## Data Processing

Use small, composable tools to post-process outputs deterministically:

- JSON: `jq`
- YAML (if needed): `yq`
- Stable selection/ordering: `sort`, `uniq`, `head`

---

## Selection

- Select from multiple results deterministically (non-interactive filtering)
- Fuzzy finder (still deterministic when using `--filter`):
  - `fzf --filter 'term' | head -n 1`

---

## Guidelines (Summary)

- Default codebase search: `ck` (after `ck --help`)
- Structural/syntax-aware search: `ast-grep`
- Prefer deterministic output shaping (`--jsonl`/`jq`, `sort`, `head`)
