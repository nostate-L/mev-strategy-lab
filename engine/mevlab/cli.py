"""Typer-based CLI for the MEV Strategy Lab.

Commands:

    mevlab list-strategies       List built-in strategies.
    mevlab generate-fixture      Generate a synthetic mempool JSONL.
    mevlab run-backtest          Run a built-in scenario and print results.
    mevlab simulate-block        Simulate a single block from a snapshot.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from mevlab.backtest import BacktestEngine
from mevlab.core.types import Token
from mevlab.mempool import MempoolReplayer, SyntheticMempoolGenerator
from mevlab.pools.uniswap_v2 import UniswapV2Pool
from mevlab.reports import (
    print_terminal_report,
    render_html_report,
    render_json_report,
)
from mevlab.strategies import SandwichStrategy, TwoPoolArbitrageStrategy

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()


def _example_pools() -> dict[str, UniswapV2Pool]:
    weth = Token(address="0x" + "11" * 20, symbol="WETH", decimals=18)
    usdc = Token(address="0x" + "22" * 20, symbol="USDC", decimals=6)
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


@app.command("list-strategies")
def list_strategies() -> None:
    """List all built-in strategies."""
    rows = [
        ("arb-2pool", "Closed-form 2-pool V2 arbitrage"),
        ("arb-tri", "Three-leg triangular arbitrage with ternary search"),
        ("sandwich", "Optimal sandwich attack on configured pools"),
        ("jit", "Just-in-time concentrated liquidity (V3)"),
        ("backrun", "Backrun large swaps with cross-pool arbitrage"),
        ("liquidation", "Lending-protocol liquidation"),
    ]
    for name, desc in rows:
        console.print(f"[cyan]{name:>14}[/cyan]  {desc}")


@app.command("generate-fixture")
def generate_fixture(
    out: Path = typer.Argument(..., help="Path to write JSONL fixture to."),
    blocks: int = typer.Option(50, help="Number of blocks of mempool data."),
    seed: int = typer.Option(42),
) -> None:
    """Generate a synthetic mempool JSONL fixture from sample pools."""
    pools = list(_example_pools().values())
    gen = SyntheticMempoolGenerator(pools, seed=seed)
    snaps = gen.stream(n_blocks=blocks)
    MempoolReplayer.from_iterable(snaps, out)
    console.print(f"[green]Wrote {len(snaps)} snapshots to {out}[/green]")


@app.command("run-backtest")
def run_backtest(
    fixture: Path = typer.Argument(
        ..., help="Path to a JSONL mempool fixture (see generate-fixture)."
    ),
    html_out: Path = typer.Option(None, help="Optional HTML report destination."),
    json_out: Path = typer.Option(None, help="Optional JSON report destination."),
) -> None:
    """Run the bundled scenario against ``fixture`` and print a report."""
    pools = _example_pools()
    weth = next(iter(pools.values())).token0

    strategies = [
        TwoPoolArbitrageStrategy(
            pairs=[("0xaaaa", "0xbbbb")],
            base_token=weth,
        ),
        SandwichStrategy(target_pools={"0xaaaa", "0xbbbb"}),
    ]
    snapshots = list(MempoolReplayer(fixture))
    result = BacktestEngine(pools=pools, strategies=strategies, snapshots=snapshots).run()
    print_terminal_report(result, console)

    if html_out is not None:
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(render_html_report(result))
        console.print(f"[green]HTML report -> {html_out}[/green]")
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(render_json_report(result))
        console.print(f"[green]JSON report -> {json_out}[/green]")


@app.command("simulate-block")
def simulate_block(
    fixture: Path = typer.Argument(...),
    index: int = typer.Option(0, help="Snapshot index to replay."),
) -> None:
    """Replay a single mempool snapshot and dump the produced block as JSON."""
    pools = _example_pools()
    weth = next(iter(pools.values())).token0
    strategies = [
        TwoPoolArbitrageStrategy(
            pairs=[("0xaaaa", "0xbbbb")],
            base_token=weth,
        )
    ]
    snaps = MempoolReplayer(fixture).head(index + 1)
    if index >= len(snaps):
        raise typer.BadParameter(f"index {index} out of range (have {len(snaps)})")
    result = BacktestEngine(pools=pools, strategies=strategies, snapshots=[snaps[index]]).run()
    block = result.blocks[0]
    payload = {
        "block_number": block.header.number,
        "base_fee": block.header.base_fee_per_gas,
        "tx_count": len(block.results),
        "gas_used": block.total_gas_used,
        "fees_wei": str(block.fees_paid_wei),
        "coinbase_payment_wei": str(block.coinbase_payment_wei),
    }
    console.print_json(json.dumps(payload))


if __name__ == "__main__":  # pragma: no cover
    app()
