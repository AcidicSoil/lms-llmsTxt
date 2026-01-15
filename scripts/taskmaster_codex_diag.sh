# path: scripts/taskmaster_codex_diag.sh
#!/usr/bin/env bash
# Task Master + Codex CLI diagnostics (bash)
#
# Usage:
#   ./scripts/taskmaster_codex_diag.sh
#   ./scripts/taskmaster_codex_diag.sh --project /path/to/repo
#   ./scripts/taskmaster_codex_diag.sh -- task-master expand --id=123
#   ./scripts/taskmaster_codex_diag.sh --project /path/to/repo -- task-master expand --id=123
#
# Notes:
# - Does NOT print API key values (only presence + length).
# - Reads .taskmaster/config.json and prints only non-secret fields.
set -u

PROJECT="."
RUN_CMD=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)
      PROJECT="$2"; shift 2;;
    --)
      shift
      RUN_CMD=("$@")
      break;;
    *)
      # If user didn't pass --, treat remaining args as run command.
      RUN_CMD=("$@")
      break;;
  esac
done

PROJECT="$(cd "$PROJECT" && pwd)"

LOG_DIR="$PROJECT/logs"
mkdir -p "$LOG_DIR"
TS="$(date +%Y%m%d_%H%M%S)"
LOG="$LOG_DIR/taskmaster_codex_diag_${TS}.log"

# Tee everything into log
exec > >(tee -a "$LOG") 2>&1

section() {
  echo ""
  echo "========================================================================================"
  echo "$1"
  echo "========================================================================================"
}

have() { command -v "$1" >/dev/null 2>&1; }

run_cmd() {
  local label="$1"; shift
  echo ""
  echo "[cmd] $label"
  echo "[exe] $1"
  echo "[arg] ${*:2}"
  "$@" || echo "[exit] $?"
}

env_presence() {
  local name="$1"
  local val="${!name-}"
  if [[ -z "${val}" ]]; then
    echo "$name = (unset)"
  else
    echo "$name = (set, length=${#val})"
  fi
}

redact_json_extract() {
  # Best-effort extraction via node if available, otherwise print a warning.
  local cfg="$1"
  if ! have node; then
    echo "[warn] node not found; cannot parse JSON summary for $cfg"
    return 0
  fi

  node - <<'NODE' "$cfg"
const fs = require("fs");
const path = process.argv[1];
try {
  const raw = fs.readFileSync(path, "utf8");
  const j = JSON.parse(raw);
  const roles = ["main","research","fallback"];
  if (j.models) {
    for (const r of roles) {
      if (j.models[r]) {
        const m = j.models[r];
        console.log(`models.${r}: provider=${m.provider ?? ""} modelId=${m.modelId ?? ""} maxTokens=${m.maxTokens ?? ""} temperature=${m.temperature ?? ""} baseURL=${m.baseURL ?? ""}`);
      }
    }
  }
  if (j.global) {
    const g = j.global;
    console.log(`global: logLevel=${g.logLevel ?? ""} debug=${g.debug ?? ""} defaultTag=${g.defaultTag ?? ""} projectName=${g.projectName ?? ""}`);
  }
} catch (e) {
  console.log(`[error] failed to parse config.json: ${e.message}`);
}
NODE
}

section "Header"
echo "Log: $LOG"
echo "ProjectPath: $PROJECT"
echo "Time: $(date -Iseconds)"
echo "User: $(id -un 2>/dev/null || true)"
echo "Shell: bash ${BASH_VERSION:-}"

cd "$PROJECT"

section "Command resolution (PATH precedence)"
for n in task-master task-master-ai tm codex node npm pnpm bun npx; do
  if have "$n"; then
    echo "$n -> $(command -v "$n")"
  else
    echo "$n -> (not found)"
  fi
done

section "Runtime versions"
have node && run_cmd "node --version" node --version || echo "node -> (not found)"
have npm && run_cmd "npm --version" npm --version || echo "npm -> (not found)"
have pnpm && run_cmd "pnpm --version" pnpm --version || echo "pnpm -> (not found)"
have bun && run_cmd "bun --version" bun --version || echo "bun -> (not found)"
have npx && run_cmd "npx --version" npx --version || echo "npx -> (not found)"
have codex && run_cmd "codex --version" codex --version || echo "codex -> (not found)"

section "Env var presence (values redacted)"
for v in \
  OPENAI_API_KEY OPENAI_BASE_URL \
  ANTHROPIC_API_KEY PERPLEXITY_API_KEY OPENROUTER_API_KEY \
  AZURE_OPENAI_API_KEY AZURE_OPENAI_ENDPOINT \
  GOOGLE_API_KEY VERTEX_PROJECT_ID VERTEX_LOCATION \
  TASK_MASTER_DEBUG TASKMASTER_DEBUG TASK_MASTER_LOG_LEVEL TASKMASTER_LOG_LEVEL
do
  env_presence "$v"
done

section "Project files (.taskmaster + configs)"
CFG="$PROJECT/.taskmaster/config.json"
STATE="$PROJECT/.taskmaster/state.json"
LEGACY="$PROJECT/.taskmasterconfig"
CURSOR="$PROJECT/.cursor/mcp.json"
DOTENV="$PROJECT/.env"

for p in "$CFG" "$STATE" "$LEGACY" "$CURSOR" "$DOTENV"; do
  if [[ -f "$p" ]]; then
    echo "exists $p = true"
  else
    echo "exists $p = false"
  fi
done

if [[ -f "$CFG" ]]; then
  echo ""
  echo "[.taskmaster/config.json] parsed summary (no secrets):"
  redact_json_extract "$CFG"
fi

if [[ -f "$DOTENV" ]]; then
  echo ""
  echo "[.env] present. Keys detected (names only):"
  # names only, no values
  grep -E '^[[:space:]]*[A-Z0-9_]+[[:space:]]*=' "$DOTENV" \
    | sed -E 's/^[[:space:]]*([A-Z0-9_]+)[[:space:]]*=.*$/- \1/' \
    | sort -u || true
fi

section "Task Master CLI checks (installed vs npx@latest)"
TM_BIN=""
for c in task-master task-master-ai tm; do
  if have "$c"; then TM_BIN="$c"; break; fi
done

if [[ -n "$TM_BIN" ]]; then
  run_cmd "$TM_BIN --version" "$TM_BIN" --version || true
  run_cmd "$TM_BIN models" "$TM_BIN" models || true
  run_cmd "$TM_BIN models --show" "$TM_BIN" models --show || true
else
  echo "No Task Master binary found on PATH (task-master / task-master-ai / tm)."
fi

if have npx; then
  run_cmd "npx -y task-master-ai@latest --version" npx -y task-master-ai@latest --version || true
  run_cmd "npx -y task-master-ai@latest models --show" npx -y task-master-ai@latest models --show || true
else
  echo "npx not found; skipping npx@latest checks."
fi

section "Package-manager view (best-effort)"
have npm && run_cmd "npm ls -g --depth=0 task-master-ai" npm ls -g --depth=0 task-master-ai || true
have pnpm && run_cmd "pnpm list -g --depth=0 task-master-ai" pnpm list -g --depth=0 task-master-ai || true
if have bun; then
  # bun global list varies by version; best-effort
  run_cmd "bun pm ls -g (best-effort)" bun pm ls -g || true
fi

if [[ ${#RUN_CMD[@]} -gt 0 ]]; then
  section "Run provided workflow command (captured output)"
  echo "[run] ${RUN_CMD[*]}"
  "${RUN_CMD[@]}" || echo "[exit] $?"
fi

echo ""
echo "Wrote log to: $LOG"
