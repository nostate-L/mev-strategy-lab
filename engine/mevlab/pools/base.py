"""Abstract pool interface.

All pool implementations expose the same minimal API:

- ``quote(direction, amount_in)`` — return the expected output without committing.
- ``swap(direction, amount_in)`` — apply state mutation and return a :class:`SwapResult`.
- ``mid_price()``    — instantaneous mid-price (token1 per token0).

Strategies and the backtest engine treat all pools through this interface so
that a sandwich on Uniswap V2 and a sandwich on Uniswap V3 can share code.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from enum import StrEnum

from mevlab.core.types import Address, SwapDirection, Token


class PoolKind(StrEnum):
    UNISWAP_V2 = "uniswap_v2"
    UNISWAP_V3 = "uniswap_v3"
    CURVE_STABLESWAP = "curve_stableswap"


@dataclass(slots=True)
class SwapResult:
    """Result of executing a swap on a pool."""

    direction: SwapDirection
    amount_in: int
    amount_out: int
    fee_paid: int
    new_mid_price: float


class BasePool(abc.ABC):
    """Common interface for all pool kinds."""

    address: Address
    kind: PoolKind
    token0: Token
    token1: Token
    fee_bps: int  # 30 == 0.30%

    @abc.abstractmethod
    def quote(self, direction: SwapDirection, amount_in: int) -> int:
        """Return the output amount for an input ``amount_in`` without state changes."""

    @abc.abstractmethod
    def swap(self, direction: SwapDirection, amount_in: int) -> SwapResult:
        """Execute the swap and mutate internal state."""

    @abc.abstractmethod
    def mid_price(self) -> float:
        """Instantaneous mid-price expressed as ``token1`` per ``token0``."""

    @abc.abstractmethod
    def clone(self) -> BasePool:
        """Return a deep copy that can be mutated without touching ``self``."""

    def fee_decimal(self) -> float:
        """Fee as a fraction (e.g. 0.003 for 30bps)."""
        return self.fee_bps / 10_000


__all__ = ["BasePool", "PoolKind", "SwapResult"]
