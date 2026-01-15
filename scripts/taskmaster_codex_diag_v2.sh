# path: scripts/taskmaster_codex_diag.sh
#!/usr/bin/env bash
set -euo pipefail

# Task Master + Codex CLI diagnostic runner
#
# What it does:
# - Captures environment + Task Master/Codex versions
# - Runs a safe scratch reproduction (does NOT touch your project)
# - Wraps codex-cli to capture the --output-schema JSON file (if present)
# - Audits the captured schema for common strict-JSON-schema violations
#
# Usage:
#   bash scripts/taskmaster_codex_diag.sh
#   bash scripts/taskmaster_codex_diag.sh --compare-latest
#
# Notes:
# - "id=123" style IDs are placeholders; in your real project you'd use:
#     task-master list
#     task-master expand --id=<real-id> --num=1
#   (Shown in Task Master docs.)  See: docs/command-reference.md :contentReference[oaicite:4]{index=4}

COMPARE_LATEST=0
for arg in "$@"; do
  case "$arg" in
    --compare-latest) COMPARE_LATEST=1 ;;
    *)
      echo "Unknown arg: $arg" >&2
      echo "Supported: --compare-latest" >&2
      exit 2
      ;;
  esac
done

TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${TM_CODEX_DIAG_LOG_DIR:-taskmaster_codex_diag_${TS}}"
mkdir -p "$LOG_DIR"

LOG="$LOG_DIR/diag.log"
# tee everything to diag.log
exec > >(tee -a "$LOG") 2>&1

section() { printf "\n========== %s ==========\n" "$*"; }

section "Host"
echo "PWD: $(pwd)"
echo "DATE: $(date -Is || date)"
uname -a 2>/dev/null || true

section "Toolchain"
command -v node >/dev/null 2>&1 && node -v || echo "node: (not found)"
command -v npm  >/dev/null 2>&1 && npm -v  || echo "npm: (not found)"

section "Task Master / Codex CLI binaries"
command -v task-master  >/dev/null 2>&1 && echo "task-master: $(command -v task-master)" || echo "task-master: (not found)"
command -v codex-cli    >/dev/null 2>&1 && echo "codex-cli:   $(command -v codex-cli)"   || echo "codex-cli:   (not found)"
command -v codex        >/dev/null 2>&1 && echo "codex:       $(command -v codex)"       || echo "codex:       (not found)"

section "Versions"
(task-master --version 2>&1) || true
# codex-cli sometimes uses --version; fall back to -v
( codex-cli --version 2>&1 || codex-cli -v 2>&1 ) || true

if [[ "$COMPARE_LATEST" -eq 1 ]]; then
  section "Compare against npm @latest (non-destructive)"
  echo "Running: npx -y -p task-master-ai@latest task-master --version"
  (npx -y -p task-master-ai@latest task-master --version 2>&1) || true
fi

section "Task Master models (current directory)"
# Do NOT use "models --show" (not in the command reference).
(task-master models 2>&1) || true

###############################################################################
# Shim codex-cli to capture --output-schema
###############################################################################
section "Install codex-cli shim (captures --output-schema if used)"
REAL_CODEX_CLI="$(command -v codex-cli || true)"
SHIM_DIR="$LOG_DIR/shim"
mkdir -p "$SHIM_DIR"

if [[ -n "${REAL_CODEX_CLI}" ]]; then
  export REAL_CODEX_CLI
  export CODEX_SHIM_LOG="$LOG_DIR/codex_shim.log"
  export CODEX_SCHEMA_COPY_DIR="$LOG_DIR"

  cat > "$SHIM_DIR/codex-cli" <<'SH'
#!/usr/bin/env bash
set -euo pipefail

# Log invocation
{
  echo "[shim codex-cli] $(date -Is || date) argv: $0 $*"
} >> "${CODEX_SHIM_LOG:-/tmp/codex_shim.log}"

# Capture --output-schema <path> or --output-schema=<path>
schema_path=""
prev=""
for arg in "$@"; do
  if [[ "$prev" == "--output-schema" ]]; then
    schema_path="$arg"
    break
  fi
  case "$arg" in
    --output-schema=*)
      schema_path="${arg#--output-schema=}"
      break
      ;;
  esac
  prev="$arg"
done

if [[ -n "$schema_path" && -f "$schema_path" && -n "${CODEX_SCHEMA_COPY_DIR:-}" ]]; then
  # Best-effort copy; do not fail if permissions block it
  cp "$schema_path" "${CODEX_SCHEMA_COPY_DIR}/captured_output_schema.json" 2>/dev/null || true
fi

exec "${REAL_CODEX_CLI}" "$@"
SH
  chmod +x "$SHIM_DIR/codex-cli"
  export PATH="$SHIM_DIR:$PATH"
  echo "Installed shim at: $SHIM_DIR/codex-cli"
  echo "Shim log: $CODEX_SHIM_LOG"
else
  echo "codex-cli not found; shim not installed."
fi

###############################################################################
# Scratch reproduction (safe; does not modify your repo)
###############################################################################
section "Scratch reproduction (safe; isolated directory)"
SCRATCH_DIR="$LOG_DIR/scratch_project"
mkdir -p "$SCRATCH_DIR"
pushd "$SCRATCH_DIR" >/dev/null

# Minimal Task Master structure
mkdir -p .taskmaster/tasks

# Minimal tasks.json per Task Master task structure docs.
# (Keep it simple so 'expand' runs and exercises codex structured output.)
cat > .taskmaster/tasks/tasks.json <<'JSON'
[
  {
    "id": "1",
    "title": "Codex schema diagnostic task",
    "description": "Reproduce codex-cli structured output schema failure in Task Master",
    "status": "pending",
    "dependencies": [],
    "priority": "medium",
    "details": "Keep output minimal; generate exactly 1 subtask.",
    "testStrategy": "N/A",
    "subtasks": []
  }
]
JSON

section "Configure models to codex-cli for scratch"
# This is the documented way to select Codex CLI as provider for a role.
# If your installed version uses different flags, the error output is still useful for triage.
(task-master models --set-main=gpt-5-codex --codex-cli 2>&1) || true

section "Run expand in scratch (this is where codex schema errors typically show)"
echo "Command: task-master expand --id=1 --num=1 --prompt='Generate exactly 1 trivial subtask.'"
(task-master expand --id=1 --num=1 --prompt="Generate exactly 1 trivial subtask." 2>&1) || true

popd >/dev/null

###############################################################################
# If we captured a schema file, audit it for common strict-schema violations
###############################################################################
section "Schema capture + audit"
CAPTURED="$LOG_DIR/captured_output_schema.json"
if [[ -f "$CAPTURED" ]]; then
  echo "Captured schema: $CAPTURED"
  echo "Auditing for common strict-structured-output issues:"
  echo "- Every object schema should set additionalProperties:false"
  echo "- Many structured-output validators require required[] to include all properties keys"

  node - "$CAPTURED" > "$LOG_DIR/schema_audit.txt" <<'NODE'
const fs = require("fs");

const schemaPath = process.argv[2]; // IMPORTANT: with `node -`, argv[2] is the first user arg
if (!schemaPath) {
  console.error("Missing schema path arg");
  process.exit(2);
}

const root = JSON.parse(fs.readFileSync(schemaPath, "utf8"));

const missingAdditionalProps = [];
const missingRequiredKeys = [];

function isObjectSchema(s) {
  if (!s || typeof s !== "object") return false;
  if (s.type === "object") return true;
  if (s.properties && typeof s.properties === "object") return true;
  return false;
}

function walk(node, path) {
  if (!node || typeof node !== "object") return;

  if (isObjectSchema(node)) {
    // additionalProperties check
    if (node.additionalProperties !== false) {
      missingAdditionalProps.push(path || "(root)");
    }

    // required should include all properties keys (common requirement in strict schema setups)
    const props = node.properties && typeof node.properties === "object" ? Object.keys(node.properties) : [];
    if (props.length) {
      const req = Array.isArray(node.required) ? node.required : [];
      const missing = props.filter(k => !req.includes(k));
      if (missing.length) {
        missingRequiredKeys.push({ path: path || "(root)", missing });
      }
    }
  }

  // recurse common schema combinators
  const next = [
    ["properties", (n) => Object.values(n.properties || {})],
    ["items", (n) => Array.isArray(n.items) ? n.items : (n.items ? [n.items] : [])],
    ["anyOf", (n) => Array.isArray(n.anyOf) ? n.anyOf : []],
    ["oneOf", (n) => Array.isArray(n.oneOf) ? n.oneOf : []],
    ["allOf", (n) => Array.isArray(n.allOf) ? n.allOf : []],
    ["not",   (n) => n.not ? [n.not] : []],
    ["additionalProperties", (n) => (n.additionalProperties && typeof n.additionalProperties === "object") ? [n.additionalProperties] : []],
  ];

  for (const [label, getChildren] of next) {
    for (const child of getChildren(node)) {
      walk(child, path ? `${path}.${label}` : label);
    }
  }
}

walk(root, "");

console.log("== Schema audit results ==");
console.log("");
console.log("Missing/invalid additionalProperties:false on object schemas:");
if (missingAdditionalProps.length) {
  for (const p of missingAdditionalProps) console.log(" - " + p);
} else {
  console.log(" (none)");
}

console.log("");
console.log("Properties not listed in required[] (may break strict structured outputs):");
if (missingRequiredKeys.length) {
  for (const r of missingRequiredKeys) {
    console.log(` - ${r.path}: missing required keys: ${r.missing.join(", ")}`);
  }
} else {
  console.log(" (none)");
}
NODE

  echo "Wrote audit report: $LOG_DIR/schema_audit.txt"
  echo "Wrote codex shim log: $LOG_DIR/codex_shim.log"
else
  echo "No schema file captured."
  echo "If the failure happens before codex-cli receives --output-schema, the shim log will still help:"
  echo "  $LOG_DIR/codex_shim.log"
fi

section "Done"
echo "Log directory: $LOG_DIR"
echo "Primary log:   $LOG"
