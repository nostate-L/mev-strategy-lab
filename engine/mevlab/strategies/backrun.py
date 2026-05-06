"""Backrunner: react to oracle-update or price-impact transactions.

The strategy waits for a transaction that mutates an external state
(oracle, large swap on a related pool) and submits an arbitrage immediately
*after* it. We use the simple heuristic that any swap larger than a
configurable threshold creates a backrun opportunity, and reuse the existing
arbitrage solver to size the response.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.builder.builder import Bundle
from mevlab.core.types import SwapDirection, Token
from mevlab.solver.arbitrage import optimal_input_ternary
from mevlab.strategies.arbitrage import _make_searcher_tx
from mevlab.strategies.base import Strategy, StrategyContext, StrategyOutput


@dataclass(slots=True)
class OracleBackrunStrategy(Strategy):
    """Backrun any large-impact swap on configured pools."""

    target_pools: set[str]
    counter_pool_for: dict[str, str]  # mapping victim_pool -> counter_pool to arb against
    base_token: Token
    name: str = "backrun"
    min_swap_size_wei: int = 10**18
    gas_per_swap: int = 150_000

    def observe(self, ctx: StrategyContext) -> StrategyOutput:
        out = StrategyOutput()
        for tx in ctx.mempool.pending:
            intent = tx.intent
            if intent is None or intent.get("kind") != "swap":
                continue
            pool_addr = intent.get("pool")
            if pool_addr not in self.target_pools:
                continue
            counter = self.counter_pool_for.get(pool_addr)
            if not counter:
                continue
            victim_pool = ctx.pool(pool_addr)
            counter_pool = ctx.pool(counter)
            if victim_pool is None or counter_pool is None:
                continue
            amount_in = int(intent.get("amount_in") or 0)
            if amount_in < self.min_swap_size_wei:
                continue

            # Simulate the victim's impact, then look for an arb between the
            # mutated pool and the unchanged counter pool.
            sim_victim = victim_pool.clone()
            try:
                sim_victim.swap(
                    SwapDirection.ZERO_FOR_ONE
                    if intent.get("dir") == "0->1"
                    else SwapDirection.ONE_FOR_ZERO,
                    amount_in,
                )
            except ValueError:
                continue

            for first, second in ((sim_victim, counter_pool), (counter_pool, sim_victim)):
                # Determine canonical directions for a base->other->base loop.
                if self.base_token in (first.token0, first.token1) and self.base_token in (
                    second.token0,
                    second.token1,
                ):
                    direction_a = (
                        SwapDirection.ZERO_FOR_ONE
                        if first.token0 == self.base_token
                        else SwapDirection.ONE_FOR_ZERO
                    )
                    direction_b = (
                        SwapDirection.ONE_FOR_ZERO
                        if second.token0 == self.base_token
                        else SwapDirection.ZERO_FOR_ONE
                    )
                    opp = optimal_input_ternary(
                        [first, second],
                        [direction_a, direction_b],
                        self.base_token,
                        upper_bound=10**21,
                    )
                    if opp is not None:
                        tip = max(1, opp.expected_profit // (self.gas_per_swap * 2 * 5))
                        bundle = Bundle(
                            transactions=[
                                tx,
                                _make_searcher_tx(
                                    first.address,
                                    f"br-{tx.hash[2:10]}-1",
                                    self.gas_per_swap,
                                    tip,
                                    ctx.next_header.base_fee_per_gas + tip,
                                ),
                                _make_searcher_tx(
                                    second.address,
                                    f"br-{tx.hash[2:10]}-2",
                                    self.gas_per_swap,
                                    tip,
                                    ctx.next_header.base_fee_per_gas + tip,
                                ),
                            ],
                            coinbase_payment_wei=opp.expected_profit // 2,
                            label=f"{self.name}/{first.address[:8]}",
                            expected_gas_used=self.gas_per_swap * 2,
                        )
                        out.bundles.append(bundle)
                        out.notes.append(
                            f"backrun {first.address[:8]} <-> {second.address[:8]} "
                            f"profit={opp.expected_profit}"
                        )
                        break
        return out


__all__ = ["OracleBackrunStrategy"]
