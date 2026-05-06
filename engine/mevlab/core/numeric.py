"""High-precision integer math primitives.

The Uniswap V3 reference implementations rely on 256-bit arithmetic, ``mulDiv``,
and ``sqrtPriceX96`` (a Q64.96 fixed-point number). Python integers are
arbitrary-precision so we don't need a separate uint256 type; we just need to
implement the same rounding semantics as the Solidity helpers.
"""

from __future__ import annotations

import math

Q96 = 1 << 96
Q128 = 1 << 128
Q192 = 1 << 192
MAX_UINT256 = (1 << 256) - 1


def mul_div(a: int, b: int, denominator: int) -> int:
    """Compute ``floor(a*b/denominator)`` with full 512-bit intermediate precision.

    Mirrors Uniswap's ``FullMath.mulDiv``. Since Python ints are arbitrary
    precision we can do this directly; we still emulate the truncation toward zero.
    """
    if denominator == 0:
        raise ZeroDivisionError("mul_div denominator is zero")
    if a < 0 or b < 0 or denominator < 0:
        raise ValueError("mul_div expects non-negative inputs")
    return (a * b) // denominator


def mul_div_round_up(a: int, b: int, denominator: int) -> int:
    """Compute ``ceil(a*b/denominator)`` with full precision."""
    result = mul_div(a, b, denominator)
    if (a * b) % denominator != 0:
        result += 1
    return result


def isqrt256(value: int) -> int:
    """Integer square root that matches ``math.isqrt`` semantics for uint256."""
    if value < 0:
        raise ValueError("isqrt256 expects a non-negative input")
    if value > MAX_UINT256:
        raise OverflowError("isqrt256 overflow: value larger than 2**256-1")
    return math.isqrt(value)


def iexp(base: int, exponent: int) -> int:
    """Integer exponentiation (positive integer exponent)."""
    if exponent < 0:
        raise ValueError("iexp expects exponent >= 0")
    return base**exponent


def float_to_q96(value: float) -> int:
    """Convert a float price ratio to a Q64.96 integer."""
    if value < 0:
        raise ValueError("price must be non-negative")
    return int(value * Q96)


def fix_q96_to_float(value: int) -> float:
    """Convert a Q64.96 integer back to a float (lossy)."""
    return value / Q96


class FullMath:
    """Namespace mirroring Uniswap's ``FullMath`` library for ergonomics."""

    @staticmethod
    def mul_div(a: int, b: int, denominator: int) -> int:
        return mul_div(a, b, denominator)

    @staticmethod
    def mul_div_round_up(a: int, b: int, denominator: int) -> int:
        return mul_div_round_up(a, b, denominator)


__all__ = [
    "FullMath",
    "MAX_UINT256",
    "Q128",
    "Q192",
    "Q96",
    "fix_q96_to_float",
    "float_to_q96",
    "iexp",
    "isqrt256",
    "mul_div",
    "mul_div_round_up",
]
