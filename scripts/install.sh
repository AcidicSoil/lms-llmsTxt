#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Install lms-llmsTxt dependencies.

Usage:
  scripts/install.sh [options]

Install modes:
  --pypi             Install the released CLI and MCP server from PyPI.
  --dev              Install this checkout in editable/development mode.
  --ui               Install HyperGraph UI dependencies under hypergraph/.
  --docs             Install documentation-site dependencies with pnpm.
  --ctx              Verify optional llms-ctx.txt support packages are installed.
  --all              Run --dev, --ui, --docs, and --ctx.

Python installer selection:
  --uv               Use uv for Python environment and package installation.
  --pip              Use python/pip for Python environment and package installation.

Environment options:
  --venv PATH        Virtual environment path for Python installs. Default: .venv
  --no-venv          Do not create or use a virtual environment for Python installs.
  --no-corepack      Skip corepack enable before pnpm install.

Other options:
  --help             Show this help.

Examples:
  scripts/install.sh --pypi --uv
  scripts/install.sh --dev --ui --docs
  scripts/install.sh --all --uv
USAGE
}

log() {
  printf '==> %s\n' "$*"
}

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  local command_name="$1"
  command -v "$command_name" >/dev/null 2>&1 || fail "required command not found: $command_name"
}

project_root() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "${script_dir}/.." && pwd
}

activate_venv() {
  local venv_path="$1"
  # shellcheck disable=SC1090
  source "${venv_path}/bin/activate"
}

create_venv_with_pip() {
  local venv_path="$1"
  require_command python3
  if [[ ! -d "$venv_path" ]]; then
    log "Creating Python virtual environment at ${venv_path}"
    python3 -m venv "$venv_path"
  fi
  activate_venv "$venv_path"
  python -m pip install --upgrade pip
}

create_venv_with_uv() {
  local venv_path="$1"
  require_command uv
  if [[ ! -d "$venv_path" ]]; then
    log "Creating Python virtual environment at ${venv_path}"
    uv venv "$venv_path"
  fi
  activate_venv "$venv_path"
}

prepare_python_env() {
  local installer="$1"
  local venv_path="$2"
  local use_venv="$3"

  if [[ "$use_venv" == "0" ]]; then
    if [[ "$installer" == "uv" ]]; then
      require_command uv
    else
      require_command python3
      python3 -m pip install --upgrade pip
    fi
    return
  fi

  if [[ "$installer" == "uv" ]]; then
    create_venv_with_uv "$venv_path"
  else
    create_venv_with_pip "$venv_path"
  fi
}

install_pypi() {
  local installer="$1"
  if [[ "$installer" == "uv" ]]; then
    log "Installing released package from PyPI with uv"
    uv pip install lms-llmsTxt
  else
    log "Installing released package from PyPI with pip"
    python -m pip install lms-llmsTxt
  fi
}

install_dev() {
  local installer="$1"
  if [[ "$installer" == "uv" ]]; then
    log "Installing development dependencies with uv"
    uv sync --extra dev
  else
    log "Installing editable package with developer extra"
    python -m pip install -e '.[dev]'
  fi
}

install_ui() {
  require_command npm
  log "Installing HyperGraph UI dependencies"
  npm --prefix hypergraph install
}

install_docs() {
  local enable_corepack="$1"
  require_command pnpm
  if [[ "$enable_corepack" == "1" ]] && command -v corepack >/dev/null 2>&1; then
    log "Enabling corepack"
    corepack enable
  fi
  log "Installing documentation-site dependencies"
  pnpm install
}

verify_ctx() {
  log "Verifying optional context artifact packages"
  python -m pip show llms-txt llm-ctx >/dev/null
}

verify_console_scripts() {
  if command -v lmstxt >/dev/null 2>&1; then
    log "lmstxt is available: $(command -v lmstxt)"
  else
    log "lmstxt is not on PATH yet; activate the virtual environment before running it"
  fi

  if command -v lmstxt-mcp >/dev/null 2>&1; then
    log "lmstxt-mcp is available: $(command -v lmstxt-mcp)"
  else
    log "lmstxt-mcp is not on PATH yet; activate the virtual environment before running it"
  fi
}

main() {
  local install_pypi_flag=0
  local install_dev_flag=0
  local install_ui_flag=0
  local install_docs_flag=0
  local verify_ctx_flag=0
  local installer="pip"
  local venv_path=".venv"
  local use_venv=1
  local enable_corepack=1

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --pypi) install_pypi_flag=1 ;;
      --dev) install_dev_flag=1 ;;
      --ui) install_ui_flag=1 ;;
      --docs) install_docs_flag=1 ;;
      --ctx) verify_ctx_flag=1 ;;
      --all)
        install_dev_flag=1
        install_ui_flag=1
        install_docs_flag=1
        verify_ctx_flag=1
        ;;
      --uv) installer="uv" ;;
      --pip) installer="pip" ;;
      --venv)
        [[ $# -ge 2 ]] || fail "--venv requires a path"
        venv_path="$2"
        shift
        ;;
      --no-venv) use_venv=0 ;;
      --no-corepack) enable_corepack=0 ;;
      --help|-h)
        usage
        exit 0
        ;;
      *) fail "unknown option: $1" ;;
    esac
    shift
  done

  if [[ "$install_pypi_flag" == "1" && "$install_dev_flag" == "1" ]]; then
    fail "choose either --pypi or --dev, not both"
  fi

  if [[ "$install_pypi_flag$install_dev_flag$install_ui_flag$install_docs_flag$verify_ctx_flag" == "00000" ]]; then
    usage
    fail "choose at least one install mode"
  fi

  cd "$(project_root)"

  if [[ "$install_pypi_flag" == "1" || "$install_dev_flag" == "1" || "$verify_ctx_flag" == "1" ]]; then
    prepare_python_env "$installer" "$venv_path" "$use_venv"
  fi

  if [[ "$install_pypi_flag" == "1" ]]; then
    install_pypi "$installer"
  fi

  if [[ "$install_dev_flag" == "1" ]]; then
    install_dev "$installer"
  fi

  if [[ "$install_ui_flag" == "1" ]]; then
    install_ui
  fi

  if [[ "$install_docs_flag" == "1" ]]; then
    install_docs "$enable_corepack"
  fi

  if [[ "$verify_ctx_flag" == "1" ]]; then
    verify_ctx
  fi

  if [[ "$install_pypi_flag" == "1" || "$install_dev_flag" == "1" ]]; then
    verify_console_scripts
  fi

  log "Install step complete"
}

main "$@"
