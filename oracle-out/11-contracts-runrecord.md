Direct answer (1–4 bullets, evidence-cited)

Integrity: mostly yes (at rest), but not end-to-end. ArtifactRef includes both size_bytes and a hash_sha256, which is sufficient for a client to verify a fetched artifact if it can obtain the full bytes that were hashed. (ArtifactRef: size_bytes, hash_sha256.)

Status across tool calls: coarse-grained only. RunRecord.status is one of pending|processing|completed|failed, with an optional error_message, which is enough for basic polling and failure reporting but not for per-artifact readiness. (RunStatus, RunRecord.status, RunRecord.error_message.)

The read path doesn’t carry verification metadata. ReadArtifactResult returns content, truncated, and total_chars, but does not return the artifact hash/size/path, so clients can’t reliably verify integrity from a read call—especially when truncated=True. (ReadArtifactResult: content, truncated, total_chars only.)

The contract lacks normalization guarantees needed for stable clients. ArtifactRef.path is an unqualified str with no declared semantics (absolute vs relative, OS-specific separators, sandbox root), which makes it fragile as a long-lived interface key across environments. (ArtifactRef.path: str.)

Risks/unknowns (bullets)

Unknown hash semantics: whether hash_sha256 is computed over raw bytes, UTF-8 text, normalized newlines, etc.; clients can mismatch hashes even with identical visible text.

Encoding/bytes vs chars mismatch: size_bytes is bytes, while reads report total_chars; clients can’t compare or validate without knowing encoding and whether reads are byte-exact.

No per-artifact lifecycle: RunRecord.status may be completed while a specific artifact is missing/partial; there’s no ArtifactRef.status or generated_at.

Timestamp reliability depends on mutation logic elsewhere: updated_at has a default, but nothing here guarantees it is refreshed on each status/artifact update.

No stable artifact identifier: clients must key off (run_id, name) or path; renames/moves break references.

Next smallest concrete experiment (1 action)

Add a single unit/integration test that:

creates a run, writes one artifact, records ArtifactRef.hash_sha256/size_bytes,

reads the artifact through the read tool/result path,

asserts truncated == False, and that sha256(returned_bytes) equals ArtifactRef.hash_sha256, and that updated_at increased when status transitioned to completed.

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next.

src/lmstxt_mcp/runs.py (where RunRecord is mutated, updated_at is set, and artifacts/hashes are attached)

src/lmstxt_mcp/server.py (tool handlers that construct ReadArtifactResult / return RunRecord)

Any artifact write/hash utility used by the MCP server (e.g., src/lmstxt_mcp/**/artifacts*.py, src/lmstxt_mcp/**/hash*.py, or the exact function that computes hash_sha256)
