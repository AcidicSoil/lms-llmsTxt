---
name: polish-cli-tool-ux
description: Improves command-line tool user experience while preserving behavior. Use when upgrading CLI projects, command frameworks, entrypoints, help output, completions, errors, validation, terminal formatting, interactive prompts, machine-readable output, and CLI documentation across any language or ecosystem.
metadata:
  short-description: Upgrade plain developer scripts into polished terminal-native CLIs.
---

# Polish CLI Tool UX

## Quick start

Upgrade a CLI project into a polished, modern, terminal-native command-line tool without changing existing behavior.

Start by discovering the project’s actual stack, entrypoints, command framework, commands, options, build/test commands, and documentation. Produce a short implementation plan before editing. Make the smallest safe changes that materially improve help output, discoverability, formatting, validation, completions, errors, interactivity, automation compatibility, and documentation.

Use [references/cli-ux-checklist.md](references/cli-ux-checklist.md) for the full audit checklist, implementation matrix, and acceptance checks.

## Workflow

### 1. Discover structure and locate files

Inspect the repository before proposing or editing anything.

Identify and record:

- Language or languages: `Unknown` if not detectable.
- Package manager or build system: `Unknown` if not detectable.
- CLI entrypoints: `Unknown` if not detectable.
- CLI command framework: `Unknown` if not detectable.
- Existing commands, subcommands, flags, positional arguments, aliases, output modes, and exit-code conventions.
- Existing build, test, lint, format, and smoke-check commands.
- README or usage documentation.
- Completion, config, environment-variable, or machine-readable output support already present.
- Scripts or automation that invoke the CLI.

Prefer repository evidence over assumptions. Search manifests, package metadata, scripts, source files, tests, documentation, and executable wrappers. Do not assume Python, Typer, Click, Node, Go, Rust, Java, .NET, Bash, or any specific ecosystem.

### 2. Read relevant evidence

Read the files that define the CLI interface and its documented behavior:

- Entrypoint files.
- Command registration files.
- Parser or framework configuration.
- Current help text and examples.
- Tests covering CLI behavior.
- README usage sections.
- Packaging or installation metadata.
- CI scripts that run the CLI.

If a likely file is missing, record `Unknown` and continue unless the user explicitly made it mandatory.

### 3. Run safe, allowed commands only when permitted

If execution is available and permitted, run only commands discovered from the repository or explicitly provided by the user.

Prefer non-destructive commands:

- Help output.
- Version output.
- Existing tests.
- Existing lint or format checks.
- Existing smoke commands.
- Dry-run commands when available.

Capture stdout, stderr, and exit codes as evidence. If execution is unavailable, forbidden, or fails, continue with static inspection and record the limitation.

Do not run destructive commands. Do not install new dependencies unless the user explicitly allows dependency changes or the repository’s normal workflow requires it.

### 4. Interpret `{{args}}`

Treat `{{args}}` as the user’s free-form request or constraints for the current invocation.

Use `{{args}}` to determine:

- Scope: full CLI, one command, documentation only, completions only, error handling only, or tests only.
- Permission level: audit-only, plan-only, edit files, add dependencies, run tests.
- Constraints: no dependencies, no interactive prompts, JSON stability, strict backward compatibility, specific command families, or specific docs.

If `{{args}}` is missing or ambiguous, choose the safest useful scope: inspect the CLI, produce an implementation plan, and make only low-risk compatibility-preserving improvements if editing is clearly allowed. Mark unresolved decisions as `TODO`.

### 5. Produce a short implementation plan before editing

Before editing, summarize:

- Detected stack.
- CLI entrypoint and framework found.
- Existing command structure.
- Highest-impact UX gaps.
- Files likely to change.
- Tests or smoke checks to add or run.
- Compatibility risks and how to avoid them.

Keep the plan short and operational.

### 6. Improve CLI UX in-place

Preserve existing behavior while improving the current implementation.

Apply the smallest idiomatic changes for the detected ecosystem:

- If a CLI framework already exists, improve it in-place rather than replacing it.
- If no clear framework exists, recommend or add the smallest idiomatic command layer needed for the detected ecosystem.
- Prefer native ecosystem conventions and libraries.
- Avoid unnecessary dependencies.
- Avoid large rewrites for cosmetic improvements.
- Do not replace the CLI framework without a clear reason.

### 7. Add or update tests and smoke checks

Add deterministic tests or smoke checks for the changed behavior where appropriate.

Cover:

- Root help output.
- Command-level help output.
- Version output.
- Invalid command behavior.
- Invalid option behavior.
- JSON output validity if JSON is added or touched.
- Non-interactive behavior.
- Color suppression or TTY behavior when practical.

Run relevant checks if execution is available. If checks cannot run, report `Unknown` and explain why.

### 8. Produce final implementation report

End with a concise implementation summary containing:

- Detected stack.
- CLI framework or entrypoint found.
- UX improvements applied.
- New flags or features added.
- Completion support added or documented.
- Tests or checks added.
- Commands to verify manually.
- Files changed.
- How to run the CLI.
- How to install completions.
- Limitations or follow-up work.

## Decision rules

### Preserve behavior first

Maintain backward compatibility unless the user explicitly authorizes a breaking change.

Preserve:

- Existing commands.
- Existing flags.
- Existing positional arguments.
- Existing aliases.
- Existing exit codes.
- Existing scripts and automation behavior.
- Existing machine-readable modes.
- Existing JSON schemas or structured output contracts.

When a UX improvement conflicts with compatibility, preserve compatibility and document the tradeoff.

### Improve discoverability

Ensure every command has a concise purpose statement.

Improve root help and command-level help with:

- Clear command descriptions.
- Organized command groups where supported.
- Argument explanations.
- Defaults.
- Environment variable references.
- Config behavior.
- Common examples.
- Readable spacing.
- Aligned columns where supported.
- Copy-pasteable commands.

### Style output semantically

Use terminal styling only where supported and appropriate.

Prefer semantic roles:

- `success`
- `warning`
- `error`
- `info`
- `muted`
- `command`
- `path`
- `option`
- `value`

Add or preserve automatic color detection. Support `--no-color`. Support `--color=auto|always|never` where idiomatic.

Ensure output degrades cleanly in non-TTY environments. Do not emit ANSI color codes in non-TTY output unless explicitly forced.

### Keep human and machine output separate

Keep styled human-readable output separate from machine-readable output.

When adding or improving machine-readable output:

- Add JSON output only where useful.
- Use idiomatic flags such as `--format text|json` when appropriate.
- Emit valid, stable JSON.
- Do not emit spinners, colors, progress bars, panels, dividers, or decorative formatting in JSON mode.
- Keep existing machine-readable modes stable.

### Make interactivity safe

Add interactive prompts only when safe.

Prompt only when:

- Running interactively.
- A required input is missing.
- A destructive action needs confirmation.
- Prompting does not break automation.

For automation:

- Add `--yes` or `--assume-yes` where destructive commands need confirmation.
- Detect CI and non-interactive environments where feasible.
- Fail with actionable errors instead of prompting in non-interactive mode.
- Never make prompts mandatory for scripts.

### Improve errors

Replace raw stack traces with concise user-facing errors by default.

Error output should include:

- What failed.
- Why it likely failed.
- How to fix it.
- Similar command or flag suggestions when supported.
- Consistent formatting.
- Appropriate non-zero exit codes.

Preserve debug stack traces behind `--debug` or equivalent.

### Add professional flags only when appropriate

Add common flags when they fit the command model and do not break compatibility:

- `--help`
- `--version`
- `--verbose`
- `--quiet`
- `--debug`
- `--dry-run`
- `--config`
- `--output`
- `--format text|json`
- `--no-color`
- `--yes`
- `--cwd` or project-root equivalent where useful

Do not add flags that have no implemented behavior. Do not change existing flag semantics.

### Add completion support

Enable or document shell completions for common shells where supported:

- bash
- zsh
- fish
- PowerShell

Add completion for commands, subcommands, flags, enum values, file paths, and known targets where feasible.

Include a command or documentation for installing completions. If the detected ecosystem does not support completions cleanly, record the limitation and provide the smallest viable documented path.

### Avoid full-screen TUI behavior

Keep the result a polished terminal-native CLI, not a full-screen TUI.

Use tables, panels, dividers, box-drawing borders, progress indicators, and spinners only when they improve clarity and do not break scripting.

Use spinners only for indeterminate interactive work. Use progress bars only when meaningful progress is measurable. Suppress both in non-TTY and CI environments.

## Output contract

For audit-only requests, produce:

```markdown
# CLI UX Audit

## Detected stack
- Language:
- Package manager:
- CLI entrypoint:
- CLI framework:
- Build command:
- Test command:

## Current CLI structure
- Commands:
- Global flags:
- Output modes:
- Completion support:
- Config/environment support:

## UX gaps
- Help/discoverability:
- Styling/formatting:
- Errors:
- Validation:
- Completion:
- Interactivity:
- Machine-readable output:
- Documentation:
- Tests:

## Implementation plan
1.
2.
3.

## Risks and compatibility notes
-
```

For implementation requests, produce:

````markdown
# CLI UX Implementation Summary

## Detected stack
-

## CLI framework or entrypoint found
-

## UX improvements applied
-

## New flags/features added
-

## Completion support
-

## Tests/checks added
-

## Files changed
-

## Commands to verify manually
```sh
TODO
```

## How to run the CLI
```sh
TODO
```

## How to install completions
```sh
TODO
```

## Limitations or follow-up work
-
````

Use `TODO` or `Unknown` for missing information. Do not fabricate commands, paths, tools, package names, or runtime behavior.

## Failure modes

### Missing input

Proceed with repository discovery. Write `TODO` for unspecified goals and `Unknown` for facts that cannot be determined.

### Ambiguous requirements

Choose the most compatibility-preserving interpretation, state it explicitly, and proceed.

### Missing files

Record `Unknown` and continue unless the user explicitly states the file is mandatory.

### Unsupported environment capability

Do not fabricate command output. Explain the limitation in the audit or final report and provide static-analysis findings where possible.

### Unsafe or destructive operation

Stop at planning or evidence gathering unless destructive actions are explicitly permitted. For destructive CLI commands, add dry-run previews and confirmation safeguards rather than executing destructive behavior.

### Existing CLI framework conflicts with desired UX

Improve the existing framework in-place where possible. Replace it only when there is a clear, documented reason and the user has authorized that level of change.

### Dependency uncertainty

Prefer no new dependency. If a dependency would materially improve reliability or idiomatic UX, document the reason, compatibility impact, and alternative. Add it only when dependency changes are permitted.

## Invocation examples

### Full CLI polish pass

User request:

```text
Polish this CLI tool UX.
```

Expected action:

- Inspect repository structure.
- Detect stack and entrypoints.
- Plan changes.
- Improve help, formatting, errors, completions, docs, and tests.
- Run available checks.
- Report changes and verification commands.

### Audit only

User request:

```text
Audit this CLI and tell me how to make it feel more professional. Do not edit files.
```

Expected action:

- Inspect repository.
- Run safe read-only help/version/test commands if permitted.
- Produce `CLI UX Audit`.
- Do not modify files.

### Completion support only

User request:

```text
Add shell completions for this CLI.
```

Expected action:

- Detect CLI framework.
- Use native completion support if available.
- Support or document bash, zsh, fish, and PowerShell where feasible.
- Add tests or smoke checks for completion generation when idiomatic.
- Document installation.

### JSON and automation mode

User request:

```text
Make this CLI automation-friendly with JSON output and non-interactive behavior.
```

Expected action:

- Preserve current human output.
- Add or improve `--format json` where useful.
- Suppress colors, spinners, and prompts in JSON/non-interactive mode.
- Validate JSON output in tests.
- Ensure CI usage remains scriptable.

### Error polish

User request:

```text
Improve the CLI errors without hiding real failures.
```

Expected action:

- Replace raw default stack traces with concise user-facing messages.
- Add remediation and suggestions.
- Preserve stack traces behind `--debug` or equivalent.
- Maintain appropriate non-zero exit codes.
