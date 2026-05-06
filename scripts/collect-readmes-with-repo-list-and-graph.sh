#!/usr/bin/env bash
# Copy README-like files from a target dir or glob into an output dir.
#
# Modes:
#   1) Default (non-recursive): copies <target>/*/<name-pattern> into:
#        <output>/<project>/<source-basename>
#   2) --recursive: finds matching files anywhere under <target> and mirrors the containing
#      folder path under <output>.
#   3) --flat: puts all matched files into ONE directory (<output>) and renames them to:
#        <parent>-<source-basename>
#      If a name collision happens (same parent folder name), it falls back to using
#      a sanitized relative path for uniqueness:
#        <relpath-with-__>-<source-basename>
#
# Also:
#   - Generates <output>/INDEX.md listing repos and linking to copied files
#     (disable with --no-index).
#   - Optional: writes a plain-text repo list with one repo per line, suitable for
#     files like .archived/repos.md or repos.txt.
#   - Optional: generates a Mermaid graph showing target -> repos -> copied README files.
#
# Usage:
#   bash scripts/collect-readmes.sh -t /path/to/projects -o /path/to/collected
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --recursive
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --flat
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --flat --recursive
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --dry-run
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --recursive --name 'README.md.teaching.md'
#   bash scripts/collect-readmes.sh -t '~/projects/**/README.md.teaching.md' -o ./_teachings --flat
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --recursive --repo-list .archived/repos.md
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --recursive --repo-list repos.txt --repo-list-format path
#   bash scripts/collect-readmes.sh -t . -o ./_readmes --recursive --repo-list .archived/repos.md --generate-graph

set -Eeuo pipefail

usage() {
  cat <<'USAGE_EOF'
collect-readmes.sh -t <target_dir_or_glob> -o <output_dir> [--recursive] [--flat] [--dry-run] [--overwrite] [--no-index] [--name <pattern>] [--repo-list <file>] [--repo-list-format <url|path|name>] [--generate-graph] [--graph-file <file>]

Options:
  -t, --target       Root folder, single file, or glob pattern to scan
  -o, --output       Destination folder to store copied matches
  -r, --recursive    Find matches anywhere under target (prunes common junk dirs)
      --flat         Store ALL matches directly under output, renaming to <parent>-<basename>
  -n, --dry-run      Print actions without copying
  -f, --overwrite    Overwrite destination file(s) if they already exist
      --no-index     Do not generate <output>/INDEX.md
      --name         Basename pattern to match (repeatable). Default: README.md
                     Examples: --name 'README.md.teaching.md'
                               --name 'README.md' --name 'README.md.*.md'
      --repo-list    Write a one-repo-per-line text/markdown file, like .archived/repos.md
                     Relative paths are written inside <output>; absolute paths are used as provided.
      --repo-list-format
                     What to write in --repo-list: url, path, or name. Default: url.
                     url uses git origin URLs when available and falls back to relative paths.
      --generate-graph
                     Write a Mermaid graph to <output>/REPO_GRAPH.md.
      --graph-file   Path for --generate-graph output. Relative paths are written inside <output>.
  -h, --help         Show help
USAGE_EOF
}

TARGET=""
OUT=""
RECURSIVE=0
FLAT=0
DRY_RUN=0
OVERWRITE=0
INDEX=1
README_NAMES=("README.md")
REPO_LIST_FILE=""
REPO_LIST_FORMAT="url"
GENERATE_GRAPH=0
GRAPH_FILE=""
TARGET_MODE=""
SCAN_BASE=""
TARGET_INPUT=""

# temp map of: <rel_root>\t<base>\t<dest_relpath>
INDEX_MAP=""

log() { printf '%s\n' "$*"; }

expand_home_path() {
  local path="$1"
  case "$path" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s/%s\n' "$HOME" "${path#~/}" ;;
    *) printf '%s\n' "$path" ;;
  esac
}

has_glob_magic() {
  local value="$1"
  [[ "$value" == *'*'* || "$value" == *'?'* || "$value" == *'['* ]]
}

glob_root_dir() {
  local pattern="$1"
  local prefix=""
  if [[ "$pattern" =~ ^([^*?\[]*) ]]; then
    prefix="${BASH_REMATCH[1]}"
  fi

  if [[ -z "$prefix" ]]; then
    printf '.\n'
    return 0
  fi

  if [[ "$prefix" == */ ]]; then
    printf '%s\n' "${prefix%/}"
  else
    dirname -- "$prefix"
  fi
}

normalize_existing_path() {
  local path="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$path"
  else
    printf '%s\n' "$path"
  fi
}

normalize_output_path() {
  local path="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath -m "$path"
  else
    printf '%s\n' "$path"
  fi
}

while (($#)); do
  case "${1:-}" in
    -t|--target) TARGET="${2:-}"; shift 2 ;;
    -o|--output) OUT="${2:-}"; shift 2 ;;
    -r|--recursive) RECURSIVE=1; shift ;;
    --flat|--single-dir) FLAT=1; shift ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -f|--overwrite) OVERWRITE=1; shift ;;
    --no-index) INDEX=0; shift ;;
    --index) INDEX=1; shift ;;
    --repo-list|--repo-list-file)
      [[ -n "${2:-}" ]] || { echo "ERROR: --repo-list requires a file path" >&2; exit 1; }
      REPO_LIST_FILE="${2:-}"
      shift 2
      ;;
    --repo-list-format)
      [[ -n "${2:-}" ]] || { echo "ERROR: --repo-list-format requires one of: url, path, name" >&2; exit 1; }
      REPO_LIST_FORMAT="${2:-}"
      shift 2
      ;;
    --generate-graph) GENERATE_GRAPH=1; shift ;;
    --graph-file)
      [[ -n "${2:-}" ]] || { echo "ERROR: --graph-file requires a file path" >&2; exit 1; }
      GENERATE_GRAPH=1
      GRAPH_FILE="${2:-}"
      shift 2
      ;;
    --name)
      [[ -n "${2:-}" ]] || { echo "ERROR: --name requires a pattern" >&2; exit 1; }
      if [[ ${#README_NAMES[@]} -eq 1 && ${README_NAMES[0]} == "README.md" ]]; then
        README_NAMES=()
      fi
      README_NAMES+=("${2}")
      shift 2
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 1 ;;
  esac
done

[[ -n "$TARGET" && -n "$OUT" ]] || { usage; exit 1; }
case "$REPO_LIST_FORMAT" in
  url|path|name) ;;
  *) echo "ERROR: --repo-list-format must be one of: url, path, name" >&2; exit 1 ;;
esac

TARGET_INPUT="$TARGET"
TARGET="$(expand_home_path "$TARGET")"
OUT="$(expand_home_path "$OUT")"

if [[ -d "$TARGET" ]]; then
  TARGET_MODE="dir"
  SCAN_BASE="$TARGET"
elif [[ -f "$TARGET" ]]; then
  TARGET_MODE="file"
  SCAN_BASE="$(dirname -- "$TARGET")"
elif has_glob_magic "$TARGET"; then
  TARGET_MODE="glob"
  SCAN_BASE="$(glob_root_dir "$TARGET")"
  [[ -d "$SCAN_BASE" ]] || { echo "ERROR: target glob root not found: $SCAN_BASE" >&2; exit 2; }
else
  echo "ERROR: target not found: $TARGET_INPUT" >&2
  exit 2
fi

SCAN_BASE="$(normalize_existing_path "$SCAN_BASE")"
[[ "$TARGET_MODE" == "dir" ]] && TARGET="$(normalize_existing_path "$TARGET")"
[[ "$TARGET_MODE" == "file" ]] && TARGET="$(normalize_existing_path "$TARGET")"
OUT="$(normalize_output_path "$OUT")"
if [[ -n "$REPO_LIST_FILE" ]]; then
  REPO_LIST_FILE="$(expand_home_path "$REPO_LIST_FILE")"
  case "$REPO_LIST_FILE" in
    /*) REPO_LIST_FILE="$(normalize_output_path "$REPO_LIST_FILE")" ;;
    *) REPO_LIST_FILE="$OUT/$REPO_LIST_FILE" ;;
  esac
fi

if (( GENERATE_GRAPH )); then
  if [[ -z "$GRAPH_FILE" ]]; then
    GRAPH_FILE="$OUT/REPO_GRAPH.md"
  else
    GRAPH_FILE="$(expand_home_path "$GRAPH_FILE")"
    case "$GRAPH_FILE" in
      /*) GRAPH_FILE="$(normalize_output_path "$GRAPH_FILE")" ;;
      *) GRAPH_FILE="$OUT/$GRAPH_FILE" ;;
    esac
  fi
fi

# Prevent recursive mode from re-copying the output folder if it's inside the scan base.
is_out_inside_target=0
case "$OUT/" in
  "$SCAN_BASE/"*) is_out_inside_target=1 ;;
esac

INDEX_FILE="$OUT/INDEX.md"
INDEX_MAP="$(mktemp -t collect-readmes.indexmap.XXXXXX)"
cleanup() { rm -f "$INDEX_MAP"; }
trap cleanup EXIT

safe_name_from_relpath() {
  # Turn a relative path into a filename-friendly token.
  # Example: "foo/bar baz" -> "foo__bar_baz"
  local s="$1"
  s="${s//\//__}"
  s="${s// /_}"
  s="${s//:/_}"
  s="${s//\\/__}"
  printf '%s' "$s"
}

is_git_repo() {
  local dir="$1"
  [[ -d "$dir/.git" || -f "$dir/.git" ]]
}

list_repos() {
  # Emits repo relpaths (one per line).
  if [[ "$TARGET_MODE" != "dir" ]]; then
    awk -F'\t' '{print $1}' "$INDEX_MAP" 2>/dev/null | awk 'NF' | sort -u
    return 0
  fi

  if (( RECURSIVE )); then
    local out_base=""
    if (( is_out_inside_target )); then
      out_base="$(basename "$OUT")"
    fi

    {
      if (( is_out_inside_target )); then
        find "$TARGET" \
          \( -path "*/node_modules" -o -path "*/dist" -o -path "*/build" -o -path "*/.venv" -o -path "*/venv" -o -path "*/__pycache__" -o -path "*/$out_base" \) -prune -false \
          -o \( -name ".git" -a -type d \) -prune -print0 \
          -o \( -name ".git" -a -type f \) -print0
      else
        find "$TARGET" \
          \( -path "*/node_modules" -o -path "*/dist" -o -path "*/build" -o -path "*/.venv" -o -path "*/venv" -o -path "*/__pycache__" \) -prune -false \
          -o \( -name ".git" -a -type d \) -prune -print0 \
          -o \( -name ".git" -a -type f \) -print0
      fi
    } | while IFS= read -r -d '' gitpath; do
      local root rel
      root="$(dirname "$gitpath")"
      rel=""
      if command -v realpath >/dev/null 2>&1; then
        rel="$(realpath --relative-to="$SCAN_BASE" "$root" 2>/dev/null || true)"
      fi
      if [[ -z "$rel" ]]; then
        rel="${root#"$SCAN_BASE"/}"
      fi
      [[ -n "$rel" ]] && printf '%s\n' "$rel"
    done | sort -u
  else
    shopt -s nullglob
    for d in "$TARGET"/*/; do
      printf '%s\n' "$(basename "${d%/}")"
    done | sort -u
    shopt -u nullglob
  fi
}

readme_dest_rel_for_repo() {
  # Best-effort: find the copied file corresponding to repo relpath.
  local repo_rel="$1"
  local dest_rel=""

  # Prefer the copy map (handles --flat collisions correctly)
  dest_rel="$(awk -F'\t' -v r="$repo_rel" '$1==r {print $3; exit}' "$INDEX_MAP" 2>/dev/null || true)"

  [[ -n "$dest_rel" ]] || return 0

  if (( DRY_RUN )); then
    printf '%s' "$dest_rel"
    return 0
  fi

  [[ -e "$OUT/$dest_rel" ]] && printf '%s' "$dest_rel" || true
}

repo_root_for_rel() {
  local repo_rel="$1"

  if [[ "$TARGET_MODE" == "dir" ]]; then
    if (( RECURSIVE )); then
      printf '%s/%s' "$SCAN_BASE" "$repo_rel"
    else
      printf '%s/%s' "$TARGET" "$repo_rel"
    fi
  else
    printf '%s/%s' "$SCAN_BASE" "$repo_rel"
  fi
}

git_origin_url() {
  local repo_root="$1"

  command -v git >/dev/null 2>&1 || return 1
  [[ -d "$repo_root/.git" || -f "$repo_root/.git" ]] || return 1

  git -C "$repo_root" remote get-url origin 2>/dev/null || true
}

normalize_repo_url() {
  local value="$1"

  value="${value%.git}"
  case "$value" in
    git@github.com:*) value="https://github.com/${value#git@github.com:}" ;;
    ssh://git@github.com/*) value="https://github.com/${value#ssh://git@github.com/}" ;;
  esac

  value="${value%.git}"
  value="${value%/}"
  printf '%s' "$value"
}

repo_line_for_repo() {
  local repo_rel="$1"
  local repo_name repo_root origin

  repo_name="$(basename "$repo_rel")"

  case "$REPO_LIST_FORMAT" in
    name)
      printf '%s' "$repo_name"
      ;;
    path)
      printf '%s' "$repo_rel"
      ;;
    url)
      repo_root="$(repo_root_for_rel "$repo_rel")"
      origin="$(git_origin_url "$repo_root" || true)"
      if [[ -n "$origin" ]]; then
        normalize_repo_url "$origin"
      else
        printf '%s' "$repo_rel"
      fi
      ;;
  esac
}

write_repo_list_file() {
  [[ -n "$REPO_LIST_FILE" ]] || return 0

  local tmp repo_rel line line_count
  tmp="$(mktemp -t collect-readmes.repolist.XXXXXX)"
  line_count=0

  while IFS= read -r repo_rel; do
    [[ -n "$repo_rel" ]] || continue
    line="$(repo_line_for_repo "$repo_rel")"
    [[ -n "$line" ]] || continue
    printf '%s\n' "$line" >> "$tmp"
    line_count=$((line_count+1))
  done < <(list_repos)

  if (( DRY_RUN )); then
    rm -f "$tmp"
    log "REPO LIST: $REPO_LIST_FILE ($line_count lines, format: $REPO_LIST_FORMAT)"
    return 0
  fi

  mkdir -p "$(dirname "$REPO_LIST_FILE")"
  mv -f "$tmp" "$REPO_LIST_FILE"
  log "Repo list written: $REPO_LIST_FILE ($line_count lines, format: $REPO_LIST_FORMAT)"
}


node_id_for() {
  local prefix="$1"
  local value="$2"
  local sum
  sum="$(printf '%s' "$value" | cksum | awk '{print $1}')"
  printf '%s_%s' "$prefix" "$sum"
}

mermaid_label() {
  local s="$1"
  s="${s//$'\n'/ }"
  s="${s//\"/ }"
  printf '%s' "$s"
}

repo_graph_label_for_repo() {
  local repo_rel="$1"
  local repo_root origin

  repo_root="$(repo_root_for_rel "$repo_rel")"
  origin="$(git_origin_url "$repo_root" || true)"
  if [[ -n "$origin" ]]; then
    normalize_repo_url "$origin"
  else
    printf '%s' "$repo_rel"
  fi
}

write_repo_graph() {
  (( GENERATE_GRAPH )) || return 0

  local tmp repo_rel repo_label repo_node readme_rel readme_node missing_node repo_count
  tmp="$(mktemp -t collect-readmes.graph.XXXXXX)"
  repo_count=0

  {
    echo "# Repository Graph"
    echo
    echo "Generated from: \`$TARGET_INPUT\`"
    echo
    echo '```mermaid'
    echo 'flowchart LR'
    printf '  source["%s"]\n' "$(mermaid_label "Target: $TARGET_INPUT")"

    while IFS= read -r repo_rel; do
      [[ -n "$repo_rel" ]] || continue
      repo_count=$((repo_count+1))

      repo_label="$(repo_graph_label_for_repo "$repo_rel")"
      repo_node="$(node_id_for repo "$repo_rel")"
      printf '  source --> %s["%s"]\n' "$repo_node" "$(mermaid_label "$repo_label")"

      readme_rel="$(readme_dest_rel_for_repo "$repo_rel" || true)"
      if [[ -n "$readme_rel" ]]; then
        readme_node="$(node_id_for readme "$repo_rel/$readme_rel")"
        printf '  %s --> %s["%s"]\n' "$repo_node" "$readme_node" "$(mermaid_label "$readme_rel")"
      else
        missing_node="$(node_id_for missing "$repo_rel")"
        printf '  %s -.-> %s["README not copied"]\n' "$repo_node" "$missing_node"
      fi
    done < <(list_repos)

    echo '```'
    echo
    echo "- Total repos: $repo_count"
  } > "$tmp"

  if (( DRY_RUN )); then
    rm -f "$tmp"
    log "GRAPH: $GRAPH_FILE"
    return 0
  fi

  mkdir -p "$(dirname "$GRAPH_FILE")"
  mv -f "$tmp" "$GRAPH_FILE"
  log "Graph written: $GRAPH_FILE"
}

write_repo_index() {
  (( INDEX )) || return 0

  local now tmp repo_rel repo_name git_flag readme_rel readme_cell repo_count scan_label
  now="$(date -Is)"
  tmp="$(mktemp -t collect-readmes.index.XXXXXX)"
  repo_count=0

  case "$TARGET_MODE" in
    dir) scan_label="$([[ $RECURSIVE -eq 1 ]] && echo recursive || echo project-root-only)" ;;
    file) scan_label="single-file" ;;
    glob) scan_label="glob" ;;
    *) scan_label="unknown" ;;
  esac

  {
    echo "# Repository Index"
    echo
    echo "- Generated: \`$now\`"
    echo "- Target: \`$TARGET_INPUT\`"
    echo "- Resolved scan base: \`$SCAN_BASE\`"
    echo "- Output: \`$OUT\`"
    echo "- Scan: \`$scan_label\`"
    echo "- README copy mode: \`$([[ $FLAT -eq 1 ]] && echo flat || echo nested)\`"
    printf -- '- Name patterns:'
    for name in "${README_NAMES[@]}"; do
      printf ' \`%s\`' "$name"
    done
    echo
    echo
    echo "| Repo | Relative Path | Git | README |"
    echo "| --- | --- | --- | --- |"

    while IFS= read -r repo_rel; do
      [[ -n "$repo_rel" ]] || continue
      repo_count=$((repo_count+1))

      repo_name="$(basename "$repo_rel")"
      if [[ "$TARGET_MODE" != "dir" ]]; then
        git_flag="$([[ -e "$SCAN_BASE/$repo_rel/.git" || -f "$SCAN_BASE/$repo_rel/.git" ]] && echo yes || echo no)"
      elif (( RECURSIVE )); then
        git_flag="yes"
      else
        git_flag="$([[ -e "$TARGET/$repo_rel/.git" || -f "$TARGET/$repo_rel/.git" ]] && echo yes || echo no)"
      fi

      readme_rel="$(readme_dest_rel_for_repo "$repo_rel" || true)"
      if [[ -n "$readme_rel" ]]; then
        readme_cell="[README]($readme_rel)"
      else
        readme_cell=""
      fi

      printf '| %s | `%s` | %s | %s |\n' "$repo_name" "$repo_rel" "$git_flag" "$readme_cell"
    done < <(list_repos)

    echo
    echo "- Total repos: $repo_count"
  } > "$tmp"

  if (( DRY_RUN )); then
    rm -f "$tmp"
    log "INDEX: $INDEX_FILE"
    return 0
  fi

  mkdir -p "$OUT"
  mv -f "$tmp" "$INDEX_FILE"
  log "Index written: $INDEX_FILE"
}

copy_one() {
  local readme="$1"
  local project_root dest_dir dest_file rel_root base safe dest_rel source_name

  project_root="$(dirname "$readme")"
  base="$(basename "$project_root")"
  source_name="$(basename "$readme")"

  rel_root=""
  if command -v realpath >/dev/null 2>&1; then
    rel_root="$(realpath --relative-to="$SCAN_BASE" "$project_root" 2>/dev/null || true)"
  fi
  if [[ -z "$rel_root" ]]; then
    rel_root="${project_root#"$SCAN_BASE"/}"
  fi
  [[ "$rel_root" == "$project_root" ]] && rel_root="$base"

  if (( FLAT )); then
    dest_dir="$OUT"
    dest_file="$dest_dir/${base}-${source_name}"

    # If the simple parent-name-based filename collides, fall back to relpath-based.
    if [[ -e "$dest_file" && $OVERWRITE -eq 0 ]]; then
      safe="$(safe_name_from_relpath "$rel_root")"
      dest_file="$dest_dir/${safe}-${source_name}"
    fi
  else
    if (( RECURSIVE )) || [[ "$TARGET_MODE" != "dir" ]]; then
      dest_dir="$OUT/$rel_root"
    else
      dest_dir="$OUT/$base"
    fi
    dest_file="$dest_dir/$source_name"
  fi

  # Record mapping for index generation (handles --flat collision names)
  dest_rel="${dest_file#"$OUT"/}"
  printf '%s\t%s\t%s\n' "$rel_root" "$base" "$dest_rel" >> "$INDEX_MAP"

  if [[ -e "$dest_file" && $OVERWRITE -eq 0 ]]; then
    log "SKIP (exists): $dest_file"
    return 0
  fi

  if (( DRY_RUN )); then
    log "COPY: $readme -> $dest_file"
    return 0
  fi

  mkdir -p "$dest_dir"
  cp -f "$readme" "$dest_file"
  log "OK: $readme -> $dest_file"
}

build_name_expr() {
  local -n _ref="$1"
  _ref=(-false)
  local pattern
  for pattern in "${README_NAMES[@]}"; do
    _ref+=(-o -name "$pattern")
  done
}

scan_target_dir_recursive() {
  local -a name_expr=()
  build_name_expr name_expr

  if (( is_out_inside_target )); then
    local out_basename
    out_basename="$(basename "$OUT")"
    while IFS= read -r -d '' f; do
      copy_one "$f"
      count=$((count+1))
    done < <(
      find "$TARGET" \
        \( -path "*/.git" -o -path "*/node_modules" -o -path "*/dist" -o -path "*/build" -o -path "*/.venv" -o -path "*/venv" -o -path "*/__pycache__" -o -path "*/$out_basename" \) -prune -false \
        -o -type f \( "${name_expr[@]}" \) -print0
    )
  else
    while IFS= read -r -d '' f; do
      copy_one "$f"
      count=$((count+1))
    done < <(
      find "$TARGET" \
        \( -path "*/.git" -o -path "*/node_modules" -o -path "*/dist" -o -path "*/build" -o -path "*/.venv" -o -path "*/venv" -o -path "*/__pycache__" \) -prune -false \
        -o -type f \( "${name_expr[@]}" \) -print0
    )
  fi
}

scan_target_dir_non_recursive() {
  local d pattern f
  shopt -s nullglob
  for d in "$TARGET"/*/; do
    for pattern in "${README_NAMES[@]}"; do
      while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        copy_one "$f"
        count=$((count+1))
      done < <(compgen -G "${d%/}/$pattern" || true)
    done
  done
  shopt -u nullglob
}

scan_target_file() {
  copy_one "$TARGET"
  count=$((count+1))
}

scan_target_glob() {
  local -a matches=()
  local f
  shopt -s globstar nullglob
  mapfile -t matches < <(compgen -G "$TARGET" || true)
  shopt -u globstar nullglob

  [[ ${#matches[@]} -gt 0 ]] || {
    echo "ERROR: target glob matched nothing: $TARGET_INPUT" >&2
    exit 2
  }

  for f in "${matches[@]}"; do
    [[ -f "$f" ]] || continue
    copy_one "$(normalize_existing_path "$f")"
    count=$((count+1))
  done
}

if (( DRY_RUN )); then
  log "DRY RUN"
fi
log "Target: $TARGET_INPUT"
log "Resolved mode: $TARGET_MODE"
log "Resolved scan base: $SCAN_BASE"
log "Output: $OUT"
log "Mode:   $([[ $FLAT -eq 1 ]] && echo flat || echo nested)"
log "Index:  $([[ $INDEX -eq 1 ]] && echo enabled || echo disabled)"
if [[ -n "$REPO_LIST_FILE" ]]; then
  log "Repo list: $REPO_LIST_FILE ($REPO_LIST_FORMAT)"
else
  log "Repo list: disabled"
fi
if (( GENERATE_GRAPH )); then
  log "Graph: $GRAPH_FILE"
else
  log "Graph: disabled"
fi
printf 'Names: '
for idx in "${!README_NAMES[@]}"; do
  if (( idx > 0 )); then
    printf ', '
  fi
  printf '%s' "${README_NAMES[idx]}"
done
printf '\n'

case "$TARGET_MODE" in
  dir)
    log "Scan:   $([[ $RECURSIVE -eq 1 ]] && echo recursive || echo project-root-only)"
    ;;
  file)
    log "Scan:   single-file"
    ;;
  glob)
    log "Scan:   glob"
    ;;
esac

if (( DRY_RUN == 0 )); then
  mkdir -p "$OUT"
fi

count=0

case "$TARGET_MODE" in
  dir)
    if (( RECURSIVE )); then
      scan_target_dir_recursive
    else
      scan_target_dir_non_recursive
    fi
    ;;
  file)
    scan_target_file
    ;;
  glob)
    scan_target_glob
    ;;
esac

write_repo_index
write_repo_list_file
write_repo_graph

log "Done. Found: $count"
