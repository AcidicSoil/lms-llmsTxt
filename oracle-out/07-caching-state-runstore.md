Direct answer (1–4 bullets, evidence-cited)

Not durable: RunStore keeps all run state in an in-memory dict (self._runs: Dict[str, RunRecord] = {}) with no persistence layer, so any process restart/crash loses all run history. (Code: _runs dict in __init__.)

max_runs is a “best-effort” cap, not a hard cap: pruning for max_runs only considers runs with status in ("completed", "failed") as eviction candidates; if many runs are "running"/in-progress, the store can grow past max_runs indefinitely. (Code: _prune_locked builds candidates only from ("completed","failed") and deletes only those; see if self._max_runs and len(self._runs) > self._max_runs: and the generator filter on statuses.)

TTL cleanup is also limited to completed/failed: expiration removal checks status in ("completed", "failed") plus updated_at < cutoff, so in-progress runs never expire via TTL. (Code: _ttl_seconds branch in _prune_locked.)

Thread-safety is reasonable, but hot-path cost scales with run count: all operations take a single Lock; list_runs() sorts the full list under that lock, which can become a bottleneck as _runs grows. (Code: with self._lock: in all methods; list_runs sorts all_runs.)

Risks/unknowns (bullets)

Memory growth under load if clients create many runs and don’t complete them (or completion is delayed), because neither TTL nor max_runs prunes non-completed statuses.

Run-ID churn / denial-of-service vector: any path that calls put_run() with unbounded new IDs can grow memory until OOM unless constrained elsewhere.

Lock contention: list_runs() and repeated pruning + sorting under lock can degrade latency if run volume is high.

Unknown from this snippet: how RunStore is instantiated and configured (whether max_runs/TTL are set; whether one global store is shared across requests/processes; typical run volume).

Next smallest concrete experiment (1 action)

Add a focused unit test that creates RunStore(max_runs=100, ttl_seconds=1) and then:

inserts 1,000 runs with status="running" and asserts len(_runs) > 100 (demonstrates cap is not enforced for in-progress),

then marks 950 as "completed" and asserts pruning reduces size to <= 100 after updates,

and verifies TTL removes only completed/failed (not running) after cutoff.

If evidence is insufficient, name the exact missing file/path pattern(s) to attach next.

src/lmstxt_mcp/models.py (definition of RunRecord, especially valid status values and timestamps used)

The file(s) where RunStore is constructed and shared (likely one of):

src/lmstxt_mcp/server.py

src/lmstxt_mcp/app.py / src/lmstxt_mcp/__init__.py

Any configuration source for max_runs, ttl_seconds, and cleanup_interval_seconds:

src/lmstxt_mcp/config.py (or equivalent settings module)
