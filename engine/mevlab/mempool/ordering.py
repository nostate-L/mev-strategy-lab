"""Priority Gas Auction (PGA) ordering.

The default Ethereum miner ordering is simple: sort transactions by the tip
they pay (``max_priority_fee_per_gas`` after the base-fee floor), break ties
by mempool arrival time. This module exposes that as a pure function so other
ordering strategies (latency-based, builder-with-bundle, etc.) can be plugged
in by accepting a :class:`OrderingPolicy`.
"""

from __future__ import annotations

from collections.abc import Callable

from mevlab.core.types import PendingTx

OrderingPolicy = Callable[[list[PendingTx], int], list[PendingTx]]


def order_by_priority_gas_auction(
    pending: list[PendingTx], base_fee_per_gas_next: int
) -> list[PendingTx]:
    """Sort transactions by effective priority fee, descending."""

    def effective_priority(tx: PendingTx) -> int:
        # Replicates the EIP-1559 effective-priority formula used by miners.
        room = max(0, tx.max_fee_per_gas - base_fee_per_gas_next)
        return min(tx.max_priority_fee_per_gas, room)

    return sorted(pending, key=lambda t: (-effective_priority(t), t.seen_at_ms, t.hash))


def order_first_come_first_served(
    pending: list[PendingTx], base_fee_per_gas_next: int
) -> list[PendingTx]:
    """Some L2s order strictly by ingress time. Provided for comparison."""
    del base_fee_per_gas_next
    return sorted(pending, key=lambda t: (t.seen_at_ms, t.hash))


__all__ = [
    "OrderingPolicy",
    "order_by_priority_gas_auction",
    "order_first_come_first_served",
]
