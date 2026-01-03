from typing import Dict, List
from threading import Lock
from .models import GenerateResult
from .errors import UnknownRunError

class RunStore:
    def __init__(self):
        self._runs: Dict[str, GenerateResult] = {}
        self._lock = Lock()

    def put_run(self, run_record: GenerateResult) -> None:
        with self._lock:
            self._runs[run_record.run_id] = run_record

    def get_run(self, run_id: str) -> GenerateResult:
        with self._lock:
            if run_id not in self._runs:
                raise UnknownRunError(f"Run ID {run_id} not found")
            return self._runs[run_id]

    def list_runs(self, limit: int = 10) -> List[GenerateResult]:
        with self._lock:
            # Return newest first (assuming insertion order reflects time)
            all_runs = list(self._runs.values())
            return all_runs[::-1][:limit]
