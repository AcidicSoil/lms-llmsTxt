from __future__ import annotations

import logging
import subprocess
from typing import Iterable, Optional, Tuple
from urllib.parse import urlparse

import requests

from .config import AppConfig

try:
    import dspy
except ImportError:
    from .signatures import dspy

logger = logging.getLogger(__name__)

try:  # Optional dependency recommended for managed unload
    import lmstudio as _LMSTUDIO_SDK  # type: ignore
except Exception:  # pragma: no cover - SDK is optional at runtime
    _LMSTUDIO_SDK = None  # type: ignore[assignment]


class LMStudioConnectivityError(RuntimeError):
    """Raised when LM Studio cannot be reached or does not expose the model."""


_MODEL_ENDPOINTS: tuple[str, ...] = ("/v1/models", "/api/v1/models", "/models")
_LOAD_ENDPOINT_PATTERNS: tuple[str, ...] = (
    "/v1/models/{model}/load",
    "/v1/models/load",
    "/v1/models/{model}",
    "/api/v1/models/{model}/load",
    "/api/v1/models/load",
    "/api/v1/models/{model}",
    "/models/{model}/load",
    "/models/load",
    "/models/{model}",
)
_UNLOAD_ENDPOINT_PATTERNS: tuple[str, ...] = (
    "/v1/models/{model}/unload",
    "/v1/models/unload",
    "/v1/models/{model}",
    "/api/v1/models/{model}/unload",
    "/api/v1/models/unload",
    "/api/v1/models/{model}",
    "/models/{model}/unload",
    "/models/unload",
    "/models/{model}",
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


def _load_model_http(
    base_url: str,
    headers: dict[str, str],
    model: str,
    endpoint_hint: Optional[str],
) -> bool:
    """
    Attempt to load the requested model via LM Studio's HTTP API.

    Returns True if any request returns a 2xx status code.
    """
    def candidate_paths() -> Iterable[str]:
        if endpoint_hint and endpoint_hint.startswith("/v1"):
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/v1")]
            yield from primary + secondary
        elif endpoint_hint and endpoint_hint.startswith("/api/v1"):
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            yield from primary + secondary
        elif endpoint_hint:
            primary = [p for p in _LOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            secondary = [p for p in _LOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            yield from primary + secondary
        else:
            yield from _LOAD_ENDPOINT_PATTERNS

    for template in candidate_paths():
        url = _build_lmstudio_url(base_url, template.format(model=model))
        body_candidates = (
            None,
            {"model": model},
            {"id": model},
            {"name": model},
        )
        for body in body_candidates:
            try:
                logger.debug("Attempting LM Studio load via %s body=%s", url, body)
                if body is None:
                    response = requests.post(url, headers=headers, timeout=10)
                else:
                    enriched_headers = dict(headers)
                    enriched_headers["Content-Type"] = "application/json"
                    response = requests.post(
                        url,
                        headers=enriched_headers,
                        json=body,
                        timeout=10,
                    )
                if response.status_code < 400:
                    logger.info(
                        "LM Studio accepted load request via %s (status %s)",
                        url,
                        response.status_code,
                    )
                    return True
                logger.debug(
                    "LM Studio rejected load request via %s (status %s: %s)",
                    url,
                    response.status_code,
                    response.text,
                )
            except requests.RequestException as exc:
                logger.debug("LM Studio load request failed via %s: %s", url, exc)
                continue
    return False


def _load_model_cli(model: str) -> bool:
    """
    Attempt to load the model using the `lms` CLI if available.
    """
    try:
        logger.debug("Attempting CLI load for model '%s'", model)
        result = subprocess.run(
            ["lms", "load", model],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
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
        "LM Studio CLI returned %s: %s %s",
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


def _unload_model_http(
    base_url: str,
    headers: dict[str, str],
    model: str,
    endpoint_hint: Optional[str],
) -> bool:
    """
    Attempt to unload the requested model via LM Studio's HTTP API.

    Returns True if any request returns a 2xx status code.
    """

    def candidate_paths() -> Iterable[str]:
        if endpoint_hint and endpoint_hint.startswith("/v1"):
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/v1")]
            yield from primary + secondary
        elif endpoint_hint and endpoint_hint.startswith("/api/v1"):
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            yield from primary + secondary
        elif endpoint_hint:
            primary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if not p.startswith("/api/v1")]
            secondary = [p for p in _UNLOAD_ENDPOINT_PATTERNS if p.startswith("/api/v1")]
            yield from primary + secondary
        else:
            yield from _UNLOAD_ENDPOINT_PATTERNS

    for template in candidate_paths():
        url = _build_lmstudio_url(base_url, template.format(model=model))
        body_candidates = (
            None,
            {"model": model},
            {"id": model},
            {"name": model},
        )
        for body in body_candidates:
            try:
                logger.debug("Attempting LM Studio unload via POST %s body=%s", url, body)
                if body is None:
                    response = requests.post(url, headers=headers, timeout=10)
                else:
                    enriched_headers = dict(headers)
                    enriched_headers["Content-Type"] = "application/json"
                    response = requests.post(
                        url,
                        headers=enriched_headers,
                        json=body,
                        timeout=10,
                    )
                if response.status_code < 400:
                    logger.info(
                        "LM Studio accepted unload request via POST %s (status %s)",
                        url,
                        response.status_code,
                    )
                    return True
                logger.debug(
                    "LM Studio rejected unload via POST %s (status %s: %s)",
                    url,
                    response.status_code,
                    response.text,
                )
            except requests.RequestException as exc:
                logger.debug("LM Studio unload request failed via %s: %s", url, exc)
                continue
    return False


def _unload_model_cli(model: str) -> bool:
    """
    Attempt to unload the model using the `lms` CLI if available.
    """
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


def _ensure_lmstudio_ready(config: AppConfig) -> None:
    """
    Confirm that LM Studio exposes the requested model, attempting to load it if needed.

    Raises
    ------
    LMStudioConnectivityError
        If the LM Studio server cannot be contacted or refuses to expose the model.
    """

    headers = {"Authorization": f"Bearer {config.lm_api_key or ''}"}
    base = config.lm_api_base.rstrip("/")

    try:
        models, endpoint_hint = _fetch_models(base, headers)
    except requests.RequestException as exc:
        raise LMStudioConnectivityError(
            f"Failed to reach LM Studio at {base}: {exc}"
        ) from exc

    if config.lm_model in models:
        logger.debug("LM Studio already has model '%s' loaded.", config.lm_model)
        return

    logger.info(
        "LM Studio does not advertise model '%s'; attempting to load it automatically.",
        config.lm_model,
    )

    loaded = _load_model_http(base, headers, config.lm_model, endpoint_hint)
    if not loaded:
        loaded = _load_model_cli(config.lm_model)

    if not loaded:
        raise LMStudioConnectivityError(
            f"Unable to load model '{config.lm_model}' automatically. "
            "Please load it in the LM Studio UI and retry."
        )

    # Re-query to confirm the model is present.
    try:
        models, _ = _fetch_models(base, headers)
    except requests.RequestException as exc:
        raise LMStudioConnectivityError(
            f"Verified load but subsequent model fetch failed: {exc}"
        ) from exc

    if config.lm_model not in models:
        raise LMStudioConnectivityError(
            f"Model '{config.lm_model}' did not appear in LM Studio after load attempts. "
            "Check the LM Studio logs for more details."
        )

    logger.info("LM Studio model '%s' is ready.", config.lm_model)


def configure_lmstudio_lm(config: AppConfig, *, cache: bool = False) -> dspy.LM:
    """
    Configure DSPy to talk to LM Studio's OpenAI-compatible endpoint.
    """

    _ensure_lmstudio_ready(config)

    lm = dspy.LM(
        f"openai/{config.lm_model}",
        api_base=config.lm_api_base,
        api_key=config.lm_api_key,
        cache=cache,
        streaming=config.lm_streaming,
    )
    dspy.configure(lm=lm)
    return lm


def unload_lmstudio_model(config: AppConfig) -> None:
    """
    Attempt to unload the configured LM Studio model to free resources.
    """

    if _unload_model_sdk(config):
        return

    headers = {"Authorization": f"Bearer {config.lm_api_key or ''}"}
    base = config.lm_api_base.rstrip("/")

    try:
        _, endpoint_hint = _fetch_models(base, headers)
    except requests.RequestException as exc:  # pragma: no cover - informational
        endpoint_hint = None
        logger.debug("Unable to refresh LM Studio endpoint hint before unload: %s", exc)

    if _unload_model_http(base, headers, config.lm_model, endpoint_hint):
        return

    if _unload_model_cli(config.lm_model):
        return

    logger.warning(
        "Failed to unload LM Studio model '%s' via SDK, HTTP, or CLI. The model may remain loaded.",
        config.lm_model,
    )


__all__ = ["configure_lmstudio_lm", "LMStudioConnectivityError", "unload_lmstudio_model"]
