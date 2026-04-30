from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from lms_llmsTxt.context_budget import ContextBudget, estimate_tokens


class SessionMemoryStore:
    """Append-only JSONL memory store with budget-aware pruning."""

    def __init__(self, path: Path, max_events: int = 2000) -> None:
        self.path = path
        self.max_events = max_events
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append_event(self, event_type: str, payload: dict[str, Any]) -> str:
        event_id = str(uuid4())
        row = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.prune_if_needed()
        return event_id

    def list_events(self, limit: int = 200) -> list[dict[str, Any]]:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        selected = lines[-max(1, limit) :]
        return [json.loads(line) for line in selected if line.strip()]

    def prune_if_needed(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_events:
            return
        kept = lines[-self.max_events :]
        self.path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _is_summary_event(event: dict[str, Any]) -> bool:
    event_type = str(event.get("type", "")).lower()
    payload = event.get("payload", {}) or {}
    payload_kind = str(payload.get("kind", "")).lower() if isinstance(payload, dict) else ""
    return event_type in {"summary", "digest_summary", "repo_digest"} or payload_kind == "summary"


def _format_event(event: dict[str, Any]) -> str:
    timestamp = event.get("timestamp")
    type_label = event.get("type", "event")
    payload = json.dumps(event.get("payload", {}), ensure_ascii=False)
    if timestamp:
        return f"[{timestamp}] [{type_label}] {payload}"
    return f"[{type_label}] {payload}"


def _truncate_to_token_budget(text: str, token_budget: int) -> str:
    if token_budget <= 0:
        return ""
    if estimate_tokens(text) <= token_budget:
        return text
    low = 0
    high = len(text)
    best = ""
    while low <= high:
        mid = (low + high) // 2
        candidate = text[:mid]
        if estimate_tokens(candidate) <= token_budget:
            best = candidate
            low = mid + 1
        else:
            high = mid - 1
    return best


def build_active_context(
    events: list[dict[str, Any]],
    max_chars: int = 12000,
    *,
    budget: ContextBudget | None = None,
) -> str:
    indexed = [(idx, event, _format_event(event)) for idx, event in enumerate(events)]

    if budget is None:
        chunks: list[str] = []
        for _, _, chunk in reversed(indexed):
            if len(chunk) > max_chars and not chunks:
                chunks.append(chunk[:max_chars])
                break
            if sum(len(x) for x in chunks) + len(chunk) > max_chars:
                break
            chunks.append(chunk)
        return "\n".join(reversed(chunks))

    max_tokens = max(1, int(budget.available_tokens))
    selected: list[tuple[int, str]] = []
    used_tokens = 0

    def _try_add_candidates(candidates: list[tuple[int, dict[str, Any], str]]) -> None:
        nonlocal used_tokens
        for idx, _, chunk in reversed(candidates):
            remaining = max_tokens - used_tokens
            if remaining <= 0:
                return
            token_len = estimate_tokens(chunk)
            if token_len <= remaining:
                selected.append((idx, chunk))
                used_tokens += token_len
                continue
            if not selected:
                truncated = _truncate_to_token_budget(chunk, remaining)
                if truncated:
                    selected.append((idx, truncated))
                    used_tokens += estimate_tokens(truncated)
            return

    summary_events = [row for row in indexed if _is_summary_event(row[1])]
    raw_events = [row for row in indexed if not _is_summary_event(row[1])]
    _try_add_candidates(summary_events)
    _try_add_candidates(raw_events)

    selected.sort(key=lambda row: row[0])
    return "\n".join(chunk for _, chunk in selected)
