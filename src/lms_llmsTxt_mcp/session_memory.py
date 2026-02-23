from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4


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
        row = {"id": event_id, "type": event_type, "payload": payload}
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


def build_active_context(events: list[dict[str, Any]], max_chars: int = 12000) -> str:
    chunks: list[str] = []
    for event in reversed(events):
        chunk = f"[{event.get('type')}] {json.dumps(event.get('payload', {}), ensure_ascii=False)}"
        if len(chunk) > max_chars and not chunks:
            chunks.append(chunk[:max_chars])
            break
        if sum(len(x) for x in chunks) + len(chunk) > max_chars:
            break
        chunks.append(chunk)
    return "\n".join(reversed(chunks))
