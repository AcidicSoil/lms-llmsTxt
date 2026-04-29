# Plan: Replace Hyperbrowser With a Compliant OSS Scraping Stack (No API-Key Dependency)

## Summary
This plan removes the mandatory Hyperbrowser API-key dependency by introducing a pluggable scraping provider layer and making a no-key OSS scraper the default.  
It does **not** bypass authentication systems; it replaces the dependency with self-hosted/open alternatives.

Chosen constraints from your selections:
1. Strategy: Pluggable OSS scraper architecture.
2. Deployment target: Local/self-hosted Node.
3. Quality target: ~95% parity with current Hyperbrowser behavior.

## Scope
In scope:
1. Introduce scraper provider abstraction with fallback chain.
2. Implement OSS providers (HTTP extraction + headless browser extraction).
3. Refactor generation flow to use provider orchestration instead of direct Hyperbrowser coupling.
4. Preserve request/metrics logging and failure semantics.
5. Add configuration and tests for parity-focused behavior.

Out of scope:
1. UI redesign.
2. Reworking graph generation prompt/model strategy.
3. Any auth bypass or key circumvention mechanism.

## Public Interfaces and Type Changes
1. New provider abstraction:
   - `lib/scrape/types.ts`
   - `ScrapeProviderName = "http" | "playwright" | "hyperbrowser"`
   - `ScrapeProvider` interface:
     - `name`
     - `isConfigured(): boolean`
     - `scrape(url, options): Promise<{ url; markdown; meta }>`
2. New orchestrator:
   - `lib/scrape/index.ts`
   - `scrapeUrls(urls, options): Promise<{ docs; diagnostics }>`
   - Diagnostics includes attempted providers, success/failure reason, duration, and selected provider.
3. Existing generate response additions:
   - `meta.scrapeProvider` (selected provider)
   - `meta.scrapeAttempts` (provider attempt history)
4. Error classes:
   - `ScrapeConfigError`
   - `ScrapeNoResultsError`
   - `ScrapeProviderError`
   - Keep mapping to stable HTTP statuses in `app/api/generate/route.ts`.

## Configuration Contract
Add environment variables:
1. `SCRAPE_PROVIDER_ORDER=http,playwright,hyperbrowser`
2. `SCRAPE_HTTP_TIMEOUT_MS=15000`
3. `SCRAPE_MAX_CONTENT_CHARS=120000`
4. `SCRAPE_PLAYWRIGHT_ENABLED=true|false`
5. `SCRAPE_PLAYWRIGHT_TIMEOUT_MS=25000`
6. `SCRAPE_PLAYWRIGHT_CONCURRENCY=2`
7. `SCRAPE_MIN_MARKDOWN_CHARS=100`
8. Keep existing `HYPERBROWSER_*` vars as optional fallback only.

Defaults selected:
1. Default order: `http,playwright,hyperbrowser`.
2. Hyperbrowser optional and never required.
3. If no provider is configured/enabled, return setup error with actionable guidance.

## Implementation Plan
1. Create provider layer.
   - Add `lib/scrape/types.ts`, `lib/scrape/utils.ts`, `lib/scrape/index.ts`.
   - Move concurrency and batch orchestration logic out of `lib/hyperbrowser.ts` into orchestrator.
2. Implement `http` provider (no key).
   - Fetch page HTML.
   - Extract readable content using a deterministic extractor (for example, Readability + Turndown).
   - Normalize markdown and trim noisy boilerplate.
   - Reject low-content outputs below `SCRAPE_MIN_MARKDOWN_CHARS`.
3. Implement `playwright` provider (self-hosted, no vendor key).
   - Launch headless browser only when HTTP extraction fails/low quality.
   - Wait for network-idle, capture `document.body` content, convert to markdown.
   - Add strict timeout and bounded concurrency controls.
4. Keep Hyperbrowser provider as optional fallback adapter.
   - Wrap current `lib/hyperbrowser.ts` behavior behind `ScrapeProvider`.
   - Mark provider optional by `isConfigured()` check on API key.
5. Refactor `app/api/generate/route.ts`.
   - Replace direct `scrapeUrls` import from `lib/hyperbrowser` with new orchestrator.
   - Emit scrape diagnostics in metrics and API response meta.
   - Preserve `x-request-id` and stage telemetry pattern.
6. Update logging taxonomy.
   - Add provider-agnostic events:
     - `scrape.provider.attempt`
     - `scrape.provider.selected`
     - `scrape.provider.exhausted`
     - `scrape.batch.completed`
   - Preserve current per-URL success/failure events.
7. Backward-compatibility and migration docs.
   - Update `.env.example` with new scrape variables.
   - Update README setup section to make Hyperbrowser optional.
   - Add migration note: “No API key required for baseline operation.”
8. Cleanup and deprecation path.
   - Keep `lib/hyperbrowser.ts` for one release cycle behind provider adapter.
   - Mark direct usage as deprecated in code comments.
   - Remove direct route coupling after stabilization.

## Failure Modes and Handling
1. HTTP provider returns blocked/empty content.
   - Fallback to Playwright provider for same URL.
2. Playwright timeout or rendering crash.
   - Log structured error and continue to next provider/URL.
3. All providers fail for all URLs.
   - Return `502` with “Failed to scrape any documentation” and include provider diagnostics.
4. Partial success across URLs.
   - Continue generation with successful docs as currently done.
5. Provider misconfiguration.
   - Return setup error indicating which provider is disabled and how to enable.

## Test Cases and Scenarios
1. Unit tests: provider selection logic.
   - Correct order handling.
   - Deduped provider list.
   - `isConfigured` gating behavior.
2. Unit tests: content normalization.
   - Boilerplate stripping.
   - Min-char threshold.
   - Markdown conversion stability.
3. Unit tests: error mapping.
   - `ScrapeConfigError` and `ScrapeNoResultsError` route to expected statuses/messages.
4. Integration tests: `/api/generate`.
   - Works with only `http` provider enabled.
   - Works with `http` fail + `playwright` success fallback.
   - Works when `hyperbrowser` absent.
   - Returns diagnostics and stable `meta` fields.
5. Performance checks (local self-hosted target).
   - 8 URL scrape batch within acceptable timeout envelope.
   - Concurrency limits enforce stable CPU/memory use.
6. Regression tests.
   - Model loading flow unchanged.
   - Generation persistence and history endpoints unchanged.

## Acceptance Criteria
1. App can generate graphs with no `HYPERBROWSER_API_KEY`.
2. Scraping succeeds on representative doc sites with target parity behavior.
3. `/api/generate` returns non-empty docs in majority of existing test topics.
4. Logs clearly show provider attempts, chosen provider, and failure reasons.
5. Existing UI behavior and response contract remain backward-compatible except additive `meta` fields.

## Rollout and Validation
1. Phase A: ship provider layer + HTTP provider behind default order.
2. Phase B: enable Playwright fallback and run parity test suite on curated topic set.
3. Phase C: keep Hyperbrowser optional fallback while monitoring scrape success rates.
4. Phase D: remove direct Hyperbrowser dependency from critical path after stability window.

## Assumptions
1. Local/self-hosted environment can run headless browser binaries.
2. Installing parser/markdown conversion dependencies is acceptable.
3. 95% parity is measured against curated internal topic URLs, not every arbitrary JS-heavy site.
4. Occasional site-specific anti-bot blocking is acceptable if fallback and diagnostics are clear.
