# Task ID: 4

**Title:** In-Memory Run Registry

**Status:** done

**Dependencies:** 2 ✓

**Priority:** medium

**Description:** Implement the storage mechanism to track generation runs and their artifacts.

**Details:**

Create `runs.py` containing a `RunStore` class. This should maintain an in-memory dictionary mapping `run_id` to `RunRecord` objects. Implement methods `put_run(run_record)`, `get_run(run_id)`, and `list_runs(limit)`. Use a thread-safe approach if necessary, though simple dicts are atomic in Python for single operations. This store bridges the generation and reading steps.

files: `src/llmstxt_mcp/runs.py`.

**Test Strategy:**

Unit tests: Add runs, retrieve them by ID, and list them with sorting/limiting. Verify `UnknownRunError` when accessing non-existent IDs.
