---
name: go-cli
description: >
  Reference skill for idiomatic Go CLI development with cobra. Load this skill when
  implementing a Go CLI binary — covers cobra command structure, go.mod setup in a
  mixed-language monorepo (Go alongside Bash), cross-platform build matrix for
  GitHub Actions (darwin/linux/windows × amd64/arm64), version injection via ldflags,
  and error handling conventions. Use whenever implementing or extending a Go CLI,
  adding new cobra subcommands, setting up build pipelines for Go binaries, or
  when the task involves cmd/cardo or internal/ Go packages.
---

# Go CLI Reference (cobra)

## go.mod in a Mixed-Language Monorepo

Place `go.mod` at the repo root when Go and Bash coexist. The module path should
match where binaries will be distributed from — use the GitHub URL convention:

```go
module github.com/your-org/your-repo

go 1.22

require (
    github.com/spf13/cobra v1.8.1
    github.com/charmbracelet/bubbletea v1.1.1
    github.com/charmbracelet/lipgloss v0.13.0
    gopkg.in/yaml.v3 v3.0.1
)
```

Run `go mod tidy` after editing to regenerate `go.sum`. Commit both files.
ShellCheck and other Bash linting is unaffected by `go.mod` presence.

## Command Structure with cobra

### Entry Point

```go
// cmd/cardo/main.go
package main

import (
    "fmt"
    "os"

    "github.com/your-org/your-repo/internal/cmd"
)

var version = "dev" // overridden at build time via ldflags

func main() {
    if err := cmd.NewRootCmd(version).Execute(); err != nil {
        fmt.Fprintln(os.Stderr, err)
        os.Exit(1)
    }
}
```

### Root Command

```go
// internal/cmd/root.go
package cmd

import (
    "github.com/spf13/cobra"
)

func NewRootCmd(version string) *cobra.Command {
    root := &cobra.Command{
        Use:           "cardo",
        Short:         "Agentic Workforce Orchestrator",
        SilenceUsage:  true,  // don't print usage on error
        SilenceErrors: true,  // handle errors in main
        RunE: func(cmd *cobra.Command, args []string) error {
            // default: open TUI board
            return runBoard(cmd.Context())
        },
    }

    root.AddCommand(
        newApproveCmd(),
        newEscalateCmd(),
        newVersionCmd(version),
    )

    return root
}
```

Key cobra flags:
- `SilenceUsage: true` — prevents usage dump on every error (show it only on bad flags)
- `SilenceErrors: true` — lets main handle error printing consistently
- `RunE` over `Run` — use `RunE` whenever the command can fail; return `fmt.Errorf(...)` to propagate

### Subcommand

```go
// internal/cmd/approve.go
package cmd

import (
    "fmt"
    "github.com/spf13/cobra"
    "github.com/your-org/your-repo/internal/actions"
)

func newApproveCmd() *cobra.Command {
    return &cobra.Command{
        Use:   "approve <issue-number>",
        Short: "Approve a pending gate decision",
        Args:  cobra.ExactArgs(1),
        RunE: func(cmd *cobra.Command, args []string) error {
            msg, err := actions.Approve(projectRoot(), args[0])
            if err != nil {
                return fmt.Errorf("approve: %w", err)
            }
            fmt.Println(msg)
            return nil
        },
    }
}
```

### Version Subcommand

```go
func newVersionCmd(version string) *cobra.Command {
    return &cobra.Command{
        Use:   "version",
        Short: "Print version",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Println(version)
        },
    }
}
```

## Version Injection via ldflags

Build with version baked in at compile time:

```bash
VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "dev")
go build \
  -ldflags "-X main.version=${VERSION}" \
  -o cardo \
  ./cmd/cardo
```

In GitHub Actions:

```yaml
- name: Build
  run: |
    VERSION="${{ github.ref_name }}"
    go build \
      -ldflags "-X main.version=${VERSION}" \
      -o dist/cardo-${{ matrix.goos }}-${{ matrix.goarch }}${{ matrix.ext }} \
      ./cmd/cardo
```

The variable name (`main.version`) must match the package + variable exactly.

## Cross-Platform Build Matrix

Use a hand-rolled bash matrix (no GoReleaser needed for simple cases):

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        include:
          - goos: darwin
            goarch: amd64
            ext: ""
          - goos: darwin
            goarch: arm64
            ext: ""
          - goos: linux
            goarch: amd64
            ext: ""
          - goos: linux
            goarch: arm64
            ext: ""
          - goos: windows
            goarch: amd64
            ext: ".exe"
          - goos: windows
            goarch: arm64
            ext: ".exe"

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version: '1.22'

      - name: Build
        env:
          GOOS: ${{ matrix.goos }}
          GOARCH: ${{ matrix.goarch }}
          CGO_ENABLED: 0
        run: |
          go build \
            -ldflags "-X main.version=${{ github.ref_name }}" \
            -o dist/cardo-${{ matrix.goos }}-${{ matrix.goarch }}${{ matrix.ext }} \
            ./cmd/cardo

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: cardo-${{ matrix.goos }}-${{ matrix.goarch }}
          path: dist/cardo-*

  release:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
        with:
          path: dist/
          merge-multiple: true

      - name: Create Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/cardo-*
```

Set `CGO_ENABLED=0` for fully static binaries (required for cross-compilation).

## Error Handling Conventions

### In library code (internal/)

Return errors, never call `os.Exit` or `log.Fatal`:

```go
// internal/state/pending.go
func ReadPending(projectRoot string) ([]PendingEntry, error) {
    path := filepath.Join(projectRoot, ".cardo", "pending.jsonl")
    data, err := os.ReadFile(path)
    if err != nil {
        if errors.Is(err, fs.ErrNotExist) {
            return nil, nil  // empty is not an error
        }
        return nil, fmt.Errorf("read pending: %w", err)
    }
    // ... parse
    return entries, nil
}
```

### Wrapping errors

Use `fmt.Errorf("context: %w", err)` to add context while preserving the original
for `errors.Is`/`errors.As` inspection. Keep context strings lowercase with no period.

### In cmd/ (cobra handlers)

Return the error from `RunE`. main.go prints it and exits 1:

```go
RunE: func(cmd *cobra.Command, args []string) error {
    result, err := doWork(args[0])
    if err != nil {
        return fmt.Errorf("approve %s: %w", args[0], err)
    }
    fmt.Println(result)
    return nil
},
```

## Project Root Detection

Cardo reads state from the current directory's `.cardo/` folder:

```go
func projectRoot() string {
    // Use current working directory — Cardo is current-directory aware
    root, err := os.Getwd()
    if err != nil {
        return "."
    }
    return root
}
```

## Local Build for Development

```bash
# Build and install to PATH for local testing
go build -o ~/.local/bin/cardo ./cmd/cardo

# Or on macOS with /usr/local/bin
go build -o /usr/local/bin/cardo ./cmd/cardo

# Verify
cardo version
```

## CI Integration (add to existing ci.yml)

```yaml
- name: Go build check
  run: go build ./cmd/cardo

- name: Go vet
  run: go vet ./...
```

These two checks are lightweight and sufficient for CI. Reserve full test suite for
release pipeline.
