"""Chain registry and well-known token tables.

Used so strategies can be parameterized by chain ID without hard-coding
addresses inside business logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.core.gas import GasModel
from mevlab.core.types import Address, Token


@dataclass(frozen=True, slots=True)
class ChainConfig:
    """Static per-chain configuration."""

    chain_id: int
    name: str
    native_symbol: str
    block_time_seconds: float
    gas_model: GasModel
    weth: Address
    usdc: Address
    usdt: Address


# Subset of mainnets used by tests and example fixtures. Addresses are mainnet
# canonical addresses; we never broadcast against them — they're only labels.
ETHEREUM = ChainConfig(
    chain_id=1,
    name="ethereum",
    native_symbol="ETH",
    block_time_seconds=12.0,
    gas_model=GasModel(),
    weth="0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    usdc="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    usdt="0xdac17f958d2ee523a2206206994597c13d831ec7",
)

ARBITRUM = ChainConfig(
    chain_id=42161,
    name="arbitrum",
    native_symbol="ETH",
    block_time_seconds=0.25,
    gas_model=GasModel(target_gas_used=15_000_000, max_change_denominator=50),
    weth="0x82af49447d8a07e3bd95bd0d56f35241523fbab1",
    usdc="0xaf88d065e77c8cc2239327c5edb3a432268e5831",
    usdt="0xfd086bc7cd5c481dcc9c85ebe478a1c0b69fcbb9",
)

REGISTRY: dict[int, ChainConfig] = {
    ETHEREUM.chain_id: ETHEREUM,
    ARBITRUM.chain_id: ARBITRUM,
}


def get_chain(chain_id: int) -> ChainConfig:
    if chain_id not in REGISTRY:
        raise KeyError(f"unknown chain_id {chain_id}")
    return REGISTRY[chain_id]


def common_tokens(chain: ChainConfig) -> dict[str, Token]:
    """Return a small dict of canonical tokens for a chain."""
    return {
        "WETH": Token(address=chain.weth, symbol="WETH", decimals=18),
        "USDC": Token(address=chain.usdc, symbol="USDC", decimals=6),
        "USDT": Token(address=chain.usdt, symbol="USDT", decimals=6),
    }


__all__ = ["ARBITRUM", "ChainConfig", "ETHEREUM", "REGISTRY", "common_tokens", "get_chain"]
