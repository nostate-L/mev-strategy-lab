"""Just-in-time (JIT) liquidity for Uniswap V3.

The strategy:
    1. Spot a large pending swap that will hit a particular V3 pool.
    2. *Immediately before* the victim swap, mint a very tight liquidity
       position spanning the predicted price range.
    3. Earn essentially the entire fee on the victim's swap.
    4. *Immediately after*, burn the position to recover the principal.

We model the economics by simulating the victim's swap with and without an
extra ``mint_liquidity`` of size ``L_jit`` covering exactly the swap range.
The JIT provider's reward is approximately ``fee_pips/1e6 * amount_in_swap``
times the fraction of the active liquidity it owns during the swap.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.builder.builder import Bundle
from mevlab.pools.uniswap_v3 import UniswapV3Pool
from mevlab.strategies.arbitrage import _make_searcher_tx
from mevlab.strategies.base import Strategy, StrategyContext, StrategyOutput


@dataclass(slots=True)
class JustInTimeLiquidityStrategy(Strategy):
    """JIT-LP attacker for V3 pools."""

    target_pools: set[str]
    name: str = "jit"
    gas_mint: int = 250_000
    gas_burn: int = 200_000
    min_swap_size_wei: int = 5 * 10**18  # 5 ETH
    min_profit_wei: int = 10**15  # 0.001 ETH
    capital_cap_wei: int = 10**22

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
            if not isinstance(pool, UniswapV3Pool):
                continue
            amount_in = int(intent.get("amount_in") or 0)
            if amount_in < self.min_swap_size_wei:
                continue

            # JIT economics: with an injected liquidity of L_jit on top of L_active,
            # the searcher captures L_jit / (L_active + L_jit) of the swap fees.
            sim = pool.clone()
            existing_liquidity = max(sim.liquidity, 1)
            # We commit capital_cap worth of liquidity for the duration of the swap.
            l_jit = self.capital_cap_wei
            captured_fraction = l_jit / (existing_liquidity + l_jit)
            fee_amount_in = amount_in * sim.fee_pips // 1_000_000
            estimated_profit = int(captured_fraction * fee_amount_in)
            if estimated_profit < self.min_profit_wei:
                continue

            tip = max(1, estimated_profit // ((self.gas_mint + self.gas_burn) * 5))
            mint_tx = _make_searcher_tx(
                pool.address,
                hash_seed=f"jit-mint-{tx.hash[2:10]}",
                gas_limit=self.gas_mint,
                max_priority=tip,
                max_fee=ctx.next_header.base_fee_per_gas + tip,
            )
            burn_tx = _make_searcher_tx(
                pool.address,
                hash_seed=f"jit-burn-{tx.hash[2:10]}",
                gas_limit=self.gas_burn,
                max_priority=tip,
                max_fee=ctx.next_header.base_fee_per_gas + tip,
            )
            bundle = Bundle(
                transactions=[mint_tx, tx, burn_tx],
                coinbase_payment_wei=estimated_profit // 2,
                label=f"{self.name}/{pool.address[:8]}",
                expected_gas_used=self.gas_mint + self.gas_burn,
                revert_protection=True,
            )
            out.bundles.append(bundle)
            out.notes.append(
                f"jit pool={pool.address[:8]} captured~{captured_fraction:.2%} "
                f"fee_in={fee_amount_in} profit~{estimated_profit}"
            )
        return out


__all__ = ["JustInTimeLiquidityStrategy"]
