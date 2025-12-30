"""LM Studio-powered llms.txt generation toolkit."""

import importlib.metadata

from .analyzer import RepositoryAnalyzer
from .config import AppConfig
from .fallback import (
    fallback_llms_payload,
    fallback_llms_markdown,
)
from .lmstudio import configure_lmstudio_lm, LMStudioConnectivityError
from .models import GenerationArtifacts, RepositoryMaterial
from .schema import LLMS_JSON_SCHEMA

try:
    __version__ = importlib.metadata.version("lmstudio-llmstxt-generator")
except importlib.metadata.PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "AppConfig",
    "GenerationArtifacts",
    "RepositoryAnalyzer",
    "RepositoryMaterial",
    "configure_lmstudio_lm",
    "LMStudioConnectivityError",
    "fallback_llms_payload",
    "fallback_llms_markdown",
    "LLMS_JSON_SCHEMA",
    "__version__",
]