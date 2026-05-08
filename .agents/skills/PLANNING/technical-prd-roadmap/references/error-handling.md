# Error Handling

## Common Issues

| Issue | Response |
|---|---|
| Scope is too broad | Split into sequenced PRDs by dependency and outcome |
| Missing repository facts | Mark assumptions and request/perform codebase inspection before naming exact files |
| User says “proceed” | Use approved context and choose the safest enabling workstream |
| PRD lacks dependencies | Convert modules into layered dependency chain before writing phases |
| Feature is too vague | Add inputs, outputs, behavior, and acceptance criteria |
| Circular dependency appears | Extract shared contracts or split responsibilities |

## Guardrails

- Do not add timelines unless requested.
- Do not optimize before eval evidence exists.
- Do not promote or apply changes without explicit source-change workflow.
- Do not hide missing evidence; state it as a risk or prerequisite.
