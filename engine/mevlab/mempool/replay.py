"""Replay mempool snapshots from JSONL files.

A snapshot file is one JSON object per line with the schema:

    {
      "captured_at_ms": 1700000000000,
      "block_number_next": 18950000,
      "base_fee_per_gas_next": 21500000000,
      "pending": [ { "hash": "0x..", ... }, ... ]
    }

This format is intentionally portable; it can be produced by an ``ethers`` or
``web3.py`` script that subscribes to ``newPendingTransactions`` and dumps
periodic snapshots, or generated synthetically (see ``synthetic.py``).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from mevlab.core.types import MempoolSnapshot, PendingTx


def _decode_tx(raw: dict[str, Any]) -> PendingTx:
    return PendingTx(
        hash=raw["hash"],
        sender=raw["sender"].lower(),
        target=raw["target"].lower(),
        value=int(raw.get("value", 0)),
        calldata=bytes.fromhex(raw.get("calldata", "").removeprefix("0x")),
        gas_limit=int(raw["gas_limit"]),
        max_fee_per_gas=int(raw["max_fee_per_gas"]),
        max_priority_fee_per_gas=int(raw["max_priority_fee_per_gas"]),
        nonce=int(raw["nonce"]),
        seen_at_ms=int(raw["seen_at_ms"]),
        intent=raw.get("intent"),
    )


def _decode_snapshot(raw: dict[str, Any]) -> MempoolSnapshot:
    return MempoolSnapshot(
        captured_at_ms=int(raw["captured_at_ms"]),
        pending=[_decode_tx(t) for t in raw["pending"]],
        base_fee_per_gas_next=int(raw["base_fee_per_gas_next"]),
        block_number_next=int(raw["block_number_next"]),
    )


class MempoolReplayer:
    """Iterate snapshots from a JSONL file, lazily."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

    def __iter__(self) -> Iterator[MempoolSnapshot]:
        with self.path.open() as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line:
                    continue
                yield _decode_snapshot(json.loads(line))

    def head(self, n: int) -> list[MempoolSnapshot]:
        out: list[MempoolSnapshot] = []
        for snap in self:
            out.append(snap)
            if len(out) >= n:
                break
        return out

    @staticmethod
    def from_iterable(snaps: Iterable[MempoolSnapshot], path: Path | str) -> Path:
        """Persist ``snaps`` as JSONL — useful for tests and fixtures."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w") as f:
            for snap in snaps:
                payload = {
                    "captured_at_ms": snap.captured_at_ms,
                    "block_number_next": snap.block_number_next,
                    "base_fee_per_gas_next": snap.base_fee_per_gas_next,
                    "pending": [
                        {
                            "hash": t.hash,
                            "sender": t.sender,
                            "target": t.target,
                            "value": t.value,
                            "calldata": "0x" + t.calldata.hex(),
                            "gas_limit": t.gas_limit,
                            "max_fee_per_gas": t.max_fee_per_gas,
                            "max_priority_fee_per_gas": t.max_priority_fee_per_gas,
                            "nonce": t.nonce,
                            "seen_at_ms": t.seen_at_ms,
                            "intent": t.intent,
                        }
                        for t in snap.pending
                    ],
                }
                f.write(json.dumps(payload, separators=(",", ":")) + "\n")
        return target


__all__ = ["MempoolReplayer"]
