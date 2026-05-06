"""Event-driven backtest engine.

Loop:

    for snapshot in mempool_stream:
        header = synthesize_header(snapshot)
        for strategy in strategies:
            output = strategy.observe(StrategyContext(...))
            for bundle in output.bundles:
                builder.submit_bundle(bundle)
        for tx in snapshot.pending:
            builder.submit_public(tx)
        block, dropped = builder.build(header)
        update_pools_with_executed_swaps(block)
        ledger.record_landed_or_lost_per_strategy(...)

The backtest engine never speaks to a real RPC; it simulates everything against
the pool objects provided in the constructor.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mevlab.backtest.ledger import Ledger
from mevlab.backtest.metrics import Metrics
from mevlab.builder.builder import Bundle, FlashbotsLikeBuilder
from mevlab.core.gas import GasModel
from mevlab.core.types import (
    Block,
    BlockHeader,
    ExecutionResult,
    MempoolSnapshot,
    PendingTx,
    SwapDirection,
    TxStatus,
)
from mevlab.pools.base import BasePool
from mevlab.strategies.base import Strategy, StrategyContext


@dataclass(slots=True)
class BacktestConfig:
    """Tunable parameters for a backtest."""

    block_gas_limit: int = 30_000_000
    gas_model: GasModel = field(default_factory=GasModel)
    block_time_seconds: float = 12.0
    starting_block_number: int = 18_000_000
    starting_base_fee: int = 20_000_000_000


@dataclass(slots=True)
class BacktestResult:
    """Output of a backtest."""

    ledger: Ledger
    blocks: list[Block]
    metrics: dict[str, Metrics]


class BacktestEngine:
    """Event-driven backtest runner."""

    def __init__(
        self,
        pools: dict[str, BasePool],
        strategies: list[Strategy],
        snapshots: list[MempoolSnapshot],
        config: BacktestConfig | None = None,
    ) -> None:
        if not strategies:
            raise ValueError("at least one strategy is required")
        self.pools = {a.lower(): p for a, p in pools.items()}
        self.strategies = strategies
        self.snapshots = snapshots
        self.config = config or BacktestConfig()
        self.ledger = Ledger()

    # --------------------------------------------------------------- helpers

    def _apply_swap(self, tx: PendingTx) -> int:
        """Apply a swap intent to the underlying pool, return gas used."""
        intent = tx.intent
        if intent is None or intent.get("kind") != "swap":
            return tx.gas_limit // 4
        pool = self.pools.get((intent.get("pool") or "").lower())
        if pool is None:
            return tx.gas_limit // 4
        amount_in = int(intent.get("amount_in") or 0)
        if amount_in <= 0:
            return tx.gas_limit // 4
        direction = (
            SwapDirection.ZERO_FOR_ONE
            if intent.get("dir") == "0->1"
            else SwapDirection.ONE_FOR_ZERO
        )
        try:
            pool.swap(direction, amount_in)
        except ValueError:
            return tx.gas_limit // 4
        return tx.gas_limit // 2

    def _execute_block(
        self,
        header: BlockHeader,
        public_tx: list[PendingTx],
        bundles: list[tuple[str, Bundle]],
    ) -> Block:
        """Execute a candidate block transaction-by-transaction."""
        block = Block(header=header)

        # 1. Bundles (sorted by revenue density). Bundles are atomic: if any
        # transaction in a bundle "reverts" (we don't model EVM reverts here,
        # but we treat saturating pools as failure), the bundle is dropped
        # entirely when ``revert_protection`` is set.
        for label, bundle in bundles:
            ok = True
            tentative_results: list[ExecutionResult] = []
            tentative_pool_state = {addr: pool.clone() for addr, pool in self.pools.items()}
            for tx in bundle.transactions:
                gas_used = self._apply_swap(tx)
                if gas_used == 0:
                    ok = False
                    break
                tentative_results.append(
                    ExecutionResult(
                        tx_hash=tx.hash,
                        status=TxStatus.SUCCESS,
                        gas_used=gas_used,
                        gas_price=header.base_fee_per_gas + tx.max_priority_fee_per_gas,
                    )
                )
            if ok or not bundle.revert_protection:
                block.results.extend(tentative_results)
                block.coinbase_payment_wei += bundle.coinbase_payment_wei
                # Estimate searcher profit recorded under bundle label.
                gross_revenue = bundle.coinbase_payment_wei * 2
                gas_paid = sum(
                    r.gas_used * r.gas_price for r in tentative_results
                )
                self.ledger.record_landed(
                    label, profit_wei=gross_revenue, gas_wei=gas_paid
                )
            else:
                # Revert protection kicks in: rollback pool state.
                for addr, snap in tentative_pool_state.items():
                    self.pools[addr] = snap
                self.ledger.record_lost(label)

        # 2. Public transactions filling the rest of the block.
        for tx in public_tx:
            gas_used = self._apply_swap(tx)
            block.results.append(
                ExecutionResult(
                    tx_hash=tx.hash,
                    status=TxStatus.SUCCESS,
                    gas_used=gas_used,
                    gas_price=header.base_fee_per_gas + tx.max_priority_fee_per_gas,
                )
            )

        return block

    # ---------------------------------------------------------------- public

    def run(self) -> BacktestResult:
        blocks: list[Block] = []
        parent_base_fee = self.config.starting_base_fee
        parent_gas_used = self.config.gas_model.target_gas_used

        for snap in self.snapshots:
            base_fee = self.config.gas_model.next_base_fee(parent_base_fee, parent_gas_used)
            header = BlockHeader(
                number=snap.block_number_next,
                timestamp=int(snap.captured_at_ms / 1000),
                base_fee_per_gas=base_fee,
                gas_limit=self.config.block_gas_limit,
            )

            # Strategies see the snapshot first.
            ctx = StrategyContext(
                mempool=snap,
                next_header=header,
                pools=self.pools,
            )
            collected_bundles: list[tuple[str, Bundle]] = []
            for strategy in self.strategies:
                out = strategy.observe(ctx)
                for bundle in out.bundles:
                    collected_bundles.append((bundle.label or strategy.name, bundle))

            # Builder ranking — bundles ordered by revenue density.
            builder = FlashbotsLikeBuilder(block_gas_limit=self.config.block_gas_limit)
            for _label, bundle in collected_bundles:
                builder.submit_bundle(bundle)
            for tx in snap.pending:
                builder.submit_public(tx)
            ordered = sorted(
                collected_bundles,
                key=lambda lb: -lb[1].revenue_per_gas(header.base_fee_per_gas),
            )

            block = self._execute_block(header, snap.pending, ordered)
            parent_base_fee = base_fee
            parent_gas_used = block.total_gas_used or self.config.gas_model.target_gas_used
            blocks.append(block)

        metrics = {
            name: Metrics.from_block_series(series, self.ledger.get(name).hit_rate)
            for name, series in self.ledger.to_block_series().items()
        }
        return BacktestResult(ledger=self.ledger, blocks=blocks, metrics=metrics)


__all__ = ["BacktestConfig", "BacktestEngine", "BacktestResult"]
