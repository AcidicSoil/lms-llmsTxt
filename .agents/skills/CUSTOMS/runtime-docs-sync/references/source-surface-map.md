# Source Surface Map

Use this to choose where documentation changes belong.

## Surface Selection

| Behavior | Primary doc surface |
|---|---|
| New command or flag | CLI reference and README quickstart |
| Runtime boundary or live-session behavior | Runtime notes or operations guide |
| Generated files | Artifact contract/reference |
| User-facing setup path | README or getting-started guide |
| Completed/remaining work | TODO, plan, roadmap, or tracking doc |
| Internal rationale | ADR or implementation note |

## Procedure

1. Search the repo for existing docs that already mention the feature, command, artifact, or runtime.
2. Prefer updating the owning surface over adding a new file.
3. If several docs mention the same behavior, update each at its proper abstraction level.
4. Avoid duplicating long explanations across docs; link from summaries to the canonical reference.
5. Keep service/tool-specific details out of generic docs unless the generic doc is explicitly the owner.

## Anti-Drift Rule

A new documentation surface is justified only when no existing doc owns the concept or the existing doc would become structurally incoherent after the update.
