from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .analyzer import RepositoryAnalyzer
from .context_budget import BudgetDecision, build_context_budget
from .config import AppConfig
from .context_compaction import compact_material
from .full_builder import build_llms_full_from_repo
from .fallback import (
    fallback_llms_payload,
    fallback_markdown_from_payload,
)
from .github import gather_repository_material, owner_repo_from_url
from .graph_builder import build_repo_graph, emit_graph_files
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
from .reasoning import sanitize_final_output
from .repo_digest import build_repo_digest
from .retry_policy import ErrorClass, classify_generation_error, next_retry_budget
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
    build_full: bool = True,
    build_ctx: bool | None = None,
    generate_graph: bool | None = None,
    graph_only: bool = False,
    verbose_budget: bool = False,
    enable_session_memory: bool | None = None,
) -> GenerationArtifacts:
    owner, repo = owner_repo_from_url(repo_url)
    repo_root = config.ensure_output_root(owner, repo)
    base_name = repo.lower().replace(" ", "-")

    logger.debug("Preparing repository material for %s", repo_url)
    material = prepare_repository_material(config, repo_url)
    try:
        analyzer = RepositoryAnalyzer(production_mode=True)
    except TypeError:
        # Compatibility with tests that monkeypatch RepositoryAnalyzer as a zero-arg callable.
        analyzer = RepositoryAnalyzer()

    fallback_payload = None
    used_fallback = False
    project_name = repo.replace("-", " ").replace("_", " ").title()

    model_loaded = False

    try:
        logger.info("Configuring LM Studio model '%s'", config.lm_model)
        configure_lmstudio_lm(config, cache=cache_lm)
        model_loaded = True

        working_material = material
        budget = build_context_budget(config, working_material)
        if verbose_budget:
            logger.info(
                "Initial budget: estimated=%s available=%s decision=%s",
                budget.estimated_prompt_tokens,
                budget.available_tokens,
                budget.decision,
            )

        if budget.decision != BudgetDecision.APPROVED:
            working_material = compact_material(working_material, budget, config)
            budget = build_context_budget(config, working_material)
            if verbose_budget:
                logger.info(
                    "After compaction: estimated=%s available=%s decision=%s",
                    budget.estimated_prompt_tokens,
                    budget.available_tokens,
                    budget.decision,
                )

        repo_digest = build_repo_digest(working_material, topic=project_name)
        llms_text = ""
        retry_step = 0
        current_budget = budget
        while True:
            try:
                result = analyzer(
                    repo_url=working_material.repo_url,
                    file_tree=working_material.file_tree,
                    readme_content=working_material.readme_content,
                    package_files=working_material.package_files,
                    default_branch=working_material.default_branch,
                    is_private=working_material.is_private,
                    github_token=config.github_token,
                    link_style=config.link_style,
                    repo_digest=repo_digest,
                )
                llms_text = result.llms_txt_content
                break
            except Exception as exc:
                err_class = classify_generation_error(exc)
                if err_class in (ErrorClass.CONTEXT_LENGTH, ErrorClass.PAYLOAD_LIMIT):
                    reduced = next_retry_budget(
                        current_budget,
                        retry_step,
                        reduction_steps=config.retry_reduction_steps,
                    )
                    retry_step += 1
                    if reduced is None:
                        raise
                    current_budget = reduced
                    working_material = compact_material(working_material, current_budget, config)
                    repo_digest = build_repo_digest(working_material, topic=project_name)
                    if verbose_budget:
                        logger.warning(
                            "Retrying generation with reduced budget step=%s estimated=%s available=%s",
                            retry_step,
                            current_budget.estimated_prompt_tokens,
                            current_budget.available_tokens,
                        )
                    continue
                raise
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
            is_private=material.is_private,
            github_token=config.github_token,
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
            is_private=material.is_private,
            github_token=config.github_token,
            link_style=config.link_style,
        )
        llms_text = fallback_markdown_from_payload(project_name, fallback_payload)
    finally:
        if model_loaded and config.lm_auto_unload:
            unload_lmstudio_model(config)

    sanitized = sanitize_final_output(llms_text, strict=True)
    llms_txt_path = repo_root / f"{base_name}-llms.txt"
    logger.info("Writing llms.txt to %s", llms_txt_path)
    _write_text(llms_txt_path, sanitized.text or llms_text, stamp)

    ctx_path: Optional[Path] = None
    should_build_ctx = config.enable_ctx if build_ctx is None else build_ctx
    if should_build_ctx:
        try:
            from llms_txt import create_ctx  # type: ignore
        except ImportError:
            create_ctx = None  # type: ignore
        if create_ctx:
            ctx_text = create_ctx(llms_text, optional=False)
            ctx_path = repo_root / f"{base_name}-llms-ctx.txt"
            logger.debug("Writing llms-ctx to %s", ctx_path)
            _write_text(ctx_path, ctx_text, stamp)

    llms_full_path: Optional[Path] = None
    if build_full and not graph_only:
        llms_full_text = build_llms_full_from_repo(
            sanitized.text or llms_text,
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

    graph_json_path: Optional[Path] = None
    force_graph_path: Optional[Path] = None
    graph_nodes_dir: Optional[Path] = None
    should_generate_graph = config.enable_repo_graph if generate_graph is None else bool(generate_graph)
    if should_generate_graph:
        digest = build_repo_digest(material, topic=project_name)
        graph = build_repo_graph(digest)
        graph_paths = emit_graph_files(graph, repo_root / "graph")
        graph_json_path = Path(graph_paths["graph_json"])
        force_graph_path = Path(graph_paths["force_json"])
        graph_nodes_dir = Path(graph_paths["nodes_dir"])

    if enable_session_memory if enable_session_memory is not None else config.enable_session_memory:
        try:
            from lms_llmsTxt_mcp.session_memory import SessionMemoryStore

            memory = SessionMemoryStore(repo_root / "session-memory.jsonl")
            memory.append_event(
                "generation",
                {
                    "repo_url": repo_url,
                    "used_fallback": used_fallback,
                    "llms_txt_path": str(llms_txt_path),
                    "graph_json_path": str(graph_json_path) if graph_json_path else None,
                },
            )
        except Exception:  # pragma: no cover - memory is optional
            logger.exception("Failed to append session memory event")

    return GenerationArtifacts(
        llms_txt_path=str(llms_txt_path),
        llms_full_path=str(llms_full_path) if llms_full_path else None,
        ctx_path=str(ctx_path) if ctx_path else None,
        json_path=str(json_path) if json_path else None,
        graph_json_path=str(graph_json_path) if graph_json_path else None,
        force_graph_path=str(force_graph_path) if force_graph_path else None,
        graph_nodes_dir=str(graph_nodes_dir) if graph_nodes_dir else None,
        used_fallback=used_fallback,
    )
