"""End-to-end test: run a tiny backtest with one strategy on synthetic data."""

from __future__ import annotations

from mevlab.backtest import BacktestEngine
from mevlab.mempool import SyntheticMempoolGenerator
from mevlab.reports import render_html_report, render_json_report
from mevlab.strategies import TwoPoolArbitrageStrategy


def test_backtest_runs_end_to_end(v2_pool_a, v2_pool_b, weth):
    pools = {v2_pool_a.address.lower(): v2_pool_a, v2_pool_b.address.lower(): v2_pool_b}
    gen = SyntheticMempoolGenerator(list(pools.values()), seed=7)
    snaps = gen.stream(n_blocks=20)

    engine = BacktestEngine(
        pools=pools,
        strategies=[
            TwoPoolArbitrageStrategy(
                pairs=[(v2_pool_a.address, v2_pool_b.address)],
                base_token=weth,
            )
        ],
        snapshots=snaps,
    )
    result = engine.run()
    assert len(result.blocks) == 20
    # We don't assert profitability — synthetic noise can move pool spreads
    # both ways — but the metrics dict must populate.
    assert result.metrics  # may be empty if zero opportunities — accept either


def test_reports_serialise(v2_pool_a, v2_pool_b, weth):
    pools = {v2_pool_a.address.lower(): v2_pool_a, v2_pool_b.address.lower(): v2_pool_b}
    gen = SyntheticMempoolGenerator(list(pools.values()), seed=11)
    snaps = gen.stream(n_blocks=5)
    engine = BacktestEngine(
        pools=pools,
        strategies=[
            TwoPoolArbitrageStrategy(
                pairs=[(v2_pool_a.address, v2_pool_b.address)],
                base_token=weth,
            )
        ],
        snapshots=snaps,
    )
    result = engine.run()
    html = render_html_report(result)
    assert "<table" in html and "</html>" in html
    j = render_json_report(result)
    assert "blocks" in j and "strategies" in j
