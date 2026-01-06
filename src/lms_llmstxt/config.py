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
            "LMSTUDIO_MODEL", "qwen3-4b-instruct-2507@q6_k_xl"
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

    def ensure_output_root(self, owner: str, repo: str) -> Path:
        """Return ``<output_root>/<owner>/<repo>`` and create it if missing."""
        repo_root = self.output_dir / owner / repo
        repo_root.mkdir(parents=True, exist_ok=True)
        return repo_root
