"""Tests for mempool ordering policies."""

from __future__ import annotations

from mevlab.core.types import PendingTx
from mevlab.mempool.ordering import (
    order_by_priority_gas_auction,
    order_first_come_first_served,
)


def _tx(h: str, tip: int, max_fee: int, seen_at_ms: int = 0) -> PendingTx:
    return PendingTx(
        hash=h,
        sender="0x0",
        target="0x1",
        value=0,
        calldata=b"",
        gas_limit=21_000,
        max_fee_per_gas=max_fee,
        max_priority_fee_per_gas=tip,
        nonce=0,
        seen_at_ms=seen_at_ms,
    )


def test_pga_orders_by_effective_priority():
    txs = [
        _tx("0x1", tip=2 * 10**9, max_fee=30 * 10**9, seen_at_ms=10),
        _tx("0x2", tip=10 * 10**9, max_fee=30 * 10**9, seen_at_ms=5),
        _tx("0x3", tip=5 * 10**9, max_fee=30 * 10**9, seen_at_ms=3),
    ]
    ordered = order_by_priority_gas_auction(txs, base_fee_per_gas_next=15 * 10**9)
    assert [t.hash for t in ordered] == ["0x2", "0x3", "0x1"]


def test_fcfs_orders_by_seen_at():
    txs = [
        _tx("0x1", tip=1, max_fee=2, seen_at_ms=300),
        _tx("0x2", tip=1, max_fee=2, seen_at_ms=100),
        _tx("0x3", tip=1, max_fee=2, seen_at_ms=200),
    ]
    ordered = order_first_come_first_served(txs, base_fee_per_gas_next=1)
    assert [t.hash for t in ordered] == ["0x2", "0x3", "0x1"]


def test_pga_caps_priority_at_max_fee_room():
    # tx2 advertises a huge tip but a tiny ``max_fee_per_gas``; the EIP-1559
    # effective priority should clip it to whatever ``max_fee - base_fee``
    # leaves available.
    txs = [
        _tx("0x1", tip=3 * 10**9, max_fee=20 * 10**9, seen_at_ms=10),
        _tx("0x2", tip=100 * 10**9, max_fee=16 * 10**9, seen_at_ms=10),
    ]
    ordered = order_by_priority_gas_auction(txs, base_fee_per_gas_next=15 * 10**9)
    assert [t.hash for t in ordered] == ["0x1", "0x2"]
