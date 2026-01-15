#!/usr/bin/env bash
# path: scripts/taskmaster_codex_diag_v3.sh
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<'USAGE'
Usage:
  ./scripts/taskmaster_codex_diag_v3.sh [--project PATH] [--id TASK_ID] [--tag TAG] [--model MODEL_ID] [--no-scratch]

Notes:
- Creates a timestamped log directory and writes:
    <logdir>/diag.log
    <logdir>/codex_shim.log
    <logdir>/schemas/*   (if --output-schema is passed to codex)
- Installs a local PATH shim for `codex` (does NOT touch your global install).
- Scratch repro uses: task-master init --yes, then runs expand + parse-prd.

Examples:
  ./scripts/taskmaster_codex_diag_v3.sh
  ./scripts/taskmaster_codex_diag_v3.sh --project . --model gpt-5.2 --id 1
  ./scripts/taskmaster_codex_diag_v3.sh --no-scratch
USAGE
}

PROJECT="."
TASK_ID=""
TAG="master"
MODEL_ID="gpt-5.2"
DO_SCRATCH="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --id) TASK_ID="${2:?}"; shift 2 ;;
    --tag) TAG="${2:?}"; shift 2 ;;
    --model) MODEL_ID="${2:?}"; shift 2 ;;
    --no-scratch) DO_SCRATCH="0"; shift 1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }

LOG_DIR="taskmaster_codex_diag_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/diag.log"
CODEX_SHIM_LOG="$LOG_DIR/codex_shim.log"
mkdir -p "$LOG_DIR/schemas" "$LOG_DIR/bin"

# tee everything
exec > >(tee -a "$LOG") 2>&1

section() {
  echo
  echo "================================================================================"
  echo "$1"
  echo "================================================================================"
}

run_cmd() {
  echo
  echo "[cmd] $*"
  set +e
  "$@"
  rc=$?
  echo "[exit] $rc"
  set -e
  return $rc
}

resolve() {
  # prints resolved command or empty
  command -v "$1" 2>/dev/null || true
}

redact_env_presence() {
  local k="$1"
  if [[ -n "${!k-}" ]]; then
    echo "$k = (set)"
  else
    echo "$k = (unset)"
  fi
}

node_json_summary_config() {
  local cfg="$1"
  CONFIG_JSON="$cfg" node - <<'NODE'
const fs = require("fs");
const p = process.env.CONFIG_JSON;
try {
  const raw = fs.readFileSync(p, "utf8");
  const j = JSON.parse(raw);

  // Heuristics: avoid printing secrets; show model wiring and providers.
  const out = {};
  if (j.models) {
    out.models = j.models;
  }
  if (j.providers) {
    out.providers = Object.keys(j.providers);
  }
  if (j.currentTag) out.currentTag = j.currentTag;

  process.stdout.write(JSON.stringify(out, null, 2) + "\n");
} catch (e) {
  process.stdout.write(`[error] failed to parse config.json: ${e.message}\n`);
}
NODE
}

node_find_first_task_id() {
  local tasks_json="$1"
  TASKS_JSON="$tasks_json" node - <<'NODE'
const fs = require("fs");
const p = process.env.TASKS_JSON;
try {
  const j = JSON.parse(fs.readFileSync(p, "utf8"));

  // tasks.json can be either legacy {tasks:[...]} or tag-scoped {master:{tasks:[...]}}
  let tasks = [];
  if (Array.isArray(j.tasks)) tasks = j.tasks;
  else if (j.master && Array.isArray(j.master.tasks)) tasks = j.master.tasks;
  else {
    // first tag key that looks like {tasks:[...]}
    for (const k of Object.keys(j)) {
      if (j[k] && Array.isArray(j[k].tasks)) { tasks = j[k].tasks; break; }
    }
  }

  const first = tasks.find(t => t && (typeof t.id === "number" || typeof t.id === "string"));
  if (!first) process.exit(0);

  // normalize "1" -> 1 if possible
  if (typeof first.id === "number") process.stdout.write(String(first.id));
  else {
    const n = Number(first.id);
    process.stdout.write(Number.isFinite(n) ? String(n) : String(first.id));
  }
} catch (_) {}
NODE
}

install_codex_shim() {
  local real_codex="$1"
  local shim="$LOG_DIR/bin/codex"

  cat >"$shim" <<'SHIM'
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

LOG_FILE="${CODEX_SHIM_LOG:?}"
REAL_CODEX="${REAL_CODEX:?}"
SCHEMA_DIR="${SCHEMA_DIR:?}"

ts() { date +"%Y-%m-%dT%H:%M:%S%z"; }

{
  echo "-----"
  echo "[ts] $(ts)"
  echo "[cwd] $(pwd)"
  echo "[argv] $0 $*"
  echo "[env] OPENAI_API_KEY=$( [[ -n "${OPENAI_API_KEY-}" ]] && echo set || echo unset )"
} >>"$LOG_FILE"

schema_path=""
prev=""

for a in "$@"; do
  if [[ "$prev" == "--output-schema" ]]; then
    schema_path="$a"
    break
  fi
  case "$a" in
    --output-schema=*)
      schema_path="${a#--output-schema=}"
      break
      ;;
  esac
  prev="$a"
done

if [[ -n "$schema_path" ]]; then
  {
    echo "[schema] detected --output-schema: $schema_path"
  } >>"$LOG_FILE"

  if [[ -f "$schema_path" ]]; then
    base="$(basename "$schema_path")"
    cp -f "$schema_path" "$SCHEMA_DIR/$base" 2>>"$LOG_FILE" || true
    # pretty print if python is available
    if command -v python3 >/dev/null 2>&1; then
      python3 -m json.tool "$schema_path" >"$SCHEMA_DIR/${base%.json}.pretty.json" 2>>"$LOG_FILE" || true
    fi
  else
    echo "[schema] file not found at path (yet?): $schema_path" >>"$LOG_FILE"
  fi
fi

exec "$REAL_CODEX" "$@"
SHIM

  chmod +x "$shim"
}

section "Header"
echo "Log: $LOG"
echo "ProjectPath: $(cd "$PROJECT" && pwd)"
echo "Time: $(ts)"
echo "User: $(id -un 2>/dev/null || true)"
echo "Shell: ${SHELL-unknown}"
echo

section "Command resolution (PATH precedence)"
for c in task-master task-master-ai tm codex codex-cli node npm pnpm bun npx; do
  p="$(resolve "$c")"
  if [[ -n "$p" ]]; then
    echo "$c -> $p"
  else
    echo "$c -> (not found)"
  fi
done

section "Runtime versions"
run_cmd node --version || true
run_cmd npm --version || true
run_cmd pnpm --version || true
run_cmd npx --version || true

# Codex CLI is installed as `codex` (it may print "codex-cli X.Y.Z")
if [[ -n "$(resolve codex)" ]]; then
  run_cmd codex --version || true
elif [[ -n "$(resolve codex-cli)" ]]; then
  run_cmd codex-cli --version || true
fi

section "Env var presence (values redacted)"
for k in OPENAI_API_KEY OPENAI_BASE_URL ANTHROPIC_API_KEY PERPLEXITY_API_KEY OPENROUTER_API_KEY \
         AZURE_OPENAI_API_KEY AZURE_OPENAI_ENDPOINT GOOGLE_API_KEY VERTEX_PROJECT_ID VERTEX_LOCATION \
         TASK_MASTER_DEBUG TASKMASTER_DEBUG TASK_MASTER_LOG_LEVEL TASKMASTER_LOG_LEVEL; do
  redact_env_presence "$k"
done

section "Project files (.taskmaster + configs)"
ABS_PROJECT="$(cd "$PROJECT" && pwd)"
CFG="$ABS_PROJECT/.taskmaster/config.json"
STATE="$ABS_PROJECT/.taskmaster/state.json"
TASKS_JSON="$ABS_PROJECT/.taskmaster/tasks/tasks.json"
ENV_FILE="$ABS_PROJECT/.env"
MCP_CURSOR="$ABS_PROJECT/.cursor/mcp.json"

echo "exists $CFG = $( [[ -f "$CFG" ]] && echo true || echo false )"
echo "exists $STATE = $( [[ -f "$STATE" ]] && echo true || echo false )"
echo "exists $TASKS_JSON = $( [[ -f "$TASKS_JSON" ]] && echo true || echo false )"
echo "exists $MCP_CURSOR = $( [[ -f "$MCP_CURSOR" ]] && echo true || echo false )"
echo "exists $ENV_FILE = $( [[ -f "$ENV_FILE" ]] && echo true || echo false )"

if [[ -f "$CFG" ]]; then
  echo
  echo "[.taskmaster/config.json] parsed summary (no secrets):"
  node_json_summary_config "$CFG"
fi

if [[ -f "$TASKS_JSON" ]]; then
  echo
  echo "[.taskmaster/tasks/tasks.json] first task id (best-effort):"
  id_guess="$(node_find_first_task_id "$TASKS_JSON" || true)"
  echo "${id_guess:-"(none found)"}"
  if [[ -z "$TASK_ID" && -n "$id_guess" ]]; then
    TASK_ID="$id_guess"
  fi
fi

if [[ -f "$ENV_FILE" ]]; then
  echo
  echo "[.env] present. Keys detected (names only):"
  # shell-safe: only extract KEY= prefix names
  grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" | sed -E 's/=.*$//' | sort -u | sed 's/^/- /' || true
fi

section "Task Master version + models"
run_cmd task-master --version || true
run_cmd task-master models --help || true
run_cmd task-master models || true

section "Published versions (no execution)"
if [[ -n "$(resolve npm)" ]]; then
  run_cmd npm view task-master-ai version || true
  run_cmd npm view @openai/codex version || true
fi

section "Install local codex shim (captures --output-schema if passed)"
REAL_CODEX_BIN="$(resolve codex || true)"
if [[ -n "$REAL_CODEX_BIN" ]]; then
  export CODEX_SHIM_LOG
  export REAL_CODEX="$REAL_CODEX_BIN"
  export SCHEMA_DIR="$ABS_PROJECT/$LOG_DIR/schemas"
  install_codex_shim "$REAL_CODEX_BIN"
  export PATH="$ABS_PROJECT/$LOG_DIR/bin:$PATH"
  echo "Installed shim: $ABS_PROJECT/$LOG_DIR/bin/codex"
  echo "Shim log:       $CODEX_SHIM_LOG"
else
  echo "codex not found; shim not installed."
fi

section "Codex auth quick checks (best-effort; non-fatal)"
if [[ -n "$(resolve codex)" ]]; then
  # Some builds support `codex auth status`, others `codex login --status`.
  run_cmd codex auth status || true
  run_cmd codex login --status || true
fi

if [[ "$DO_SCRATCH" == "1" ]]; then
  section "Scratch reproduction (isolated directory; attempts expand + parse-prd)"
  SCRATCH="$ABS_PROJECT/$LOG_DIR/scratch_project"
  mkdir -p "$SCRATCH"
  pushd "$SCRATCH" >/dev/null

  echo "Scratch dir: $SCRATCH"

  # init project non-interactively (supported as --yes / -y in recent versions)
  run_cmd task-master init --yes || run_cmd task-master init -y || true

  # force models to codex-cli provider by selecting a codex-cli model id
  run_cmd task-master models --set-main "$MODEL_ID" || true
  run_cmd task-master models --set-research "$MODEL_ID" || true
  run_cmd task-master models --set-fallback "$MODEL_ID" || true
  run_cmd task-master models || true

  # ensure tasks.json exists with a numeric id (1) to avoid "Task 1 not found" due to string ids
  mkdir -p .taskmaster/tasks
  cat > .taskmaster/tasks/tasks.json <<JSON
{
  "$TAG": {
    "tasks": [
      {
        "id": 1,
        "title": "Diag Repro Task",
        "description": "Minimal task to trigger expand using Codex CLI provider.",
        "status": "pending",
        "dependencies": [],
        "priority": "low",
        "details": "",
        "testStrategy": "",
        "subtasks": []
      }
    ],
    "metadata": {
      "tag": { "currentTag": "$TAG", "availableTags": ["$TAG"] }
    }
  }
}
JSON

  echo
  echo "Running expand (should hit generateObject path):"
  run_cmd task-master expand --id=1 --num=1 --prompt="Generate exactly 1 trivial subtask." || true

  # parse-prd attempt (flags vary by version)
  cat > prd.md <<'PRD'
# Minimal PRD
Build a tiny CLI that prints "hello" and has one unit test.
PRD

  echo
  echo "Running parse-prd (best-effort flag detection):"
  if task-master parse-prd --help 2>/dev/null | grep -q -- "--file"; then
    run_cmd task-master parse-prd --file prd.md || true
  else
    run_cmd task-master parse-prd prd.md || run_cmd task-master parse-prd || true
  fi

  popd >/dev/null

  section "Schema capture results"
  if compgen -G "$LOG_DIR/schemas/*" >/dev/null; then
    echo "Captured schema files:"
    ls -la "$LOG_DIR/schemas"
  else
    echo "No schema file captured (Task Master may not be passing --output-schema to codex in this path)."
    echo "Still useful: $CODEX_SHIM_LOG"
  fi
fi

section "Done"
echo "Log directory: $LOG_DIR"
echo "Primary log:   $LOG"
echo "Codex shim log: $CODEX_SHIM_LOG"
