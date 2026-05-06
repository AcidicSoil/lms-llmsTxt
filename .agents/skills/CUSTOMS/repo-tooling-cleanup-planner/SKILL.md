---
name: repo-tooling-cleanup-planner
description: "Review bloated repo tooling, scripts, configs, generated folders, and dependencies to create a lean cleanup plan. WHEN: \"clean up repo tooling\", \"too many scripts\", \"build artifacts everywhere\", \"dependency bloat\", \"simplify package.json\"."
---

# Repo Tooling Cleanup Planner

Use this skill to turn a messy web app repo into a clearer, leaner tooling setup.

## Workflow

1. **Inventory tooling**
   - Review `package.json`, lockfiles, build scripts, framework configs, deployment config, test config, and generated folders.
   - Group items by purpose: dev, build, preview, deploy, test, lint, codegen, cache, reports, and local state.

2. **Identify the intended app model**
   - Determine whether the repo should be a static SPA, SSR app, full-stack app, or deployment-specific hybrid.
   - Use source evidence, not folder names alone.

3. **Classify scripts**
   - Keep scripts that support the chosen app model.
   - Flag stale, duplicate, misleading, or framework-incompatible scripts.
   - Separate local development scripts from production deploy scripts.

4. **Separate artifacts from source**
   - Treat generated folders like `dist/`, `.output/`, `.nitro/`, `.vercel/`, `.vite/`, `.tanstack/`, reports, logs, and test outputs as disposable unless proven otherwise.
   - Recommend `.gitignore` entries for generated outputs.

5. **Find dependency bloat**
   - Flag duplicate packages, overlapping UI systems, unused devtools, runtime-only mistakes, and server packages imported near client boundaries.
   - Prioritize removals that reduce install size, build graph size, or browser bundle size.

6. **Produce a cleanup plan**
   - Recommend the smallest safe changes first.
   - Mark risky changes that require source rewrites.
   - Include verification commands after cleanup.

## Output Format

```markdown
## Diagnosis
[Current repo tooling state]

## Tooling Inventory
| Area | Current Items | Keep / Remove / Review | Reason |
|---|---|---|---|

## Script Cleanup
[Recommended package.json scripts]

## Generated Artifacts
[Folders/files to ignore or delete locally]

## Dependency Cleanup
[Duplicate, stale, overlapping, or suspicious dependencies]

## Cleanup Plan
1. [Safe cleanup]
2. [Moderate cleanup]
3. [Risky cleanup requiring code changes]

## Verification
\```bash
[commands to confirm the repo still works]
\```

## Bottom Line
[Direct recommendation]
```

## Example

Input: a repo with Vite, TanStack Start, Nitro, Vercel output config, old SPA preview scripts, duplicated dependencies, build reports, logs, and generated folders.

Expected result: identify the chosen app model, simplify scripts around one build owner, ignore generated artifacts, flag duplicate dependencies, and produce a safe cleanup sequence.
