"""Uniswap V3 (concentrated liquidity) pool with full tick traversal.

This is a faithful Python implementation of the v3-core swap loop. Liquidity
positions are represented as a dict mapping ``tick_index -> liquidity_net``;
tick boundaries are tracked sparsely so empty space between initialized ticks
is skipped in O(1) per traversal step.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field

from mevlab.core.numeric import fix_q96_to_float
from mevlab.core.types import Address, SwapDirection, Token
from mevlab.pools._v3_swapmath import compute_swap_step
from mevlab.pools._v3_tickmath import (
    MAX_SQRT_RATIO,
    MIN_SQRT_RATIO,
    get_sqrt_ratio_at_tick,
    get_tick_at_sqrt_ratio,
)
from mevlab.pools.base import BasePool, PoolKind, SwapResult


@dataclass(slots=True)
class V3Tick:
    """Sparse representation of an initialized tick boundary.

    ``liquidity_net`` is the change in active liquidity when the tick is
    crossed left-to-right; left-to-left crossings flip its sign as in the
    contract.
    """

    index: int
    liquidity_net: int


@dataclass(slots=True)
class UniswapV3Pool(BasePool):
    """Concentrated-liquidity pool."""

    address: Address
    token0: Token
    token1: Token
    tick_spacing: int
    fee_pips: int  # e.g. 3000 = 0.30%
    sqrt_price_x96: int
    liquidity: int
    tick: int
    ticks: dict[int, int] = field(default_factory=dict)  # tick_index -> liquidity_net
    kind: PoolKind = PoolKind.UNISWAP_V3

    @property
    def fee_bps(self) -> int:  # type: ignore[override]
        return self.fee_pips // 100

    # --------------------------------------------------------------- helpers

    def add_position(self, lower_tick: int, upper_tick: int, liquidity: int) -> None:
        """Mint a position covering ``[lower_tick, upper_tick)``."""
        if lower_tick >= upper_tick:
            raise ValueError("lower_tick must be < upper_tick")
        self.ticks[lower_tick] = self.ticks.get(lower_tick, 0) + liquidity
        self.ticks[upper_tick] = self.ticks.get(upper_tick, 0) - liquidity
        if lower_tick <= self.tick < upper_tick:
            self.liquidity += liquidity

    def _sorted_ticks(self) -> list[int]:
        return sorted(self.ticks.keys())

    def _next_initialized_tick(self, lte: bool) -> int | None:
        ticks = self._sorted_ticks()
        if not ticks:
            return None
        if lte:
            idx = bisect_right(ticks, self.tick) - 1
            return ticks[idx] if idx >= 0 else None
        idx = bisect_left(ticks, self.tick + 1)
        return ticks[idx] if idx < len(ticks) else None

    # ------------------------------------------------------------------ core

    def _swap_loop(self, direction: SwapDirection, amount_specified: int) -> tuple[int, int, int]:
        """Run the v3 swap loop and return ``(amount_in, amount_out, fee_paid)``."""
        if amount_specified <= 0:
            raise ValueError("amount_specified must be positive")
        zero_for_one = direction == SwapDirection.ZERO_FOR_ONE
        sqrt_price_limit = MIN_SQRT_RATIO + 1 if zero_for_one else MAX_SQRT_RATIO - 1

        amount_remaining = amount_specified
        amount_in_total = 0
        amount_out_total = 0
        fee_total = 0

        # safety bound — far more iterations than any realistic pool needs
        for _ in range(2048):
            if amount_remaining == 0:
                break
            if (zero_for_one and self.sqrt_price_x96 <= sqrt_price_limit) or (
                not zero_for_one and self.sqrt_price_x96 >= sqrt_price_limit
            ):
                break

            next_tick = self._next_initialized_tick(lte=zero_for_one)
            if next_tick is None:
                break
            sqrt_target = get_sqrt_ratio_at_tick(next_tick)
            if zero_for_one:
                sqrt_target = max(sqrt_target, sqrt_price_limit)
            else:
                sqrt_target = min(sqrt_target, sqrt_price_limit)

            sqrt_next, step_in, step_out, step_fee = compute_swap_step(
                self.sqrt_price_x96,
                sqrt_target,
                self.liquidity,
                amount_remaining,
                self.fee_pips,
            )
            self.sqrt_price_x96 = sqrt_next
            amount_in_total += step_in
            amount_out_total += step_out
            fee_total += step_fee
            amount_remaining -= step_in + step_fee

            # If we reached the next tick boundary, cross it.
            if sqrt_next == get_sqrt_ratio_at_tick(next_tick):
                liquidity_net = self.ticks.get(next_tick, 0)
                if zero_for_one:
                    liquidity_net = -liquidity_net
                self.liquidity += liquidity_net
                self.tick = next_tick - 1 if zero_for_one else next_tick
            else:
                self.tick = get_tick_at_sqrt_ratio(self.sqrt_price_x96)

        return amount_in_total, amount_out_total, fee_total

    # ---------------------------------------------------------------- public

    def quote(self, direction: SwapDirection, amount_in: int) -> int:
        clone = self.clone()
        _, amount_out, _ = clone._swap_loop(direction, amount_in)
        return amount_out

    def swap(self, direction: SwapDirection, amount_in: int) -> SwapResult:
        amount_in_used, amount_out, fee_paid = self._swap_loop(direction, amount_in)
        return SwapResult(
            direction=direction,
            amount_in=amount_in_used,
            amount_out=amount_out,
            fee_paid=fee_paid,
            new_mid_price=self.mid_price(),
        )

    def mid_price(self) -> float:
        # mid-price (token1 per token0) ≈ (sqrtPriceX96 / 2^96)^2
        return fix_q96_to_float(self.sqrt_price_x96) ** 2

    def clone(self) -> UniswapV3Pool:
        return UniswapV3Pool(
            address=self.address,
            token0=self.token0,
            token1=self.token1,
            tick_spacing=self.tick_spacing,
            fee_pips=self.fee_pips,
            sqrt_price_x96=self.sqrt_price_x96,
            liquidity=self.liquidity,
            tick=self.tick,
            ticks=dict(self.ticks),
        )


__all__ = ["UniswapV3Pool", "V3Tick"]
