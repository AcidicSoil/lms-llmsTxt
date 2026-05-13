---
name: github-actions-debug
description: Debug failed GitHub Actions CI/CD workflow runs. Use when user asks to fix CI, debug a failed workflow, check why a build failed, investigate GitHub Actions errors, or troubleshoot pipeline failures.
---

# GitHub Actions Debug — Phoenix Agentic Website Frontend

## Repo Context

- **Owner**: `rivie13`
- **Repo**: `Phoenix-Agentic-Website-Frontend`
- **Type**: Public (Website Frontend)

## Workflows in this repo

| Workflow file | Purpose |
|---------------|---------|
| `ci.yml` | Lint + Typecheck + Test + Build on push/PR to main |

## PR gate usage (required)

During PR work, treat failed GitHub Actions checks as a merge blocker:

1. Inspect failed runs for the PR branch.
2. Triage root cause from failing jobs.
3. Fix locally and re-validate (`npm run lint; npm run typecheck; npm run test; npm run build`).
4. Push and verify checks recover.

## CI Pipeline Details

The `ci.yml` workflow runs:
1. **Checkout** code
2. **Setup Node.js** 20 with npm cache
3. **Install dependencies**: `npm ci`
4. **Lint**: `npm run lint`
5. **Typecheck**: `npm run typecheck`
6. **Test**: `npm run test`
7. **Build**: `npm run build`

## Debugging Workflow: Step-by-step

### Step 1: List recent workflow runs

```
mcp_github_github_actions_list(method="list_workflow_runs", owner="rivie13", repo="Phoenix-Agentic-Website-Frontend")
```

### Step 2: List workflow jobs for the failed run

```
mcp_github_github_actions_list(method="list_workflow_jobs", owner="rivie13", repo="Phoenix-Agentic-Website-Frontend", resource_id="<RUN_ID>")
```

### Step 3: Get job logs for the failed job

```
mcp_github_github_get_job_logs(owner="rivie13", repo="Phoenix-Agentic-Website-Frontend", job_id=<JOB_ID>)
```

### Step 4: Analyze the failure

Common failure patterns:

| Failure type | Typical cause | Fix |
|-------------|---------------|-----|
| ESLint error | Style violations | Run `npm run lint` locally, fix violations |
| TypeScript error | Type mismatch, missing annotations | Run `npm run typecheck` locally |
| Test failure | Test assertion error | Run `npm run test` locally |
| Build failure | SSR-incompatible imports, missing env vars | Run `npm run build` locally |
| `npm ci` failure | Lock file out of sync | Run `npm install` and commit `package-lock.json` |

### Step 5: Fix locally and verify

1. Read the error from the job logs
2. Run locally:
   - `npm run lint` — reproduce lint errors
   - `npm run typecheck` — reproduce type errors
   - `npm run test` — reproduce test failures
   - `npm run build` — reproduce build failures
3. Make the fix
4. Run full check to confirm all pass

### Step 6: Re-trigger the workflow (optional)

```
mcp_github_github_actions_run_trigger(owner="rivie13", repo="Phoenix-Agentic-Website-Frontend", workflow_id="ci.yml")
```
