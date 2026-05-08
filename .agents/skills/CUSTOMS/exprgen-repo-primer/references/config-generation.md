# Exprgen Config Generation Guidance

Generate configs that match exprgen's current declarative recipe model.

## Supported Recipe Fields

| Field | Use |
|---|---|
| `description` | Short human-readable purpose. |
| `triggers` | Alternate names developers may type. |
| `paths` | One or more repo-relative search roots. |
| `directory` | Single fallback search root when `paths` is absent. |
| `extensions` | File extensions converted to ripgrep globs. |
| `intent` | Limited search shape with `kind`, `base`, and `file_extensions`. |
| `compiler` | Optional literal `ripgrep`. |

Keep recipes declarative. Do not emit executable hooks, shell snippets, arbitrary command templates, aliases, or unsupported fields.

## Heuristics

1. Prefer stable repo concepts over one-off filenames.
2. Use concise recipe names developers will naturally type: `docs`, `src`, `tests`, `configs`, `adrs`, `cli`, `schemas`, `migrations`, `examples`.
3. Add triggers for common synonyms: `documentation`, `source`, `specs`, `settings`.
4. Scope paths narrowly enough to reduce noise but broadly enough to survive refactors.
5. Use extensions only when they materially improve search precision.
6. Exclude generated folders by not selecting them as recipe paths; exprgen recipes do not currently support exclude globs.
7. When a desired behavior is not supported by recipes, add a caveat instead of forcing invalid YAML.

## Review Checks

- YAML is valid.
- Recipe keys use only supported fields.
- Paths are repo-relative and observed or clearly marked as proposed.
- Recipe names are short, lowercase, and memorable.
- Examples follow `search <recipe> for <query>`.
- Output does not claim exprgen executes commands; it generates command expressions.

## Example

```yaml
recipes:
  docs:
    description: Search project documentation
    triggers:
      - documentation
    paths:
      - docs
    extensions:
      - md
```

Example prompt: `exprgen search docs for install`.
