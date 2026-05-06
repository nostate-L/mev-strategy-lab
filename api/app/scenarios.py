"""Reusable scenarios for the API.

Centralised here so that the API, the CLI, and the backtest worker share the
same canonical pool/strategy fixtures.
"""

from __future__ import annotations

from mevlab.core.types import Token
from mevlab.pools.uniswap_v2 import UniswapV2Pool
from mevlab.strategies import (
    SandwichStrategy,
    Strategy,
    TwoPoolArbitrageStrategy,
)


def demo_tokens() -> tuple[Token, Token]:
    weth = Token(address="0x" + "11" * 20, symbol="WETH", decimals=18)
    usdc = Token(address="0x" + "22" * 20, symbol="USDC", decimals=6)
    return weth, usdc


def demo_pools() -> dict[str, UniswapV2Pool]:
    weth, usdc = demo_tokens()
    return {
        "0xaaaa": UniswapV2Pool(
            address="0xaaaa",
            token0=weth,
            token1=usdc,
            reserve0=10_000 * 10**18,
            reserve1=20_000_000 * 10**6,
            fee_bps=30,
        ),
        "0xbbbb": UniswapV2Pool(
            address="0xbbbb",
            token0=weth,
            token1=usdc,
            reserve0=8_000 * 10**18,
            reserve1=16_500_000 * 10**6,
            fee_bps=30,
        ),
    }


def demo_strategies() -> list[Strategy]:
    weth, _ = demo_tokens()
    return [
        TwoPoolArbitrageStrategy(
            pairs=[("0xaaaa", "0xbbbb")],
            base_token=weth,
        ),
        SandwichStrategy(target_pools={"0xaaaa", "0xbbbb"}),
    ]


__all__ = ["demo_pools", "demo_strategies", "demo_tokens"]
