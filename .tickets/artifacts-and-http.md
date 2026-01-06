Yes—if LM Studio is running on Windows and you’re using a **local stdio MCP server**, the server command must be runnable **on Windows** (installed in a Windows Python environment and on `PATH`, or referenced by absolute path). The MCP JSON format expects `command` to be an absolute path or available on the system `PATH`. ([LM Studio][1])

If you only installed `lms-llmsTxt` in WSL (or another environment), LM Studio won’t be able to spawn `lmstxt-mcp` from Windows.

---

## Do not store artifacts “wherever it is installed”

That approach is brittle for exactly the reason MCP configs often use launchers like `npx`/`uvx`: the install location may be **ephemeral** or change on upgrade.

A concrete example: the official `server-memory` changed its default from “installation path” to “current working directory” because the install path is unstable when using `npx` and upgrades caused data loss; users were ending up with files under `.npm/_npx/.../node_modules/...`, which is not stable or friendly. ([GitHub][2])

So: don’t bind user data/artifacts to the package install directory.

---

## What “similar MCP servers” do instead

### Pattern A — Explicit working directory / explicit paths

Python MCP Server Make:

* runs with `uvx ...`
* takes `--working-dir` and expects absolute paths in client config ([GitHub][3])

This avoids guessing and avoids install-path storage.

### Pattern B — Client-provided filesystem roots (best UX + best security model)

The official filesystem server uses MCP **Roots**:

* server asks the client for roots (`roots/list`)
* allowed directories become the client’s configured roots
* operations are restricted to those roots ([npm][4])

This is the cleanest “users don’t worry about setup” model when the client supports Roots.

### Pattern C — Stable user-data directory fallback

When Roots aren’t available, servers typically fall back to something stable (cwd or a user data dir), not install dir. The `server-memory` discussion explicitly rejects install dir because it changes. ([GitHub][2])

---

## Best way to handle artifacts for your server (recommended)

### 1) Make artifacts root stable by default (no client config required)

Resolve `ARTIFACTS_ROOT` in this order:

1. **If client supports Roots**: pick a root and use a subdir like `<root>/.lmstxt/artifacts` (create it) ([Model Context Protocol][5])
2. Else if env var set (keep your existing override): `LLMSTXT_MCP_ALLOWED_ROOT`
3. Else fallback to an OS user-data dir (Windows: `%LOCALAPPDATA%/...`, macOS: `~/Library/Application Support/...`, Linux: `~/.local/share/...`)

This makes “just works” the default and avoids brittle install paths.

### 2) Keep security boundaries

Even with a friendlier default, keep enforcing “only write under artifacts root” (same idea as Roots boundaries). ([Model Context Protocol][5])

### 3) Expose the resolved artifacts directory via a tool

Add a tool like `lmstxt_get_paths` that returns:

* resolved artifacts root
* resolved output dir for the current run
  This removes guesswork in clients that don’t show process cwd.

### 4) Document one “boring” local install path for each OS

For LM Studio local stdio on Windows: recommend `pipx install lms-llmsTxt` (or `uv tool install ...`) so `lmstxt-mcp` is on PATH, then config uses `"command": "lmstxt-mcp"`. The config standard explicitly relies on PATH/absolute command availability. ([FastMCP][6])

---

## Optional: avoid the Windows/WSL split entirely

LM Studio supports **remote MCP servers** by URL (with headers). ([LM Studio][1])
If you add Streamable HTTP to your server, you can run it anywhere (WSL, Docker, another machine) and LM Studio connects over HTTP—no PATH issues.

---

## Practical guidance for your immediate scenario

* For LM Studio on Windows + stdio MCP: **install the package on Windows** (pip/pipx/uv tool), ensure `lmstxt-mcp` is on PATH, and keep artifacts under a stable root as above. ([FastMCP][6])
* Do **not** change artifacts to save “where installed”; follow the patterns above (Roots → env override → stable user-data fallback). ([GitHub][2])

[1]: https://lmstudio.ai/docs/app/mcp "Use MCP Servers | LM Studio Docs"
[2]: https://github.com/modelcontextprotocol/servers/pull/2160 "mcp-server-memory: use working directory for default path by solatis · Pull Request #2160 · modelcontextprotocol/servers · GitHub"
[3]: https://github.com/MCP-Mirror/wrale_mcp-server-make "GitHub - MCP-Mirror/wrale_mcp-server-make: Mirror of https://github.com/wrale/mcp-server-make"
[4]: https://www.npmjs.com/package/%40modelcontextprotocol/server-filesystem?utm_source=chatgpt.com "@modelcontextprotocol/server-filesystem - npm"
[5]: https://modelcontextprotocol.io/specification/2025-06-18/client/roots "Roots - Model Context Protocol"
[6]: https://gofastmcp.com/integrations/mcp-json-configuration "MCP JSON Configuration  FastMCP - FastMCP"
