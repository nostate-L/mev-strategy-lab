"""Pretty-print backtest results to a terminal using ``rich``."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from mevlab.backtest.engine import BacktestResult


def print_terminal_report(result: BacktestResult, console: Console | None = None) -> None:
    console = console or Console()
    table = Table(title="MEV Backtest — per-strategy summary")
    table.add_column("Strategy", style="bold cyan")
    table.add_column("Net P&L (ETH)", justify="right")
    table.add_column("Avg/block", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Hit", justify="right")
    table.add_column("Landed/Total", justify="right")

    for name, m in sorted(result.metrics.items(), key=lambda kv: -kv[1].total_pnl_wei):
        led = result.ledger.get(name)
        table.add_row(
            name,
            f"{m.total_pnl_wei / 1e18:+,.6f}",
            f"{m.mean_per_block_wei / 1e18:+.6f}",
            f"{m.sharpe:,.2f}",
            f"{m.max_drawdown_fraction:.2%}",
            f"{m.hit_rate:.1%}",
            f"{led.bundles_landed}/{led.bundles_landed + led.bundles_lost}",
        )

    console.print(table)
    console.print(
        f"[dim]{len(result.blocks)} blocks  ·  "
        f"total gas {sum(b.total_gas_used for b in result.blocks):,}  ·  "
        f"fees {sum(b.fees_paid_wei for b in result.blocks) / 1e18:.4f} ETH[/dim]"
    )


__all__ = ["print_terminal_report"]
