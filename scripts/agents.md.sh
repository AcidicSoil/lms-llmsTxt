# path: scripts/collect_llms_full_rsync.sh
#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"                               # repo root
OUT="${2:-artifacts/AGENTS\.md}"              # destination folder
LOG="${3:-artifacts/collect_AGENTS\.md_rsync.log}"

mkdir -p "$OUT" "$(dirname "$LOG")"

rsync -av --prune-empty-dirs \
  --include='*/' --include='*AGENTS*.md' --exclude='*' \
  "$ROOT"/ "$OUT"/ | tee "$LOG"
