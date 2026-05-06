"""Tests for the sandwich-solver."""

from __future__ import annotations

from mevlab.core.types import SwapDirection
from mevlab.solver.sandwich import optimal_sandwich_amount


def test_sandwich_finds_profitable_attack(v2_pool_a):
    plan = optimal_sandwich_amount(
        v2_pool_a,
        direction=SwapDirection.ZERO_FOR_ONE,
        victim_amount_in=50 * 10**18,  # 50 WETH victim
        victim_min_amount_out=0,  # no slippage protection
        upper_bound=10**21,
    )
    assert plan is not None
    assert plan.expected_profit > 0
    assert plan.front_amount > 0


def test_sandwich_respects_slippage_constraint(v2_pool_a):
    # Quote victim's "natural" output, then set min_out just under it.
    natural = v2_pool_a.quote(SwapDirection.ZERO_FOR_ONE, 50 * 10**18)
    plan = optimal_sandwich_amount(
        v2_pool_a,
        direction=SwapDirection.ZERO_FOR_ONE,
        victim_amount_in=50 * 10**18,
        victim_min_amount_out=int(natural * 0.999),  # 0.1% slippage
        upper_bound=10**21,
    )
    assert plan is not None
    # Front amount must be small enough that the victim still gets >= min_out.
    sim = v2_pool_a.clone()
    sim.swap(SwapDirection.ZERO_FOR_ONE, plan.front_amount)
    victim_actual = sim.quote(SwapDirection.ZERO_FOR_ONE, 50 * 10**18)
    assert victim_actual >= int(natural * 0.999)


def test_sandwich_returns_none_when_victim_already_reverts(v2_pool_a):
    natural = v2_pool_a.quote(SwapDirection.ZERO_FOR_ONE, 50 * 10**18)
    plan = optimal_sandwich_amount(
        v2_pool_a,
        direction=SwapDirection.ZERO_FOR_ONE,
        victim_amount_in=50 * 10**18,
        victim_min_amount_out=natural * 2,  # impossible
        upper_bound=10**21,
    )
    assert plan is None
