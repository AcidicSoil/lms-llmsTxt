Direct answer (1–4 bullets, evidence-cited)

Yes—add pagination metadata / cursors, because the current “preview” path can truncate without telling the client how to continue: read_resource_text() calls read_text_preview(..., settings.LLMSTXT_MCP_RESOURCE_MAX_CHARS) and, when truncated, only appends "... (content truncated)" with no offset/next cursor information. (See read_resource_text() in src/lmstxt_mcp/artifacts.py.)

Chunk reads exist but are UX-hostile because they return only a raw string: read_artifact_chunk(..., offset, limit) -> str provides no next_offset, total_size, or eof indicator, so clients must guess pagination state and re-stat the file externally. (See read_artifact_chunk() signature/body in src/lmstxt_mcp/artifacts.py.)

If you do cursors, define them explicitly as byte offsets and return total_bytes (and ideally content_type/encoding) because the current implementation mixes text mode reading with seek(offset) while using path.stat().st_size (bytes) as the bounds check—this is a recipe for incorrect paging on non-ASCII text or newline translation. (See file_size = path.stat().st_size and open(..., "r", encoding="utf-8"); f.seek(offset) in read_artifact_chunk().)

Risks/unknowns (bullets)

Protocol/compat risk: If MCP “read resource” responses are expected to be plain text, returning structured metadata may require a new tool/endpoint rather than changing existing ones (to avoid breaking clients that assume str).

Cursor correctness risk: Offsets must be consistent (bytes vs chars). The current chunking approach bounds by byte size but seeks in a text stream; this can mispage or fail for UTF-8 multi-byte characters.

Binary/encoding ambiguity: Current behavior collapses all decode failures to "<Binary or non-UTF-8 content>", losing partial-read usefulness for “mostly text” files with a few bad bytes.

Missing evidence: I can’t confirm how MCP resources are wired (whether a JSON payload is acceptable) or how read_text_preview() defines truncation (chars vs bytes) without seeing the referenced implementations.

Next smallest concrete experiment (1 action)

Add a new backwards-compatible API (and MCP tool) that returns a structured page object, e.g. read_artifact_page(..., cursor: int, limit: int) -> { content, next_cursor, total_bytes, eof, encoding, is_binary }, implemented by opening the file in binary mode, seeking by byte cursor, reading limit bytes, then decoding with utf-8 using errors="replace" (or returning is_binary=True if a heuristic trips). Keep existing read_resource_text() and read_artifact_chunk() unchanged for compatibility.

If evidence is insufficient, exact missing file/path pattern(s) to attach next

src/lmstxt_mcp/hashing.py (especially read_text_preview() semantics: chars vs bytes, truncation behavior)

src/lmstxt_mcp/config.py (definition of LLMSTXT_MCP_RESOURCE_MAX_CHARS and any related paging limits)

The MCP wiring that exposes these functions (likely src/lmstxt_mcp/server.py and/or any tool/resource registration code paths that call read_resource_text() / read_artifact_chunk()).
