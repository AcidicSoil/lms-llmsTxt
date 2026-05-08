---
name: exprgen-repo-primer
description: "Scans repositories and drafts project-specific exprgen recipe configs. WHEN: \"prime exprgen\", \"generate exprgen config\", \"scan repo for exprgen recipes\", \"propose .exprgen.yaml\", \"setup exprgen for this repo\"."
---

# Exprgen Repo Primer

Use this skill to inspect a repository before development starts and draft a safe, declarative `.exprgen.yaml` that primes exprgen with common project search scopes.

## Workflow

1. **Scan the repo** - Inspect directory names, file extensions, package/config files, docs, tests, scripts, generated-output folders, and domain vocabulary.
2. **Infer recurring expressions** - Identify frequent developer searches such as source code, docs, tests, configs, ADRs, migrations, schemas, CLI code, or examples.
3. **Generate recipes only** - Produce `.exprgen.yaml` using supported declarative recipe fields; never add shell hooks, command templates, or executable config.
4. **Explain choices** - For each recipe, include its purpose, paths, extensions, triggers, and one example request.
5. **Flag uncertainty** - Mark missing paths, unsupported recipe needs, or risky assumptions instead of inventing repo facts.

For detailed rules, use [config generation guidance](references/config-generation.md). For the output shape, use the [exprgen config template](templates/exprgen-config.yaml). If filesystem access is available, the [repo scanner script](scripts/scan-repo.sh) can summarize directories and extensions first.

## Output

Return:

1. Proposed `.exprgen.yaml`.
2. Recipe rationale table.
3. Starter exprgen prompts for developers.
4. Caveats and manual review items.
