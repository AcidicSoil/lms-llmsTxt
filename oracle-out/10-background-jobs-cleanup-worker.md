Direct answer (1–4 bullets, evidence-cited)

Pruning is thread-safe and mutation-safe, and it only deletes terminal runs. Both prune_expired() and _prune_locked() operate under self._lock, and the TTL pass iterates over list(self._runs.items()) before deleting keys; deletions are restricted to status in ("completed", "failed"). (runs.py: prune_expired, _prune_locked)

The worker avoids “obvious” duplicate threads in single-threaded startup, but it’s not concurrency-safe and has no shutdown path. It bails out if TTL/interval aren’t set and if an existing cleanup thread is alive, but the check/set isn’t protected by a lock; concurrent calls can race and start >1 daemon thread. The loop is while True with no stop event. (runs.py: start_cleanup_worker, _loop)

Log spam is bounded in the success case, but unbounded under a persistent exception. It logs info only when removed is non-zero, but logger.exception("Run cleanup failed") will fire every interval forever if prune_expired() consistently raises—no backoff. (runs.py: _loop)

Max-runs pruning can fail to bound memory if too many runs are non-terminal. The max-runs block only considers candidates with status in ("completed", "failed"); if the store is dominated by “running”/non-terminal runs, len(self._runs) > self._max_runs can remain true while removing nothing. (runs.py: _prune_locked max-runs section)

Risks/unknowns (bullets)

Race risk: start_cleanup_worker() can start multiple daemon threads if invoked concurrently (e.g., multiple server instances/routers calling it) because there’s no lock around the “already running” check + assignment.

Unbounded growth: If clients create many “running” runs (or runs never transition to completed/failed), neither TTL pruning nor max-runs pruning will remove them.

Operational noise: If prune_expired() ever throws deterministically (e.g., unexpected RunRecord shape/field type), logs will repeat every cleanup_interval_seconds indefinitely.

Lifecycle management: No mechanism to stop/replace the worker (tests, graceful shutdown, hot-reload) without discarding the whole RunStore.

Next smallest concrete experiment (1 action)

Add a minimal concurrency + bounding test: spawn two threads that call start_cleanup_worker() simultaneously (with TTL + interval set), then assert only one cleanup thread is created and that max_runs is actually enforced when the store contains only non-terminal statuses (demonstrating current unbounded behavior).

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next.

src/llmstxt_mcp/models.py (definition of RunRecord, especially status enum/allowed values and updated_at semantics).

src/llmstxt_mcp/server.py (or wherever RunStore.start_cleanup_worker() is invoked) to confirm call frequency/concurrency and whether shutdown hooks exist.

src/llmstxt_mcp/config.py (defaults for ttl_seconds and cleanup_interval_seconds, and whether they can be reloaded dynamically).
