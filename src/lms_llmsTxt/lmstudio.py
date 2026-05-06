from __future__ import annotations

import logging
import subprocess
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

import requests

from .config import AppConfig

try:
    import dspy
except ImportError:
    from .signatures import dspy

try:
    from dspy.adapters.json_adapter import _get_structured_outputs_response_format
except Exception:  # pragma: no cover - private helper exists in supported DSPy versions
    _get_structured_outputs_response_format = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:  # Optional dependency recommended for managed unload
    import lmstudio as _LMSTUDIO_SDK  # type: ignore
except Exception:  # pragma: no cover - SDK is optional at runtime
    _LMSTUDIO_SDK = None  # type: ignore[assignment]


class LMStudioConnectivityError(RuntimeError):
    """Raised when LM Studio cannot be reached or does not expose the model."""


class LMStudioJSONAdapter(dspy.JSONAdapter):
    """
    DSPy JSON adapter for LM Studio's OpenAI-compatible server.

    LM Studio supports structured output via JSON Schema. DSPy's stock
    JSONAdapter may fall back to the older `json_object` mode when LiteLLM does
    not recognize a local model as schema-capable. LM Studio rejects that older
    response_format, so this adapter forces the structured schema path and never
    downgrades to `json_object`.
    """

    def _apply_response_schema(self, lm_kwargs: dict[str, Any], signature: type) -> None:
        if _get_structured_outputs_response_format is None:
            raise RuntimeError("DSPy JSON structured-output helper is unavailable")
        lm_kwargs["response_format"] = _get_structured_outputs_response_format(
            signature,
            self.use_native_function_calling,
        )

    def __call__(
        self,
        lm: Any,
        lm_kwargs: dict[str, Any],
        signature: type,
        demos: list[dict[str, Any]],
        inputs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self._apply_response_schema(lm_kwargs, signature)
        return dspy.ChatAdapter.__call__(self, lm, lm_kwargs, signature, demos, inputs)

    async def acall(
        self,
        lm: Any,
        lm_kwargs: dict[str, Any],
        signature: type,
        demos: list[dict[str, Any]],
        inputs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        self._apply_response_schema(lm_kwargs, signature)
        return await dspy.ChatAdapter.acall(self, lm, lm_kwargs, signature, demos, inputs)


_MODEL_ENDPOINTS: tuple[str, ...] = ("/v1/models", "/api/v1/models", "/models")
_SMALL_TEXT_MODEL_HINTS: tuple[str, ...] = (
    "0.5b",
    "0.6b",
    "0.8b",
    "1b",
    "1.2b",
    "1.5b",
    "2b",
    "3b",
    "4b",
)
_TEXT_MODEL_EXCLUSION_HINTS: tuple[str, ...] = (
    "embedding",
    "rerank",
    "reranker",
    "vl",
    "vision",
    "ocr",
)


def _build_lmstudio_url(base: str, endpoint: str) -> str:
    """
    Join ``base`` and ``endpoint`` while avoiding duplicated version prefixes.
    """

    base_trimmed = base.rstrip("/")
    path = endpoint
    for prefix in ("/v1", "/api/v1"):
        if base_trimmed.endswith(prefix) and path.startswith(prefix):
            path = path[len(prefix) :] or ""
            if path and not path.startswith("/"):
                path = "/" + path
            break

    if not path.startswith("/"):
        path = "/" + path if path else ""

    return base_trimmed + path


def _fetch_models(
    base_url: str, headers: dict[str, str]
) -> Tuple[set[str], Optional[str]]:
    """
    Return (models, successful_endpoint) by probing known LM Studio endpoints.

    Recent LM Studio releases mirror OpenAI's `/v1/models` endpoint, while older
    builds exposed `/api/v1/models` or `/models`. We probe the known variants and
    return the first that yields a usable payload.
    """
    last_error: Optional[requests.RequestException] = None
    for endpoint in _MODEL_ENDPOINTS:
        url = _build_lmstudio_url(base_url, endpoint)
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            last_error = exc
            logger.debug("LM Studio GET %s failed: %s", url, exc)
            continue

        models: set[str] = set()
        if isinstance(payload, dict) and "data" in payload:
            for item in payload["data"]:
                if isinstance(item, dict):
                    identifier = item.get("id") or item.get("name")
                    if identifier:
                        models.add(str(identifier))
                elif isinstance(item, str):
                    models.add(item)
        elif isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    identifier = item.get("id") or item.get("name")
                    if identifier:
                        models.add(str(identifier))
                elif isinstance(item, str):
                    models.add(item)

        logger.debug("LM Studio models from %s: %s", url, models or "<empty>")
        return models, endpoint

    if last_error:
        raise last_error
    return set(), None



def _rest_api_base(api_base: str) -> str:
    """Return the LM Studio host root for native /api/v1 management endpoints."""
    base = api_base.rstrip("/")
    for suffix in ("/v1", "/api/v1", "/api/v0"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def _lmstudio_headers(config: AppConfig, *, json_content: bool = False) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {config.lm_api_key or 'lm-studio'}"}
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def _load_payload(config: AppConfig) -> dict[str, object]:
    payload: dict[str, object] = {
        "model": str(config.lm_model),
        "echo_load_config": True,
    }
    if config.lm_context_length:
        payload["context_length"] = int(config.lm_context_length)
    elif config.max_context_tokens:
        payload["context_length"] = int(config.max_context_tokens)
    if config.lm_ttl_seconds > 0:
        payload["ttl"] = int(config.lm_ttl_seconds)
    return payload


def _load_model_rest(config: AppConfig) -> bool:
    """Load the configured model with LM Studio's documented REST endpoint."""
    if not config.lm_model:
        return False
    url = f"{_rest_api_base(config.lm_api_base)}/api/v1/models/load"
    payload = _load_payload(config)
    try:
        logger.info(
            "Requesting LM Studio model load for '%s' via %s (ttl=%s, context_length=%s)",
            config.lm_model,
            url,
            payload.get("ttl", "default"),
            payload.get("context_length", "default"),
        )
        response = requests.post(
            url,
            headers=_lmstudio_headers(config, json_content=True),
            json=payload,
            timeout=(10, 120),
        )
    except requests.RequestException as exc:
        logger.debug("LM Studio REST load request failed: %s", exc)
        return False

    if response.status_code >= 400:
        logger.debug(
            "LM Studio REST load rejected model '%s' (status %s: %s)",
            config.lm_model,
            response.status_code,
            response.text,
        )
        return False

    try:
        data = response.json()
    except ValueError:
        data = {}
    instance_id = data.get("instance_id") if isinstance(data, dict) else None
    if instance_id:
        config.lm_instance_id = str(instance_id)
    logger.info(
        "LM Studio REST loaded model '%s'%s.",
        config.lm_model,
        f" as instance '{config.lm_instance_id}'" if config.lm_instance_id else "",
    )
    return True


def _model_rank(model: str) -> tuple[int, int, str]:
    lowered = model.lower()
    excluded = any(hint in lowered for hint in _TEXT_MODEL_EXCLUSION_HINTS)
    for index, hint in enumerate(_SMALL_TEXT_MODEL_HINTS):
        if hint in lowered:
            return (2 if excluded else 0, index, lowered)
    return (3 if excluded else 1, len(_SMALL_TEXT_MODEL_HINTS), lowered)


def choose_lmstudio_test_model(
    config: AppConfig,
    *,
    preferred_model: str | None = None,
) -> str:
    """
    Choose a small available LM Studio text model for live integration tests.

    This avoids coupling live tests to a large or locally-missing model from
    ``LMSTUDIO_MODEL``. Runtime application configuration remains unchanged;
    callers opt into this helper for test/smoke workflows.
    """
    headers = {"Authorization": f"Bearer {config.lm_api_key or ''}"}
    base = config.lm_api_base.rstrip("/")
    models, _endpoint_hint = _fetch_models(base, headers)
    available = {model.strip() for model in models if model and model.strip()}
    if not available:
        raise LMStudioConnectivityError(
            f"LM Studio at {base} did not advertise any models. Load a small text model, "
            "or set LMSTUDIO_TEST_MODEL to a loaded model identifier."
        )

    def is_excluded(candidate: str) -> bool:
        lowered = candidate.lower()
        return any(hint in lowered for hint in _TEXT_MODEL_EXCLUSION_HINTS)

    for candidate in (preferred_model, config.lm_model):
        if candidate and candidate.strip() in available and not is_excluded(candidate):
            return candidate.strip()

    ranked = sorted(available, key=_model_rank)
    return ranked[0]


def _load_model_sdk(config: AppConfig) -> bool:
    """Load or get the model using LM Studio's Python SDK, with TTL when possible."""
    if _LMSTUDIO_SDK is None or not config.lm_model:
        return False

    _configure_sdk_client(config)
    try:
        set_timeout = getattr(_LMSTUDIO_SDK, "set_sync_api_timeout", None)
        if callable(set_timeout):
            set_timeout(max(60, config.semantic_graph_timeout_seconds, config.lm_unload_timeout_seconds))
    except Exception as exc:  # pragma: no cover - diagnostic only
        logger.debug("LM Studio SDK set_sync_api_timeout failed: %s", exc)

    kwargs: dict[str, object] = {}
    if config.lm_ttl_seconds > 0:
        kwargs["ttl"] = int(config.lm_ttl_seconds)
    try:
        _LMSTUDIO_SDK.llm(config.lm_model, **kwargs)  # type: ignore[attr-defined]
        logger.info(
            "LM Studio SDK ensured model '%s' is loaded%s.",
            config.lm_model,
            f" with ttl={config.lm_ttl_seconds}s" if config.lm_ttl_seconds > 0 else "",
        )
        return True
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK load failed for '%s': %s", config.lm_model, exc)
        return False


def _load_model_cli(config: AppConfig) -> bool:
    """Load the model with `lms load`, using documented TTL/context flags."""
    model = config.lm_model or ""
    args = ["lms", "load", model]
    if config.lm_ttl_seconds > 0:
        args.extend(["--ttl", str(config.lm_ttl_seconds)])
    context_length = config.lm_context_length or config.max_context_tokens
    if context_length:
        args.extend(["--context-length", str(context_length)])
    try:
        logger.debug("Attempting CLI load for model '%s' with args=%s", model, args)
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        logger.debug("LM Studio CLI (lms) not found on PATH; skipping CLI load.")
        return False
    except subprocess.SubprocessError as exc:  # pragma: no cover - defensive
        logger.debug("LM Studio CLI load failed: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("LM Studio CLI reported successful load for '%s'.", model)
        return True

    logger.debug(
        "LM Studio CLI load returned %s: %s %s",
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return False


def _unload_model_rest(config: AppConfig) -> bool:
    """Unload using LM Studio's documented REST endpoint."""
    instance_id = config.lm_instance_id or config.lm_model
    if not instance_id:
        return False
    url = f"{_rest_api_base(config.lm_api_base)}/api/v1/models/unload"
    try:
        response = requests.post(
            url,
            headers=_lmstudio_headers(config, json_content=True),
            json={"instance_id": instance_id},
            timeout=(5, max(1, config.lm_unload_timeout_seconds)),
        )
    except requests.RequestException as exc:
        logger.debug("LM Studio REST unload request failed: %s", exc)
        return False

    if response.status_code < 400:
        logger.info("LM Studio REST unloaded model instance '%s'.", instance_id)
        return True

    logger.debug(
        "LM Studio REST unload rejected instance '%s' (status %s: %s)",
        instance_id,
        response.status_code,
        response.text,
    )
    return False


def _unload_model_cli(model: str) -> bool:
    """Attempt to unload the model using the documented `lms unload` command."""
    try:
        logger.debug("Attempting CLI unload for model '%s'", model)
        result = subprocess.run(
            ["lms", "unload", model],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        logger.debug("LM Studio CLI (lms) not found on PATH; skipping CLI unload.")
        return False
    except subprocess.SubprocessError as exc:  # pragma: no cover - defensive
        logger.debug("LM Studio CLI unload failed: %s", exc)
        return False

    if result.returncode == 0:
        logger.info("LM Studio CLI reported successful unload for '%s'.", model)
        return True

    logger.debug(
        "LM Studio CLI unload returned %s: %s %s",
        result.returncode,
        result.stdout,
        result.stderr,
    )
    return False

def _host_from_api_base(api_base: str | None) -> Optional[str]:
    if not api_base:
        return None
    parsed = urlparse(str(api_base))
    host = parsed.netloc or parsed.path
    host = host.strip("/") if host else ""
    return host or None


def _configure_sdk_client(config: AppConfig) -> None:
    if _LMSTUDIO_SDK is None:
        return
    host = _host_from_api_base(config.lm_api_base)
    if not host:
        return
    try:
        configure = getattr(_LMSTUDIO_SDK, "configure_default_client", None)
        if callable(configure):
            configure(host)
    except Exception as exc:  # pragma: no cover - diagnostic only
        logger.debug("LM Studio SDK configure_default_client failed: %s", exc)


def _unload_model_sdk(config: AppConfig) -> bool:
    """
    Attempt to unload the configured model via the official LM Studio Python SDK.
    """
    if _LMSTUDIO_SDK is None:
        return False

    _configure_sdk_client(config)

    target_key = (config.lm_model or "").strip()
    handles: list = []
    try:
        handles = list(_LMSTUDIO_SDK.list_loaded_models("llm"))  # type: ignore[attr-defined]
    except AttributeError:
        try:
            client = _LMSTUDIO_SDK.get_default_client()  # type: ignore[attr-defined]
            handles = list(client.llm.list_loaded_models())  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - diagnostic path
            logger.debug("LM Studio SDK list_loaded_models unavailable: %s", exc)
            handles = []
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK list_loaded_models failed: %s", exc)
        handles = []

    selected = []
    for handle in handles:
        try:
            identifier = getattr(handle, "identifier", None)
            model_key = getattr(handle, "model_key", None) or getattr(handle, "modelKey", None)
        except Exception:  # pragma: no cover - defensive
            identifier = model_key = None
        if target_key and target_key not in {identifier, model_key}:
            continue
        selected.append(handle)
    if not selected:
        selected = handles

    success = False
    for handle in selected:
        try:
            handle.unload()
            success = True
        except Exception as exc:  # pragma: no cover - diagnostic path
            logger.debug("LM Studio SDK failed to unload handle %r: %s", handle, exc)

    if success:
        logger.info("LM Studio SDK unloaded model '%s'.", target_key or selected[0])
        return True

    try:
        if target_key:
            handle = _LMSTUDIO_SDK.llm(target_key)  # type: ignore[attr-defined]
        else:
            handle = _LMSTUDIO_SDK.llm()  # type: ignore[attr-defined]
    except TypeError:
        handle = _LMSTUDIO_SDK.llm()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK llm(%s) failed: %s", target_key or "<default>", exc)
        return False

    try:
        handle.unload()
        logger.info("LM Studio SDK unloaded model '%s'.", target_key or getattr(handle, "model_key", "<default>"))
        return True
    except Exception as exc:  # pragma: no cover - diagnostic path
        logger.debug("LM Studio SDK handle unload failed: %s", exc)
        return False


def _ensure_lmstudio_ready(config: AppConfig) -> None:
    """Ensure the configured model is available to LM Studio for this run."""
    target_model = (config.lm_model or "").strip()
    if not target_model:
        raise LMStudioConnectivityError(
            "No LM Studio model configured. Set LMSTUDIO_MODEL in your .env file "
            "or pass --model with an LM Studio model identifier."
        )

    headers = _lmstudio_headers(config)
    base = config.lm_api_base.rstrip("/")

    try:
        models, _endpoint_hint = _fetch_models(base, headers)
    except requests.RequestException as exc:
        raise LMStudioConnectivityError(
            f"Failed to reach LM Studio at {base}: {exc}"
        ) from exc

    if target_model in models:
        logger.info(
            "LM Studio already advertises model '%s'; using existing instance.",
            target_model,
        )
        return

    logger.info(
        "LM Studio model '%s' is not loaded/advertised; loading with ttl=%ss and context_length=%s.",
        target_model,
        config.lm_ttl_seconds,
        config.lm_context_length or config.max_context_tokens,
    )

    loaded = _load_model_rest(config) or _load_model_sdk(config) or _load_model_cli(config)
    if loaded:
        try:
            refreshed_models, _ = _fetch_models(base, headers)
        except requests.RequestException:
            refreshed_models = set()
        if not refreshed_models or target_model in refreshed_models or config.lm_instance_id:
            return

    available = ", ".join(sorted(models)) if models else "none advertised"
    raise LMStudioConnectivityError(
        f"LM Studio model '{target_model}' was not detected and automatic load failed. "
        "Download the model with `lms get`, load it with `lms load`, or set LMSTUDIO_MODEL/--model "
        f"to one of the available models. Available models: {available}."
    )


def configure_lmstudio_lm(config: AppConfig, *, cache: bool = False) -> dspy.LM:
    """
    Configure DSPy to talk to LM Studio's OpenAI-compatible endpoint.
    """

    _ensure_lmstudio_ready(config)
    target_model = (config.lm_model or "").strip()

    lm = dspy.LM(
        f"openai/{target_model}",
        api_base=config.lm_api_base,
        api_key=config.lm_api_key,
        cache=cache,
        streaming=config.lm_streaming,
    )
    # LM Studio supports JSON Schema structured output. Use a schema-only DSPy
    # adapter so local models are not asked to follow fragile text placeholders,
    # and never downgrade to the older `json_object` response format that LM
    # Studio rejects.
    dspy.configure(lm=lm, adapter=LMStudioJSONAdapter())
    return lm


def unload_lmstudio_model(config: AppConfig) -> None:
    """Attempt to unload the configured LM Studio model to free resources."""
    if _unload_model_sdk(config):
        return

    if _unload_model_rest(config):
        return

    if _unload_model_cli(config.lm_model or ""):
        return

    logger.warning(
        "Failed to unload LM Studio model '%s' via SDK, REST, or CLI. The model may remain loaded.",
        config.lm_model,
    )


__all__ = [
    "choose_lmstudio_test_model",
    "configure_lmstudio_lm",
    "LMStudioJSONAdapter",
    "LMStudioConnectivityError",
    "unload_lmstudio_model",
]
