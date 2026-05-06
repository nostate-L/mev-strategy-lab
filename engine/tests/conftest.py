"""Shared fixtures for engine tests."""

from __future__ import annotations

import pytest

from mevlab.core.types import Token
from mevlab.pools.uniswap_v2 import UniswapV2Pool


@pytest.fixture()
def weth() -> Token:
    return Token(address="0x" + "11" * 20, symbol="WETH", decimals=18)


@pytest.fixture()
def usdc() -> Token:
    return Token(address="0x" + "22" * 20, symbol="USDC", decimals=6)


@pytest.fixture()
def wbtc() -> Token:
    return Token(address="0x" + "33" * 20, symbol="WBTC", decimals=8)


@pytest.fixture()
def v2_pool_a(weth: Token, usdc: Token) -> UniswapV2Pool:
    """A "rich" pool with a tight spread."""
    return UniswapV2Pool(
        address="0x" + "aa" * 20,
        token0=weth,
        token1=usdc,
        reserve0=10_000 * 10**18,
        reserve1=20_000_000 * 10**6,
        fee_bps=30,
    )


@pytest.fixture()
def v2_pool_b(weth: Token, usdc: Token) -> UniswapV2Pool:
    """An "illiquid" pool with a worse price."""
    return UniswapV2Pool(
        address="0x" + "bb" * 20,
        token0=weth,
        token1=usdc,
        reserve0=8_000 * 10**18,
        reserve1=16_500_000 * 10**6,
        fee_bps=30,
    )
