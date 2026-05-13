# CLI UX Checklist

Use this reference while auditing or implementing CLI polish improvements.

## Discovery checklist

Record each item as detected, `Unknown`, or `TODO`.

| Area | Evidence to collect |
|---|---|
| Language | Source extensions, manifests, build files |
| Package manager | Lockfiles, manifests, scripts |
| CLI entrypoints | Executables, package bin metadata, command wrappers, main functions |
| CLI framework | Parser imports, command registration, help generation |
| Commands | Root command, subcommands, aliases, hidden/internal commands |
| Arguments | Positional arguments, defaults, required values |
| Options | Global flags, command flags, env-var-backed options |
| Output modes | Text, JSON, quiet, verbose, debug, logs |
| Error handling | Exceptions, validation errors, exit codes, stack traces |
| Completion | Existing completion commands, generated scripts, docs |
| Interactivity | Prompts, confirmations, CI behavior, non-TTY behavior |
| Config | Explicit flags, environment variables, config files, defaults |
| Documentation | README usage, examples, completion docs, env vars, config docs |
| Tests | CLI unit tests, integration tests, shell smoke tests, snapshots |
| CI | Commands that verify CLI starts and help renders |

## Implementation priority

Apply improvements in this order unless `{{args}}` narrows scope:

1. Preserve current behavior and establish a baseline.
2. Improve help text and command descriptions.
3. Add or refine validation and user-facing errors.
4. Add safe color and formatting controls.
5. Add completion support or completion documentation.
6. Add automation-friendly output modes.
7. Add safe interactive prompts and destructive-action confirmations.
8. Add progress indicators for long-running interactive work.
9. Update documentation.
10. Add tests and smoke checks.

## Help and discoverability

Verify:

- Root help has a clear one-line summary.
- Root help lists commands with concise descriptions.
- Commands are grouped logically where supported.
- Command help explains positional arguments.
- Command help explains options and defaults.
- Required arguments are visibly marked.
- Environment variables are documented.
- Config file behavior is documented.
- Examples cover common workflows.
- Examples are copy-pasteable.
- Text is readable in a standard terminal width.
- Columns align where the framework supports alignment.
- Deprecated commands or aliases are labeled without breaking them.

## Structured styled output

Target a polished terminal-native feel without breaking scripts.

Use styling for meaning, not decoration:

| Semantic role | Use for |
|---|---|
| success | Completed operations |
| warning | Recoverable problems, risky choices |
| error | Failed operations |
| info | Neutral status |
| muted | Secondary details |
| command | Commands the user can run |
| path | File and directory paths |
| option | Flags and options |
| value | User-provided or computed values |

Verify:

- Color is automatically disabled in non-TTY output.
- `--no-color` is supported.
- `--color=auto|always|never` is supported where idiomatic.
- Colors are not hardcoded in ways that become unreadable on dark or light themes.
- JSON and machine-readable output never contains ANSI styling.
- Tables and panels are used only when they improve comprehension.
- Decorative formatting is suppressed for automation.

## Shell completion

Add or document completion support for:

- bash
- zsh
- fish
- PowerShell

Completion targets to consider:

- Commands.
- Subcommands.
- Flags.
- Enum values.
- File paths.
- Known project targets.
- Config profile names.
- Output formats.
- Shell names.

Document:

- How to generate completion scripts.
- How to install completion scripts.
- Whether completion generation is dynamic or static.
- Any shell-specific limitations.

If completion support is not feasible, record `Unknown` or `TODO` with the reason.

## Interactive ergonomics

Add prompts only when safe.

Interactive prompts may be used for:

- Missing required input.
- First-time setup.
- Confirmation before destructive actions.
- Optional next-step guidance after success.

Automation safeguards:

- Detect non-interactive mode where feasible.
- Detect CI where feasible.
- Fail with actionable errors instead of prompting when non-interactive.
- Add `--yes` or `--assume-yes` for destructive operations.
- Add `--dry-run` previews for file or external-state changes.
- Never require a prompt for scripts.

Confirmation prompts should make clear:

- What will change.
- What target is affected.
- Whether the action is reversible.
- How to bypass safely for automation.

## Error UX

User-facing errors should be concise and actionable.

Preferred structure:

```text
Error: <what failed>

Cause: <likely cause, when known>
Fix: <specific remediation>
Try: <copy-pasteable command or valid values, when useful>
```

Verify:

- Raw stack traces are hidden by default.
- `--debug` or equivalent exposes stack traces/logs.
- Invalid commands suggest similar commands where supported.
- Invalid flags suggest similar flags where supported.
- Invalid enum values list valid values.
- Missing files include the checked path.
- Config errors include the source file or variable.
- Exit codes remain appropriate and backward compatible.
- Real errors are not swallowed.

## Professional flags

Consider adding these only when they are meaningful and idiomatic:

| Flag | Purpose |
|---|---|
| `--help` | Help output |
| `--version` | Version output |
| `--verbose` | More detail |
| `--quiet` | Less human output |
| `--debug` | Debug logs or stack traces |
| `--dry-run` | Preview changes |
| `--config` | Config file path |
| `--output` | Output file path |
| `--format text|json` | Human or machine output |
| `--no-color` | Disable ANSI styling |
| `--yes` / `--assume-yes` | Non-interactive confirmation |
| `--cwd` | Project root or working directory override |

Rules:

- Do not add a flag without implemented behavior.
- Do not change existing flag semantics.
- Keep global options available across subcommands where the framework supports it.
- Preserve aliases and old options.

## Machine-readable output

When adding JSON or other structured output:

- Keep human output and machine output separate.
- Emit valid JSON only.
- Do not print logs, banners, spinners, progress, color, panels, or warnings to stdout in JSON mode.
- Send diagnostics to stderr if required and safe.
- Keep schemas stable.
- Add tests that parse the JSON.
- Preserve existing machine-readable modes.

## Progress and long-running operations

Use progress UX only when it helps.

| Situation | UX |
|---|---|
| Unknown duration, interactive TTY | Spinner |
| Known measurable progress, interactive TTY | Progress bar |
| Non-TTY, CI, JSON, quiet mode | No spinner or progress bar |
| Completion | Summary with elapsed time when useful |

Avoid:

- Spinners in scripts.
- Progress bars when progress cannot be measured.
- Decorative output that makes logs noisy.
- Rewriting output in environments that do not support it.

## Validation and suggestions

Validate before work begins when possible:

- Paths exist or are creatable as appropriate.
- Config files exist and parse.
- Enum values are valid.
- Required inputs are present.
- Mutually exclusive options are not combined.
- Output paths are writable.
- Destructive operations target the intended resource.
- Project root detection is correct.

Suggestions should include:

- Valid enum values.
- Similar command names.
- Similar option names.
- Expected file path or config location.
- Example command.

## Documentation updates

Update README or equivalent docs with:

- CLI usage section if absent.
- Root command example.
- Common workflow examples.
- Command-specific examples.
- Completion installation.
- Environment variables.
- Config file behavior.
- Config precedence.
- JSON or output format behavior.
- Color and non-interactive behavior.
- Exit-code documentation if idiomatic.
- Before/after examples when useful.
- `doctor`, `check`, or `init` behavior if added.

Config precedence should be documented as:

1. Explicit flags.
2. Environment variables.
3. Config file.
4. Defaults.

## Tests and smoke checks

Add or update deterministic coverage for:

- Root help output.
- Command-level help output.
- Version output.
- Invalid command behavior.
- Invalid option behavior.
- Required argument validation.
- Mutually exclusive option validation.
- JSON output validity if JSON exists.
- Non-interactive behavior.
- Color suppression where practical.
- Completion generation where practical.
- Destructive command confirmation or `--dry-run` behavior where relevant.

Testing rules:

- Do not rely on terminal color support unless explicitly testing color.
- Prefer stable assertions over brittle full snapshots unless snapshot testing is idiomatic.
- Preserve existing tests.
- Add shell-level smoke tests where idiomatic.
- Include a CI check that verifies the CLI starts and help renders where feasible.

## Nice-to-have enhancements

Consider only when appropriate for the project:

- Command aliases for common workflows.
- `doctor` or `check` command for environment validation.
- `init` command for first-time setup.
- Project root autodetection.
- Helpful next steps after setup/init commands.
- Rich tables for lists and summaries.
- `--dry-run` previews for state-changing commands.
- Better install/update/version messaging.
- Consistent logging levels.
- Manpage generation.
- Markdown help generation.
- Snapshot tests for help output.
- Global options shared across subcommands.

## Hard constraints

Follow these constraints exactly:

- Do not turn the CLI into a full-screen TUI unless explicitly requested.
- Do not add decorative output that breaks scripting.
- Do not emit ANSI color codes in non-TTY output unless forced.
- Do not make interactive prompts mandatory for automation.
- Do not replace the existing CLI framework without a clear reason.
- Do not introduce large dependencies for minor formatting improvements.
- Do not remove existing flags, commands, aliases, or output modes.
- Do not hide real errors; provide debug access for stack traces or logs.
- Do not invent commands, file paths, package names, or runtime behavior.
- Do not run destructive operations unless explicitly permitted.

## Acceptance criteria

A completed CLI polish pass satisfies:

- CLI help output is visibly structured, readable, and professional.
- Existing commands still work.
- Existing flags, arguments, aliases, exit codes, and automation paths are preserved.
- Common shell completions are available or documented.
- Errors are actionable and consistently formatted.
- Interactive prompts appear only when safe.
- Non-interactive and CI usage remain automation-friendly.
- JSON or machine-readable output is clean when provided.
- Tests or smoke checks verify main CLI behavior.
- Implementation remains idiomatic for the detected language and ecosystem.
