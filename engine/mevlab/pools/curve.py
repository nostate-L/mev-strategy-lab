"""Curve StableSwap pool (n-coin invariant).

Implements the canonical StableSwap invariant:

``A * n^n * sum(x_i) + D = A * n^n * D + D^(n+1) / (n^n * prod(x_i))``

We solve for ``D`` and for ``y`` (the new balance of an output coin given new
balances of the others) with the same Newton iteration the contract uses, then
take a 4-bps swap fee on the output side.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mevlab.core.types import Address, SwapDirection, Token
from mevlab.pools.base import BasePool, PoolKind, SwapResult


@dataclass(slots=True)
class CurveStableSwapPool(BasePool):
    """A 2-coin StableSwap pool (e.g. 3pool subsets, USDC/USDT, frxETH/ETH)."""

    address: Address
    token0: Token
    token1: Token
    balance0: int
    balance1: int
    amplification: int = 100
    fee_bps: int = 4
    admin_fee_bps: int = 0
    kind: PoolKind = PoolKind.CURVE_STABLESWAP
    rate0: int = 10**18
    rate1: int = 10**18
    n_coins: int = field(default=2, init=False)

    # ------------------------------------------------------------ invariants

    def _xp(self) -> tuple[int, int]:
        """Balances rebased to a common 1e18 unit."""
        return (
            self.balance0 * self.rate0 // self.token0.unit,
            self.balance1 * self.rate1 // self.token1.unit,
        )

    def _get_d(self, xp: tuple[int, int]) -> int:
        s = sum(xp)
        if s == 0:
            return 0
        ann = self.amplification * self.n_coins
        d = s
        for _ in range(255):
            d_p = d
            for x in xp:
                d_p = d_p * d // (self.n_coins * x + 1)
            d_prev = d
            d = (ann * s + d_p * self.n_coins) * d // (
                (ann - 1) * d + (self.n_coins + 1) * d_p
            )
            if abs(d - d_prev) <= 1:
                return d
        return d

    def _get_y(self, in_index: int, out_index: int, x_in_new: int, xp: tuple[int, int]) -> int:
        d = self._get_d(xp)
        ann = self.amplification * self.n_coins
        c = d
        s = 0
        new_xp = list(xp)
        new_xp[in_index] = x_in_new
        for i, x in enumerate(new_xp):
            if i == out_index:
                continue
            s += x
            c = c * d // (x * self.n_coins)
        c = c * d // (ann * self.n_coins)
        b = s + d // ann

        y = d
        for _ in range(255):
            y_prev = y
            y = (y * y + c) // (2 * y + b - d)
            if abs(y - y_prev) <= 1:
                return y
        return y

    # ------------------------------------------------------------------ swap

    def quote(self, direction: SwapDirection, amount_in: int) -> int:
        if amount_in <= 0:
            return 0
        in_idx, out_idx = (0, 1) if direction == SwapDirection.ZERO_FOR_ONE else (1, 0)
        xp = self._xp()
        rate_in = self.rate0 if in_idx == 0 else self.rate1
        rate_out = self.rate0 if out_idx == 0 else self.rate1
        token_in_unit = self.token0.unit if in_idx == 0 else self.token1.unit
        token_out_unit = self.token0.unit if out_idx == 0 else self.token1.unit
        x_in_new = xp[in_idx] + amount_in * rate_in // token_in_unit
        y_new = self._get_y(in_idx, out_idx, x_in_new, xp)
        dy_xp = xp[out_idx] - y_new - 1  # subtract 1 wei to round in pool's favour
        dy = dy_xp * token_out_unit // rate_out
        fee = dy * self.fee_bps // 10_000
        return dy - fee

    def swap(self, direction: SwapDirection, amount_in: int) -> SwapResult:
        amount_out = self.quote(direction, amount_in)
        if amount_out <= 0:
            raise ValueError("Curve swap produced no output")
        if direction == SwapDirection.ZERO_FOR_ONE:
            self.balance0 += amount_in
            self.balance1 -= amount_out
        else:
            self.balance1 += amount_in
            self.balance0 -= amount_out
        fee = amount_out * self.fee_bps // 10_000
        return SwapResult(
            direction=direction,
            amount_in=amount_in,
            amount_out=amount_out,
            fee_paid=fee,
            new_mid_price=self.mid_price(),
        )

    def mid_price(self) -> float:
        if self.balance0 == 0:
            return 0.0
        # Mid-price under StableSwap is the marginal exchange rate around 1e-9.
        probe = max(self.balance0 // 10**9, 1)
        out = self.quote(SwapDirection.ZERO_FOR_ONE, probe)
        return out / probe if probe else 0.0

    def clone(self) -> CurveStableSwapPool:
        return CurveStableSwapPool(
            address=self.address,
            token0=self.token0,
            token1=self.token1,
            balance0=self.balance0,
            balance1=self.balance1,
            amplification=self.amplification,
            fee_bps=self.fee_bps,
            admin_fee_bps=self.admin_fee_bps,
            rate0=self.rate0,
            rate1=self.rate1,
        )


__all__ = ["CurveStableSwapPool"]
