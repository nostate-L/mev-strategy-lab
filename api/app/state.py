"""In-memory state used by the API.

For a slim demo this avoids external dependencies (Postgres / Redis) at the
cost of restartability. The store interface is plain enough that swapping in a
real backing store is straightforward.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from mevlab.backtest.engine import BacktestResult


@dataclass(slots=True)
class StoredBacktest:
    id: str
    created_at: datetime
    result: BacktestResult
    notes: list[str] = field(default_factory=list)


class _BacktestStore:
    """Thread-safe in-memory store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[str, StoredBacktest] = {}

    def put(self, result: BacktestResult, notes: list[str]) -> StoredBacktest:
        with self._lock:
            entry = StoredBacktest(
                id=str(uuid.uuid4()),
                created_at=datetime.now(UTC),
                result=result,
                notes=notes,
            )
            self._items[entry.id] = entry
            return entry

    def get(self, backtest_id: str) -> StoredBacktest | None:
        with self._lock:
            return self._items.get(backtest_id)

    def all(self) -> list[StoredBacktest]:
        with self._lock:
            return list(self._items.values())


BACKTESTS = _BacktestStore()


__all__ = ["BACKTESTS", "StoredBacktest"]
