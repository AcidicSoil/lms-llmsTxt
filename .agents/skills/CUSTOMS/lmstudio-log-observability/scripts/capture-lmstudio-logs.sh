#!/usr/bin/env bash
set -euo pipefail

SOURCE="${1:-server}"
OUTPUT="${2:-lmstudio-${SOURCE}.jsonl}"

if ! command -v lms >/dev/null 2>&1; then
  echo "ERROR: lms CLI not found in PATH." >&2
  exit 1
fi

case "$SOURCE" in
  server)
    exec lms log stream --source server --json | tee -a "$OUTPUT"
    ;;
  model)
    exec lms log stream --source model --filter input,output --json | tee -a "$OUTPUT"
    ;;
  runtime)
    if ! lms log stream --help 2>/dev/null | grep -qi 'runtime'; then
      echo "ERROR: this lms CLI does not list runtime as a log source." >&2
      exit 2
    fi
    exec lms log stream --source runtime --json | tee -a "$OUTPUT"
    ;;
  *)
    echo "Usage: $0 [server|model|runtime] [output.jsonl]" >&2
    exit 64
    ;;
esac
