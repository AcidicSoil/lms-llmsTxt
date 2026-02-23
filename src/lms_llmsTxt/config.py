from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    """
    Runtime configuration for the LM Studio llms.txt generator.

    Users can override defaults through environment variables:
      - ``LMSTUDIO_MODEL``: LM Studio model identifier.
      - ``LMSTUDIO_BASE_URL``: API base URL (defaults to http://localhost:1234/v1).
      - ``LMSTUDIO_API_KEY``: Optional API key (LM Studio accepts any string).
      - ``OUTPUT_DIR``: Root folder for generated artifacts.
      - ``ENABLE_CTX``: Set truthy to emit llms-ctx.txt files when llms_txt.create_ctx
        is available.
    """
    lm_model: str = field(
        default_factory=lambda: os.getenv(
            "LMSTUDIO_MODEL", "qwen_qwen3-vl-4b-instruct"
        )
    )
    lm_api_base: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    )
    lm_api_key: str = field(
        default_factory=lambda: os.getenv("LMSTUDIO_API_KEY", "lm-studio")
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "artifacts"))
    )
    github_token: str | None = field(
        default_factory=lambda: os.getenv("GITHUB_ACCESS_TOKEN")
        or os.getenv("GH_TOKEN")
    )
    link_style: str = field(
        default_factory=lambda: os.getenv("LINK_STYLE", "blob")
    )
    enable_ctx: bool = field(default_factory=lambda: _env_flag("ENABLE_CTX", False))
    lm_streaming: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_STREAMING", True))
    lm_auto_unload: bool = field(default_factory=lambda: _env_flag("LMSTUDIO_AUTO_UNLOAD", True))
    max_context_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_CONTEXT_TOKENS", "32768"))
    )
    max_output_tokens: int = field(
        default_factory=lambda: int(os.getenv("MAX_OUTPUT_TOKENS", "4096"))
    )
    context_headroom_ratio: float = field(
        default_factory=lambda: float(os.getenv("CONTEXT_HEADROOM_RATIO", "0.15"))
    )
    max_file_tree_lines: int = field(
        default_factory=lambda: int(os.getenv("MAX_FILE_TREE_LINES", "1200"))
    )
    max_readme_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_README_CHARS", "24000"))
    )
    max_package_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_PACKAGE_CHARS", "18000"))
    )
    retry_reduction_steps: tuple[float, ...] = field(
        default_factory=lambda: tuple(
            float(part.strip())
            for part in os.getenv("RETRY_REDUCTION_STEPS", "0.70,0.50").split(",")
            if part.strip()
        )
    )
    enable_repo_graph: bool = field(default_factory=lambda: _env_flag("ENABLE_REPO_GRAPH", False))
    enable_session_memory: bool = field(
        default_factory=lambda: _env_flag("ENABLE_SESSION_MEMORY", False)
    )

    def ensure_output_root(self, owner: str, repo: str) -> Path:
        """Return ``<output_root>/<owner>/<repo>`` and create it if missing."""
        repo_root = self.output_dir / owner / repo
        repo_root.mkdir(parents=True, exist_ok=True)
        return repo_root
