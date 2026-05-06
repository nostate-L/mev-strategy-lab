"""Tests for the V3 pool, focusing on tick-math invariants."""

from __future__ import annotations

import math

import pytest

from mevlab.core.types import SwapDirection, Token
from mevlab.pools._v3_tickmath import (
    MAX_TICK,
    MIN_TICK,
    get_sqrt_ratio_at_tick,
    get_tick_at_sqrt_ratio,
)
from mevlab.pools.uniswap_v3 import UniswapV3Pool


def test_tickmath_round_trip_at_zero():
    sqrt_at_zero = get_sqrt_ratio_at_tick(0)
    assert sqrt_at_zero == 1 << 96


@pytest.mark.parametrize("tick", [-2_000, -100, -1, 0, 1, 100, 2_000, 100_000])
def test_tickmath_round_trip(tick: int):
    s = get_sqrt_ratio_at_tick(tick)
    assert get_tick_at_sqrt_ratio(s) == tick


def test_tickmath_extremes_are_strictly_monotonic():
    a = get_sqrt_ratio_at_tick(MIN_TICK + 10)
    b = get_sqrt_ratio_at_tick(MIN_TICK + 100)
    c = get_sqrt_ratio_at_tick(MAX_TICK - 100)
    assert a < b < c


def test_v3_swap_zero_for_one_is_monotonic_decreasing(weth: Token, usdc: Token):
    pool = UniswapV3Pool(
        address="0xv3a",
        token0=weth,
        token1=usdc,
        tick_spacing=10,
        fee_pips=3000,
        sqrt_price_x96=get_sqrt_ratio_at_tick(0),
        liquidity=10**21,
        tick=0,
    )
    pool.add_position(-887270, 887270, 10**21)
    p_before = pool.mid_price()
    out1 = pool.quote(SwapDirection.ZERO_FOR_ONE, 10**18)
    out2 = pool.quote(SwapDirection.ZERO_FOR_ONE, 5 * 10**18)
    assert out2 > out1
    pool.swap(SwapDirection.ZERO_FOR_ONE, 5 * 10**18)
    assert pool.mid_price() < p_before


def test_v3_quote_does_not_mutate_state(weth: Token, usdc: Token):
    pool = UniswapV3Pool(
        address="0xv3b",
        token0=weth,
        token1=usdc,
        tick_spacing=10,
        fee_pips=3000,
        sqrt_price_x96=get_sqrt_ratio_at_tick(0),
        liquidity=10**21,
        tick=0,
    )
    pool.add_position(-887270, 887270, 10**21)
    snap = (pool.sqrt_price_x96, pool.liquidity, pool.tick)
    pool.quote(SwapDirection.ZERO_FOR_ONE, 10**19)
    assert (pool.sqrt_price_x96, pool.liquidity, pool.tick) == snap


def test_v3_clone_independence(weth: Token, usdc: Token):
    pool = UniswapV3Pool(
        address="0xv3c",
        token0=weth,
        token1=usdc,
        tick_spacing=10,
        fee_pips=3000,
        sqrt_price_x96=get_sqrt_ratio_at_tick(0),
        liquidity=10**21,
        tick=0,
    )
    pool.add_position(-887270, 887270, 10**21)
    clone = pool.clone()
    clone.swap(SwapDirection.ZERO_FOR_ONE, 10**19)
    assert clone.sqrt_price_x96 != pool.sqrt_price_x96
    assert clone.liquidity != pool.liquidity or clone.tick != pool.tick


def test_v3_mid_price_consistent_with_sqrt_price(weth: Token, usdc: Token):
    sqrt = get_sqrt_ratio_at_tick(0)
    pool = UniswapV3Pool(
        address="0xv3d",
        token0=weth,
        token1=usdc,
        tick_spacing=10,
        fee_pips=3000,
        sqrt_price_x96=sqrt,
        liquidity=1,
        tick=0,
    )
    expected = (sqrt / (1 << 96)) ** 2
    assert math.isclose(pool.mid_price(), expected, rel_tol=1e-12)
