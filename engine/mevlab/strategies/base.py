"""Searcher strategy interface.

Every strategy implements ``observe(context) -> StrategyOutput``: given the
state of the world at the start of a block (mempool, pools, gas), it returns
zero or more bundles to submit to the builder. Bundles are typed with a
``label`` so the backtest engine can attribute P&L per strategy.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

from mevlab.builder.builder import Bundle
from mevlab.core.types import BlockHeader, MempoolSnapshot
from mevlab.pools.base import BasePool


@dataclass(slots=True)
class StrategyContext:
    """Read-only context handed to a strategy each block."""

    mempool: MempoolSnapshot
    next_header: BlockHeader
    pools: dict[str, BasePool]  # address -> pool
    searcher_capital_wei: int = 10**21  # 1k WETH equivalent default
    gas_token_per_eth: int = 10**18

    def pool(self, address: str) -> BasePool | None:
        return self.pools.get(address.lower())


@dataclass(slots=True)
class StrategyOutput:
    """Bundles to submit + diagnostic notes."""

    bundles: list[Bundle] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class Strategy(abc.ABC):
    """Abstract base class for searcher strategies."""

    name: str = "base"

    @abc.abstractmethod
    def observe(self, ctx: StrategyContext) -> StrategyOutput:
        """Inspect the world and emit zero or more bundles."""

    # Convenience for subclass introspection.
    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<Strategy {self.name}>"


__all__ = ["Strategy", "StrategyContext", "StrategyOutput"]
