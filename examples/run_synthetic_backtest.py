"""Example: run a 200-block synthetic-mempool backtest.

Usage::

    python examples/run_synthetic_backtest.py
"""

from __future__ import annotations

from pathlib import Path

from mevlab.backtest.engine import BacktestEngine
from mevlab.core.types import Token
from mevlab.mempool.synthetic import SyntheticMempoolGenerator
from mevlab.pools.uniswap_v2 import UniswapV2Pool
from mevlab.reports import print_terminal_report, render_html_report
from mevlab.strategies import SandwichStrategy, TwoPoolArbitrageStrategy


def main() -> None:
    weth = Token(address="0x" + "11" * 20, symbol="WETH", decimals=18)
    usdc = Token(address="0x" + "22" * 20, symbol="USDC", decimals=6)

    pools = {
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

    strategies = [
        TwoPoolArbitrageStrategy(pairs=[("0xaaaa", "0xbbbb")], base_token=weth),
        SandwichStrategy(target_pools={"0xaaaa", "0xbbbb"}),
    ]

    snapshots = SyntheticMempoolGenerator(list(pools.values()), seed=1337).stream(n_blocks=200)
    result = BacktestEngine(pools=pools, strategies=strategies, snapshots=snapshots).run()

    print_terminal_report(result)

    out = Path("report.html")
    out.write_text(render_html_report(result), encoding="utf-8")
    print(f"\nFull HTML report written to {out.resolve()}")


if __name__ == "__main__":
    main()
