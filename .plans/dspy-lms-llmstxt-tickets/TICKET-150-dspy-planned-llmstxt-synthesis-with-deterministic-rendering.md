---
ticket_id: "tkt_lmsllmstxt_authoritative_synthesis"
title: "Final llms.txt content is planned by DSPy while markdown formatting stays deterministic"
agent: "codex"
done: false
goal: "The final llms.txt artifact is based on DSPy-owned section planning and content synthesis, while local code remains the deterministic formatter and fallback path stays intact."
---

## Tasks
- Add DSPy modules for `llms.txt` section planning and final content synthesis.
- Make final semantic decisions model-controlled under explicit constraints while keeping local code as the final markdown formatter.
- Refactor `GenerateLLMsTxt` into the authoritative planning or synthesis path, or remove it if it remains redundant.
- Promote `GenerateUsageExamples` into final section planning and output generation, or remove the call if it remains unused.
- Preserve the fallback heuristic bucket renderer as a separate failure path.

## Acceptance criteria
- Final `llms.txt` inclusion, ordering, and section content come from the DSPy planning and synthesis path rather than only deterministic local bucket logic.
- Final markdown serialization remains deterministic and is not replaced by free-form model formatting.
- Fallback generation remains separate and available when LM connectivity or synthesis fails.
- CLI and FastMCP consumers keep the existing artifact contract.

## Tests
- Generate `llms.txt` artifacts for representative repositories and verify the section plan drives output content while markdown shape remains stable.
- Simulate synthesis failure and verify fallback artifact generation still runs.
- Verify CLI and FastMCP outputs remain compatible with the existing contract.

## Notes
- Source: "Move final semantic decisions into DSPy, keep markdown formatting deterministic", "GenerateLLMsTxt should either become authoritative or be removed", "GenerateUsageExamples should either feed the artifact or be deleted."
- Constraints:
  - Do not replace deterministic artifact formatting with free-form model output.
  - Do not collapse the fallback generator into the DSPy path.
  - Do not disturb the artifact contract consumed by external tooling.
- Evidence:
  - `GenerateLLMsTxt`
  - `GenerateUsageExamples`
  - `render_llms_markdown`
- Dependencies:
  - TICKET-100-repository-analyzer-staged-pipeline.md
  - TICKET-110-pin-and-audit-dspy-litellm-upgrade-path.md
  - TICKET-130-selective-evidence-planning-for-large-repos.md
- Unknowns:
  - Exact section taxonomy beyond example sections is not fully specified.
