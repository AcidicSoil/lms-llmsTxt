# Task ID: 3

**Title:** Security & File Hashing Utilities

**Status:** done

**Dependencies:** 1 ✓

**Priority:** high

**Description:** Implement path validation security controls and file hashing utilities.

**Details:**

Create `security.py` to implement `validate_output_dir`. This function must resolve paths and ensure they are contained within `LLMSTXT_MCP_ALLOWED_ROOT` to prevent path traversal. Create `hashing.py` to implement `sha256_file` (streaming read) and `read_text_preview` (reads first N chars). These utilities are critical for the generation and artifact access layers.

Libraries: `pathlib`, `hashlib`.
files: `src/lmstxt_mcp/security.py`, `src/lmstxt_mcp/hashing.py`.

**Test Strategy:**

Unit tests: 1) Attempt to access paths outside the allowed root (e.g., `../etc/passwd`) and assert `OutputDirNotAllowedError`. 2) Verify SHA256 matches known values for test files. 3) Verify preview returns correct truncation boolean.
