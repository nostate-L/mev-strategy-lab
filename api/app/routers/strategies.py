"""Strategy listing endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/strategies", tags=["strategies"])


class StrategyDescriptor(BaseModel):
    name: str
    title: str
    description: str
    requires_v3: bool = False
    builtin: bool = True


_REGISTRY = [
    StrategyDescriptor(
        name="arb-2pool",
        title="2-Pool Arbitrage",
        description=(
            "Closed-form optimal trade size between two Uniswap-V2 pools "
            "with the same token pair. O(1) compute per opportunity."
        ),
    ),
    StrategyDescriptor(
        name="arb-tri",
        title="Triangular Arbitrage",
        description=(
            "Three-leg cycle (e.g. ETH→USDC→WBTC→ETH) sized via ternary search."
        ),
    ),
    StrategyDescriptor(
        name="sandwich",
        title="Sandwich Attack",
        description=(
            "Optimal front-run amount given a victim swap, respecting the "
            "victim's slippage guard."
        ),
    ),
    StrategyDescriptor(
        name="jit",
        title="Just-In-Time Liquidity",
        description=(
            "Mint a tight V3 LP position immediately before a large pending swap "
            "and burn it immediately after."
        ),
        requires_v3=True,
    ),
    StrategyDescriptor(
        name="backrun",
        title="Oracle / Whale Backrunner",
        description=(
            "Detects large pending swaps that move pool prices and arbitrages "
            "against an unaffected counter-pool right after."
        ),
    ),
    StrategyDescriptor(
        name="liquidation",
        title="Lending Liquidation",
        description=(
            "Repays a fraction of a sub-1.0 health-factor account's debt to "
            "seize collateral at the protocol's bonus discount."
        ),
    ),
]


@router.get("", response_model=list[StrategyDescriptor])
def list_strategies() -> list[StrategyDescriptor]:
    return _REGISTRY
