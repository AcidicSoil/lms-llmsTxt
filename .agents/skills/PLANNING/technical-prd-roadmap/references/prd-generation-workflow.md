# PRD Generation Workflow

Use this guide when converting notes, approvals, or transcripts into technical PRDs.

## Steps

1. **Scope the workstream** — Identify the approved decision, what is in scope, and what must be deferred.
2. **Pick the template** — Use the base template for concise PRDs; use RPG when implementation order, modules, and dependencies matter.
3. **Write product context first** — Problem, users, value, success metrics, and assumptions.
4. **Decompose functionally** — Capabilities describe what the system does. Features include inputs, outputs, and behavior.
5. **Decompose structurally** — Repository modules describe where functionality lives and what each module exports.
6. **Order by dependency** — Foundation first, then layers that depend on it. Avoid circular dependencies.
7. **Phase the roadmap** — Each phase needs entry criteria, tasks, acceptance criteria, tests, exit criteria, and delivered value.
8. **Close with safeguards** — Add risks, mitigations, non-goals, open questions, and next PRD scope.

## Split Criteria

Split into multiple PRDs when workstreams have different users, artifacts, commands, owners, or risk gates.

## Sequencing Pattern

Discovery or inventory → classification or context mapping → evaluation → decisioning → optimization → promotion or rollout.
