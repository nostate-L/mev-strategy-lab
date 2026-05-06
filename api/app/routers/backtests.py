"""Backtest endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from mevlab.backtest.engine import BacktestEngine
from mevlab.mempool.synthetic import SyntheticMempoolGenerator
from mevlab.reports import render_html_report, render_json_report
from pydantic import BaseModel, Field

from app.scenarios import demo_pools, demo_strategies
from app.state import BACKTESTS

router = APIRouter(prefix="/backtests", tags=["backtests"])


class RunBacktestRequest(BaseModel):
    n_blocks: int = Field(default=50, ge=1, le=2_000)
    seed: int = Field(default=42)
    notes: list[str] = Field(default_factory=list)


class StrategyMetricView(BaseModel):
    name: str
    total_pnl_eth: float
    mean_per_block_eth: float
    sharpe: float
    hit_rate: float
    max_drawdown_eth: float
    bundles_landed: int
    bundles_lost: int


class BacktestResponse(BaseModel):
    id: str
    created_at: str
    n_blocks: int
    strategies: list[StrategyMetricView]
    notes: list[str]


def _to_response(stored) -> BacktestResponse:
    metrics = []
    for name, m in stored.result.metrics.items():
        led = stored.result.ledger.get(name)
        metrics.append(
            StrategyMetricView(
                name=name,
                total_pnl_eth=m.total_pnl_wei / 1e18,
                mean_per_block_eth=m.mean_per_block_wei / 1e18,
                sharpe=m.sharpe,
                hit_rate=m.hit_rate,
                max_drawdown_eth=m.max_drawdown_wei / 1e18,
                bundles_landed=led.bundles_landed,
                bundles_lost=led.bundles_lost,
            )
        )
    return BacktestResponse(
        id=stored.id,
        created_at=stored.created_at.isoformat(),
        n_blocks=len(stored.result.blocks),
        strategies=metrics,
        notes=stored.notes,
    )


@router.post("", response_model=BacktestResponse)
def run_backtest(req: RunBacktestRequest) -> BacktestResponse:
    pools = demo_pools()
    gen = SyntheticMempoolGenerator(list(pools.values()), seed=req.seed)
    snaps = gen.stream(n_blocks=req.n_blocks)
    result = BacktestEngine(
        pools=pools,
        strategies=demo_strategies(),
        snapshots=snaps,
    ).run()
    stored = BACKTESTS.put(result, req.notes)
    return _to_response(stored)


@router.get("", response_model=list[BacktestResponse])
def list_backtests() -> list[BacktestResponse]:
    return [_to_response(s) for s in BACKTESTS.all()]


@router.get("/{backtest_id}", response_model=BacktestResponse)
def get_backtest(backtest_id: str) -> BacktestResponse:
    stored = BACKTESTS.get(backtest_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    return _to_response(stored)


@router.get("/{backtest_id}/report.html", response_class=Response)
def get_html_report(backtest_id: str) -> Response:
    stored = BACKTESTS.get(backtest_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    return Response(content=render_html_report(stored.result), media_type="text/html")


@router.get("/{backtest_id}/report.json", response_class=Response)
def get_json_report(backtest_id: str) -> Response:
    stored = BACKTESTS.get(backtest_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="backtest not found")
    return Response(content=render_json_report(stored.result), media_type="application/json")
