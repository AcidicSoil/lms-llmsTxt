---
name: production-workflow-runbook
description: "Generate production-ready delivery runbooks for brownfield or greenfield software projects by target type. WHEN: \"create an e2e runbook\", \"production workflow\", \"delivery runbook\", \"web app runbook\", \"CLI tool runbook\", \"AI app runbook\", \"brownfield greenfield\"."
license: MIT
metadata:
  version: "1.0.0"
---

# Production Workflow Runbook

Create execution-grade runbooks that take a project from intake to polished production launch.

## Workflow

1. Classify the request: target type, brownfield vs greenfield, release surface, finish line, and constraints.
2. Load [Core Lifecycle](references/core-lifecycle.md) and [Project Overlays](references/project-overlays.md).
3. Load only the matching target references: [Web App](references/targets/web-app.md), [CLI Tool](references/targets/cli-tool.md), [Dev Tool](references/targets/dev-tool.md), [AI App](references/targets/ai-app.md), [API Service](references/targets/api-service.md), [Library SDK](references/targets/library-sdk.md), [Mobile App](references/targets/mobile-app.md), or [Browser Extension](references/targets/browser-extension.md).
4. Add [Production Readiness](references/production-readiness.md) and use [Output Templates](references/output-templates.md) for consistent structure.
5. Produce a concrete runbook with phases, artifacts, gates, target-specific risks, verification, and definition of done.

## Output Contract

Always include:
- assumptions and scope
- canonical lifecycle
- brownfield or greenfield overlay
- target-specific workflow
- artifacts to create
- release gates
- polish checklist
- production-readiness checklist
- done criteria

## Examples

| Input | Expected output |
|---|---|
| "Create a production runbook for a greenfield AI app" | AI-app lifecycle with evals, safety, telemetry, UX polish, and launch gates |
| "Brownfield CLI migration runbook" | Baseline, compatibility, characterization tests, command UX, packaging, and rollout plan |

## Error Handling

If target type is missing, choose the closest conventional target and label the assumption. If multiple targets apply, generate a shared lifecycle plus separate target overlays. If scope is too broad, keep the runbook phased and explicitly separate required gates from optional enhancements.
