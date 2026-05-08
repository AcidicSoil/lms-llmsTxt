## Output Specifications by Mode

### 1) `OUTPUT_MODE=script` -> Bash script using GitHub CLI

Emit exactly one fenced code block with language `bash`.

The script must define these placeholders at the top:

```bash
: "${OWNER:=your-org-or-user}"
: "${REPO:=your-repo}"
: "${PROJECT_NAME:=Project Roadmap}"
: "${PROJECT_VISIBILITY:=private}"
: "${DRY_RUN:=true}"
: "${LINK_PROJECT_TO_REPO:=true}"
: "${DEFAULT_STATUS:=Todo}"
```

Include this usage header:

```bash
# Usage:
#   OWNER=my-org REPO=my-repo PROJECT_NAME="Roadmap" PROJECT_VISIBILITY=private DRY_RUN=true bash GitHub_Project_Plan.sh
#   OWNER=my-org REPO=my-repo PROJECT_NAME="Roadmap" PROJECT_VISIBILITY=private DRY_RUN=false bash GitHub_Project_Plan.sh
```

The script must:

1. Run pre-flight checks.
2. Ensure the project exists and visibility is applied.
3. Optionally link the project to the repository.
4. Ensure `Status`, `Priority`, and `Estimate` fields exist.
5. Ensure labels exist.
6. Ensure milestones exist.
7. Create or reuse issues.
8. Add missing issues to the project.
9. Set project item fields for status, priority, and numeric estimates.
10. Print a final summary.

Use functions for repeatable operations. Fail fast for unexpected mutation errors when `DRY_RUN=false`. Clean up temporary files.

---

### 2) `OUTPUT_MODE=csv` -> Portable issue-import CSV

Emit exactly one fenced code block with language `csv`.

CSV mode is a portable issue-import artifact for external import workflows. Do not claim GitHub.com provides a universal native CSV issue importer.

Header:

```csv
Title,Body,Labels,Milestone,Assignees
```

Rules:

- Escape CSV fields correctly.
- `Body` must include `Context`, `Acceptance Criteria`, `Dependencies`, `Estimate`, and `Source` sections.
- Labels are semicolon-separated inside one CSV cell, such as `enhancement;m:M1;priority:P1`.
- Backlog items have an empty `Milestone` cell and include `backlog`.
- Assignees are comma-separated inside one CSV cell when present; otherwise empty.

---

### 3) `OUTPUT_MODE=json` -> Project and issue payload

Emit exactly one fenced code block with language `json`.

Use this shape:

```json
{
  "project": {
    "name": "<PROJECT_NAME>",
    "visibility": "private|public",
    "platform": "GitHub Projects v2"
  },
  "overview": {
    "name": "...",
    "goals": [],
    "scope": "...",
    "nonGoals": [],
    "stakeholders": [],
    "environments": [],
    "repos": [],
    "risks": [],
    "assumptions": []
  },
  "milestones": [
    {
      "key": "M1",
      "title": "M1: <Name>",
      "description": "...",
      "deliverable": "...",
      "dependencies": []
    }
  ],
  "issues": [
    {
      "id": "ISS-001",
      "title": "...",
      "body": {
        "context": "...",
        "acceptanceCriteria": ["...", "...", "..."],
        "dependencies": ["ISS-000 or exact issue title"],
        "estimate": { "scale": "pts", "value": null },
        "source": { "file": "tasks.json|PRD|README|inferred", "section": "..." }
      },
      "labels": ["enhancement", "m:M1", "priority:P1"],
      "milestone": "M1: <Name>",
      "assignees": [],
      "priority": "P1",
      "type": "feature"
    }
  ],
  "backlog": [
    {
      "id": "ISS-B001",
      "title": "...",
      "body": {
        "context": "...",
        "acceptanceCriteria": ["...", "...", "..."],
        "dependencies": [],
        "estimate": { "scale": "pts", "value": null },
        "source": { "file": "inferred", "section": "Backlog" }
      },
      "labels": ["backlog", "enhancement", "priority:P2"],
      "milestone": null,
      "assignees": [],
      "priority": "P2",
      "type": "feature"
    }
  ]
}
```

Rules:

- JSON must parse as valid JSON.
- Use `null`, not empty strings, for unknown numeric estimates.
- Keep issue body fields structured; do not collapse them into Markdown strings.
- Backlog items must use `"milestone": null`.

---
