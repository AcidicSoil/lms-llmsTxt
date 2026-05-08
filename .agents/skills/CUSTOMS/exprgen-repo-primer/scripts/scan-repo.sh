#!/usr/bin/env bash
set -euo pipefail

root="${1:-.}"
cd "$root"

printf 'Top-level directories:\n'
find . -maxdepth 2 -type d \
  ! -path './.git*' ! -path './node_modules*' ! -path './dist*' ! -path './build*' \
  | sed 's#^./##' | sort | head -120

printf '\nCommon file extensions:\n'
find . -type f \
  ! -path './.git/*' ! -path './node_modules/*' ! -path './dist/*' ! -path './build/*' \
  | awk '
    match($0, /\.([A-Za-z0-9]+)$/, m) { count[tolower(m[1])]++ }
    END { for (ext in count) print count[ext], ext }
  ' | sort -nr | head -40

printf '\nLikely config files:\n'
find . -maxdepth 3 -type f \
  \( -name 'package.json' -o -name 'tsconfig*.json' -o -name '*.config.*' -o -name '.env*' -o -name 'Makefile' -o -name 'Dockerfile' \) \
  | sed 's#^./##' | sort | head -80
