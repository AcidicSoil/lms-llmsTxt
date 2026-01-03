# Task ID: 8

**Title:** Stdio-Safe Logging Implementation

**Status:** done

**Dependencies:** 7 ✓

**Priority:** medium

**Description:** Configure logging to ensure no interference with the stdio transport. [Updated: 1/3/2026]

**Details:**

Update `server.py` or `config.py` to configure the Python `logging` module. Ensure the root logger writes to `sys.stderr` and NOT `sys.stdout`, as stdout is reserved for the JSON-RPC protocol in stdio mode. Set log levels based on the configuration.

files: `src/llmstxt_mcp/server.py`.

**Test Strategy:**

Manual/Scripted test: Run the server in stdio mode, emit logs, and verify they appear on stderr while the JSON-RPC communication on stdout remains valid JSON.
