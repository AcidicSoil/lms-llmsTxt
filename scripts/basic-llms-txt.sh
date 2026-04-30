# path: scripts/collect_llms_basic_rsync.sh
#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"                                 # repo root
OUT="${2:-artifacts/llms-basic}"               # destination
LOG="${3:-artifacts/collect_llms_basic.log}"   # log file

mkdir -p "$OUT" "$(dirname "$LOG")"

rsync -av --prune-empty-dirs \
  --include='*/' \
  --exclude='*llms-full*.txt' \
  --exclude='*llms-ctx*.txt' \
  --include='*llms.txt' \
  --exclude='*' \
  "$ROOT"/ "$OUT"/ | tee "$LOG"
