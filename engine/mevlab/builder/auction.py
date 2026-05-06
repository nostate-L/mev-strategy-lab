"""Block-space auction abstraction.

Used to score competing searcher bundles when several point at the same victim
or the same arbitrage. The winner pays the second-highest bid (Vickrey-style),
but bidders only see their own valuation; we expose the auction as a pure
function so strategies and the backtest engine can drive it.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.builder.builder import Bundle


@dataclass(slots=True, frozen=True)
class AuctionResult:
    winner: Bundle | None
    clearing_price_wei: int
    runner_up: Bundle | None


class BlockSpaceAuction:
    """A simple second-price auction for an exclusive opportunity slot."""

    def __init__(self, base_fee_per_gas_next: int) -> None:
        self.base_fee_per_gas_next = base_fee_per_gas_next

    def settle(self, bundles: list[Bundle]) -> AuctionResult:
        if not bundles:
            return AuctionResult(None, 0, None)

        ranked = sorted(
            bundles,
            key=lambda b: -b.revenue_per_gas(self.base_fee_per_gas_next),
        )
        winner = ranked[0]
        runner_up = ranked[1] if len(ranked) > 1 else None
        clearing = (
            int(runner_up.revenue_per_gas(self.base_fee_per_gas_next))
            if runner_up is not None
            else 0
        )
        return AuctionResult(winner=winner, clearing_price_wei=clearing, runner_up=runner_up)


__all__ = ["AuctionResult", "BlockSpaceAuction"]
