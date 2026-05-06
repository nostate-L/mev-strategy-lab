"""Sandwich strategy.

Looks at every pending swap with a known victim intent and tries to wrap it
with optimal-sized front and back transactions.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.builder.builder import Bundle
from mevlab.core.types import PendingTx, SwapDirection
from mevlab.solver.sandwich import optimal_sandwich_amount
from mevlab.strategies.arbitrage import _make_searcher_tx
from mevlab.strategies.base import Strategy, StrategyContext, StrategyOutput


@dataclass(slots=True)
class SandwichStrategy(Strategy):
    """Naïve sandwich attacker on configured pools."""

    target_pools: set[str]  # pool addresses we are willing to sandwich
    name: str = "sandwich"
    gas_per_swap: int = 150_000
    min_profit_wei: int = 5 * 10**14  # 0.0005 ETH minimum to bother
    capital_cap_wei: int = 5 * 10**20  # 500 WETH equivalent

    def observe(self, ctx: StrategyContext) -> StrategyOutput:
        out = StrategyOutput()
        for tx in ctx.mempool.pending:
            intent = tx.intent
            if intent is None or intent.get("kind") != "swap":
                continue
            pool_addr = intent.get("pool")
            if pool_addr not in self.target_pools:
                continue
            pool = ctx.pool(pool_addr)
            if pool is None:
                continue

            direction = (
                SwapDirection.ZERO_FOR_ONE
                if intent.get("dir") == "0->1"
                else SwapDirection.ONE_FOR_ZERO
            )
            amount_in = int(intent.get("amount_in") or 0)
            min_out = int(intent.get("min_out") or 0)
            if amount_in <= 0:
                continue
            try:
                plan = optimal_sandwich_amount(
                    pool,
                    direction=direction,
                    victim_amount_in=amount_in,
                    victim_min_amount_out=min_out,
                    upper_bound=min(self.capital_cap_wei, max(amount_in * 50, 10**18)),
                )
            except ValueError:
                continue
            if plan is None or plan.expected_profit < self.min_profit_wei:
                continue

            tip = max(1, plan.expected_profit // (self.gas_per_swap * 2 * 5))
            front = _make_searcher_tx(
                target=pool.address,
                hash_seed=f"sw-front-{tx.hash[2:10]}",
                gas_limit=self.gas_per_swap,
                max_priority=tip,
                max_fee=ctx.next_header.base_fee_per_gas + tip,
            )
            back = _make_searcher_tx(
                target=pool.address,
                hash_seed=f"sw-back-{tx.hash[2:10]}",
                gas_limit=self.gas_per_swap,
                max_priority=tip,
                max_fee=ctx.next_header.base_fee_per_gas + tip,
            )
            bundle = Bundle(
                transactions=[front, _victim_facsimile(tx), back],
                coinbase_payment_wei=plan.expected_profit // 2,
                label=f"{self.name}/{pool.address[:8]}",
                expected_gas_used=self.gas_per_swap * 3,
                revert_protection=True,
            )
            out.bundles.append(bundle)
            out.notes.append(
                f"sandwich {pool.address[:8]} profit={plan.expected_profit} front={plan.front_amount}"
            )
        return out


def _victim_facsimile(tx: PendingTx) -> PendingTx:
    """Return the victim tx unchanged — included here for clarity."""
    return tx


__all__ = ["SandwichStrategy"]
