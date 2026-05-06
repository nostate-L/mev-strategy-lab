"""Backtest metrics: Sharpe, drawdown, gas-adjusted return, hit rate."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Metrics:
    """Numerical summary of a single strategy's backtest performance."""

    total_pnl_wei: int
    mean_per_block_wei: float
    stddev_per_block_wei: float
    sharpe: float
    max_drawdown_wei: int
    max_drawdown_fraction: float
    hit_rate: float
    n_blocks: int

    @classmethod
    def from_block_series(cls, series: list[int], hit_rate: float) -> Metrics:
        if not series:
            return cls(0, 0.0, 0.0, 0.0, 0, 0.0, hit_rate, 0)
        mean = sum(series) / len(series)
        variance = sum((x - mean) ** 2 for x in series) / max(1, len(series) - 1)
        stddev = math.sqrt(variance)
        sharpe = mean / stddev if stddev > 0 else 0.0
        # Sharpe is unitless; we annualise by sqrt(blocks-per-year). 12-second
        # blocks = ~2.6M blocks/year. Callers can pass their own scale if needed.
        sharpe_annualised = sharpe * math.sqrt(2_628_000)

        # Drawdown on a per-block cumulative-sum series.
        peak = 0
        cum = 0
        max_dd = 0
        max_dd_peak = 1  # avoid div0
        for v in series:
            cum += v
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
                max_dd_peak = peak if peak > 0 else 1
        return cls(
            total_pnl_wei=sum(series),
            mean_per_block_wei=mean,
            stddev_per_block_wei=stddev,
            sharpe=sharpe_annualised,
            max_drawdown_wei=max_dd,
            max_drawdown_fraction=max_dd / max_dd_peak,
            hit_rate=hit_rate,
            n_blocks=len(series),
        )


__all__ = ["Metrics"]
