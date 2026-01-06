# Task ID: 5

**Title:** Artifact Access Logic

**Status:** done

**Dependencies:** 3 ✓, 4 ✓

**Priority:** high

**Description:** Implement the core logic for resolving, reading, and chunking artifact content.

**Details:**

Create `artifacts.py`. Implement `resource_uri(run_id, artifact)` to generate standard URIs. Implement `read_resource_text` which uses `hashing.read_text_preview` for truncated reads suitable for MCP Resources. Implement `read_artifact_chunk` for the chunking tool, handling `offset` and `limit` to slice file content safely. Ensure dependencies on `runs.py` to resolve `run_id` to file paths.

files: `src/lmstxt_mcp/artifacts.py`.

**Test Strategy:**

Unit tests: Create dummy files, perform chunked reads at various offsets (start, middle, end, past end). Verify truncation banners are prepended when reading as a resource.

## Subtasks

### 5.1. Initialize Artifacts Module and URI Logic

**Status:** done  
**Dependencies:** None  

Create the artifacts module structure and implement the URI generation helper function. [Updated: 1/3/2026]

**Details:**

Create `src/lmstxt_mcp/artifacts.py`. Import necessary dependencies including the `RunStore` from `runs.py`. Implement the `resource_uri(run_id: str, artifact_name: str) -> str` function to generate standardized URIs (e.g., `lmstxt://{run_id}/{artifact}`) used by the MCP server to identify resources.

### 5.2. Implement Truncated Resource Reading

**Status:** done  
**Dependencies:** 5.1  

Develop the logic to read artifact files for MCP Resources, ensuring content is truncated if it exceeds limits.

**Details:**

Implement `read_resource_text(run_id, artifact)`. This function must resolve the file path using `RunStore`, read the text content, and check against `LLMSTXT_MCP_RESOURCE_MAX_CHARS`. If the content exceeds the limit, truncate it and append a footer (e.g., '... truncated') to prevent overloading the MCP client.

### 5.3. Implement Chunked Artifact Reading

**Status:** done  
**Dependencies:** 5.1  

Create the logic for reading specific slices of a file based on offset and limit parameters for the reading tool.

**Details:**

Implement `read_artifact_chunk(run_id, artifact, offset, limit)`. Use python file seeking (`seek`) to navigate to the `offset` and read up to `limit` characters. Handle edge cases such as `offset` exceeding file size (return empty string) or `limit` extending past EOF. Ensure file handles are closed safely.
