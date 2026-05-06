"""JSON report exporter for backtest results."""

from __future__ import annotations

import json

from mevlab.backtest.engine import BacktestResult


def render_json_report(result: BacktestResult) -> str:
    """Return a JSON string capturing every metric and per-block series."""
    payload = {
        "strategies": {
            name: {
                "total_pnl_wei": str(m.total_pnl_wei),
                "mean_per_block_wei": m.mean_per_block_wei,
                "stddev_per_block_wei": m.stddev_per_block_wei,
                "sharpe": m.sharpe,
                "max_drawdown_wei": str(m.max_drawdown_wei),
                "max_drawdown_fraction": m.max_drawdown_fraction,
                "hit_rate": m.hit_rate,
                "n_blocks": m.n_blocks,
            }
            for name, m in result.metrics.items()
        },
        "ledger": {
            name: {
                "realised_profit_wei": str(p.realised_profit_wei),
                "gas_paid_wei": str(p.gas_paid_wei),
                "bundles_landed": p.bundles_landed,
                "bundles_lost": p.bundles_lost,
                "block_profits_wei": [str(x) for x in p.block_profits_wei],
            }
            for name, p in result.ledger.all().items()
        },
        "blocks": [
            {
                "number": b.header.number,
                "base_fee_per_gas": str(b.header.base_fee_per_gas),
                "gas_used": b.total_gas_used,
                "fees_paid_wei": str(b.fees_paid_wei),
                "coinbase_payment_wei": str(b.coinbase_payment_wei),
            }
            for b in result.blocks
        ],
    }
    return json.dumps(payload, indent=2)


__all__ = ["render_json_report"]
