"""Per-strategy P&L ledger."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass(slots=True)
class StrategyPnL:
    """Aggregated P&L for one strategy over the backtest window."""

    name: str
    realised_profit_wei: int = 0
    gas_paid_wei: int = 0
    bundles_landed: int = 0
    bundles_lost: int = 0
    block_profits_wei: list[int] = field(default_factory=list)

    @property
    def net_profit_wei(self) -> int:
        return self.realised_profit_wei - self.gas_paid_wei

    @property
    def hit_rate(self) -> float:
        total = self.bundles_landed + self.bundles_lost
        return self.bundles_landed / total if total else 0.0


class Ledger:
    """Mutable ledger used by the backtest engine to attribute P&L."""

    def __init__(self) -> None:
        self._by_strategy: dict[str, StrategyPnL] = {}

    def get(self, name: str) -> StrategyPnL:
        if name not in self._by_strategy:
            self._by_strategy[name] = StrategyPnL(name=name)
        return self._by_strategy[name]

    def record_landed(self, name: str, *, profit_wei: int, gas_wei: int) -> None:
        entry = self.get(name)
        entry.realised_profit_wei += profit_wei
        entry.gas_paid_wei += gas_wei
        entry.bundles_landed += 1
        entry.block_profits_wei.append(profit_wei - gas_wei)

    def record_lost(self, name: str) -> None:
        self.get(name).bundles_lost += 1

    def all(self) -> dict[str, StrategyPnL]:
        return dict(self._by_strategy)

    def total_net_profit_wei(self) -> int:
        return sum(p.net_profit_wei for p in self._by_strategy.values())

    def to_block_series(self) -> dict[str, list[int]]:
        """Return per-strategy time series of net P&L per block."""
        return {name: list(p.block_profits_wei) for name, p in self._by_strategy.items()}

    def merge(self, other: Ledger) -> None:
        for name, pnl in other._by_strategy.items():
            local = self.get(name)
            local.realised_profit_wei += pnl.realised_profit_wei
            local.gas_paid_wei += pnl.gas_paid_wei
            local.bundles_landed += pnl.bundles_landed
            local.bundles_lost += pnl.bundles_lost
            local.block_profits_wei.extend(pnl.block_profits_wei)


def aggregate(ledgers: list[Ledger]) -> Ledger:
    out = Ledger()
    counts: dict[str, int] = defaultdict(int)
    for led in ledgers:
        out.merge(led)
        for name in led.all():
            counts[name] += 1
    return out


__all__ = ["Ledger", "StrategyPnL", "aggregate"]
