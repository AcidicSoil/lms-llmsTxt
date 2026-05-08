## Current GitHub Technical Rules for Script Mode

When `OUTPUT_MODE=script`, generate a Bash script that is current for GitHub CLI and GitHub Projects v2.

### GitHub CLI and Auth

- Use `gh` as the primary interface.
- Verify `gh` is installed.
- Verify authentication with `gh auth status`.
- Project commands require the GitHub Projects scope. If project commands fail for authorization reasons, print a clear instruction to run:

```bash
gh auth refresh -s project
```

- Prefer `gh --json`, `--jq`, and `--format json` where available.
- Do not require external `jq` unless the script explicitly checks for it.

### Project Creation and Visibility

- Use GitHub Projects v2 commands.
- Create projects with:

```bash
gh project create --owner "$OWNER" --title "$PROJECT_NAME" --format json
```

- Do **not** pass visibility to `gh project create`.
- Apply visibility separately with:

```bash
gh project edit "$PROJECT_NUMBER" --owner "$OWNER" --visibility PUBLIC
# or
gh project edit "$PROJECT_NUMBER" --owner "$OWNER" --visibility PRIVATE
```

- The input variable may be lowercase `private|public`; map it to `PRIVATE|PUBLIC` before calling GitHub CLI.
- Reuse an existing project when a project with the exact title already exists for `OWNER`.
- Capture both project number and project node ID.
- Optionally link the project to the repository with `gh project link` when appropriate.

### Project Fields

- Discover fields with:

```bash
gh project field-list "$PROJECT_NUMBER" --owner "$OWNER" --format json
```

- Never hard-code project field IDs.
- Never hard-code single-select option IDs.
- Ensure these project fields exist:
  - `Status`: `SINGLE_SELECT` with options `Todo`, `In Progress`, `Blocked`, `Done`
  - `Priority`: `SINGLE_SELECT` with options `P0`, `P1`, `P2`
  - `Estimate`: `NUMBER`
- Re-read project field metadata after creating fields.
- Resolve field IDs and option IDs before setting item values.

### Project Items

- Add issues to the project explicitly with:

```bash
gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$ISSUE_URL" --format json
```

- Do not rely on `gh issue create --project` when project fields need to be set.
- Find or capture the project item ID before editing fields.
- Set fields with `gh project item-edit` using:
  - `--id <project-item-id>`
  - `--project-id <project-node-id>`
  - `--field-id <field-id>`
  - exactly one value flag per call, such as `--single-select-option-id`, `--number`, `--text`, or `--date`
- Use separate `gh project item-edit` calls for `Status`, `Priority`, and `Estimate`.
- Set `Estimate` only when a numeric value is known. Otherwise leave the project field empty and keep `TBD` in the issue body.

### Labels, Milestones, and Issues

- Labels may be managed with `gh label list` / `gh label create` or with `gh api`.
- Repository milestones are managed through REST endpoints using `gh api`; do not assume a first-class `gh milestone` command.
- Reuse milestones by exact title.
- Reuse labels by exact label name.
- Reuse issues by exact title match in the target repository.
- Write multiline issue bodies to temporary files and pass them with `--body-file`.
- Omit `--milestone` for backlog issues.
- Omit assignee flags when assignees are empty.
- Include dependencies in issue bodies. Do not claim native GitHub issue dependency links are created unless the script actually calls the relevant dependency API and verifies success.

### Idempotency and Safety

The script must be safe to re-run. It must not duplicate:

- Projects
- Fields
- Labels
- Milestones
- Issues
- Project items

Respect `DRY_RUN=true` by printing actions instead of mutating GitHub.

Use safe quoting for all titles, bodies, labels, milestone names, URLs, and user-provided values. Avoid GNU-only Bash features; target macOS Bash 3.2+ compatibility unless the user requests otherwise.

---
