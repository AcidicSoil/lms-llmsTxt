# Task ID: 1

**Title:** Project Foundation & Configuration Module

**Status:** done

**Dependencies:** None

**Priority:** high

**Description:** Establish the project structure, dependency management, and configuration loading logic.

**Details:**

Initialize the project following the `src/lmstxt_mcp/` structure. Create `config.py` using Pydantic Settings or `python-dotenv` to manage environment variables (e.g., `LLMSTXT_MCP_ALLOWED_ROOT`, `LLMSTXT_MCP_RESOURCE_MAX_CHARS`). Ensure `pyproject.toml` includes dependencies for `mcp` (using `fastmcp` if available/compatible or standard `mcp` SDK) and the local `lmstudio-lmstxt-generator` package. Set up `errors.py` to define custom exception classes like `OutputDirNotAllowedError` and `LMStudioUnavailableError`.

Libraries: `pydantic`, `pydantic-settings`, `mcp`.
files: `src/lmstxt_mcp/config.py`, `src/lmstxt_mcp/errors.py`, `pyproject.toml`.

**Test Strategy:**

Unit tests verifying that environment variables are correctly parsed into the config object and that defaults are applied. Test custom error instantiation.
