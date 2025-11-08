
Specification handoff to implement the four “Next Steps”:

A) Analyze multiple repositories
--------------------------------

**Goal:** accept N repos, emit per-repo artifacts and a merged top-level `llms.txt`.
**Interfaces:**

* **CLI**: support either repeated args or a file list.

  * `lmstxt --repo <url> [--repo <url> …]`

  * `lmstxt --repos-file <path>` (newline-separated)

* **Library**:

  * `run_generation_multi(repos: list[str], config: AppConfig, …) -> list[GenerationArtifacts]`

  * `merge_llms_documents(per_repo_llms: list[str], strategy: {"union"|"topk"}, k:int=10) -> str`

* **Output:**

  * Per-repo: same paths under `<OUTPUT_DIR>/<owner>/<repo>/…` (preserves current layout). src-no-tests

  * Top-level aggregate folder `<OUTPUT_DIR>/aggregate/` with:

    * `aggregate-llms.txt` (merged curated sections; dedupe by URL; stable order = taxonomy then alpha). Current taxonomy order should be reused. src-no-tests

    * `aggregate-llms-full.txt` (first K blocks per repo, configurable).

    * `aggregate-metrics.json` (see section C).

**Merging rules:**

* Normalize titles using `_nicify_title`; reuse `_score` to rank links; drop dead links via `_url_alive`. src-no-tests

* Bucket by existing `TAXONOMY`. Limit each bucket to 20 items total. src-no-tests

**Failure model:** if a repo falls back, include it with `used_fallback=true` note in summary; this is already produced by `run_generation`. src-no-tests

B) Support different documentation formats
------------------------------------------

**Scope:** expand parsing and text extraction while keeping the curated-link pipeline.
**Plan:**

* Extend file detection in `build_dynamic_buckets` to include `.ipynb`, `.rst`, `.mdx`, `.html` (most are already handled). Add `.adoc` and `.org`. src-no-tests

* Introduce `docs_normalizer.py` with:

  * `detect_mime(path, api_hint:str|None) -> str`

  * `to_text(path:str, body:bytes, mime:str) -> str`

    * `.ipynb`: load JSON, join markdown + code cells as fenced text.

    * `.rst`: naive reST→text by stripping directives; future: optional docutils.

    * `.html`: reuse existing `_html_to_text`.

* Hook normalization inside `build_llms_full_from_repo` where GitHub or web bodies are converted to text prior to truncation and link harvesting. Keep size caps.

**Acceptance:** `llms-full` shows readable text blocks for notebooks and reST pages, with “Links discovered” appended as today.

C) Documentation quality metrics
--------------------------------

**Deliverable:** `metrics.json` per repo and `aggregate-metrics.json` for multi-repo.
**Metric set:**

1. **Docs coverage:** fraction of files matching docs formats over total files. Uses file tree already fetched.

2. **Taxonomy coverage:** presence per bucket (Docs, Tutorials, API, Concepts, Optional). Derived from dynamic buckets. src-no-tests

3. **Onboarding completeness:** boolean + score if “install/quickstart/README/index” exists. Uses `_short_note` and regex signals. src-no-tests

4. **API reference depth:** count of `API` bucket links.

5. **Link liveness:** share of curated URLs that are reachable using `_url_alive`. src-no-tests

6. **Recency:** last commit date of any doc file vs today; needs an extra GitHub API call.

7. **Private-aware sourcing:** flag if repo is private to adjust `prefer_raw` choice already implemented. pyproject

**Schema:** include alongside existing LLMS JSON payload title; store as `repo-metrics.json` next to artifacts.

**CLI:** `--metrics` (on by default), `--no-metrics` to disable.

D) Web interface for interactive analysis
-----------------------------------------

**Stack:** FastAPI backend with simple server-rendered pages first; optional React later.

**Endpoints:**

* `POST /analyze` body `{ "repos": [<urls>], "options": {...} }` → returns job id.

* `GET /jobs/{id}` → JSON status with paths to outputs when done.

* `GET /artifacts/{owner}/{repo}` → lists per-repo files with links.

* `GET /aggregate` → returns aggregate artifacts if multi-repo.

* SSE stream `/events/{id}` for progress messages from pipeline.

**Backend integration:**

* Wrap existing `run_generation` and new `run_generation_multi`. Use a simple thread pool. Artifacts root from `AppConfig.ensure_output_root`. pyproject

* Provide `.env` for `LMSTUDIO_*`, `OUTPUT_DIR`, `GITHUB_ACCESS_TOKEN`. pyproject

**UI features:**

* Form for URLs, toggle for ctx, metrics, and K for aggregate.

* Live progress lines mirrored from logger.

**Security:** never expose tokens; only serve static files from output dir.

**Alternatives with trade-offs:**

* Streamlit: fastest UI, less control over job orchestration.

* CLI-only JSON: simplest, no server, but no interactivity.

* Celery worker: scales jobs, adds infra.

* * *

Steps
=====

1. **CLI & pipeline multi-repo:**

    * Add `--repo` repeatable and `--repos-file` to `cli.py`. Parse into list. Call `run_generation_multi`. src-no-tests

    * Implement `run_generation_multi` in `pipeline.py`: loop `run_generation`, then build aggregate artifacts.

2. **Aggregator:**

    * Parse each per-repo `llms.txt`. Collect links via existing `_PAGE_LINK`, then re-bucket and render using `render_llms_markdown`. src-no-tests

3. **Docs normalizer:**

    * Create `docs_normalizer.py` and call from `full_builder.build_llms_full_from_repo` before size enforcement.

4. **Metrics:**

    * Add `metrics.py` to compute metrics from file tree, buckets, and HEAD commit times via GitHub API.

    * Emit `repo-metrics.json`; include summary line in CLI output. src-no-tests

5. **Web API:**

    * Add `api/app.py` (FastAPI). Endpoints above. Wire to pipeline.

6. **Tests:**

    * Unit test `merge_llms_documents`, `to_text` for `.ipynb`/`.rst`, and metrics calculations.

7. **Docs:**

    * Update README with new flags and API routes.

Commands
========

* Run single-repo today:

  * `lmstxt https://github.com/<owner>/<repo>`

  * `lmstxt https://github.com/<owner>/<repo> | tee -a llmstxt.log` pyproject src-no-tests

* Proposed multi-repo via repeated flags:

  * `lmstxt --repo https://github.com/o/r1 --repo https://github.com/o/r2`

  * `lmstxt --repo https://github.com/o/r1 --repo https://github.com/o/r2 | tee -a llmstxt.log`

* Proposed multi-repo via file:

  * `lmstxt --repos-file repos.txt`

  * `lmstxt --repos-file repos.txt | tee -a llmstxt.log`

* Verify LM Studio connectivity:

  * `curl -s ${LMSTUDIO_BASE_URL:-http://localhost:1234}/v1/models`

  * `curl -s ${LMSTUDIO_BASE_URL:-http://localhost:1234}/v1/models | tee -a llmstxt.log`

* Start FastAPI (after adding `api/app.py`):

  * `uvicorn api.app:app --reload --port 8000`

  * `uvicorn api.app:app --reload --port 8000 | tee -a llmstxt.log`

Snippets
========

    # cli.py — add args
    parser.add_argument("--repo", action="append", help="GitHub repo URL. Repeatable.")
    parser.add_argument("--repos-file", type=Path, help="File with one GitHub URL per line.")


    # pipeline.py — new multi entry
    def run_generation_multi(repos: list[str], config: AppConfig, **kw) -> list[GenerationArtifacts]:
        results = []
        for url in repos:
            results.append(run_generation(url, config, **kw))
        return results


    # aggregator.py — merge
    def merge_llms_documents(docs: list[str], topk:int=20) -> str:
        from .analyzer import TAXONOMY, render_llms_markdown
        from .full_builder import iter_llms_links
        links = []
        for doc in docs:
            links.extend(iter_llms_links(doc))
        # dedupe by URL
        seen = {}
        for title, url in links:
            seen.setdefault(url, title)
        # bucket by TAXONOMY name heuristics from path/title
        # rank by existing _score(url/path) if available
        # render with render_llms_markdown(project_name="Aggregate", project_purpose="", remember_bullets=[], buckets=buckets)
        ...


    # docs_normalizer.py — outline
    def to_text(path: str, body: bytes, mime: str) -> str:
        if path.lower().endswith(".ipynb"):
            import json
            nb = json.loads(body.decode("utf-8", "ignore"))
            parts = []
            for cell in nb.get("cells", []):
                if cell.get("cell_type") == "markdown":
                    parts.append("".join(cell.get("source", [])))
                elif cell.get("cell_type") == "code":
                    parts.append("```python\n" + "".join(cell.get("source", [])) + "\n```")
            return "\n\n".join(parts)
        if path.lower().endswith(".rst"):
            import re
            text = body.decode("utf-8", "ignore")
            text = re.sub(r"^:[^\\n]+$", "", text, flags=re.M)
            return text
        # html and md handled by existing utilities
        return body.decode("utf-8", "replace")


    # metrics.py — sketch
    def compute_metrics(file_tree:str, buckets, docs_paths:set[str], live_urls:set[str], dead_urls:set[str], last_doc_commit_iso:str) -> dict:
        return {
            "docsCoverage": len(docs_paths) / max(1, len(file_tree.splitlines())),
            "taxonomyCoverage": {name: bool(items) for name, items in buckets},
            "onboardingCompleteness": any(n in p.lower() for p in docs_paths for n in ["readme.md","getting-started","quickstart","install"]),
            "apiRefDepth": sum(1 for name, items in buckets if name=="API" for _ in items),
            "linkLiveness": {"alive": len(live_urls), "dead": len(dead_urls)},
            "recencyIso": last_doc_commit_iso,
        }
    }

Defaults & Placeholders
=======================

* `{OUTPUT_DIR}` → `./artifacts` (via `AppConfig`) pyproject

* `{LMSTUDIO_BASE_URL}` → `http://localhost:1234/v1` and `{LMSTUDIO_API_KEY}` arbitrary string if LM Studio requires it. pyproject

* `{LMSTUDIO_MODEL}` → `qwen3-4b-instruct-2507@q6_k_xl` default. pyproject

* `{REPOS_FILE}` → path to newline list of URLs `{https://github.com/<owner>/<repo>}`.

* `{K}` → 20 aggregate items per bucket.

* `{ENABLE_CTX}` → false by default; when true and `llms_txt.create_ctx` is importable, ctx is emitted. src-no-tests pyproject

Next actions
============

* Confirm CLI flag shape (`--repo` repeatable and `--repos-file`) or prefer a single `--input`.

* If approved, scaffolding for `aggregator.py`, `docs_normalizer.py`, `metrics.py`, and `api/app.py` can be produced next, aligned to current module structure.

**Source for the requested “Next Steps”:** the tutorial’s list matches the items above. next-steps llms\_txt\_generation-DSPy\_tutori…

---
