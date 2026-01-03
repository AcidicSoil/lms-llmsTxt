# Task ID: 10

**Title:** Packaging & Entry Point Verification

**Status:** done

**Dependencies:** 8 ✓, 9 ✓

**Priority:** low

**Description:** Finalize packaging and verify the CLI entry point works for both transports.

**Details:**

Ensure `pyproject.toml` defines the correct `project.scripts` entry point (e.g., `llmstxt-mcp = llmstxt_mcp.server:main`). Verify that running `llmstxt-mcp` defaults to stdio mode and accepts flags for HTTP mode if implemented. Create a basic README documenting installation and usage.

files: `pyproject.toml`, `README.md`.

**Test Strategy:**

Smoke test: Install the package locally (`pip install -e .`) and run the CLI command. Verify it starts up without crashing and prints expected startup logs to stderr.
