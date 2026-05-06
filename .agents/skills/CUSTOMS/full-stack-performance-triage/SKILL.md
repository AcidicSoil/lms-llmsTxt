---
name: full-stack-performance-triage
description: "Diagnose why a web app became slower after adding frameworks, server routes, build layers, or heavy dependencies. WHEN: \"why is the app slower\", \"dev server got slow\", \"build is slower\", \"performance triage\", \"bundle got huge\"."
---

# Full-Stack Performance Triage

Use this skill to explain and prioritize performance slowdowns in frontend or full-stack web apps.

## Workflow

1. **Clarify the slowdown type**
   - Separate dev startup, HMR, production build time, deploy time, server response time, and browser runtime performance.
   - If unclear, analyze all likely categories and label assumptions.

2. **Identify architecture growth**
   - Compare the current app model against the original simpler model.
   - Look for added SSR, server routes, server functions, API handlers, deployment runtimes, and generated outputs.

3. **Inspect dependency weight**
   - Flag heavy runtime packages, UI systems, animation libraries, syntax highlighters, markdown/rendering tools, database clients, AI SDKs, and devtools.
   - Distinguish “large but acceptable” from “likely imported too high in the app.”

4. **Check client/server boundaries**
   - Look for server-only imports leaking into route components, shared helpers, client components, or browser-facing bundles.
   - Pay special attention to file system, database, AI provider, upload, and persistence modules.

5. **Prioritize measurement**
   - Recommend simple commands to measure build time, dev startup, output sizes, largest chunks, and heavy imports.
   - Prefer direct evidence over guessing.

6. **Rank cleanup by impact**
   - Start with app model clarity, lazy-loading heavy routes, strict server boundaries, duplicate dependency removal, devtools isolation, and generated-output cleanup.

## Output Format

```markdown
## Diagnosis
[Plain-language reason the app slowed down]

## Likely Slowdown Sources
1. [Highest-likelihood cause]
2. [Next cause]
3. [Next cause]

## What to Measure First
\```bash
[commands]
\```

## High-Impact Cleanup Order
1. [Cleanup]
2. [Cleanup]
3. [Cleanup]

## Bottom Line
[Direct performance recommendation]
```

## Example

Input: a repo that started as a Vite app but now includes TanStack Start, Nitro, server routes, API handlers, AI SDKs, database packages, large UI systems, and generated deployment outputs.

Expected result: explain that the slowdown is structural, identify full-stack build/runtime expansion and dependency growth as likely causes, then give measurement commands and a prioritized cleanup plan.
