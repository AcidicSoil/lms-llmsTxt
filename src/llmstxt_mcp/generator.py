import threading
import logging
import uuid
from typing import Any
from pathlib import Path
from lmstudiotxt_generator.pipeline import run_generation
from lmstudiotxt_generator import LMStudioConnectivityError
from lmstudiotxt_generator.models import GenerationArtifacts
from .errors import LMStudioUnavailableError
from .models import GenerateResult, ArtifactRef
from .runs import RunStore
from .hashing import sha256_file

_lock = threading.Lock()
logger = logging.getLogger(__name__)

def safe_generate(
    run_store: RunStore, 
    url: str, 
    output_dir: str = "./output", 
    depth: int = 1,
    concurrency: int = 5,
    skip_repo_check: bool = False,
    cache_lm: bool = True
) -> GenerateResult:
    """
    Thread-safe wrapper around run_generation that updates the run store.
    """
    run_id = str(uuid.uuid4())
    
    with _lock:
        try:
            # Note: run_generation expects string path or Path object
            # It returns GenerationArtifacts dataclass
            artifacts: GenerationArtifacts = run_generation(
                url=url,
                output_dir=output_dir,
                depth=depth,
                concurrency=concurrency,
                skip_repo_check=skip_repo_check,
                cache_lm=cache_lm
            )
            
            # Process artifacts into our domain model
            refs = []
            
            # Helper to add artifact
            def add_artifact(path_str: str | None, name: str):
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
            add_artifact(artifacts.llms_full_path, "llms-full.txt")
            add_artifact(artifacts.ctx_path, "llms-ctx.txt")
            add_artifact(artifacts.json_path, "llms.json")
            
            result = GenerateResult(
                run_id=run_id,
                status="success",
                artifacts=refs
            )
            run_store.put_run(result)
            return result

        except LMStudioConnectivityError as e:
            logger.error(f"LM Studio connectivity error: {e}")
            fail_result = GenerateResult(
                run_id=run_id,
                status="failed",
                error_message=f"LM Studio is unavailable: {e}"
            )
            run_store.put_run(fail_result)
            raise LMStudioUnavailableError(f"LM Studio is unavailable: {e}") from e
            
        except Exception as e:
            logger.exception("Unexpected error during generation")
            fail_result = GenerateResult(
                run_id=run_id,
                status="failed",
                error_message=str(e)
            )
            run_store.put_run(fail_result)
            raise RuntimeError(f"Generation failed: {e}") from e
