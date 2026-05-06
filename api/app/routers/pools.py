"""Pool listing endpoint (demo data only)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.scenarios import demo_pools

router = APIRouter(prefix="/pools", tags=["pools"])


class PoolDescriptor(BaseModel):
    address: str
    kind: str
    token0_symbol: str
    token1_symbol: str
    reserve0: str
    reserve1: str
    mid_price: float
    fee_bps: int


@router.get("", response_model=list[PoolDescriptor])
def list_pools() -> list[PoolDescriptor]:
    out: list[PoolDescriptor] = []
    for pool in demo_pools().values():
        out.append(
            PoolDescriptor(
                address=pool.address,
                kind=pool.kind.value,
                token0_symbol=pool.token0.symbol,
                token1_symbol=pool.token1.symbol,
                reserve0=str(pool.reserve0),
                reserve1=str(pool.reserve1),
                mid_price=pool.mid_price(),
                fee_bps=pool.fee_bps,
            )
        )
    return out
