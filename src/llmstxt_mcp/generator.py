import threading
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple

from lmstudiotxt_generator.pipeline import run_generation
from lmstudiotxt_generator.full_builder import build_llms_full_from_repo, iter_llms_links
from lmstudiotxt_generator.github import gather_repository_material, owner_repo_from_url
from lmstudiotxt_generator import LMStudioConnectivityError, AppConfig
from lmstudiotxt_generator.models import GenerationArtifacts

from .errors import LMStudioUnavailableError, OutputDirNotAllowedError
from .models import RunRecord, ArtifactRef
from .runs import RunStore
from .hashing import sha256_file
from .security import validate_output_dir

_lock = threading.Lock()
logger = logging.getLogger(__name__)

def _base_name_from_llms_path(path: Path) -> str:
    name = path.name
    suffix = "-llms.txt"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return path.stem


def _find_artifact(run: RunRecord, name: str) -> Optional[ArtifactRef]:
    return next((a for a in run.artifacts if a.name == name), None)


def _upsert_artifact_list(artifacts: list[ArtifactRef], ref: ArtifactRef) -> None:
    for idx, existing in enumerate(artifacts):
        if existing.name == ref.name:
            artifacts[idx] = ref
            return
    artifacts.append(ref)


def _write_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _artifact_ref_from_path(name: str, path: Path) -> Optional[ArtifactRef]:
    if not path.exists():
        return None
    return ArtifactRef(
        name=name,
        path=str(path.absolute()),
        size_bytes=path.stat().st_size,
        hash_sha256=sha256_file(path),
    )


def _repo_root_from_url(output_dir: Path, repo_url: str) -> Path:
    owner, repo = owner_repo_from_url(repo_url)
    return output_dir / owner / repo


def _artifact_path_from_url(output_dir: Path, repo_url: str, artifact_name: str) -> Path:
    _, repo = owner_repo_from_url(repo_url)
    base_name = repo.lower().replace(" ", "-")
    repo_root = _repo_root_from_url(output_dir, repo_url)
    suffix_map = {
        "llms.txt": "llms.txt",
        "llms-full.txt": "llms-full.txt",
        "llms-ctx.txt": "llms-ctx.txt",
        "llms.json": "llms.json",
    }
    suffix = suffix_map.get(artifact_name, artifact_name)
    return repo_root / f"{base_name}-{suffix}"


def _resolve_llms_txt_path(
    run_store: RunStore,
    run_id: str,
    repo_url: Optional[str],
    output_dir: Path,
) -> Tuple[Path, RunRecord]:
    run = run_store.get_run(run_id)
    llms_artifact = _find_artifact(run, "llms.txt")
    if llms_artifact:
        return Path(llms_artifact.path), run

    if not repo_url:
        raise ValueError("repo_url is required when llms.txt is not present in the run")

    llms_path = _artifact_path_from_url(output_dir, repo_url, "llms.txt")
    return llms_path, run


def _ensure_llms_txt(
    repo_url: str,
    output_dir: Path,
    *,
    cache_lm: bool = False,
) -> Path:
    llms_path = _artifact_path_from_url(output_dir, repo_url, "llms.txt")
    if llms_path.exists():
        return llms_path

    logger.info("llms.txt missing; generating now for %s", repo_url)
    config = AppConfig(output_dir=output_dir)
    artifacts = run_generation(
        repo_url=repo_url,
        config=config,
        cache_lm=cache_lm,
        build_full=False,
        build_ctx=False,
    )
    generated_path = Path(artifacts.llms_txt_path)
    if not generated_path.exists():
        raise FileNotFoundError(f"llms.txt not found after generation at {generated_path}")
    return generated_path


def safe_generate_llms_txt(
    run_store: RunStore,
    run_id: Optional[str],
    url: str,
    output_dir: str = "./artifacts",
    cache_lm: bool = True,
) -> RunRecord:
    """
    Thread-safe wrapper around run_generation that only writes llms.txt (+ optional llms.json).
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)
    logger.info("Generating llms.txt for %s (run_id=%s)", url, run_id)

    # Security: Validate output directory before use
    try:
        validated_dir = validate_output_dir(Path(output_dir))
    except OutputDirNotAllowedError as e:
        logger.error("Security violation: %s", e)
        run_store.update_run(run_id, status="failed", error_message=str(e))
        raise

    # Construct AppConfig from arguments
    config = AppConfig(output_dir=validated_dir)

    with _lock:
        try:
            # Call run_generation with correct signature
            artifacts: GenerationArtifacts = run_generation(
                repo_url=url,
                config=config,
                cache_lm=cache_lm,
                build_full=False,
                build_ctx=False,
            )

            # Process artifacts into our domain model
            refs: list[ArtifactRef] = []

            # Helper to add artifact
            def add_artifact(path_str: str | None, name: str) -> None:
                if not path_str:
                    return
                p = Path(path_str)
                if p.exists():
                    refs.append(ArtifactRef(
                        name=name,
                        path=str(p.absolute()),
                        size_bytes=p.stat().st_size,
                        hash_sha256=sha256_file(p)
                    ))

            add_artifact(artifacts.llms_txt_path, "llms.txt")
            add_artifact(artifacts.json_path, "llms.json")

            result = run_store.update_run(
                run_id,
                status="completed",
                artifacts=refs,
                error_message=None,
            )
            logger.info("llms.txt generation complete (run_id=%s)", run_id)
            return result

        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e

        except Exception as e:
            logger.error("Unexpected error during generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e


def safe_generate_llms_full(
    run_store: RunStore,
    run_id: Optional[str],
    repo_url: Optional[str],
    output_dir: str = "./artifacts",
) -> RunRecord:
    """
    Build llms-full.txt from an existing llms.txt artifact referenced by run_id,
    or resolve llms.txt by repo_url + output_dir if run_id is omitted.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)

    with _lock:
        try:
            logger.info("Starting llms-full generation (run_id=%s, repo_url=%s)", run_id, repo_url)
            logger.info("Resolving llms.txt via run_id %s", run_id)
            llms_path, run = _resolve_llms_txt_path(
                run_store=run_store,
                run_id=run_id,
                repo_url=repo_url,
                output_dir=Path(output_dir),
            )

            output_root = llms_path.parent.parents[1] if llms_path.exists() else Path(output_dir)
            validated_dir = validate_output_dir(output_root)

            if not llms_path.exists():
                if not repo_url:
                    raise ValueError("repo_url is required to generate llms.txt")
                llms_path = _ensure_llms_txt(repo_url, validated_dir)

            llms_ref = _artifact_ref_from_path("llms.txt", llms_path)
            if not llms_ref:
                raise FileNotFoundError(f"llms.txt not found at {llms_path}")

            llms_text = llms_path.read_text(encoding="utf-8")
            repo_root = llms_path.parent
            config = AppConfig(output_dir=validated_dir)

            if not repo_url:
                raise ValueError("repo_url is required to generate llms-full.txt")
            material = gather_repository_material(repo_url, config.github_token)
            link_count = sum(1 for _ in iter_llms_links(llms_text))
            logger.info("Building llms-full from %s curated links", link_count)
            llms_full_text = build_llms_full_from_repo(
                llms_text,
                prefer_raw=not material.is_private,
                default_ref=material.default_branch,
                token=config.github_token,
                link_style=config.link_style,
            )

            base_name = _base_name_from_llms_path(llms_path)
            llms_full_path = repo_root / f"{base_name}-llms-full.txt"
            _write_text(llms_full_path, llms_full_text)
            logger.info("Wrote llms-full.txt to %s", llms_full_path)

            ref = ArtifactRef(
                name="llms-full.txt",
                path=str(llms_full_path.absolute()),
                size_bytes=llms_full_path.stat().st_size,
                hash_sha256=sha256_file(llms_full_path),
            )

            updated_artifacts = list(run.artifacts)
            _upsert_artifact_list(updated_artifacts, llms_ref)
            _upsert_artifact_list(updated_artifacts, ref)

            updated = run_store.update_run(
                run_id,
                status="completed",
                artifacts=updated_artifacts,
                error_message=None,
            )
            logger.info("llms-full generation complete (run_id=%s)", run_id)
            return updated
        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e
        except Exception as e:
            logger.exception("Unexpected error during llms-full generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e


def safe_generate_llms_ctx(
    run_store: RunStore,
    run_id: Optional[str],
    repo_url: Optional[str] = None,
    output_dir: str = "./artifacts",
) -> RunRecord:
    """
    Build llms-ctx.txt from an existing llms.txt artifact referenced by run_id,
    or resolve llms.txt by repo_url + output_dir if run_id is omitted.
    """
    if not run_id:
        run_id = str(uuid.uuid4())
        run_store.put_run(RunRecord(run_id=run_id, status="processing"))
    else:
        run_store.update_run(run_id, status="processing", error_message=None)

    with _lock:
        try:
            logger.info("Starting llms-ctx generation (run_id=%s, repo_url=%s)", run_id, repo_url)
            logger.info("Resolving llms.txt via run_id %s", run_id)
            llms_path, run = _resolve_llms_txt_path(
                run_store=run_store,
                run_id=run_id,
                repo_url=repo_url,
                output_dir=Path(output_dir),
            )
            output_root = llms_path.parent.parents[1] if llms_path.exists() else Path(output_dir)
            validated_dir = validate_output_dir(output_root)

            if not llms_path.exists():
                if not repo_url:
                    raise ValueError("repo_url is required to generate llms.txt")
                llms_path = _ensure_llms_txt(repo_url, validated_dir)

            llms_ref = _artifact_ref_from_path("llms.txt", llms_path)
            if not llms_ref:
                raise FileNotFoundError(f"llms.txt not found at {llms_path}")
            llms_text = llms_path.read_text(encoding="utf-8")

            try:
                from llms_txt import create_ctx  # type: ignore
            except ImportError as exc:
                raise RuntimeError("llms_txt is not installed; cannot generate llms-ctx.txt") from exc

            ctx_text = create_ctx(llms_text, optional=False)
            repo_root = llms_path.parent
            base_name = _base_name_from_llms_path(llms_path)
            ctx_path = repo_root / f"{base_name}-llms-ctx.txt"
            _write_text(ctx_path, ctx_text)
            logger.info("Wrote llms-ctx.txt to %s", ctx_path)

            ref = ArtifactRef(
                name="llms-ctx.txt",
                path=str(ctx_path.absolute()),
                size_bytes=ctx_path.stat().st_size,
                hash_sha256=sha256_file(ctx_path),
            )
            updated_artifacts = list(run.artifacts)
            _upsert_artifact_list(updated_artifacts, llms_ref)
            _upsert_artifact_list(updated_artifacts, ref)
            updated = run_store.update_run(
                run_id,
                status="completed",
                artifacts=updated_artifacts,
                error_message=None,
            )
            logger.info("llms-ctx generation complete (run_id=%s)", run_id)
            return updated
        except LMStudioConnectivityError as e:
            logger.error("LM Studio connectivity error: %s", e)
            run_store.update_run(
                run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}",
            )
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e
        except Exception as e:
            logger.exception("Unexpected error during llms-ctx generation")
            run_store.update_run(
                run_id,
                status="failed",
                error_message=str(e),
            )
            raise RuntimeError(f"Generation failed: {e}") from e