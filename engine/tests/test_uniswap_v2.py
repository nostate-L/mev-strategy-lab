"""Tests for the constant-product pool."""

from __future__ import annotations

import pytest

from mevlab.core.types import SwapDirection, Token
from mevlab.pools.uniswap_v2 import UniswapV2Pool


def test_quote_matches_solidity_formula(v2_pool_a):
    # Hand-computed: 1 WETH → ?
    # amount_in_with_fee = 1e18 * 9970 = 9.97e21
    # numerator = 9.97e21 * 20e12 = 1.994e35
    # denominator = 1e22 * 1e4 + 9.97e21 = 1.00997e26
    # out = numerator // denominator
    amount_in = 10**18
    out = v2_pool_a.quote(SwapDirection.ZERO_FOR_ONE, amount_in)
    expected_num = amount_in * 9970 * v2_pool_a.reserve1
    expected_den = v2_pool_a.reserve0 * 10_000 + amount_in * 9970
    assert out == expected_num // expected_den


def test_swap_mutates_reserves_and_preserves_k_growth(v2_pool_a):
    k_before = v2_pool_a.k
    res = v2_pool_a.swap(SwapDirection.ZERO_FOR_ONE, 10**18)
    k_after = v2_pool_a.k
    assert res.amount_out > 0
    assert k_after >= k_before  # fee makes k grow strictly


def test_swap_then_inverse_quote_returns_close_to_original(v2_pool_a):
    pool = v2_pool_a.clone()
    delta_in = 5 * 10**18
    out = pool.swap(SwapDirection.ZERO_FOR_ONE, delta_in).amount_out
    # Reverse direction quote — won't be equal to delta_in because of fees, but
    # should be within ~0.6% (two 30-bps swaps).
    back = pool.quote(SwapDirection.ONE_FOR_ZERO, out)
    assert 0 < back < delta_in
    assert (delta_in - back) / delta_in < 0.012


def test_required_input_inverse_of_quote(v2_pool_a):
    pool = v2_pool_a.clone()
    target_out = 1500 * 10**6  # 1500 USDC out
    needed = pool.quote_required_input(SwapDirection.ZERO_FOR_ONE, target_out)
    actual_out = pool.quote(SwapDirection.ZERO_FOR_ONE, needed)
    # rounding semantics give us *at least* the target out.
    assert actual_out >= target_out


def test_clone_is_independent(v2_pool_a):
    clone = v2_pool_a.clone()
    clone.swap(SwapDirection.ZERO_FOR_ONE, 10**18)
    assert clone.reserve0 != v2_pool_a.reserve0
    assert clone.reserve1 != v2_pool_a.reserve1


def test_zero_amount_quote_is_zero(v2_pool_a):
    assert v2_pool_a.quote(SwapDirection.ZERO_FOR_ONE, 0) == 0


def test_swap_drains_pool_raises(weth: Token, usdc: Token):
    pool = UniswapV2Pool(
        address="0xfff",
        token0=weth,
        token1=usdc,
        reserve0=1,
        reserve1=1,
        fee_bps=30,
    )
    with pytest.raises(ValueError):
        pool.swap(SwapDirection.ZERO_FOR_ONE, 10**18)
