# path: scripts/collect_llms_full_rsync.sh
#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"                               # repo root
OUT="${2:-artifacts/llms-full}"              # destination folder
LOG="${3:-artifacts/collect_llms_full_rsync.log}"

mkdir -p "$OUT" "$(dirname "$LOG")"

rsync -av --prune-empty-dirs \
  --include='*/' --include='*llms-full*.txt' --exclude='*' \
  "$ROOT"/ "$OUT"/ | tee "$LOG"
