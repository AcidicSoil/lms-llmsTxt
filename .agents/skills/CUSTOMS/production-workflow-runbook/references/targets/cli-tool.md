# CLI Tool Runbook

## End State

Stable, distributable CLI with excellent help text, predictable behavior, upgrade path, and cross-platform support.

## Critical Tracks

- command model
- argument parsing
- output UX
- config/auth
- packaging/distribution
- platform compatibility
- shell ergonomics
- docs/examples

## Workflow

1. Define personas: human operator, developer, CI user. Specify interactive and non-interactive modes.
2. Design command tree, flags, defaults, exit codes, machine-readable output, prompts, help text, and config precedence.
3. Build parser, logging levels, config loader, credential handling, version/update command, shell completion, installer, telemetry policy.
4. Build slices: init/bootstrap, config/auth, core command path, output/report/export, diagnostics, CI mode.
5. Harden: Windows/macOS/Linux, paths, permissions, non-TTY execution, network failure, retries, idempotency, shell quoting, large output.
6. Polish: intuitive names, crisp help, useful examples, actionable errors, quiet default output, diagnostic verbose mode.

## Production Checklist

- package publishing path documented
- install, uninstall, and upgrade tested
- versioning policy defined
- changelog process defined
- completion scripts available
- clean-environment smoke tests in CI
- stable exit code contract documented

## Brownfield Notes

Preserve commands, flags, output formats, and exit codes unless intentionally version-breaking. Deprecate with warnings before removal.
