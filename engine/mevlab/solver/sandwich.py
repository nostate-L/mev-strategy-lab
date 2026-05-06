"""Optimal sandwich-attack sizing.

A sandwich consists of three transactions on the same pool:

    1. ``front-run``  — searcher swaps ``a`` of ``base`` into the pool.
    2. ``victim``     — victim swaps ``v`` (already in mempool, immutable).
    3. ``back-run``   — searcher reverses, swapping the resulting ``other``
       token amount back to ``base``.

The searcher's profit is the back-run output minus ``a`` and minus gas cost.
The two binding constraints are:

    a)  the victim's slippage protection (``min_amount_out_v``) must still
        clear after the front-run pushes the price.
    b)  the back-run cannot withdraw more than the pool now contains; this
        is automatically respected by the AMM math.

Because profit(a) is unimodal on the feasible region, we run a constrained
ternary search; we additionally derive an upper bound from constraint (a) so
the search interval is tight.
"""

from __future__ import annotations

from dataclasses import dataclass

from mevlab.core.types import SwapDirection
from mevlab.pools.base import BasePool


@dataclass(slots=True, frozen=True)
class SandwichPlan:
    """Result of solving for an optimal sandwich."""

    front_amount: int
    expected_profit: int
    victim_output_after: int
    new_mid_price_after_front: float
    new_mid_price_after_victim: float
    new_mid_price_after_back: float


def _simulate(
    pool: BasePool,
    front: int,
    victim: int,
    direction: SwapDirection,
) -> tuple[int, int, float, float, float]:
    """Return ``(profit, victim_out, p_after_front, p_after_victim, p_after_back)``.

    ``front`` may be 0 — in that case we skip the front and back swaps and
    return the victim's natural output.
    """
    sim = pool.clone()
    intermediate_amount = 0
    if front > 0:
        front_swap = sim.swap(direction, front)
        intermediate_amount = front_swap.amount_out
    p_after_front = sim.mid_price()
    victim_swap = sim.swap(direction, victim)
    p_after_victim = sim.mid_price()
    reverse_dir = (
        SwapDirection.ONE_FOR_ZERO
        if direction == SwapDirection.ZERO_FOR_ONE
        else SwapDirection.ZERO_FOR_ONE
    )
    back_amount_out = 0
    if intermediate_amount > 0:
        back_swap = sim.swap(reverse_dir, intermediate_amount)
        back_amount_out = back_swap.amount_out
    p_after_back = sim.mid_price()
    profit = back_amount_out - front
    return profit, victim_swap.amount_out, p_after_front, p_after_victim, p_after_back


def optimal_sandwich_amount(
    pool: BasePool,
    *,
    direction: SwapDirection,
    victim_amount_in: int,
    victim_min_amount_out: int,
    upper_bound: int,
    iterations: int = 64,
) -> SandwichPlan | None:
    """Solve for the optimal front-run amount given a victim trade in mempool.

    Parameters
    ----------
    pool: pool the victim is trading on (will not be mutated).
    direction: direction of the victim's trade.
    victim_amount_in: input amount the victim has signed.
    victim_min_amount_out: victim's minimum-acceptable output (slippage guard).
    upper_bound: hard cap on searcher capital (e.g. flashloan ceiling).
    iterations: ternary search iterations; 64 gives sub-wei precision on
        anything below 1e18 base units.
    """
    if victim_amount_in <= 0:
        raise ValueError("victim_amount_in must be positive")
    if upper_bound <= 0:
        return None

    # First check: even with a zero front-run, does victim trade through?
    base_profit, base_victim_out, *_ = _simulate(pool, 0, victim_amount_in, direction)
    if base_victim_out < victim_min_amount_out:
        # Victim already reverts; no sandwich opportunity.
        return None

    def feasible(a: int) -> bool:
        if a <= 0:
            return True
        _, victim_out, *_ = _simulate(pool, a, victim_amount_in, direction)
        return victim_out >= victim_min_amount_out

    def profit(a: int) -> int:
        if a <= 0:
            return 0
        if not feasible(a):
            return -10**30  # large negative sentinel
        p, *_ = _simulate(pool, a, victim_amount_in, direction)
        return p

    # Binary-search the largest feasible front amount (it must satisfy
    # constraint (a)). This becomes the upper bound for the ternary search.
    lo_feasible, hi_feasible = 0, upper_bound
    while lo_feasible + 1 < hi_feasible:
        mid = (lo_feasible + hi_feasible) // 2
        if feasible(mid):
            lo_feasible = mid
        else:
            hi_feasible = mid - 1
    feasible_cap = max(1, lo_feasible)

    lo, hi = 1, feasible_cap
    for _ in range(iterations):
        if hi - lo <= 4:
            break
        m1 = lo + (hi - lo) // 3
        m2 = hi - (hi - lo) // 3
        if profit(m1) < profit(m2):
            lo = m1
        else:
            hi = m2

    candidates = sorted({lo, (lo + hi) // 2, hi, max(1, lo - 1)})
    best = max(candidates, key=profit)
    p, victim_out, p_front, p_victim, p_back = _simulate(
        pool, best, victim_amount_in, direction
    )
    if p <= 0:
        return None
    return SandwichPlan(
        front_amount=best,
        expected_profit=p,
        victim_output_after=victim_out,
        new_mid_price_after_front=p_front,
        new_mid_price_after_victim=p_victim,
        new_mid_price_after_back=p_back,
    )


__all__ = ["SandwichPlan", "optimal_sandwich_amount"]
