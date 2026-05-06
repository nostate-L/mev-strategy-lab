"""Arbitrage strategies (cyclic 2- and 3-pool)."""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.builder.builder import Bundle
from mevlab.core.types import PendingTx, SwapDirection, Token
from mevlab.pools.base import BasePool
from mevlab.pools.uniswap_v2 import UniswapV2Pool
from mevlab.solver.arbitrage import (
    closed_form_two_pool_v2,
    optimal_input_ternary,
)
from mevlab.strategies.base import Strategy, StrategyContext, StrategyOutput


def _make_searcher_tx(
    target: str, hash_seed: str, gas_limit: int, max_priority: int, max_fee: int
) -> PendingTx:
    return PendingTx(
        hash=("0xa" + hash_seed).ljust(66, "0")[:66],
        sender="0x" + "fee" * 13 + "01",
        target=target,
        value=0,
        calldata=b"",
        gas_limit=gas_limit,
        max_fee_per_gas=max_fee,
        max_priority_fee_per_gas=max_priority,
        nonce=0,
        seen_at_ms=0,
    )


@dataclass(slots=True)
class TwoPoolArbitrageStrategy(Strategy):
    """Find profitable 2-pool arbitrage on a curated pair list every block."""

    pairs: list[tuple[str, str]]  # pairs of pool addresses sharing a token pair
    base_token: Token
    name: str = "arb-2pool"
    gas_per_swap: int = 150_000

    def observe(self, ctx: StrategyContext) -> StrategyOutput:  # noqa: D401
        out = StrategyOutput()
        for addr_a, addr_b in self.pairs:
            pool_a = ctx.pool(addr_a)
            pool_b = ctx.pool(addr_b)
            if pool_a is None or pool_b is None:
                continue
            if isinstance(pool_a, UniswapV2Pool) and isinstance(pool_b, UniswapV2Pool):
                opp = closed_form_two_pool_v2(pool_a, pool_b, self.base_token)
            else:
                # generic AMMs — find direction by mid-price comparison
                price_a = pool_a.mid_price()
                price_b = pool_b.mid_price()
                if price_a == 0 or price_b == 0:
                    continue
                if price_a >= price_b:
                    pools = [pool_a, pool_b]
                else:
                    pools = [pool_b, pool_a]
                directions = (
                    [
                        (
                            SwapDirection.ZERO_FOR_ONE
                            if pools[0].token0 == self.base_token
                            else SwapDirection.ONE_FOR_ZERO
                        ),
                        (
                            SwapDirection.ONE_FOR_ZERO
                            if pools[1].token0 == self.base_token
                            else SwapDirection.ZERO_FOR_ONE
                        ),
                    ]
                )
                upper = min(self._reserve_of(pools[0], self.base_token) // 4, ctx.searcher_capital_wei)
                opp = optimal_input_ternary(
                    pools, directions, self.base_token, upper_bound=max(upper, 2)
                )
            if opp is None:
                continue

            bundle = Bundle(
                transactions=[
                    _make_searcher_tx(
                        target=p.address,
                        hash_seed=f"{ctx.next_header.number:x}{i:02x}",
                        gas_limit=self.gas_per_swap,
                        max_priority=opp.expected_profit // (self.gas_per_swap * len(opp.path) * 5),
                        max_fee=ctx.next_header.base_fee_per_gas
                        + opp.expected_profit // (self.gas_per_swap * len(opp.path)),
                    )
                    for i, p in enumerate(opp.path)
                ],
                coinbase_payment_wei=opp.expected_profit // 2,
                label=f"{self.name}/{addr_a[:8]}/{addr_b[:8]}",
                expected_gas_used=self.gas_per_swap * len(opp.path),
            )
            out.bundles.append(bundle)
            out.notes.append(
                f"opp profit={opp.expected_profit} input={opp.optimal_input} hops={len(opp.path)}"
            )
        return out

    @staticmethod
    def _reserve_of(pool: BasePool, token: Token) -> int:
        if isinstance(pool, UniswapV2Pool):
            return pool.reserve0 if pool.token0 == token else pool.reserve1
        # Conservative default for V3/Curve — use a small fraction of liquidity.
        return 10**24


@dataclass(slots=True)
class TriangularArbitrageStrategy(Strategy):
    """Three-leg arbitrage (e.g. ETH -> USDC -> WBTC -> ETH)."""

    legs: list[tuple[str, str, str]]  # tuple of three pool addresses
    base_token: Token
    name: str = "arb-tri"
    gas_per_swap: int = 150_000

    def observe(self, ctx: StrategyContext) -> StrategyOutput:
        out = StrategyOutput()
        for triple in self.legs:
            pools = [ctx.pool(a) for a in triple]
            if any(p is None for p in pools):
                continue
            # Determine canonical directions by following the token graph.
            directions: list[SwapDirection] = []
            cursor = self.base_token
            valid = True
            for pool in pools:
                if pool.token0 == cursor:
                    directions.append(SwapDirection.ZERO_FOR_ONE)
                    cursor = pool.token1
                elif pool.token1 == cursor:
                    directions.append(SwapDirection.ONE_FOR_ZERO)
                    cursor = pool.token0
                else:
                    valid = False
                    break
            if not valid or cursor != self.base_token:
                continue

            upper = max(2, min(ctx.searcher_capital_wei, 10**21))
            opp = optimal_input_ternary(
                list(pools), directions, self.base_token, upper_bound=upper
            )
            if opp is None:
                continue
            bundle = Bundle(
                transactions=[
                    _make_searcher_tx(
                        target=p.address,
                        hash_seed=f"{ctx.next_header.number:x}{i:02x}",
                        gas_limit=self.gas_per_swap,
                        max_priority=max(
                            1, opp.expected_profit // (self.gas_per_swap * 3 * 5)
                        ),
                        max_fee=ctx.next_header.base_fee_per_gas
                        + max(1, opp.expected_profit // (self.gas_per_swap * 3)),
                    )
                    for i, p in enumerate(pools)
                ],
                coinbase_payment_wei=opp.expected_profit // 2,
                label=f"{self.name}/{triple[0][:6]}…",
                expected_gas_used=self.gas_per_swap * 3,
            )
            out.bundles.append(bundle)
            out.notes.append(f"tri opp profit={opp.expected_profit} legs={len(pools)}")
        return out


__all__ = ["TriangularArbitrageStrategy", "TwoPoolArbitrageStrategy"]
