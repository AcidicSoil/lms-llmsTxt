## Required Plan Characteristics

- Generate at least **10 high-level issues**.
- Each issue must include **3–5 acceptance criteria**.
- Group issues into **3–6 milestones/phases** mapped to real deliverables.
- Include a **Backlog** group for future, optional, deferred, or unscoped work.
- Include labels, dependencies, priority, issue type, and effort estimate placeholders.
- Keep issue titles imperative, scoped, and implementation-ready.
- Avoid duplicate or near-duplicate issues.
- Use concise, non-marketing language.

---

## Normalized Internal Model

Build this internal model before emitting any artifact:

```text
ProjectOverview {
  name,
  goals[],
  scope,
  non_goals[],
  stakeholders[],
  environments[],
  repos[],
  risks[],
  assumptions[]
}

Milestones [
  {
    key: "M1",
    name,
    description,
    start?,
    end?,
    deliverable,
    dependencies[]
  }
]

Issues [
  {
    id,
    title,
    milestoneKey,
    description,
    acceptanceCriteria[3..5],
    labels[],
    assignees?,
    dependencies[],
    estimate?: { scale: "pts" | "days", value? },
    priority?: "P0" | "P1" | "P2",
    type?: "feature" | "bug" | "chore" | "docs",
    source: { file: "tasks.json" | "PRD" | "README" | "inferred", section? }
  }
]

BacklogIssues [
  ...same issue shape...
]
```

---

## Label Taxonomy

Use these labels consistently:

- Type labels: `enhancement`, `bug`, `docs`, `chore`
- Milestone labels: `m:M1`, `m:M2`, `m:M3`, etc.
- Priority labels: `priority:P0`, `priority:P1`, `priority:P2`
- Backlog label: `backlog`
- Optional domain labels only when clearly useful: `api`, `ui`, `infra`, `security`, `testing`, `data`, `ci`, `auth`, `db`

Map internal issue type to GitHub label:

- `feature` -> `enhancement`
- `bug` -> `bug`
- `docs` -> `docs`
- `chore` -> `chore`

---

## Milestone Rules

- Use milestone keys `M1`, `M2`, `M3`, etc.
- Milestone titles must be `M1: <Name>`.
- Milestone descriptions must name the deliverable and major dependencies.
- Backlog issues have no GitHub milestone and must include the `backlog` label.
- Milestones must be deliverable-oriented, not team- or department-oriented.

---

## Issue Body Format

Every Markdown issue body must include these sections in this order:

```markdown
## Context
<short implementation context>

## Acceptance Criteria
- [ ] <observable criterion>
- [ ] <observable criterion>
- [ ] <observable criterion>

## Dependencies
- <issue id, exact issue title, or None>

## Estimate
- Scale: pts
- Value: TBD

## Source
- File: <tasks.json|PRD|README|inferred>
- Section: <section or N/A>
```

Acceptance criteria must start with observable verbs such as `Create`, `Render`, `Validate`, `Persist`, `Reject`, `Return`, `Log`, `Deploy`, `Document`, `Test`, `Verify`, `Handle`, `Expose`, `Migrate`, `Seed`, or `Configure`.

---
