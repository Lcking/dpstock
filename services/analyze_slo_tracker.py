import threading
import time
from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Deque, Dict, List, Optional


@dataclass
class AnalyzeSample:
    started_at: float
    first_chunk_ms: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"  # running | completed | timeout | error
    chunk_count: int = 0


class AnalyzeSloTracker:
    """
    In-memory SLO tracker for /api/analyze.

    Tracks:
    - first chunk latency
    - total duration
    - completion / timeout / error rates
    """

    def __init__(self, max_samples: int = 500) -> None:
        self._lock = threading.Lock()
        self._samples: Deque[AnalyzeSample] = deque(maxlen=max_samples)

    def start(self) -> AnalyzeSample:
        sample = AnalyzeSample(started_at=time.time())
        with self._lock:
            self._samples.append(sample)
        return sample

    @staticmethod
    def mark_first_chunk(sample: AnalyzeSample) -> None:
        if sample.first_chunk_ms is None:
            sample.first_chunk_ms = (time.time() - sample.started_at) * 1000

    @staticmethod
    def add_chunk(sample: AnalyzeSample, n: int = 1) -> None:
        sample.chunk_count += n

    @staticmethod
    def finish(sample: AnalyzeSample, status: str) -> None:
        sample.status = status
        sample.duration_ms = (time.time() - sample.started_at) * 1000

    def snapshot(self) -> Dict[str, object]:
        with self._lock:
            items = list(self._samples)

        total = len(items)
        if total == 0:
            return {
                "total_requests": 0,
                "status_counts": {"completed": 0, "timeout": 0, "error": 0, "running": 0},
                "first_chunk_ms": {"p50": None, "p95": None},
                "duration_ms": {"p50": None, "p95": None},
                "avg_chunk_count": None,
            }

        status_counts = {"completed": 0, "timeout": 0, "error": 0, "running": 0}
        first_chunk_values: List[float] = []
        duration_values: List[float] = []
        total_chunks = 0

        for s in items:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1
            if s.first_chunk_ms is not None:
                first_chunk_values.append(s.first_chunk_ms)
            if s.duration_ms is not None:
                duration_values.append(s.duration_ms)
            total_chunks += s.chunk_count

        def p95(values: List[float]) -> Optional[float]:
            if not values:
                return None
            ordered = sorted(values)
            idx = max(0, int(len(ordered) * 0.95) - 1)
            return round(ordered[idx], 2)

        return {
            "total_requests": total,
            "status_counts": status_counts,
            "first_chunk_ms": {
                "p50": round(median(first_chunk_values), 2) if first_chunk_values else None,
                "p95": p95(first_chunk_values),
            },
            "duration_ms": {
                "p50": round(median(duration_values), 2) if duration_values else None,
                "p95": p95(duration_values),
            },
            "avg_chunk_count": round(total_chunks / total, 2) if total else None,
        }


analyze_slo_tracker = AnalyzeSloTracker()
