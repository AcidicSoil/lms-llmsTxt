Direct answer (1–4 bullets, evidence-cited)

A single global allowed root is sufficient for single-tenant/local installs, but it is not sufficient for future multi-tenant deployments where different tenants must be hard-isolated at the filesystem boundary (you currently have exactly one root: LLMSTXT_MCP_ALLOWED_ROOT: Path = Path("./output")). Evidence: src/lmstxt_mcp/config.py:5.

Supporting per-request roots via raw client-provided paths is a security footgun (it moves the trust boundary to user input). If you support “per-request roots,” it should be per-tenant/per-workspace roots resolved server-side (e.g., from authenticated tenant identity → configured root), not arbitrary paths. Evidence: the only boundary control shown is a single configured root in Settings. src/lmstxt_mcp/config.py:4–14.

The lowest-risk evolution path is: keep one default root, but refactor internals so the “allowed root” is an injected parameter (derived from request context) instead of a global constant—enabling multi-tenant without redesign later. Evidence: boundary is currently only expressible as a singleton setting. src/lmstxt_mcp/config.py:4–14.

Risks/unknowns (bullets)

Tenant identity / auth: MCP requests may not carry a trustworthy tenant identifier today; without it, “per-tenant root” can’t be enforced meaningfully.

Isolation level: path-based controls alone may be insufficient for hostile tenants; you may also need OS/container sandboxing depending on threat model.

Cross-tenant leakage via shared output naming: even with separate roots, any shared indices/run stores/logging that include paths could leak metadata.

Symlink and traversal handling depends on the validator (not shown here); whether it resolves symlinks and enforces containment correctly is decisive for any root scheme.

Next smallest concrete experiment (1 action)

Refactor boundary enforcement to accept an allowed_root: Path argument (defaulting to settings.LLMSTXT_MCP_ALLOWED_ROOT) and thread it through the call chain; do not expose a “root path” tool parameter—only allow a server-resolved root. This creates the extension point needed for multi-tenant later with minimal surface-area change.

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next

src/lmstxt_mcp/security.py (the full validate_output_dir implementation and any helpers it calls)

src/lmstxt_mcp/server.py (where tool inputs are parsed and where output_dir/root is chosen)

src/lmstxt_mcp/*.py files that call the validator or write artifacts (search for validate_output_dir(, output_dir, Path(, and file writes like open( / write_text()
