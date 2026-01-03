# Task ID: 2

**Title:** Data Models & Type Definitions

**Status:** done

**Dependencies:** 1 ✓

**Priority:** high

**Description:** Define Pydantic models for MCP tool inputs/outputs and internal data structures.

**Details:**

Implement `models.py` to define schemas for `GenerateResult`, `ArtifactRef`, and `ReadArtifactResult`. Use Pydantic to enforce types and constraints. Define `ArtifactName` literals (e.g., `llms.txt`, `llms-full.txt`). Ensure strict typing for tool arguments to leverage MCP's automatic schema generation capabilities.

Libraries: `pydantic`.
files: `src/llmstxt_mcp/models.py`.

**Test Strategy:**

Unit tests ensuring valid data passes validation and invalid data raises ValidationError. Verify JSON serialization formats.
