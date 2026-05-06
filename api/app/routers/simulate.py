"""Single-block simulation endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.scenarios import demo_pools, demo_strategies
from mevlab.backtest.engine import BacktestEngine
from mevlab.mempool.synthetic import SyntheticMempoolGenerator

router = APIRouter(prefix="/simulate-block", tags=["simulate"])


class SimulateBlockRequest(BaseModel):
    seed: int = Field(default=42)


class SimulatedBlockResponse(BaseModel):
    block_number: int
    base_fee_per_gas_wei: str
    tx_count: int
    gas_used: int
    fees_paid_eth: float
    coinbase_payment_eth: float


@router.post("", response_model=SimulatedBlockResponse)
def simulate_block(req: SimulateBlockRequest) -> SimulatedBlockResponse:
    pools = demo_pools()
    gen = SyntheticMempoolGenerator(list(pools.values()), seed=req.seed)
    snaps = gen.stream(n_blocks=1)
    result = BacktestEngine(
        pools=pools,
        strategies=demo_strategies(),
        snapshots=snaps,
    ).run()
    block = result.blocks[0]
    return SimulatedBlockResponse(
        block_number=block.header.number,
        base_fee_per_gas_wei=str(block.header.base_fee_per_gas),
        tx_count=len(block.results),
        gas_used=block.total_gas_used,
        fees_paid_eth=block.fees_paid_wei / 1e18,
        coinbase_payment_eth=block.coinbase_payment_wei / 1e18,
    )
