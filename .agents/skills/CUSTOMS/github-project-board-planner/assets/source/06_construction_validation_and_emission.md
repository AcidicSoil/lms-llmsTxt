## Construction Rules

1. Parse and merge sources using `tasks.json` > `PRD.txt` > `README.md`.
2. Preserve task hierarchy from `tasks.json` when present.
3. Convert parent tasks into high-level issues.
4. Convert subtasks into acceptance criteria or dependent issues based on size and independence.
5. Create 3–6 milestones that reflect actual deliverables.
6. Generate at least 10 high-level issues distributed across milestones.
7. Generate at least 2 backlog issues unless the user explicitly forbids backlog items.
8. Give every issue 3–5 acceptance criteria.
9. Start every acceptance criterion with an observable verb.
10. Use imperative, scoped issue titles.
11. Refer to dependencies by issue ID or exact issue title.
12. Use consistent labels and priority values.
13. Do not invent assignees.
14. Do not invent exact dates unless provided.
15. Do not include explanatory prose outside the selected artifact.

---

## Validation Before Emission

Privately validate before emitting:

- `OUTPUT_MODE` is valid; otherwise default to `script`.
- Milestone count is 3–6.
- High-level issue count is at least 10.
- Backlog exists.
- Every non-backlog issue has a milestone.
- Every backlog issue has no milestone.
- Every issue has 3–5 acceptance criteria.
- Every issue has one type label and one priority label.
- Every milestone issue has an `m:<MilestoneKey>` label.
- Every backlog issue has `backlog`.
- Script mode supports `DRY_RUN`.
- Script mode is idempotent by exact project title, field name, label name, milestone title, issue title, and project item URL/content.
- Script mode does not hard-code project field IDs or single-select option IDs.
- Script mode does not require external `jq` unless checked.
- CSV is valid CSV.
- JSON parses as valid JSON.

If validation fails, repair privately and emit only the corrected artifact.

---

## Final Emission Rule

Emit only the artifact for the selected mode. No explanations. No rationale. No citations. No extra text.
