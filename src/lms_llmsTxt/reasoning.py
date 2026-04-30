from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

_REASONING_BLOCK_RE = re.compile(r"<(think|analysis|reasoning)>.*?</\1>", re.IGNORECASE | re.DOTALL)
_REASONING_PREFIX_RE = re.compile(
    r"^(?:Reasoning|Analysis|Chain of thought|Thinking):.*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(slots=True)
class CanonicalResponse:
    final_text: str
    reasoning_text: str | None = None
    provider_hint: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CanonicalResponse":
        return cls(
            final_text=str(data.get("final_text", "")),
            reasoning_text=data.get("reasoning_text"),
            provider_hint=data.get("provider_hint"),
            raw_metadata=dict(data.get("raw_metadata") or {}),
        )


@dataclass(slots=True)
class SanitizedOutput:
    text: str
    extracted_reasoning: str | None = None
    was_modified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SanitizedOutput":
        return cls(
            text=str(data.get("text", "")),
            extracted_reasoning=data.get("extracted_reasoning"),
            was_modified=bool(data.get("was_modified", False)),
        )


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def canonicalize_response(raw_output: Any, provider_hint: str | None = None) -> CanonicalResponse:
    final_text = ""
    reasoning_text = None

    if isinstance(raw_output, dict):
        final_text = _as_text(
            raw_output.get("final_text")
            or raw_output.get("llms_txt_content")
            or raw_output.get("content")
            or raw_output.get("answer")
        )
        reasoning_text = _as_text(
            raw_output.get("reasoning_text")
            or raw_output.get("reasoning_content")
            or raw_output.get("thinking")
            or raw_output.get("analysis")
        ) or None
    elif isinstance(raw_output, str):
        final_text = raw_output
    else:
        final_text = _as_text(getattr(raw_output, "final_text", None) or getattr(raw_output, "llms_txt_content", None) or getattr(raw_output, "content", None) or getattr(raw_output, "answer", None))
        reasoning_text = _as_text(
            getattr(raw_output, "reasoning_text", None)
            or getattr(raw_output, "reasoning_content", None)
            or getattr(raw_output, "thinking", None)
            or getattr(raw_output, "analysis", None)
        ) or None

    if not final_text and reasoning_text:
        final_text = reasoning_text

    return CanonicalResponse(
        final_text=final_text,
        reasoning_text=reasoning_text,
        provider_hint=provider_hint,
        raw_metadata={"raw_type": type(raw_output).__name__},
    )


def sanitize_final_output(text: str, strict: bool = True) -> SanitizedOutput:
    src = text or ""
    extracted: list[str] = []

    def _extract_block(match: re.Match[str]) -> str:
        extracted.append(match.group(0))
        return ""

    cleaned = _REASONING_BLOCK_RE.sub(_extract_block, src)

    if strict:
        prefix_matches = _REASONING_PREFIX_RE.findall(cleaned)
        if prefix_matches:
            extracted.extend(prefix_matches)
        cleaned = _REASONING_PREFIX_RE.sub("", cleaned)

    # Normalize extra blank lines introduced by stripping wrappers.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    return SanitizedOutput(
        text=cleaned,
        extracted_reasoning="\n\n".join(extracted).strip() or None,
        was_modified=(cleaned != src.strip()),
    )
