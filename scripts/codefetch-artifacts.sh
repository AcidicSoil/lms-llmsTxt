# path: scripts/codefetch-artifacts.sh
#!/usr/bin/env bash
set -euo pipefail

subdirs="${1:-}"            # e.g. "TanStack/router,TanStack/table"
out="${2:-artifacts_codebase.md}"

args=()
if [[ -n "$subdirs" ]]; then
  IFS=',' read -ra DIRS <<< "$subdirs"
  for d in "${DIRS[@]}"; do
    args+=( --include-dir "artifacts/$d" )
  done
else
  args+=( --include-dir "artifacts" )
fi

pnpm exec codefetch "${args[@]}" --exclude-dirs __pycache__ -o "$out"
