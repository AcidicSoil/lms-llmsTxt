# path: scripts/task-master-workflow.sh
#!/usr/bin/env bash
set -euo pipefail

# Task Master typical workflow:
# init -> parse-prd (-r) -> analyze-complexity (-r) -> expand (-a -r)
#
# Docs:
# - CLI basics: task-master init, task-master parse-prd <file>  (README) :contentReference[oaicite:2]{index=2}
# - analyze-complexity --research, expand --all --research (command reference) :contentReference[oaicite:3]{index=3}
# - suggested PRD location: .taskmaster/docs/prd.txt (tutorial) :contentReference[oaicite:4]{index=4}

usage() {
  cat <<'EOF'
Usage:
  scripts/task-master-workflow.sh [options]

Options:
  --project-dir <dir>     Project root (default: current directory)
  --prd <file>            PRD file path (default: .taskmaster/docs/prd.txt)
  --rules <csv>           Pass-through for init: --rules cursor,windsurf,vscode
  --num-tasks <n>         Pass-through for parse-prd: --num-tasks=<n> (0 = auto)
  --research              Enable research mode where supported (default: on)
  --no-research           Disable research mode
  --force-init            Run init even if .taskmaster already exists
  --models-setup          Run: task-master models --setup (interactive) after init
  --force-expand          Pass-through for expand: --force (regenerate subtasks)
  --bin <cmd>             Override binary (e.g., task-master or tm)
  -h, --help              Show help

Examples:
  scripts/task-master-workflow.sh --prd docs/prd.md
  scripts/task-master-workflow.sh --rules cursor,windsurf --num-tasks 0
  scripts/task-master-workflow.sh --no-research
EOF
}

PROJECT_DIR="$(pwd)"
PRD_PATH=""
RULES_CSV=""
NUM_TASKS=""
RESEARCH=1
FORCE_INIT=0
MODELS_SETUP=0
FORCE_EXPAND=0
TM_BIN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) PROJECT_DIR="$2"; shift 2 ;;
    --prd) PRD_PATH="$2"; shift 2 ;;
    --rules) RULES_CSV="$2"; shift 2 ;;
    --num-tasks) NUM_TASKS="$2"; shift 2 ;;
    --research) RESEARCH=1; shift ;;
    --no-research) RESEARCH=0; shift ;;
    --force-init) FORCE_INIT=1; shift ;;
    --models-setup) MODELS_SETUP=1; shift ;;
    --force-expand) FORCE_EXPAND=1; shift ;;
    --bin) TM_BIN="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

cd "$PROJECT_DIR"

# Default PRD location after init per tutorial.
if [[ -z "${PRD_PATH}" ]]; then
  PRD_PATH=".taskmaster/docs/prd.md"
fi

# Resolve Task Master executable.
# Preference order:
#  1) --bin override
#  2) task-master on PATH
#  3) tm on PATH (some setups alias it)
#  4) npx --no-install task-master (for local node_modules/.bin)
TM=()
if [[ -n "${TM_BIN}" ]]; then
  TM=("${TM_BIN}")
elif command -v task-master >/dev/null 2>&1; then
  TM=("task-master")
elif command -v tm >/dev/null 2>&1; then
  TM=("tm")
elif command -v npx >/dev/null 2>&1; then
  TM=("npx" "--no-install" "task-master")
else
  echo "ERROR: Could not find task-master (or tm) and npx is unavailable." >&2
  echo "Install Task Master (npm package: task-master-ai) or run from a project with local install." >&2
  exit 1
fi

supports_flag() {
  # supports_flag <subcommand> <flag>
  # Uses '--help' output; safe for scripting. If help fails, returns false.
  local sub="$1"
  local flag="$2"
  if "${TM[@]}" "${sub}" --help >/dev/null 2>&1; then
    "${TM[@]}" "${sub}" --help 2>&1 | grep -qE -- "(^|[[:space:]])${flag}([=,[:space:]]|$)"
  else
    return 1
  fi
}

run_step() {
  local label="$1"; shift
  echo "==> ${label}"
  echo "+ $*"
  "$@"
  echo
}

# 1) init
if [[ ${FORCE_INIT} -eq 1 || ! -d ".taskmaster" ]]; then
  INIT_ARGS=()
  if [[ -n "${RULES_CSV}" ]]; then
    INIT_ARGS+=(--rules "${RULES_CSV}")
  fi
  run_step "task-master init" "${TM[@]}" init "${INIT_ARGS[@]}"
else
  echo "==> task-master init (skipped: .taskmaster already exists)"
  echo
fi

# Optional: configure models (interactive).
if [[ ${MODELS_SETUP} -eq 1 ]]; then
  run_step "task-master models --setup (interactive)" "${TM[@]}" models --setup
fi

# Validate PRD exists before parsing.
if [[ ! -f "${PRD_PATH}" ]]; then
  echo "ERROR: PRD file not found: ${PRD_PATH}" >&2
  echo "Tip: after init, place a PRD at .taskmaster/docs/prd.txt (or pass --prd <path>)." >&2
  exit 1
fi

# 2) parse-prd (-r)
# Docs show positional PRD file. Some versions also accept --input=...; we detect if present.
PARSE_ARGS=()
if supports_flag "parse-prd" "--input"; then
  PARSE_ARGS+=(--input="${PRD_PATH}")
else
  PARSE_ARGS+=("${PRD_PATH}")
fi
if [[ -n "${NUM_TASKS}" ]]; then
  PARSE_ARGS+=(--num-tasks="${NUM_TASKS}")
fi

# Research flag: not listed for parse-prd in the command reference, so only pass if supported.
if [[ ${RESEARCH} -eq 1 ]] && supports_flag "parse-prd" "--research"; then
  PARSE_ARGS+=(--research)
fi

run_step "task-master parse-prd" "${TM[@]}" parse-prd "${PARSE_ARGS[@]}"

# 3) analyze-complexity (-r)
ANALYZE_ARGS=()
if [[ ${RESEARCH} -eq 1 ]]; then
  ANALYZE_ARGS+=(--research)
fi
run_step "task-master analyze-complexity" "${TM[@]}" analyze-complexity "${ANALYZE_ARGS[@]}"

# 4) expand (-a -r)
EXPAND_ARGS=(--all)
if [[ ${FORCE_EXPAND} -eq 1 ]]; then
  EXPAND_ARGS+=(--force)
fi
if [[ ${RESEARCH} -eq 1 ]]; then
  EXPAND_ARGS+=(--research)
fi
run_step "task-master expand" "${TM[@]}" expand "${EXPAND_ARGS[@]}"

echo "Done. Next typical commands: task-master list, task-master next, task-master show <id>." >&2
