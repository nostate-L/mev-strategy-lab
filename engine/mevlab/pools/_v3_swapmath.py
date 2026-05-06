"""Uniswap V3 swap-math primitives.

Implements the four ``SqrtPriceMath`` helpers and the ``SwapMath`` step
function from v3-core. We preserve the exact rounding directions used by the
contract because rounding determines whether a tick boundary is crossed or
just barely missed.
"""

from __future__ import annotations

from mevlab.core.numeric import Q96, mul_div, mul_div_round_up


def get_amount0_delta(sqrt_a: int, sqrt_b: int, liquidity: int, round_up: bool) -> int:
    """Token0 amount required to move price from ``sqrt_a`` to ``sqrt_b``."""
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    if sqrt_a == 0:
        raise ValueError("sqrt price must be > 0")
    numerator1 = liquidity << 96
    numerator2 = sqrt_b - sqrt_a
    if round_up:
        return mul_div_round_up(mul_div_round_up(numerator1, numerator2, sqrt_b), 1, sqrt_a)
    return mul_div(numerator1, numerator2, sqrt_b) // sqrt_a


def get_amount1_delta(sqrt_a: int, sqrt_b: int, liquidity: int, round_up: bool) -> int:
    """Token1 amount required to move price from ``sqrt_a`` to ``sqrt_b``."""
    if sqrt_a > sqrt_b:
        sqrt_a, sqrt_b = sqrt_b, sqrt_a
    if round_up:
        return mul_div_round_up(liquidity, sqrt_b - sqrt_a, Q96)
    return mul_div(liquidity, sqrt_b - sqrt_a, Q96)


def get_next_sqrt_price_from_amount0_rounding_up(
    sqrt_p: int, liquidity: int, amount: int, add: bool
) -> int:
    """New sqrtPrice when adding/removing ``amount`` of token0."""
    if amount == 0:
        return sqrt_p
    numerator1 = liquidity << 96
    if add:
        product = amount * sqrt_p
        if product // amount == sqrt_p:
            denominator = numerator1 + product
            if denominator >= numerator1:
                return mul_div_round_up(numerator1, sqrt_p, denominator)
        # fallback: numerator1 / (numerator1/sqrt_p + amount)
        return -(-numerator1 // (numerator1 // sqrt_p + amount))  # ceil
    else:
        product = amount * sqrt_p
        if not (product // amount == sqrt_p and numerator1 > product):
            raise ValueError("price impact saturates pool")
        denominator = numerator1 - product
        return mul_div_round_up(numerator1, sqrt_p, denominator)


def get_next_sqrt_price_from_amount1_rounding_down(
    sqrt_p: int, liquidity: int, amount: int, add: bool
) -> int:
    """New sqrtPrice when adding/removing ``amount`` of token1."""
    if add:
        quotient = (amount << 96) // liquidity
        return sqrt_p + quotient
    quotient = mul_div_round_up(amount, Q96, liquidity)
    if sqrt_p <= quotient:
        raise ValueError("price impact saturates pool")
    return sqrt_p - quotient


def compute_swap_step(
    sqrt_price_current: int,
    sqrt_price_target: int,
    liquidity: int,
    amount_remaining: int,
    fee_pips: int,
) -> tuple[int, int, int, int]:
    """One step of a Uniswap V3 swap.

    Returns ``(sqrt_price_next, amount_in_step, amount_out_step, fee_step)``.

    ``amount_remaining > 0`` means ``exactInput``; we always treat the swap as
    exact-input here (the lab does not do exact-output simulations).
    """
    zero_for_one = sqrt_price_current >= sqrt_price_target
    amount_remaining_less_fee = amount_remaining * (1_000_000 - fee_pips) // 1_000_000

    if zero_for_one:
        amount_in_to_target = get_amount0_delta(
            sqrt_price_target, sqrt_price_current, liquidity, True
        )
    else:
        amount_in_to_target = get_amount1_delta(
            sqrt_price_current, sqrt_price_target, liquidity, True
        )

    if amount_remaining_less_fee >= amount_in_to_target:
        sqrt_price_next = sqrt_price_target
    elif zero_for_one:
        sqrt_price_next = get_next_sqrt_price_from_amount0_rounding_up(
            sqrt_price_current, liquidity, amount_remaining_less_fee, True
        )
    else:
        sqrt_price_next = get_next_sqrt_price_from_amount1_rounding_down(
            sqrt_price_current, liquidity, amount_remaining_less_fee, True
        )

    reached_target = sqrt_price_target == sqrt_price_next

    if zero_for_one:
        amount_in_step = (
            amount_in_to_target
            if reached_target
            else get_amount0_delta(sqrt_price_next, sqrt_price_current, liquidity, True)
        )
        amount_out_step = get_amount1_delta(sqrt_price_next, sqrt_price_current, liquidity, False)
    else:
        amount_in_step = (
            amount_in_to_target
            if reached_target
            else get_amount1_delta(sqrt_price_current, sqrt_price_next, liquidity, True)
        )
        amount_out_step = get_amount0_delta(sqrt_price_current, sqrt_price_next, liquidity, False)

    if not reached_target:
        # entire ``amount_remaining`` is consumed in this step; fee absorbs the rest.
        fee_step = amount_remaining - amount_in_step
    else:
        fee_step = mul_div_round_up(amount_in_step, fee_pips, 1_000_000 - fee_pips)

    return sqrt_price_next, amount_in_step, amount_out_step, fee_step


__all__ = [
    "compute_swap_step",
    "get_amount0_delta",
    "get_amount1_delta",
    "get_next_sqrt_price_from_amount0_rounding_up",
    "get_next_sqrt_price_from_amount1_rounding_down",
]
