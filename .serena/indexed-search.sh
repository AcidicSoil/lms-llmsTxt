#!/usr/bin/env bash
set -Eeuo pipefail

# indexed-search.sh
# Stable Serena search entrypoint for already-indexed qmd/ck skill surfaces.
#
# This script is intentionally standalone. It does not source qks/qk/qkcs
# wrapper functions and it does not require a .serena directory to exist.
# Serena calls this script; the script performs the safe restricted calls.
#
# Allowed public commands:
#   qks      <query>                         -> qmd collection: skills
#   qkcs     <query>                         -> qmd collection: skill-set
#   qk       <query> <allowed-collection>    -> qmd collection allowlist
#   ckskills <query>                         -> ck over allowed existing skill roots
#   ckskill  <query> <skill-name-or-path>    -> ck over one allowed existing skill dir
#
# Blocked public commands:
#   qmd, ck, index, clean, rebuild, install, add, sync
#
# Placement examples:
#   ./indexed-search.sh
#   ./.serena/indexed-search.sh
#
# Environment:
#   QMD_BIN                         default: qmd
#   CK_BIN                          default: ck
#   SERENA_QMD_LIMIT                default: 10
#   SERENA_CK_LIMIT                 default: 10
#   SERENA_QK_ALLOWED_COLLECTIONS   default: skills:skill-set
#   SERENA_CK_ALLOWED_ROOTS         colon-separated existing skill roots
#   SERENA_PROJECT_DIR              default: current working directory

SCRIPT_NAME="${0##*/}"
PROJECT_DIR="${SERENA_PROJECT_DIR:-$PWD}"
QMD_BIN="${QMD_BIN:-qmd}"
CK_BIN="${CK_BIN:-ck}"
QMD_LIMIT="${SERENA_QMD_LIMIT:-10}"
CK_LIMIT="${SERENA_CK_LIMIT:-10}"
QK_ALLOWED_COLLECTIONS="${SERENA_QK_ALLOWED_COLLECTIONS:-skills:skill-set}"

usage() {
  cat >&2 <<USAGE
Usage:
  $SCRIPT_NAME --check
  $SCRIPT_NAME --list
  $SCRIPT_NAME qks <query>
  $SCRIPT_NAME qkcs <query>
  $SCRIPT_NAME qk <query> <allowed-existing-qmd-collection>
  $SCRIPT_NAME ckskills <query>
  $SCRIPT_NAME ckskill <query> <skill-name-or-path>

Allowed qmd collections by default:
  skills, skill-set

Notes:
  - qks maps to qmd collection "skills".
  - qkcs maps to qmd collection "skill-set".
  - skill-set is the curated skills collection.
  - skills is the global/default skills collection.
  - This script does not require .serena/ wrapper files.
USAGE
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

require_exact_args() {
  local expected="$1"
  local actual="$2"
  local form="$3"
  [[ "$actual" -eq "$expected" ]] || fail "$form"
}

require_command_for_use() {
  local bin="$1"
  local purpose="$2"
  command -v "$bin" >/dev/null 2>&1 || fail "$purpose requires '$bin' on PATH; no wrapper files are required"
}

valid_collection_token() {
  local collection="$1"
  [[ "$collection" =~ ^[A-Za-z0-9._:@/+~-]+$ ]]
}

collection_is_allowed() {
  local collection="$1"
  local allowed item

  allowed="${QK_ALLOWED_COLLECTIONS//,/:}"
  IFS=':' read -r -a _serena_allowed_collections <<< "$allowed"
  for item in "${_serena_allowed_collections[@]}"; do
    [[ -n "$item" && "$collection" == "$item" ]] && return 0
  done

  return 1
}

run_qmd_collection_query() {
  local query="$1"
  local collection="$2"

  [[ -n "$query" ]] || fail "query must not be empty"
  valid_collection_token "$collection" || fail "invalid qmd collection token: $collection"
  collection_is_allowed "$collection" || fail "qmd collection '$collection' is not allowed; allowed collections: ${QK_ALLOWED_COLLECTIONS//,/:}"
  require_command_for_use "$QMD_BIN" "qmd collection search"

  "$QMD_BIN" query "$query" -c "$collection" -n "$QMD_LIMIT"
}

append_existing_dir() {
  local -n out_ref="$1"
  local dir="$2"
  [[ -d "$dir" ]] && out_ref+=("$dir")
}

candidate_ck_roots() {
  local roots=()
  local env_roots="${SERENA_CK_ALLOWED_ROOTS:-}"
  local root

  if [[ -n "$env_roots" ]]; then
    IFS=':' read -r -a _serena_env_roots <<< "$env_roots"
    for root in "${_serena_env_roots[@]}"; do
      [[ -n "$root" ]] && append_existing_dir roots "$root"
    done
  fi

  append_existing_dir roots "$PROJECT_DIR/.agents/skills"
  append_existing_dir roots "$PROJECT_DIR/.serena/skills"
  append_existing_dir roots "$PROJECT_DIR/skills"
  append_existing_dir roots "$PROJECT_DIR/skill-set"
  append_existing_dir roots "$PROJECT_DIR/curated-skills"
  append_existing_dir roots "$HOME/.agents/skills"
  append_existing_dir roots "$HOME/.config/skills"

  printf '%s\n' "${roots[@]}" | awk 'NF && !seen[$0]++'
}

realpath_portable() {
  local path="$1"
  if command -v realpath >/dev/null 2>&1; then
    realpath "$path"
  else
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$path"
  fi
}

path_is_under_allowed_root() {
  local target="$1"
  local target_real root root_real

  [[ -d "$target" ]] || return 1
  target_real="$(realpath_portable "$target")"

  while IFS= read -r root; do
    [[ -n "$root" ]] || continue
    root_real="$(realpath_portable "$root")"
    [[ "$target_real" == "$root_real" || "$target_real" == "$root_real"/* ]] && return 0
  done < <(candidate_ck_roots)

  return 1
}

resolve_skill_target() {
  local target="$1"
  local root direct nested

  if [[ -d "$target" ]]; then
    path_is_under_allowed_root "$target" || fail "ckskill target is outside allowed skill roots: $target"
    realpath_portable "$target"
    return 0
  fi

  [[ "$target" =~ ^[A-Za-z0-9._@/+~-]+$ ]] || fail "invalid skill name/path token: $target"

  while IFS= read -r root; do
    [[ -n "$root" ]] || continue

    direct="$root/$target"
    if [[ -d "$direct" ]]; then
      realpath_portable "$direct"
      return 0
    fi

    nested="$(find "$root" -mindepth 1 -maxdepth 3 -type d -name "$target" -print -quit 2>/dev/null || true)"
    if [[ -n "$nested" ]]; then
      realpath_portable "$nested"
      return 0
    fi
  done < <(candidate_ck_roots)

  fail "skill target '$target' was not found under allowed existing skill roots"
}

run_ck_over_dir() {
  local query="$1"
  local dir="$2"

  [[ -n "$query" ]] || fail "query must not be empty"
  [[ -d "$dir" ]] || fail "ck target directory does not exist: $dir"
  require_command_for_use "$CK_BIN" "ck indexed skill search"

  "$CK_BIN" --hybrid "$query" "$dir" --limit "$CK_LIMIT"
}

run_ckskills() {
  local query="$1"
  local roots=()
  local root found=0

  while IFS= read -r root; do
    [[ -n "$root" ]] && roots+=("$root")
  done < <(candidate_ck_roots)

  [[ "${#roots[@]}" -gt 0 ]] || fail "no existing allowed skill roots found for ckskills; set SERENA_CK_ALLOWED_ROOTS if needed"

  for root in "${roots[@]}"; do
    printf '## ck root: %s\n' "$root"
    if run_ck_over_dir "$query" "$root"; then
      found=1
    fi
  done

  [[ "$found" -eq 1 ]]
}

run_ckskill() {
  local query="$1"
  local target="$2"
  local resolved

  resolved="$(resolve_skill_target "$target")"
  printf '## ck skill: %s\n' "$resolved"
  run_ck_over_dir "$query" "$resolved"
}

check() {
  printf 'script: %s\n' "$SCRIPT_NAME"
  printf 'project_dir: %s\n' "$PROJECT_DIR"
  printf 'requires_.serena_wrappers: no\n'

  if command -v "$QMD_BIN" >/dev/null 2>&1; then
    printf 'qmd: ok (%s)\n' "$(command -v "$QMD_BIN")"
  else
    printf 'qmd: missing; qks/qk/qkcs will fail only if invoked\n'
  fi

  if command -v "$CK_BIN" >/dev/null 2>&1; then
    printf 'ck: ok (%s)\n' "$(command -v "$CK_BIN")"
  else
    printf 'ck: missing; ckskills/ckskill will fail only if invoked\n'
  fi

  printf 'allowed_qmd_collections: %s\n' "${QK_ALLOWED_COLLECTIONS//,/:}"
  printf 'known_existing_ck_skill_roots:\n'
  candidate_ck_roots | sed 's/^/  - /' || true

  # This is an informational check. It must not block just because optional
  # tools or roots are unavailable in the current shell/session.
  return 0
}

list_surface() {
  cat <<LIST
qks	qmd collection skills
qkcs	qmd collection skill-set
qk	qmd collection from allowlist: ${QK_ALLOWED_COLLECTIONS//,/:}
ckskills	ck search over existing allowed skill roots
ckskill	ck search over one allowed existing skill directory
LIST
}

main() {
  [[ "$#" -ge 1 ]] || { usage; exit 2; }

  case "$1" in
    --help|-h|help)
      usage
      ;;
    --check|check)
      check
      ;;
    --list|list)
      list_surface
      ;;
    qks)
      shift
      require_exact_args 1 "$#" "usage: $SCRIPT_NAME qks <query>"
      run_qmd_collection_query "$1" "skills"
      ;;
    qkcs)
      shift
      require_exact_args 1 "$#" "usage: $SCRIPT_NAME qkcs <query>"
      run_qmd_collection_query "$1" "skill-set"
      ;;
    qk)
      shift
      require_exact_args 2 "$#" "usage: $SCRIPT_NAME qk <query> <allowed-existing-qmd-collection>"
      run_qmd_collection_query "$1" "$2"
      ;;
    ckskills)
      shift
      require_exact_args 1 "$#" "usage: $SCRIPT_NAME ckskills <query>"
      run_ckskills "$1"
      ;;
    ckskill)
      shift
      require_exact_args 2 "$#" "usage: $SCRIPT_NAME ckskill <query> <skill-name-or-path>"
      run_ckskill "$1" "$2"
      ;;
    qmd|ck|index|clean|rebuild|install|add|sync)
      fail "'$1' is blocked through $SCRIPT_NAME; use only qks, qk, qkcs, ckskills, or ckskill"
      ;;
    *)
      fail "unsupported command '$1'; use --help for allowed commands"
      ;;
  esac
}

main "$@"
