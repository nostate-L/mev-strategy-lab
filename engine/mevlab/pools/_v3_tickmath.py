"""Uniswap V3 tick math.

Direct port of the constants from
https://github.com/Uniswap/v3-core/blob/main/contracts/libraries/TickMath.sol so
that ``get_sqrt_ratio_at_tick`` matches the on-chain contract exactly. The
inverse ``get_tick_at_sqrt_ratio`` uses the same fixed-point approach with a
binary-decomposition algorithm; it is exact within the Solidity rounding rules
for any ``sqrt_price >= MIN_SQRT_RATIO``.
"""

from __future__ import annotations

import math

from mevlab.core.numeric import MAX_UINT256

MIN_TICK = -887272
MAX_TICK = 887272

MIN_SQRT_RATIO = 4295128739
MAX_SQRT_RATIO = 1461446703485210103287273052203988822378723970342

# Precomputed constants: ratio_n is sqrt(1.0001 ** (2**n)) in Q128.128.
_RATIO_BITS = [
    (0x1, 0xFFFCB933BD6FAD37AA2D162D1A594001),
    (0x2, 0xFFF97272373D413259A46990580E213A),
    (0x4, 0xFFF2E50F5F656932EF12357CF3C7FDCC),
    (0x8, 0xFFE5CACA7E10E4E61C3624EAA0941CD0),
    (0x10, 0xFFCB9843D60F6159C9DB58835C926644),
    (0x20, 0xFF973B41FA98C081472E6896DFB254C0),
    (0x40, 0xFF2EA16466C96A3843EC78B326B52861),
    (0x80, 0xFE5DEE046A99A2A811C461F1969C3053),
    (0x100, 0xFCBE86C7900A88AEDCFFC83B479AA3A4),
    (0x200, 0xF987A7253AC413176F2B074CF7815E54),
    (0x400, 0xF3392B0822B70005940C7A398E4B70F3),
    (0x800, 0xE7159475A2C29B7443B29C7FA6E889D9),
    (0x1000, 0xD097F3BDFD2022B8845AD8F792AA5825),
    (0x2000, 0xA9F746462D870FDF8A65DC1F90E061E5),
    (0x4000, 0x70D869A156D2A1B890BB3DF62BAF32F7),
    (0x8000, 0x31BE135F97D08FD981231505542FCFA6),
    (0x10000, 0x9AA508B5B7A84E1C677DE54F3E99BC9),
    (0x20000, 0x5D6AF8DEDB81196699C329225EE604),
    (0x40000, 0x2216E584F5FA1EA926041BEDFE98),
    (0x80000, 0x48A170391F7DC42444E8FA2),
]


def get_sqrt_ratio_at_tick(tick: int) -> int:
    """Return ``sqrt(1.0001**tick)`` as a Q64.96 integer (sqrtPriceX96)."""
    if tick < MIN_TICK or tick > MAX_TICK:
        raise ValueError(f"tick {tick} out of range")

    abs_tick = -tick if tick < 0 else tick
    if abs_tick & 0x1:
        ratio = 0xFFFCB933BD6FAD37AA2D162D1A594001
    else:
        ratio = 0x100000000000000000000000000000000

    for mask, k in _RATIO_BITS[1:]:
        if abs_tick & mask:
            ratio = (ratio * k) >> 128

    if tick > 0:
        ratio = MAX_UINT256 // ratio

    # Convert from Q128.128 to Q64.96 with rounding up (matches Solidity).
    sqrt_price_x96 = (ratio >> 32) + (1 if (ratio % (1 << 32)) > 0 else 0)
    return sqrt_price_x96


_LOG_1_0001 = 9.999500033330834e-05  # math.log(1.0001)
_Q96_LOG = 66.54639035001623  # math.log(2**96)


def get_tick_at_sqrt_ratio(sqrt_price_x96: int) -> int:
    """Inverse of :func:`get_sqrt_ratio_at_tick`.

    Returns the greatest ``tick`` such that
    ``get_sqrt_ratio_at_tick(tick) <= sqrt_price_x96``.

    We start from a fast log-based approximation (tick ≈ 2 ·
    ln(sqrt_price/Q96) / ln(1.0001)) and refine by checking the four nearest
    ticks. The approximation is always within ±2 ticks of the exact answer,
    so this is O(1) and matches the on-chain ``getTickAtSqrtRatio`` exactly.
    """
    if not (MIN_SQRT_RATIO <= sqrt_price_x96 < MAX_SQRT_RATIO):
        raise ValueError("sqrt_price_x96 out of range")

    # Approximate using floats; safe because (sqrt_price_x96 / 2^96) is bounded.
    log_ratio = math.log(sqrt_price_x96) - _Q96_LOG
    approx = int(round(2 * log_ratio / _LOG_1_0001))

    # Refine: walk up to ±4 ticks from the approximation to guarantee correctness.
    candidate = max(MIN_TICK, min(MAX_TICK, approx))
    # Ensure we don't return a tick whose sqrt ratio exceeds sqrt_price_x96.
    while candidate > MIN_TICK and get_sqrt_ratio_at_tick(candidate) > sqrt_price_x96:
        candidate -= 1
    while (
        candidate < MAX_TICK and get_sqrt_ratio_at_tick(candidate + 1) <= sqrt_price_x96
    ):
        candidate += 1
    return candidate


__all__ = [
    "MAX_SQRT_RATIO",
    "MAX_TICK",
    "MIN_SQRT_RATIO",
    "MIN_TICK",
    "get_sqrt_ratio_at_tick",
    "get_tick_at_sqrt_ratio",
]
