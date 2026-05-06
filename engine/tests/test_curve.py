"""Tests for the StableSwap pool."""

from __future__ import annotations

import pytest

from mevlab.core.types import SwapDirection, Token
from mevlab.pools.curve import CurveStableSwapPool


@pytest.fixture()
def usdc(usdc: Token) -> Token:
    return usdc


def test_stableswap_quote_close_to_unit_when_balanced(usdc: Token):
    usdt = Token(address="0x" + "44" * 20, symbol="USDT", decimals=6)
    pool = CurveStableSwapPool(
        address="0xc1",
        token0=usdc,
        token1=usdt,
        balance0=10**12,  # 1M USDC
        balance1=10**12,  # 1M USDT
        amplification=1000,
    )
    out = pool.quote(SwapDirection.ZERO_FOR_ONE, 10**6)  # 1 USDC
    # Should get ~1 USDT minus 4-bps fee. Both tokens use 1e6 base units.
    assert 999_500 <= out <= 1_000_000


def test_stableswap_swap_mutates_balances(usdc: Token):
    usdt = Token(address="0x" + "44" * 20, symbol="USDT", decimals=6)
    pool = CurveStableSwapPool(
        address="0xc2",
        token0=usdc,
        token1=usdt,
        balance0=10**12,
        balance1=10**12,
    )
    res = pool.swap(SwapDirection.ZERO_FOR_ONE, 10_000 * 10**6)
    assert res.amount_out > 0
    assert pool.balance0 == 10**12 + 10_000 * 10**6
    assert pool.balance1 == 10**12 - res.amount_out


def test_stableswap_imbalance_widens_spread(usdc: Token):
    usdt = Token(address="0x" + "44" * 20, symbol="USDT", decimals=6)
    pool = CurveStableSwapPool(
        address="0xc3",
        token0=usdc,
        token1=usdt,
        balance0=10**12,
        balance1=10**12,
        amplification=1000,
    )
    # Push pool way out of balance.
    pool.swap(SwapDirection.ZERO_FOR_ONE, 800_000 * 10**6)
    out = pool.quote(SwapDirection.ZERO_FOR_ONE, 10**6)
    # After heavy imbalance, 1 USDC should get noticeably less than 1 USDT.
    # Output is in 1e6 base units; expect a meaningful drop versus the balanced ~999_600.
    assert out < 990_000
