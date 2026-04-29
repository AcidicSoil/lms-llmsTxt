**Built with [Hyperbrowser](https://hyperbrowser.ai)**

# HyperGraph

Turn any technical topic into a traversable skill graph your agent can navigate. This is the difference between an agent that follows instructions and one that understands a domain.

HyperGraph scrapes real sources with Hyperbrowser, then uses CLIProxyAPI (OpenAI-compatible endpoint) to generate a network of interconnected markdown nodes — each one a complete thought, linked with wikilinks the agent can follow.

```
Search → Hyperbrowser scrape → CLIProxyAPI graph generation → Interactive force graph
```

## What it generates

- **MOC** — Map of Content; the entry point your agent reads first
- **Concepts** — foundational ideas, theories, and frameworks
- **Patterns** — reusable techniques and approaches
- **Gotchas** — failure modes and counterintuitive findings

Every node has a YAML `description` the agent can scan without reading the full file. Wikilinks are woven into prose so the agent knows *why* to follow them.

## Get an API key

Get your Hyperbrowser API key at [https://hyperbrowser.ai](https://hyperbrowser.ai)

## Quick start

```bash
git clone https://github.com/yourusername/hypergraph
cd hypergraph
npm install
cp .env.example .env.local   # fill in your keys
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and enter any technical topic.

## Environment variables

```bash
HYPERBROWSER_API_KEY=          # from hyperbrowser.ai
DATABASE_URL=file:./data/hypergraph.db

# CLIProxyAPI endpoint (with or without /v1; app normalizes automatically)
CLIPROXY_BASE_URL=http://localhost:8080/v1
CLIPROXY_API_KEY=
DEFAULT_MODEL=

# Search providers (set one or more)
SERPER_API_KEY=                # from serper.dev
BRAVE_API_KEY=                 # from api.search.brave.com
TAVILY_API_KEY=                # from tavily.com

# Search behavior
SEARCH_PROVIDER_ORDER=serper,brave,tavily
SEARCH_MAX_RESULTS=8

HYPERBROWSER_MAX_CONCURRENCY=1 # free plan: keep at 1. paid plans can increase this.

# Logging
LOG_LEVEL=info
LOG_SINK_MODE=dual
LOG_DIR=.logs/hypergraph
LOG_FILE_BASENAME=app
LOG_ROTATE_MAX_SIZE_MB=50
LOG_RETENTION_DAYS=14
LOG_RETENTION_MAX_FILES=20
LOG_RETENTION_SWEEP_INTERVAL_MIN=60
```

## Search provider fallback

The app now supports multiple search providers and automatically falls back in order when one is unavailable, fails, or returns no usable docs.

- Default order: `serper,brave,tavily`
- Configure order with: `SEARCH_PROVIDER_ORDER`
- You only need to set one provider key to run the app
- If no provider keys are set, `/api/generate` returns a setup error

## Model selection (CLIProxyAPI)

- `CLIPROXY_BASE_URL` supports both forms:
  - `http://127.0.0.1:8317`
  - `http://127.0.0.1:8317/v1`
- The app normalizes the base URL to OpenAI-compatible `/v1/*` routes automatically
- The app loads models from `GET /v1/models` via your configured `CLIPROXY_BASE_URL`
- Users select a model from a dropdown in the topic input
- The selected model is sent to `/api/generate`
- If no model can be loaded, generation is disabled with an inline error
- `DEFAULT_MODEL` is used as backend fallback when request model is missing

## Free plan & concurrency

The free Hyperbrowser plan supports **1 concurrent browser session**. By default the app scrapes URLs **sequentially** (one at a time), so it works out of the box on any plan.

If you hit a concurrency limit the app will show an amber warning banner with an **Upgrade plan** link rather than crashing silently. To unlock parallel scraping, upgrade at [hyperbrowser.ai](https://hyperbrowser.ai) and set `HYPERBROWSER_MAX_CONCURRENCY` to match your plan's limit.

## Logging

- Server-side routes emit structured JSON logs.
- Default sink mode is `dual`: logs go to both stdout and local files.
- Log files are stored at `.logs/hypergraph` by default.
- Active file:
  - `.logs/hypergraph/app-current.ndjson`
- Rotated files:
  - `.logs/hypergraph/app-YYYYMMDD-HHMMSS.ndjson`
- `/api/generate` now emits in-progress stage lifecycle events:
  - `api.generate.stage.started`
  - `api.generate.stage.succeeded`
  - `api.generate.stage.failed`
- Per-URL scraping progress is logged during generation:
  - `scrape.url.succeeded`
  - `scrape.url.failed`
- LLM generation lifecycle is logged:
  - `llm.generate.started`
  - `llm.generate.completed`
  - `llm.generate.failed`
- Each API request emits one canonical completion event:
  - `api.generate.completed`
  - `api.models.completed`
- Every response includes `x-request-id`, and logs include the same `requestId` for correlation.
- Strict redaction is applied in logging helpers:
  - API keys, tokens, secrets, authorization headers, and cookies are redacted.
- Large payloads are truncated and raw scraped/source content is not logged.
- Tune verbosity with `LOG_LEVEL` (for example: `debug`, `info`, `warn`, `error`).
- Retention policy defaults:
  - Rotate at `50MB` per file (`LOG_ROTATE_MAX_SIZE_MB`)
  - Delete files older than `14` days (`LOG_RETENTION_DAYS`)
  - Keep at most `20` log files (`LOG_RETENTION_MAX_FILES`)

### Reviewing Logs

```bash
tail -f .logs/hypergraph/app-current.ndjson
```

```bash
jq -c 'select(.requestId=="<REQUEST_ID>")' .logs/hypergraph/*.ndjson
```

## Persistent Generation Store

- HyperGraph persists successful generations in SQLite via Drizzle.
- Default DB path: `file:./data/hypergraph.db` (set with `DATABASE_URL`).
- `/api/generate` now includes `meta.generationId` when persistence succeeds.
- If persistence fails, generation still returns with `meta.persistenceWarning="store_failed"`.

### History APIs

- `GET /api/generations` — list recent stored generations (summary)
- `GET /api/generations/:id` — fetch full stored payload (`graph` + `files`) to rebuild graph views
- `DELETE /api/generations/:id` — remove a stored generation

### Drizzle Commands

```bash
npm run db:generate
npm run db:migrate
npm run db:studio
```

## Theme

- The app includes a header dark mode toggle (landing and results views).
- First load follows your OS preference.
- Theme choice is persisted in `localStorage` under `hypergraph-theme`.

## Stack

- **Next.js 16** — App Router, API routes
- **Hyperbrowser** — scrapes source material with `onlyMainContent` for clean output
- **CLIProxyAPI (OpenAI-compatible)** — routes generation across your configured providers/models
- **Serper / Brave / Tavily** — web search providers with auto-fallback
- **react-force-graph-2d** — force-directed graph canvas rendering
- **react-markdown** — renders node content in the VS Code-style preview panel

## OSS Replacement Roadmap

- See `docs/oss-alternatives-hypergraph.md` for the migration plan and candidate OSS replacements (Cytoscape.js, Sigma.js, Vis Network, ELK/Dagre).

## Download

Every generated graph can be downloaded as a `.zip` containing ready-to-use markdown files. Drop the folder into `.claude/skills/` or `.cursor/skills/` and point your agent at `moc.md` as the entry point.

---

Follow [@hyperbrowser](https://x.com/hyperbrowser) for updates.
