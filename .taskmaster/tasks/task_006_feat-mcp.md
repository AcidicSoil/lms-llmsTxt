# Task ID: 6

**Title:** Generator Integration & Serialized Execution

**Status:** done

**Dependencies:** 5 ✓

**Priority:** high

**Description:** Wrap the external `lmstudiotxt_generator` library with thread-safe execution logic.

**Details:**

In `server.py` (or a dedicated integration module), implement the `llmstxt_generate` tool logic. Import `run_generation` from the external library. Use a `threading.Lock` to ensure only one generation runs at a time (avoiding global config races). Capture exceptions (specifically connectivity errors) and map them to `LMStudioUnavailableError`. Calculate hashes for outputs and register the run in `RunStore`.

Libraries: `lmstudiotxt_generator`.
files: `src/llmstxt_mcp/server.py`.

**Test Strategy:**

Integration test: Mock the external `run_generation` to write temporary files. Verify that the MCP tool wrapper correctly calls the mock, computes metadata, and updates the RunStore.

## Subtasks

### 6.1. Implement Thread-Safe Generator Wrapper

**Status:** done  
**Dependencies:** None  

Create the integration module and implement the locking mechanism to ensure serial execution of the generator.

**Details:**

Create `src/llmstxt_mcp/generator.py` (or integrate into `server.py`). Import `run_generation` from `lmstudiotxt_generator`. Instantiate a module-level `threading.Lock`. Define a function `safe_generate` that uses the lock as a context manager to wrap the call to `run_generation`. This ensures that concurrent requests to the MCP server do not trigger race conditions in the external library's global configuration.

### 6.2. Implement Error Translation Layer

**Status:** done  
**Dependencies:** 6.1  

Add error handling logic to map external library exceptions to internal domain errors.

**Details:**

In the generation wrapper, wrap the `run_generation` call in a try/except block. Specifically identify connectivity errors (e.g., connection refused from LM Studio) and raise a `LMStudioUnavailableError` (defined in `errors.py`). Ensure generic exceptions are also caught and wrapped or logged appropriately to prevent server crashes while releasing the lock in a `finally` block.

### 6.3. Integrate Output Hashing and RunStore Updates

**Status:** done  
**Dependencies:** 6.1, 6.2  

Process generation outputs, calculate hashes, and register the completed run in the RunStore.

**Details:**

Upon successful generation, use the hashing utilities from `src/llmstxt_mcp/hashing.py` to calculate SHA256 checksums for the output files. Construct a `Run` object with the status, timestamp, and artifact metadata. Call the `RunStore` instance to save the run. Return the final result object expected by the MCP tool interface.
