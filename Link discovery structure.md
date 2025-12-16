## You asked

I want to give the users the option to structure the urls using either/or 'blob' and/or 'raw'. Currently it will use the blob pattern, but I want it to give us the option to replace the 'blob' with 'raw'.

---

Pertinent files (link discovery + link URL shaping):

* `src/lmstudiotxt_generator/analyzer.py`

  * `build_dynamic_buckets(...)` enumerates candidate doc/source paths from `file_tree` and assigns each a `page["url"]` via `construct_raw_url(...)`. This is the primary place where “curated” links are _discovered_ (from the repo tree) and _structured_ into sections.

        src

* `src/lmstudiotxt_generator/github.py`

  * `construct_raw_url(repo_url, path, ref=None)` currently returns a **blob** URL: `https://github.com/<owner>/<repo>/blob/<ref>/<path>`. Despite its name, this is the function enforcing the blob pattern.

        src

* `src/lmstudiotxt_generator/fallback.py`

  * `fallback_llms_payload(...)` calls `build_dynamic_buckets(...)`, so fallback output inherits the same blob URL construction.

        src

* `src/lmstudiotxt_generator/full_builder.py`

  * `_resolve_repo_url(...)` converts repo-relative links discovered inside Markdown/HTML into canonical **blob** URLs (`https://github.com/.../blob/...`). This controls the “Links discovered” section in `llms-full`.

        src

Minimal change set to support `blob` and/or `raw` URL styles:

1. Replace/rename `construct_raw_url` in `github.py` into a single source of truth that supports both:

    * `construct_github_file_url(repo_url, path, ref=None, style: Literal["blob","raw"]="blob")`

    * `blob`: `https://github.com/<owner>/<repo>/blob/<ref>/<path>`

    * `raw`: `https://raw.githubusercontent.com/<owner>/<repo>/<ref>/<path>`

        src

2. Thread `style` into `build_dynamic_buckets(...)` in `analyzer.py`, then use it when setting `page["url"]` (instead of calling the blob-only function).

    src

3. Thread the same `style` through:

    * `RepositoryAnalyzer.forward(...)` → `build_dynamic_buckets(...)`

    * `fallback_llms_payload(...)` → `build_dynamic_buckets(...)`

        src

4. Update `_resolve_repo_url(...)` in `full_builder.py` to return either blob or raw for repo-relative links it resolves (so “Links discovered” matches the selected style).

    src

Operational constraint:

* `raw.githubusercontent.com` links will not work for private repos unless the viewer has authenticated access in their environment; blob links typically remain usable in more contexts.

    src

---

* `src/lmstudiotxt_generator/github.py`
* `src/lmstudiotxt_generator/analyzer.py`
* `src/lmstudiotxt_generator/fallback.py`
* `src/lmstudiotxt_generator/full_builder.py`
