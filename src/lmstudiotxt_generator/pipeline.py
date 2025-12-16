from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .analyzer import RepositoryAnalyzer
from .config import AppConfig
from .full_builder import build_llms_full_from_repo
from .fallback import (
    fallback_llms_payload,
    fallback_markdown_from_payload,
)
from .github import gather_repository_material, owner_repo_from_url
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
from .schema import LLMS_JSON_SCHEMA

try:  # Optional import; litellm is a transitive dependency of dspy.
    from litellm.exceptions import BadRequestError as LiteLLMBadRequestError
except Exception:  # pragma: no cover - fall back to generic Exception
    LiteLLMBadRequestError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import RateLimitError as LiteLLMRateLimitError
except Exception:  # pragma: no cover
    LiteLLMRateLimitError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import AuthenticationError as LiteAuthError
except Exception:  # pragma: no cover
    LiteAuthError = tuple()  # type: ignore[assignment]
try:
    from litellm.exceptions import NotFoundError as LiteNotFoundError
except Exception:  # pragma: no cover
    LiteNotFoundError = tuple()  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _timestamp_comment(prefix: str = "# Generated") -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"{prefix}: {now} UTC"


def _write_text(path: Path, content: str, stamp: bool) -> None:
    text = content.rstrip()
    if stamp:
        text += "\n\n" + _timestamp_comment()
    path.write_text(text + "\n", encoding="utf-8")


def prepare_repository_material(config: AppConfig, repo_url: str) -> RepositoryMaterial:
    return gather_repository_material(repo_url, config.github_token)


def run_generation(
    repo_url: str,
    config: AppConfig,
    *,
    stamp: bool = False,
    cache_lm: bool = False,
) -> GenerationArtifacts:
    owner, repo = owner_repo_from_url(repo_url)
    repo_root = config.ensure_output_root(owner, repo)
    base_name = repo.lower().replace(" ", "-")

    logger.debug("Preparing repository material for %s", repo_url)
    material = prepare_repository_material(config, repo_url)
    analyzer = RepositoryAnalyzer()

    fallback_payload = None
    used_fallback = False
    project_name = repo.replace("-", " ").replace("_", " ").title()

    model_loaded = False

    try:
        logger.info("Configuring LM Studio model '%s'", config.lm_model)
        configure_lmstudio_lm(config, cache=cache_lm)
        model_loaded = True

        result = analyzer(
            repo_url=material.repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            package_files=material.package_files,
            default_branch=material.default_branch,
            link_style=config.link_style,
        )
        llms_text = result.llms_txt_content
    except (
        LiteLLMBadRequestError,
        LiteLLMRateLimitError,
        LiteAuthError,
        LiteNotFoundError,
        LMStudioConnectivityError,
    ) as exc:
        used_fallback = True
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            link_style=config.link_style,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    except Exception as exc:  # pragma: no cover - defensive fallback
        used_fallback = True
        logger.exception("Unexpected error during DSPy generation: %s", exc)
        logger.warning("Falling back to heuristic llms.txt generation using %s.", LLMS_JSON_SCHEMA["title"])
        fallback_payload = fallback_llms_payload(
            repo_name=project_name,
            repo_url=repo_url,
            file_tree=material.file_tree,
            readme_content=material.readme_content,
            default_branch=material.default_branch,
            link_style=config.link_style,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    finally:
        if model_loaded and config.lm_auto_unload:
            unload_lmstudio_model(config)

    llms_txt_path = repo_root / f"{base_name}-llms.txt"
    logger.info("Writing llms.txt to %s", llms_txt_path)
    _write_text(llms_txt_path, llms_text, stamp)

    ctx_path: Optional[Path] = None
    if config.enable_ctx:
        try:
            from llms_txt import create_ctx  # type: ignore
        except ImportError:
            create_ctx = None  # type: ignore
        if create_ctx:
            ctx_text = create_ctx(llms_text, optional=False)
            ctx_path = repo_root / f"{base_name}-llms-ctx.txt"
            logger.debug("Writing llms-ctx to %s", ctx_path)
            _write_text(ctx_path, ctx_text, stamp)

    llms_full_text = build_llms_full_from_repo(
        llms_text,
        prefer_raw=not material.is_private,
        default_ref=material.default_branch,
        token=config.github_token,
        link_style=config.link_style,
    )
    llms_full_path = repo_root / f"{base_name}-llms-full.txt"
    logger.debug("Writing llms-full to %s", llms_full_path)
    _write_text(llms_full_path, llms_full_text, stamp)

    json_path: Optional[Path] = None
    if fallback_payload:
        json_path = repo_root / f"{base_name}-llms.json"
        json_path.write_text(json.dumps(fallback_payload, indent=2), encoding="utf-8")
        logger.info("Fallback JSON payload written to %s", json_path)

    return GenerationArtifacts(
        llms_txt_path=str(llms_txt_path),
        llms_full_path=str(llms_full_path),
        ctx_path=str(ctx_path) if ctx_path else None,
        json_path=str(json_path) if json_path else None,
        used_fallback=used_fallback,
    )
