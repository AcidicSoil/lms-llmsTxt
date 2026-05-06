---
name: build-stack-auditor
description: "Audit bloated frontend/full-stack app tooling and identify the minimum conventional build stack. WHEN: \"why are there multiple builds\", \"what tooling do we need\", \"audit our build stack\", \"Vite Nitro Vercel TanStack\", \"repo feels bloated\"."
---

# Build Stack Auditor

Use this skill to diagnose overlapping build, framework, and deployment tooling in web app repos.

## Workflow

1. **Identify the app model**
   - Determine whether the repo is a static SPA, SSR app, full-stack framework app, or hybrid.
   - Look for source evidence: API routes, server functions, SSR entrypoints, server-only modules, and deployment outputs.

2. **Map each tool to its role**
   - Classify tools as:
     - framework
     - bundler
     - router
     - server/runtime layer
     - deployment platform
     - cache/generated output
     - test/report artifact

3. **Find the build owner**
   - Inspect `package.json`, build scripts, framework configs, and deployment config.
   - Identify the single command that should own production builds.
   - Flag redundant or conflicting build paths.

4. **Separate source from artifacts**
   - Treat folders like `dist/`, `.output/`, `.nitro/`, `.vercel/`, `.vite/`, `.tanstack/`, reports, and logs as generated unless proven otherwise.

5. **Recommend the minimum stack**
   - For a static React SPA, default to:
     - React
     - Vite
     - router if used
     - static hosting
   - For a full-stack app, keep only the framework/runtime layers required by active server-side features.

6. **Explain tradeoffs plainly**
   - State what can be removed safely.
   - State what requires rewriting source code.
   - Distinguish “bloated tooling” from “necessary complexity.”

## Output Format

```markdown
## Diagnosis
[Plain-language summary of current app model]

## Tool Map
| Tool | Role | Keep? | Why |
|---|---|---:|---|

## Minimum Conventional Setup
[Recommended lean stack]

## Likely Bloat
[Generated folders, duplicate tools, stale scripts, conflicting outputs]

## Cleanup Plan
1. [Highest-impact cleanup]
2. [Next cleanup]
3. [Validation step]

## Bottom Line
[Direct recommendation]
```

## Example

Input: a repo using Vite, TanStack Router, TanStack Start, Nitro, and Vercel with both `dist/` and `.output/`.

Expected result: identify whether the app is still a Vite SPA or has become a TanStack Start full-stack app, then recommend either a static Vite setup or a full-stack TanStack Start/Nitro setup based on actual server-side code.
