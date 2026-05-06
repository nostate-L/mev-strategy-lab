"""Liquidation strategy.

Models an Aave/Compound-style liquidation: when an account's health factor
crosses below 1.0 we can repay part of its debt and seize collateral at a
discount. The lab does not maintain a full lending-protocol state machine —
instead it accepts a list of *liquidation candidates* (account, debt amount,
collateral amount, bonus_bps, oracle pool) injected by an external indexer or
test fixture.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mevlab.builder.builder import Bundle
from mevlab.strategies.arbitrage import _make_searcher_tx
from mevlab.strategies.base import Strategy, StrategyContext, StrategyOutput


@dataclass(slots=True)
class LiquidationCandidate:
    account: str
    repay_amount_wei: int
    seize_amount_wei: int
    bonus_bps: int  # liquidation bonus in basis points (e.g. 500 = 5%)
    oracle_pool: str  # pool address feeding the price


@dataclass(slots=True)
class LiquidationStrategy(Strategy):
    """Liquidate every candidate whose net profit (post-gas) is positive."""

    candidates: list[LiquidationCandidate] = field(default_factory=list)
    name: str = "liquidation"
    gas_per_liquidation: int = 350_000
    min_profit_wei: int = 10**15

    def observe(self, ctx: StrategyContext) -> StrategyOutput:
        out = StrategyOutput()
        for c in self.candidates:
            net_profit = c.seize_amount_wei - c.repay_amount_wei
            if net_profit < self.min_profit_wei:
                continue
            tip = max(1, net_profit // (self.gas_per_liquidation * 5))
            tx = _make_searcher_tx(
                c.oracle_pool,
                hash_seed=f"liq-{c.account[2:10]}",
                gas_limit=self.gas_per_liquidation,
                max_priority=tip,
                max_fee=ctx.next_header.base_fee_per_gas + tip,
            )
            bundle = Bundle(
                transactions=[tx],
                coinbase_payment_wei=net_profit // 2,
                label=f"{self.name}/{c.account[:8]}",
                expected_gas_used=self.gas_per_liquidation,
            )
            out.bundles.append(bundle)
            out.notes.append(
                f"liquidate {c.account[:8]} bonus={c.bonus_bps}bps profit={net_profit}"
            )
        return out


__all__ = ["LiquidationCandidate", "LiquidationStrategy"]
