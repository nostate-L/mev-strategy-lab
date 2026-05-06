"""Uniswap V2 (constant-product) pool.

The math here is the classic ``x*y = k`` AMM with a per-swap fee taken from the
input. We keep the variables in the same units the on-chain contract uses (raw
token base units) so traces are easy to compare against real ``getAmountOut``
calls.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.core.types import Address, SwapDirection, Token
from mevlab.pools.base import BasePool, PoolKind, SwapResult

FEE_DENOMINATOR = 10_000


@dataclass(slots=True)
class UniswapV2Pool(BasePool):
    """Constant-product pool with optional non-default fee.

    ``fee_bps`` defaults to 30 (the canonical Uniswap V2 fee). Sushi V2-style
    pools or custom forks can pass higher fees.
    """

    address: Address
    token0: Token
    token1: Token
    reserve0: int
    reserve1: int
    fee_bps: int = 30
    kind: PoolKind = PoolKind.UNISWAP_V2

    # ---------------------------------------------------------------- helpers

    def _reserves_for(self, direction: SwapDirection) -> tuple[int, int]:
        if direction == SwapDirection.ZERO_FOR_ONE:
            return self.reserve0, self.reserve1
        return self.reserve1, self.reserve0

    def _set_reserves(self, direction: SwapDirection, reserve_in: int, reserve_out: int) -> None:
        if direction == SwapDirection.ZERO_FOR_ONE:
            self.reserve0, self.reserve1 = reserve_in, reserve_out
        else:
            self.reserve1, self.reserve0 = reserve_in, reserve_out

    # ----------------------------------------------------------------- public

    def quote(self, direction: SwapDirection, amount_in: int) -> int:
        if amount_in <= 0:
            return 0
        reserve_in, reserve_out = self._reserves_for(direction)
        amount_in_with_fee = amount_in * (FEE_DENOMINATOR - self.fee_bps)
        numerator = amount_in_with_fee * reserve_out
        denominator = reserve_in * FEE_DENOMINATOR + amount_in_with_fee
        return numerator // denominator

    def quote_required_input(self, direction: SwapDirection, amount_out: int) -> int:
        """Inverse of ``quote``: minimum input required for a given output."""
        if amount_out <= 0:
            return 0
        reserve_in, reserve_out = self._reserves_for(direction)
        if amount_out >= reserve_out:
            raise ValueError("amount_out exceeds pool reserves")
        numerator = reserve_in * amount_out * FEE_DENOMINATOR
        denominator = (reserve_out - amount_out) * (FEE_DENOMINATOR - self.fee_bps)
        return numerator // denominator + 1

    def swap(self, direction: SwapDirection, amount_in: int) -> SwapResult:
        amount_out = self.quote(direction, amount_in)
        if amount_out <= 0:
            raise ValueError("swap produces zero output")
        reserve_in, reserve_out = self._reserves_for(direction)
        new_reserve_in = reserve_in + amount_in
        new_reserve_out = reserve_out - amount_out
        if new_reserve_out <= 0:
            raise ValueError("swap drains pool")
        self._set_reserves(direction, new_reserve_in, new_reserve_out)
        fee_paid = amount_in * self.fee_bps // FEE_DENOMINATOR
        return SwapResult(
            direction=direction,
            amount_in=amount_in,
            amount_out=amount_out,
            fee_paid=fee_paid,
            new_mid_price=self.mid_price(),
        )

    def mid_price(self) -> float:
        if self.reserve0 == 0:
            return 0.0
        return self.reserve1 / self.reserve0

    def clone(self) -> UniswapV2Pool:
        return UniswapV2Pool(
            address=self.address,
            token0=self.token0,
            token1=self.token1,
            reserve0=self.reserve0,
            reserve1=self.reserve1,
            fee_bps=self.fee_bps,
        )

    @property
    def k(self) -> int:
        """The invariant ``x*y`` (useful for tests)."""
        return self.reserve0 * self.reserve1


__all__ = ["FEE_DENOMINATOR", "UniswapV2Pool"]
