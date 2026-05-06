"""Arbitrage solvers.

Three independent algorithms live here, in increasing order of generality:

1. :func:`closed_form_two_pool_v2` — exact optimal-trade-size formula for the
   special case of two Uniswap V2 (constant-product) pools sharing the same
   token pair.
2. :func:`optimal_input_ternary` — derivative-free ternary search that works
   for any two pool objects exposing the :class:`BasePool` interface, even
   when their swap functions aren't differentiable in closed form (V3, Curve,
   stableswap fallbacks, etc.).
3. :func:`find_negative_cycles` — Bellman-Ford on the log-price graph that
   surfaces *all* arbitrage opportunities across an arbitrary pool universe,
   including triangular and longer cycles.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log

import networkx as nx

from mevlab.core.types import SwapDirection, Token
from mevlab.pools.base import BasePool
from mevlab.pools.uniswap_v2 import FEE_DENOMINATOR, UniswapV2Pool


@dataclass(slots=True, frozen=True)
class ArbitrageOpportunity:
    """A profitable closed-loop arbitrage trade."""

    path: list[BasePool]
    directions: list[SwapDirection]
    optimal_input: int
    expected_profit: int
    input_token: Token


@dataclass(slots=True, frozen=True)
class NegativeCycle:
    """A negative-weight cycle in the log-price graph (i.e. arbitrage path)."""

    nodes: list[str]
    edges: list[tuple[str, str, str]]  # (from_token, to_token, pool_address)
    log_profit: float


# ---------------------------------------------------------------- 2-pool V2 --


def _solve_two_pool_oneway(
    pool_in: UniswapV2Pool,
    pool_out: UniswapV2Pool,
    base_token: Token,
) -> ArbitrageOpportunity | None:
    """Closed-form solution for one specific cycle direction.

    The cycle is ``base -> other`` on ``pool_in``, then ``other -> base`` on
    ``pool_out``. Returns ``None`` when there is no profit in this direction.
    """
    if pool_in.fee_bps != pool_out.fee_bps:
        return None

    def reserves(pool: UniswapV2Pool) -> tuple[int, int]:
        if pool.token0 == base_token:
            return pool.reserve0, pool.reserve1
        return pool.reserve1, pool.reserve0

    ra_b, ra_o = reserves(pool_in)
    rb_b, rb_o = reserves(pool_out)
    g = (FEE_DENOMINATOR - pool_in.fee_bps) / FEE_DENOMINATOR

    discriminant = ra_b * ra_o * rb_o * rb_b * g * g
    if discriminant <= 0:
        return None
    numerator = (discriminant**0.5) - ra_b * rb_o
    denominator = g * (rb_o + g * ra_o)
    if denominator <= 0 or numerator <= 0:
        return None
    optimal_input = int(numerator / denominator)
    if optimal_input <= 0:
        return None

    direction_a = (
        SwapDirection.ZERO_FOR_ONE if pool_in.token0 == base_token else SwapDirection.ONE_FOR_ZERO
    )
    direction_b = (
        SwapDirection.ONE_FOR_ZERO if pool_out.token0 == base_token else SwapDirection.ZERO_FOR_ONE
    )
    sim_a = pool_in.clone()
    sim_b = pool_out.clone()
    try:
        out_a = sim_a.swap(direction_a, optimal_input).amount_out
        out_b = sim_b.swap(direction_b, out_a).amount_out
    except ValueError:
        return None
    profit = out_b - optimal_input
    if profit <= 0:
        return None
    return ArbitrageOpportunity(
        path=[pool_in, pool_out],
        directions=[direction_a, direction_b],
        optimal_input=optimal_input,
        expected_profit=profit,
        input_token=base_token,
    )


def closed_form_two_pool_v2(
    pool_a: UniswapV2Pool,
    pool_b: UniswapV2Pool,
    base_token: Token,
) -> ArbitrageOpportunity | None:
    """Exact optimal-input formula for V2 ↔ V2 arbitrage.

    Tries *both* cycle directions (``a→b`` and ``b→a``) and returns the more
    profitable one — or ``None`` if neither is profitable.

    Derivation (omitting algebra): for two CP pools with reserves
    ``(Ra_b, Ra_o), (Rb_o, Rb_b)`` and per-pool fee multipliers ``g1, g2``
    (where ``g = (10000-fee_bps)/10000``), the profit-maximising trade size in
    units of ``base_token`` for the cycle ``pool_in → pool_out`` is

        x* = (sqrt(Ra_b * Ra_o * Rb_o * Rb_b * g1 * g2) - Ra_b * Rb_o)
              / (g1 * (Rb_o + g2 * Ra_o))

    rounded down.
    """
    if base_token not in (pool_a.token0, pool_a.token1):
        raise ValueError("base_token not present in pool_a")
    if base_token not in (pool_b.token0, pool_b.token1):
        raise ValueError("base_token not present in pool_b")

    candidates: list[ArbitrageOpportunity] = []
    forward = _solve_two_pool_oneway(pool_a, pool_b, base_token)
    if forward is not None:
        candidates.append(forward)
    backward = _solve_two_pool_oneway(pool_b, pool_a, base_token)
    if backward is not None:
        candidates.append(backward)
    if not candidates:
        return None
    return max(candidates, key=lambda o: o.expected_profit)


# -------------------------------------------------------- generic ternary --


def _profit_along_path(
    pools: list[BasePool], directions: list[SwapDirection], amount_in: int
) -> int:
    """Simulate ``amount_in`` through the path and return ``output - input``."""
    cursor = amount_in
    for pool, direction in zip(pools, directions, strict=True):
        clone = pool.clone()
        cursor = clone.swap(direction, cursor).amount_out
        if cursor <= 0:
            return -amount_in
    return cursor - amount_in


def optimal_input_ternary(
    pools: list[BasePool],
    directions: list[SwapDirection],
    base_token: Token,
    *,
    upper_bound: int,
    iterations: int = 80,
) -> ArbitrageOpportunity | None:
    """Ternary search the optimal input on an arbitrary closed-loop path.

    Profit as a function of input on a closed AMM loop is unimodal under mild
    regularity assumptions (it is the difference between a strictly concave
    output and a linear input), so ternary search converges to the maximum in
    O(log_1.5(N)) iterations.
    """
    if not pools or len(pools) != len(directions):
        raise ValueError("pools and directions must align and be non-empty")

    lo, hi = 1, max(upper_bound, 2)
    for _ in range(iterations):
        if hi - lo <= 4:
            break
        m1 = lo + (hi - lo) // 3
        m2 = hi - (hi - lo) // 3
        if _profit_along_path(pools, directions, m1) < _profit_along_path(pools, directions, m2):
            lo = m1
        else:
            hi = m2

    # Sample a small grid in the converged window for the final pick.
    candidates = sorted({lo, (lo + hi) // 2, hi, max(1, lo - 1), hi + 1})
    best = max(candidates, key=lambda x: _profit_along_path(pools, directions, x))
    profit = _profit_along_path(pools, directions, best)
    if profit <= 0:
        return None
    return ArbitrageOpportunity(
        path=pools,
        directions=directions,
        optimal_input=best,
        expected_profit=profit,
        input_token=base_token,
    )


# ----------------------------------------------------- Bellman-Ford cycles --


def _build_log_graph(pools: list[BasePool]) -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for pool in pools:
        # Mid-price is token1 per token0; log price ratio after one-unit fee.
        try:
            mid = pool.mid_price()
        except Exception:  # noqa: BLE001 - pool may be uninitialised
            continue
        if mid <= 0:
            continue
        fee_factor = 1 - pool.fee_decimal()
        # forward edge token0 -> token1 has weight -log(mid * fee)
        g.add_edge(
            pool.token0.address,
            pool.token1.address,
            key=pool.address,
            weight=-log(mid * fee_factor),
            pool=pool,
            direction=SwapDirection.ZERO_FOR_ONE,
        )
        g.add_edge(
            pool.token1.address,
            pool.token0.address,
            key=pool.address,
            weight=-log((1 / mid) * fee_factor),
            pool=pool,
            direction=SwapDirection.ONE_FOR_ZERO,
        )
    return g


def find_negative_cycles(pools: list[BasePool], *, max_cycles: int = 16) -> list[NegativeCycle]:
    """Return up to ``max_cycles`` negative-weight cycles in the log-price graph.

    A negative cycle in the ``-log(price * (1-fee))`` graph is exactly an
    arbitrage opportunity: traversing it leaves you with strictly more of the
    starting token than you began with, even after fees.
    """
    g = _build_log_graph(pools)
    if g.number_of_edges() == 0:
        return []

    cycles: list[NegativeCycle] = []
    seen: set[tuple[str, ...]] = set()

    nodes = list(g.nodes)
    if not nodes:
        return []
    nodes_set = set(nodes)

    # Standard Bellman-Ford with predecessor tracking, restarted from each source
    # so we can find disjoint cycles (not just one).
    for source in nodes:
        if len(cycles) >= max_cycles:
            break
        dist = dict.fromkeys(nodes, float("inf"))
        pred: dict[str, tuple[str, str] | None] = dict.fromkeys(nodes, None)
        dist[source] = 0.0

        for _ in range(len(nodes) - 1):
            updated = False
            for u, v, edge_key, data in g.edges(keys=True, data=True):
                w = data["weight"]
                if dist[u] + w < dist[v] - 1e-12:
                    dist[v] = dist[u] + w
                    pred[v] = (u, edge_key)
                    updated = True
            if not updated:
                break

        for u, v, _key, data in g.edges(keys=True, data=True):
            w = data["weight"]
            if dist[u] + w < dist[v] - 1e-12:
                # Walk predecessors |V| times to land inside the cycle.
                cur = v
                for _ in range(len(nodes)):
                    parent = pred[cur]
                    if parent is None:
                        break
                    cur = parent[0]
                if cur not in nodes_set:
                    continue

                # Extract the cycle by following predecessors until we revisit ``cur``.
                cycle_nodes: list[str] = [cur]
                cycle_edges: list[tuple[str, str, str]] = []
                node = cur
                visited_local: set[str] = {cur}
                for _ in range(len(nodes) + 1):
                    parent = pred[node]
                    if parent is None:
                        break
                    parent_node, edge_key = parent
                    cycle_edges.append((parent_node, node, edge_key))
                    cycle_nodes.append(parent_node)
                    if parent_node in visited_local:
                        # trim everything before the second visit
                        idx = cycle_nodes.index(parent_node)
                        cycle_nodes = cycle_nodes[idx:]
                        cycle_edges = cycle_edges[: len(cycle_nodes) - 1]
                        break
                    visited_local.add(parent_node)
                    node = parent_node

                cycle_nodes.reverse()
                cycle_edges.reverse()
                signature = tuple(sorted(cycle_nodes))
                if signature in seen:
                    continue
                seen.add(signature)

                log_profit = sum(g[u][v][k]["weight"] for u, v, k in cycle_edges)
                if log_profit < 0:
                    cycles.append(
                        NegativeCycle(
                            nodes=cycle_nodes,
                            edges=cycle_edges,
                            log_profit=log_profit,
                        )
                    )
                if len(cycles) >= max_cycles:
                    break

    return cycles


__all__ = [
    "ArbitrageOpportunity",
    "NegativeCycle",
    "closed_form_two_pool_v2",
    "find_negative_cycles",
    "optimal_input_ternary",
]
