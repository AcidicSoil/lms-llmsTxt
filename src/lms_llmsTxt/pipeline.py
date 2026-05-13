from __future__ import annotations

import json
import logging
import re
import requests
import threading
import time
import uuid
from dataclasses import asdict, is_dataclass
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
from .github import fetch_file_content, gather_repository_material, owner_repo_from_url
from .graph_builder import build_repo_graph, emit_graph_files
from .graph_dspy_synthesizer import enrich_repo_graph_with_dspy
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError, unload_lmstudio_model
from .models import GenerationArtifacts, RepositoryMaterial
from .reasoning import sanitize_final_output
from .repo_digest import EvidenceFetchLimits, apply_evidence_plan, build_repo_digest, plan_evidence_paths, suggested_evidence_limit
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


def _append_jsonl(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _record_run_event(
    *,
    events_path: Path,
    log_path: Path,
    run_id: str,
    stage: str,
    status: str,
    started_at: float | None = None,
    **fields: object,
) -> None:
    now = time.perf_counter()
    payload: dict[str, object] = {
        "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "run_id": run_id,
        "stage": stage,
        "status": status,
    }
    if started_at is not None:
        payload["duration_ms"] = round((now - started_at) * 1000, 2)
    payload.update({key: value for key, value in fields.items() if value is not None})
    _append_jsonl(events_path, payload)

    duration = f" duration_ms={payload['duration_ms']}" if "duration_ms" in payload else ""
    extras = " ".join(
        f"{key}={value}"
        for key, value in payload.items()
        if key not in {"ts", "run_id", "stage", "status", "duration_ms"}
    )
    line = f"{payload['ts']} {status.upper()} {stage}{duration} {extras}".rstrip()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")



class RunLog:
    """Append-only per-run JSONL telemetry for debugging slow or stuck runs."""

    def __init__(self, path: Path, *, repo_url: str, owner: str, repo: str, model: str | None, run_id: str | None = None) -> None:
        self.path = path
        self.run_id = run_id or uuid.uuid4().hex
        self.started_at = time.perf_counter()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.event(
            "run.started",
            repo_url=repo_url,
            owner=owner,
            repo=repo,
            model=model,
        )

    def event(self, event: str, **fields: object) -> None:
        elapsed_ms = int((time.perf_counter() - self.started_at) * 1000)
        payload = {
            "run_id": self.run_id,
            "event": event,
            "elapsed_ms": elapsed_ms,
            "ts": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            **fields,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=str, sort_keys=True) + "\n")

    def stage_start(self, stage: str, **fields: object) -> float:
        self.event(f"{stage}.started", **fields)
        return time.perf_counter()

    def stage_end(self, stage: str, started_at: float, **fields: object) -> None:
        self.event(
            f"{stage}.completed",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            **fields,
        )

    def stage_failed(self, stage: str, started_at: float, error: BaseException, **fields: object) -> None:
        self.event(
            f"{stage}.failed",
            duration_ms=int((time.perf_counter() - started_at) * 1000),
            error_type=type(error).__name__,
            error=str(error),
            **fields,
        )


def _material_metrics(material: RepositoryMaterial) -> dict[str, int | bool]:
    return {
        "file_tree_lines": len([line for line in material.file_tree.splitlines() if line.strip()]),
        "readme_chars": len(material.readme_content),
        "package_chars": len(material.package_files),
        "is_private": material.is_private,
    }


def _timestamp_comment(prefix: str = "# Generated") -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return f"{prefix}: {now} UTC"


def _write_text(path: Path, content: str, stamp: bool) -> None:
    text = content.rstrip()
    if stamp:
        text += "\n\n" + _timestamp_comment()
    path.write_text(text + "\n", encoding="utf-8")


def _unload_lmstudio_model_safely(config: AppConfig, run_log: RunLog | None = None) -> None:
    timeout_seconds = max(0, int(config.lm_unload_timeout_seconds))
    if timeout_seconds == 0:
        started = run_log.stage_start("lm.unload", timeout_seconds=timeout_seconds) if run_log else None
        try:
            unload_lmstudio_model(config)
        finally:
            if run_log and started is not None:
                run_log.stage_end("lm.unload", started)
        return

    error: list[BaseException] = []

    def unload() -> None:
        try:
            unload_lmstudio_model(config)
        except BaseException as exc:  # pragma: no cover - defensive cleanup path
            error.append(exc)

    thread = threading.Thread(
        target=unload,
        name="lmstudio-unload",
        daemon=True,
    )
    started = run_log.stage_start("lm.unload", timeout_seconds=timeout_seconds) if run_log else None
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        logger.warning(
            "Timed out after %ss while unloading LM Studio model '%s'; continuing so the CLI can exit. "
            "Set LMSTUDIO_AUTO_UNLOAD=false to keep models loaded intentionally, or increase "
            "LMSTUDIO_UNLOAD_TIMEOUT_SECONDS if unloads are slow.",
            timeout_seconds,
            config.lm_model,
        )
        if run_log and started is not None:
            run_log.event("lm.unload.timeout", timeout_seconds=timeout_seconds, model=config.lm_model)
        return

    if error:
        logger.warning("LM Studio model unload failed: %s", error[0])
        if run_log and started is not None:
            run_log.stage_failed("lm.unload", started, error[0])
    elif run_log and started is not None:
        run_log.stage_end("lm.unload", started, model=config.lm_model)



def _graph_enrichment_auto_decision(material: RepositoryMaterial, config: AppConfig) -> tuple[bool, str]:
    """Return whether bounded per-node DSPy graph enrichment can be attempted."""
    if not config.lm_model:
        return False, "no LM Studio model is configured"

    source_chars = len(material.readme_content or "") + len(material.package_files or "")
    if source_chars < 120:
        return False, "not enough source evidence for node-specific synthesis"

    return True, "per-node graph synthesis uses bounded node specs and can run on large repository trees"


def _fetch_graph_evidence_content(
    owner: str,
    repo: str,
    path: str,
    ref: str,
    token: str | None,
) -> str | None:
    """Best-effort graph evidence fetch; graph depth must not break generation."""
    try:
        return fetch_file_content(owner, repo, path, ref, token)
    except Exception as exc:  # pragma: no cover - exact HTTP failures vary by GitHub state
        logger.debug("Skipping graph evidence fetch for %s: %s", path, exc)
        return None

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
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_log_path = repo_root / f"{base_name}-run-{run_id}.log"
    run_events_path = repo_root / f"{base_name}-run-{run_id}.jsonl"
    run_log = RunLog(run_events_path, repo_url=repo_url, owner=owner, repo=repo, model=config.lm_model)
    total_started_at = time.perf_counter()
    run_log = RunLog(run_events_path, repo_url=repo_url, owner=owner, repo=repo, model=config.lm_model, run_id=run_id)
    _record_run_event(
        events_path=run_events_path,
        log_path=run_log_path,
        run_id=run_id,
        stage="run",
        status="started",
        repo_url=repo_url,
        model=config.lm_model,
        generate_graph=generate_graph if generate_graph is not None else config.enable_repo_graph,
    )

    logger.debug("Preparing repository material for %s", repo_url)
    material_started_at = time.perf_counter()
    material = prepare_repository_material(config, repo_url)
    _record_run_event(
        events_path=run_events_path,
        log_path=run_log_path,
        run_id=run_id,
        stage="prepare_repository_material",
        status="completed",
        started_at=material_started_at,
        file_tree_lines=len([line for line in material.file_tree.splitlines() if line.strip()]),
        readme_chars=len(material.readme_content or ""),
        package_chars=len(material.package_files or ""),
    )
    analyzer_construct_started_at = time.perf_counter()
    try:
        analyzer = RepositoryAnalyzer(production_mode=True)
    except TypeError:
        # Compatibility with tests that monkeypatch RepositoryAnalyzer as a zero-arg callable.
        analyzer = RepositoryAnalyzer()
    _record_run_event(
        events_path=run_events_path,
        log_path=run_log_path,
        run_id=run_id,
        stage="analyzer_construct",
        status="completed",
        started_at=analyzer_construct_started_at,
        analyzer_type=type(analyzer).__name__,
    )

    fallback_payload = None
    used_fallback = False
    fallback_reason = None
    project_name = repo.replace("-", " ").replace("_", " ").title()
    analyzer_trace = None

    model_loaded = False

    try:
        logger.info("Configuring LM Studio model '%s'", config.lm_model)
        lm_config_started_at = time.perf_counter()
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="lmstudio_configure",
            status="started",
            model=config.lm_model,
            api_base=config.lm_api_base,
        )
        configure_lmstudio_lm(config, cache=cache_lm)
        model_loaded = True
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="lmstudio_configure",
            status="completed",
            started_at=lm_config_started_at,
            model=config.lm_model,
        )

        working_material = material
        budget = build_context_budget(config, working_material)
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="context_budget",
            status="computed",
            estimated_prompt_tokens=budget.estimated_prompt_tokens,
            available_tokens=budget.available_tokens,
            decision=budget.decision.value if hasattr(budget.decision, "value") else str(budget.decision),
        )
        if verbose_budget:
            logger.info(
                "Initial budget: estimated=%s available=%s decision=%s",
                budget.estimated_prompt_tokens,
                budget.available_tokens,
                budget.decision,
            )

        digest_stage = run_log.stage_start("repo_digest.initial")
        planning_digest = build_repo_digest(material, topic=project_name)
        run_log.stage_end("repo_digest.initial", digest_stage, subsystem_count=len(planning_digest.subsystems))
        evidence_plan = None
        if budget.decision != BudgetDecision.APPROVED:
            evidence_stage = run_log.stage_start("evidence_planning")
            evidence_plan = plan_evidence_paths(
                material,
                planning_digest,
                max_paths=suggested_evidence_limit(
                    budget.estimated_prompt_tokens,
                    budget.available_tokens,
                ),
            )
            run_log.stage_end(
                "evidence_planning",
                evidence_stage,
                candidate_count=evidence_plan.candidate_count,
                selected_count=evidence_plan.selected_count,
                dropped_count=evidence_plan.dropped_count,
                budget_reason=evidence_plan.budget_reason,
            )
            if evidence_plan.dropped_paths:
                apply_stage = run_log.stage_start("evidence_apply", selected_count=evidence_plan.selected_count)
                working_material = apply_evidence_plan(
                    material,
                    evidence_plan,
                    fetch_content=lambda path: fetch_file_content(
                        owner,
                        repo,
                        path,
                        material.default_branch,
                        config.github_token,
                    ),
                )
                run_log.stage_end("evidence_apply", apply_stage, **_material_metrics(working_material))
                budget_stage = run_log.stage_start("context_budget.after_evidence")
                budget = build_context_budget(config, working_material)
                run_log.stage_end(
                    "context_budget.after_evidence",
                    budget_stage,
                    estimated_prompt_tokens=budget.estimated_prompt_tokens,
                    available_tokens=budget.available_tokens,
                    decision=str(budget.decision),
                )
                if verbose_budget:
                    logger.info(
                        "After evidence planning: estimated=%s available=%s decision=%s selected=%s dropped=%s",
                        budget.estimated_prompt_tokens,
                        budget.available_tokens,
                        budget.decision,
                        len(evidence_plan.selected_paths),
                        len(evidence_plan.dropped_paths),
                    )

        if budget.decision != BudgetDecision.APPROVED:
            compact_stage = run_log.stage_start("context_compaction", decision=str(budget.decision))
            working_material = compact_material(working_material, budget, config)
            run_log.stage_end("context_compaction", compact_stage, **_material_metrics(working_material))
            budget_stage = run_log.stage_start("context_budget.after_compaction")
            budget = build_context_budget(config, working_material)
            run_log.stage_end(
                "context_budget.after_compaction",
                budget_stage,
                estimated_prompt_tokens=budget.estimated_prompt_tokens,
                available_tokens=budget.available_tokens,
                decision=str(budget.decision),
            )
            if verbose_budget:
                logger.info(
                    "After compaction: estimated=%s available=%s decision=%s",
                    budget.estimated_prompt_tokens,
                    budget.available_tokens,
                    budget.decision,
                )

        digest_stage = run_log.stage_start("repo_digest.final")
        repo_digest = build_repo_digest(working_material, topic=project_name)
        run_log.stage_end("repo_digest.final", digest_stage, subsystem_count=len(repo_digest.subsystems))
        llms_text = ""
        retry_step = 0
        current_budget = budget
        while True:
            try:
                analyzer_started_at = time.perf_counter()
                _record_run_event(
                    events_path=run_events_path,
                    log_path=run_log_path,
                    run_id=run_id,
                    stage="dspy_analyzer",
                    status="started",
                    retry_step=retry_step,
                )
                analyzer_kwargs = {
                    "repo_url": working_material.repo_url,
                    "file_tree": working_material.file_tree,
                    "readme_content": working_material.readme_content,
                    "package_files": working_material.package_files,
                    "default_branch": working_material.default_branch,
                    "is_private": working_material.is_private,
                    "github_token": config.github_token,
                    "link_style": config.link_style,
                    "repo_digest": repo_digest,
                }
                analyzer_stage = run_log.stage_start(
                    "analyzer.generate",
                    retry_step=retry_step,
                    file_tree_chars=len(working_material.file_tree),
                    readme_chars=len(working_material.readme_content),
                    package_chars=len(working_material.package_files),
                )
                try:
                    result = analyzer(**analyzer_kwargs)
                except TypeError as call_exc:
                    # Some test/mocked DSPy module variants expose forward() only.
                    if callable(getattr(analyzer, "forward", None)):
                        logger.debug("Analyzer is not directly callable; invoking forward()")
                        result = analyzer.forward(**analyzer_kwargs)
                    else:
                        raise call_exc
                run_log.stage_end("analyzer.generate", analyzer_stage, retry_step=retry_step)
                llms_text = result.llms_txt_content
                _record_run_event(
                    events_path=run_events_path,
                    log_path=run_log_path,
                    run_id=run_id,
                    stage="dspy_analyzer",
                    status="completed",
                    started_at=analyzer_started_at,
                    retry_step=retry_step,
                    output_chars=len(llms_text or ""),
                )
                analyzer_trace = getattr(result, "trace", None)
                if analyzer_trace is not None and evidence_plan is not None and evidence_plan.dropped_paths:
                    analyzer_trace.selected_evidence = [
                        *[
                            {
                                "path": path,
                                "reason": evidence_plan.selected_reasons.get(path, "selected"),
                                "stage": "evidence-planning",
                                "content_fetched": path in evidence_plan.fetched_paths,
                            }
                            for path in evidence_plan.selected_paths
                        ],
                        *[
                            {
                                "path": item.get("path"),
                                "reason": item.get("reason", "fetch-skipped"),
                                "stage": "evidence-fetch",
                                "content_fetched": False,
                            }
                            for item in evidence_plan.fetch_skipped
                        ],
                        *analyzer_trace.selected_evidence,
                    ]
                    analyzer_trace.dropped_evidence = [
                        {
                            "path": path,
                            "reason": "budget-limited",
                            "stage": "evidence-planning",
                        }
                        for path in evidence_plan.dropped_paths
                    ]
                    analyzer_trace.model_section_planning.setdefault(
                        "evidence_budget",
                        {
                            "candidate_count": evidence_plan.candidate_count,
                            "max_paths": evidence_plan.max_paths,
                            "selected_count": evidence_plan.selected_count,
                            "dropped_count": evidence_plan.dropped_count,
                            "budget_reason": evidence_plan.budget_reason,
                        },
                    )
                    analyzer_trace.compaction_reasons.insert(
                        0,
                        "Selective evidence planning ran before deterministic compaction.",
                    )
                break
            except Exception as exc:
                if 'analyzer_stage' in locals():
                    run_log.stage_failed("analyzer.generate", analyzer_stage, exc, retry_step=retry_step)
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
                    run_log.event(
                        "analyzer.retry_budget_reduced",
                        retry_step=retry_step,
                        estimated_prompt_tokens=current_budget.estimated_prompt_tokens,
                        available_tokens=current_budget.available_tokens,
                        error_class=str(err_class),
                    )
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
        fallback_reason = str(exc)
        run_log.event("generation.fallback", reason=fallback_reason, error_type=type(exc).__name__)
        logger.warning("LM generation unavailable; using fallback output. Reason: %s", exc)
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="dspy_analyzer",
            status="fallback",
            error=str(exc),
        )
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
        fallback_reason = str(exc)
        run_log.event("generation.fallback", reason=fallback_reason, error_type=type(exc).__name__, unexpected=True)
        logger.exception("Unexpected error during DSPy generation: %s", exc)
        logger.warning("Falling back to heuristic llms.txt generation using %s.", LLMS_JSON_SCHEMA["title"])
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="dspy_analyzer",
            status="fallback",
            error=str(exc),
        )
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

    sanitized = sanitize_final_output(llms_text, strict=True)
    llms_txt_path = repo_root / f"{base_name}-llms.txt"
    logger.info("Writing llms.txt to %s", llms_txt_path)
    write_stage = run_log.stage_start("artifact.write_llms_txt", path=str(llms_txt_path))
    _write_text(llms_txt_path, sanitized.text or llms_text, stamp)
    run_log.stage_end("artifact.write_llms_txt", write_stage, path=str(llms_txt_path), chars=len(sanitized.text or llms_text))
    _record_run_event(
        events_path=run_events_path,
        log_path=run_log_path,
        run_id=run_id,
        stage="write_llms_txt",
        status="completed",
        path=str(llms_txt_path),
        output_chars=len(sanitized.text or llms_text),
    )

    trace_path: Optional[Path] = None
    if analyzer_trace is not None:
        trace_path = repo_root / f"{base_name}-trace.json"
        trace_payload = asdict(analyzer_trace) if is_dataclass(analyzer_trace) else analyzer_trace
        trace_write_stage = run_log.stage_start("artifact.write_analyzer_trace", path=str(trace_path))
        trace_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
        run_log.stage_end("artifact.write_analyzer_trace", trace_write_stage, path=str(trace_path))
        logger.info("Analyzer trace written to %s", trace_path)

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
        full_write_stage = run_log.stage_start("artifact.write_llms_full", path=str(llms_full_path))
        _write_text(llms_full_path, llms_full_text, stamp)
        run_log.stage_end("artifact.write_llms_full", full_write_stage, path=str(llms_full_path), chars=len(llms_full_text))

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
        graph_material = working_material if 'working_material' in locals() else material
        graph_planning_digest = build_repo_digest(graph_material, topic=project_name)
        graph_evidence_stage = run_log.stage_start("graph.evidence_planning")
        graph_evidence_max_paths = max(24, int(config.semantic_graph_max_subsystems) * 8)
        graph_evidence_plan = plan_evidence_paths(
            graph_material,
            graph_planning_digest,
            max_paths=graph_evidence_max_paths,
        )
        if graph_evidence_plan.selected_paths:
            graph_material = apply_evidence_plan(
                graph_material,
                graph_evidence_plan,
                fetch_content=lambda path: _fetch_graph_evidence_content(
                    owner,
                    repo,
                    path,
                    graph_material.default_branch,
                    config.github_token,
                ),
                limits=EvidenceFetchLimits(
                    max_fetches=min(graph_evidence_max_paths, max(12, int(config.semantic_graph_max_subsystems) * 4)),
                    max_bytes_per_fetch=max(1_200, int(config.semantic_graph_max_excerpt_chars) * 3),
                    max_total_bytes=max(8_000, int(config.semantic_graph_max_source_chars)),
                    max_path_depth=8,
                ),
            )
        run_log.stage_end(
            "graph.evidence_planning",
            graph_evidence_stage,
            candidate_count=graph_evidence_plan.candidate_count,
            selected_count=graph_evidence_plan.selected_count,
            fetched_count=len(graph_evidence_plan.fetched_paths),
            skipped_count=len(graph_evidence_plan.fetch_skipped),
        )
        digest = build_repo_digest(graph_material, topic=project_name)
        graph = build_repo_graph(digest)
        decision_stage = run_log.stage_start("graph.dspy_enrichment_decision")
        should_enrich_graph, enrichment_reason = _graph_enrichment_auto_decision(graph_material, config)
        run_log.stage_end(
            "graph.dspy_enrichment_decision",
            decision_stage,
            should_enrich_graph=should_enrich_graph,
            reason=enrichment_reason,
        )
        if not should_enrich_graph:
            logger.info("Skipping DSPy repo graph node synthesis automatically: %s", enrichment_reason)
            _record_run_event(
                events_path=run_events_path,
                log_path=run_log_path,
                run_id=run_id,
                stage="repo_graph_dspy_enrichment_decision",
                status="skipped",
                reason=enrichment_reason,
            )
        else:
            try:
                dspy_graph_started_at = time.perf_counter()
                logger.info("Attempting bounded DSPy repo graph node synthesis automatically: %s", enrichment_reason)
                _record_run_event(
                    events_path=run_events_path,
                    log_path=run_log_path,
                    run_id=run_id,
                    stage="repo_graph_dspy_enrichment",
                    status="started",
                    reason=enrichment_reason,
                    timeout_seconds=config.semantic_graph_timeout_seconds,
                    max_output_tokens=config.semantic_graph_max_output_tokens,
                    max_source_chars=config.semantic_graph_max_source_chars,
                    max_subsystems=config.semantic_graph_max_subsystems,
                )
                graph = enrich_repo_graph_with_dspy(graph, digest, graph_material, config)
                _record_run_event(
                    events_path=run_events_path,
                    log_path=run_log_path,
                    run_id=run_id,
                    stage="repo_graph_dspy_enrichment",
                    status="completed",
                    started_at=dspy_graph_started_at,
                    node_count=len(graph.nodes),
                )
            except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("DSPy repo graph node synthesis failed; using deterministic graph: %s", exc)
                _record_run_event(
                    events_path=run_events_path,
                    log_path=run_log_path,
                    run_id=run_id,
                    stage="repo_graph_dspy_enrichment",
                    status="fallback",
                    error=str(exc),
                )
            except BaseException:
                if model_loaded and config.lm_auto_unload:
                    _unload_lmstudio_model_safely(config, run_log=run_log)
                    model_loaded = False
                raise
        graph_paths = emit_graph_files(graph, repo_root / "graph")
        graph_json_path = Path(graph_paths["graph_json"])
        force_graph_path = Path(graph_paths["force_json"])
        graph_nodes_dir = Path(graph_paths["nodes_dir"])
        run_log.event(
            "graph.emit",
            graph_json=str(graph_json_path),
            force_graph=str(force_graph_path),
            nodes_dir=str(graph_nodes_dir),
        )
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="repo_graph_emit",
            status="completed",
            graph_json_path=str(graph_json_path),
            force_graph_path=str(force_graph_path),
            graph_nodes_dir=str(graph_nodes_dir),
        )

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

    if model_loaded and config.lm_auto_unload:
        unload_started_at = time.perf_counter()
        _unload_lmstudio_model_safely(config)
        _record_run_event(
            events_path=run_events_path,
            log_path=run_log_path,
            run_id=run_id,
            stage="lmstudio_unload",
            status="completed",
            started_at=unload_started_at,
        )

    _record_run_event(
        events_path=run_events_path,
        log_path=run_log_path,
        run_id=run_id,
        stage="run",
        status="completed",
        started_at=total_started_at,
        used_fallback=used_fallback,
    )

    return GenerationArtifacts(
        llms_txt_path=str(llms_txt_path),
        llms_full_path=str(llms_full_path) if llms_full_path else None,
        ctx_path=str(ctx_path) if ctx_path else None,
        json_path=str(json_path) if json_path else None,
        graph_json_path=str(graph_json_path) if graph_json_path else None,
        force_graph_path=str(force_graph_path) if force_graph_path else None,
        graph_nodes_dir=str(graph_nodes_dir) if graph_nodes_dir else None,
        trace_path=str(trace_path) if trace_path else None,
        run_log_path=str(run_log_path),
        run_events_path=str(run_events_path),
        used_fallback=used_fallback,
        fallback_reason=fallback_reason,
    )
