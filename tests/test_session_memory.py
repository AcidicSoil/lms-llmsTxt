from pathlib import Path

from lms_llmsTxt_mcp.session_memory import SessionMemoryStore, build_active_context


def test_session_memory_append_and_prune(tmp_path: Path):
    store = SessionMemoryStore(tmp_path / "memory.jsonl", max_events=2)
    store.append_event("a", {"x": 1})
    store.append_event("b", {"x": 2})
    store.append_event("c", {"x": 3})
    events = store.list_events(limit=10)
    assert len(events) == 2
    assert events[0]["type"] == "b"
    assert events[1]["type"] == "c"


def test_build_active_context_budget():
    events = [
        {"type": "one", "payload": {"message": "a" * 100}},
        {"type": "two", "payload": {"message": "b" * 100}},
    ]
    context = build_active_context(events, max_chars=120)
    assert "[two]" in context
