"""Flashbots-like block builder.

A builder receives:
- a ``public mempool`` ordered by priority gas auction
- zero or more ``Bundle`` submissions from searchers (atomic, all-or-nothing)

It produces a block by:
1. Sorting bundles by ``(coinbase_payment + tip * gas_used) / gas_used``
   descending — i.e. the per-gas revenue they offer the proposer.
2. Greedily placing bundles into the block as long as gas remains.
3. Filling the rest with the public mempool, again by per-gas tip.

This is intentionally a *model* — real PBS-era builders run trial executions
and combinatorial auctions. We approximate the model well enough that
strategies competing in the simulator face realistic incentives.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mevlab.core.types import Block, BlockHeader, PendingTx
from mevlab.mempool.ordering import order_by_priority_gas_auction


@dataclass(slots=True)
class Bundle:
    """An atomic sequence of transactions submitted by a searcher."""

    transactions: list[PendingTx]
    coinbase_payment_wei: int = 0
    label: str = ""
    expected_gas_used: int | None = None
    revert_protection: bool = True

    @property
    def gas_limit_total(self) -> int:
        return sum(t.gas_limit for t in self.transactions)

    def revenue_per_gas(self, base_fee_next: int) -> float:
        """Coinbase-bribe revenue + tips, divided by gas, in wei/gas."""
        gas = self.expected_gas_used or self.gas_limit_total
        if gas <= 0:
            return 0.0
        tips = sum(
            min(t.max_priority_fee_per_gas, max(0, t.max_fee_per_gas - base_fee_next)) * t.gas_limit
            for t in self.transactions
        )
        return (self.coinbase_payment_wei + tips) / gas


@dataclass(slots=True)
class FlashbotsLikeBuilder:
    """A block builder implementing bundle-first PBS-style ordering."""

    public_mempool: list[PendingTx] = field(default_factory=list)
    bundles: list[Bundle] = field(default_factory=list)
    block_gas_limit: int = 30_000_000

    def submit_bundle(self, bundle: Bundle) -> None:
        self.bundles.append(bundle)

    def submit_public(self, tx: PendingTx) -> None:
        self.public_mempool.append(tx)

    def build(self, header: BlockHeader) -> tuple[Block, list[PendingTx]]:
        """Produce the next block and return ``(block, dropped_transactions)``.

        Dropped transactions are returned so they can be re-queued in the next
        snapshot, matching real-world mempool behaviour.
        """
        ordered_pub = order_by_priority_gas_auction(
            self.public_mempool, header.base_fee_per_gas
        )
        ordered_bundles = sorted(
            self.bundles, key=lambda b: -b.revenue_per_gas(header.base_fee_per_gas)
        )

        block = Block(header=header)
        gas_left = self.block_gas_limit
        chosen_bundles: list[Bundle] = []

        for bundle in ordered_bundles:
            need = bundle.gas_limit_total
            if need <= gas_left:
                chosen_bundles.append(bundle)
                gas_left -= need
                block.coinbase_payment_wei += bundle.coinbase_payment_wei

        chosen_pub: list[PendingTx] = []
        for tx in ordered_pub:
            if tx.gas_limit <= gas_left:
                chosen_pub.append(tx)
                gas_left -= tx.gas_limit

        # Real builders would now interleave; we keep the order
        # ``[bundle1, bundle2, ..., public]`` which matches Flashbots' spec.
        included_txs: list[PendingTx] = []
        for bundle in chosen_bundles:
            included_txs.extend(bundle.transactions)
        included_txs.extend(chosen_pub)

        # Caller is responsible for executing transactions; we surface them via
        # block.results in the backtest engine. Here we just record gas used.
        for tx in included_txs:
            block.results.append(
                _stub_result(tx, gas_price=header.base_fee_per_gas + tx.max_priority_fee_per_gas)
            )

        # Compute ``dropped`` transactions: all those that didn't make it.
        chosen_set = {t.hash for t in chosen_pub}
        dropped = [t for t in ordered_pub if t.hash not in chosen_set]

        # reset for next round
        self.public_mempool = []
        self.bundles = []

        return block, dropped


def _stub_result(tx, *, gas_price: int):
    from mevlab.core.types import ExecutionResult, TxStatus

    return ExecutionResult(
        tx_hash=tx.hash,
        status=TxStatus.SUCCESS,
        gas_used=tx.gas_limit // 2,
        gas_price=gas_price,
    )


__all__ = ["Bundle", "FlashbotsLikeBuilder"]
