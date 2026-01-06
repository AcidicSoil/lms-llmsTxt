# Task ID: 9

**Title:** Request Limits & Error Normalization

**Status:** done

**Dependencies:** 7 ✓

**Priority:** medium

**Description:** Harden the server by enforcing limits and ensuring clean error reporting.

**Details:**

Refine `artifacts.py` and `server.py` to enforce `MAX_CHARS` limits on resource reads and chunk sizes. Implement a global error handler or try/except blocks in tool entry points to catch internal exceptions (e.g., `LMStudioUnavailableError`, `OutputDirNotAllowedError`) and return user-friendly error strings instead of stack traces to the MCP client.

files: `src/lmstxt_mcp/errors.py`, `src/lmstxt_mcp/server.py`.

**Test Strategy:**

Unit tests: Trigger exceptions and verify the returned error message format. Test boundary conditions for chunk sizes to ensure limits are respected.
