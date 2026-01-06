import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from threading import Lock, Thread
from .models import RunRecord
from .errors import UnknownRunError

logger = logging.getLogger(__name__)

class RunStore:
    def __init__(
        self,
        max_runs: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        cleanup_interval_seconds: Optional[int] = None,
    ):
        self._runs: Dict[str, RunRecord] = {}
        self._lock = Lock()
        self._max_runs = max_runs if max_runs and max_runs > 0 else None
        self._ttl_seconds = ttl_seconds if ttl_seconds and ttl_seconds > 0 else None
        self._cleanup_interval_seconds = (
            cleanup_interval_seconds if cleanup_interval_seconds and cleanup_interval_seconds > 0 else None
        )
        self._cleanup_thread: Optional[Thread] = None

    def put_run(self, run_record: RunRecord) -> None:
        with self._lock:
            self._runs[run_record.run_id] = run_record
            self._prune_locked()

    def update_run(self, run_id: str, **updates: object) -> RunRecord:
        with self._lock:
            if run_id not in self._runs:
                raise UnknownRunError(f"Run ID {run_id} not found")
            existing = self._runs[run_id]
            updates.pop("run_id", None)
            updated = existing.model_copy(
                update={**updates, "updated_at": datetime.now(timezone.utc)}
            )
            self._runs[run_id] = updated
            self._prune_locked()
            return updated

    def get_run(self, run_id: str) -> RunRecord:
        with self._lock:
            if run_id not in self._runs:
                raise UnknownRunError(f"Run ID {run_id} not found")
            return self._runs[run_id]

    def list_runs(self, limit: int = 10) -> List[RunRecord]:
        with self._lock:
            all_runs = list(self._runs.values())
            # Return newest first based on updated timestamp
            all_runs.sort(key=lambda run: run.updated_at, reverse=True)
            return all_runs[:limit]

    def prune_expired(self) -> int:
        now = datetime.now(timezone.utc)
        with self._lock:
            return self._prune_locked(now=now)

    def start_cleanup_worker(self) -> None:
        if not self._ttl_seconds or not self._cleanup_interval_seconds:
            return
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            return

        def _loop() -> None:
            while True:
                time.sleep(self._cleanup_interval_seconds)
                try:
                    removed = self.prune_expired()
                    if removed:
                        logger.info("Pruned %s expired run(s)", removed)
                except Exception:
                    logger.exception("Run cleanup failed")

        self._cleanup_thread = Thread(target=_loop, daemon=True)
        self._cleanup_thread.start()

    def _prune_locked(self, now: Optional[datetime] = None) -> int:
        removed = 0
        if not now:
            now = datetime.now(timezone.utc)

        if self._ttl_seconds:
            cutoff = now - timedelta(seconds=self._ttl_seconds)
            for run_id, run in list(self._runs.items()):
                if run.status in ("completed", "failed") and run.updated_at < cutoff:
                    del self._runs[run_id]
                    removed += 1

        if self._max_runs and len(self._runs) > self._max_runs:
            candidates = sorted(
                ((run_id, run) for run_id, run in self._runs.items() if run.status in ("completed", "failed")),
                key=lambda item: item[1].updated_at,
            )
            for run_id, _run in candidates:
                if len(self._runs) <= self._max_runs:
                    break
                del self._runs[run_id]
                removed += 1

        return removed
