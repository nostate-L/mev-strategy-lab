# Strategies

This document derives the optimisation problems each built-in strategy
solves. The solver implementations live in `mevlab/solver/` and
`mevlab/strategies/`.

## 1. Two-pool V2 arbitrage (closed form)

**Setup.** Two Uniswap-V2 pools `A` and `B` over the same token pair
`(X, Y)`, with reserves `(x_A, y_A)`, `(x_B, y_B)` and a multiplicative
fee `γ = 1 − fee`. We borrow a flash amount of `X`, swap on `A`,
swap the resulting `Y` back on `B`, and want the value of `X` we end
with to exceed what we borrowed.

**Closed form.** For a swap-`X→Y→X` cycle the optimal input is

```
δx* = (sqrt(γ_A · γ_B · x_A · y_A · x_B · y_B) − x_A · y_B) / (γ_A · y_B + γ_A · γ_B · y_A)
```

(or zero if the numerator is negative). The implementation tries both
directions (A→B and B→A) and returns the better one.

**Code.** [`mevlab/solver/arbitrage.py`](../engine/mevlab/solver/arbitrage.py) → `closed_form_two_pool_v2`.

## 2. Multi-hop arbitrage (ternary search)

For paths longer than two pools, or paths involving V3 / Curve pools,
profit is **unimodal** in the input amount. We exploit this with a
ternary search on `[1, upper_bound]`, then refine with a local grid
around the optimum (5 candidates) to escape the converged window.

**Code.** [`mevlab/solver/arbitrage.py`](../engine/mevlab/solver/arbitrage.py) → `optimal_input_ternary`.

## 3. Negative-cycle detection (Bellman-Ford)

We build a directed multigraph where each pool contributes two edges
(one per swap direction), weighted by the negative log of the marginal
rate after fee. A negative cycle in this graph corresponds to an
arbitrage. We restart Bellman-Ford from every node and walk
predecessors to extract disjoint cycles.

**Code.** [`mevlab/solver/arbitrage.py`](../engine/mevlab/solver/arbitrage.py) → `find_negative_cycles`.

## 4. Sandwich attack (constrained ternary search)

**Constraint.** The victim has signed a swap with a `min_amount_out`
guard. Any front-run that pushes the price too far causes the victim
transaction to revert, which kills the back-leg too.

**Procedure.**

1. Binary search the largest front-run amount that keeps the victim's
   trade above its slippage guard.
2. Ternary search profit on `[1, feasible_cap]`.
3. Refine on a local 4-candidate grid.

**Code.** [`mevlab/solver/sandwich.py`](../engine/mevlab/solver/sandwich.py) → `optimal_sandwich_amount`.

## 5. Just-in-time liquidity (V3)

Captures a fraction of the swap fees of a large pending V3 swap by
minting a tight LP position around the active tick, then burning it
immediately. With `L_active` already in range and `L_jit` injected:

```
captured = L_jit / (L_active + L_jit) · fee_in
```

**Code.** [`mevlab/strategies/jit.py`](../engine/mevlab/strategies/jit.py).

## 6. Oracle / whale backrun

Detects pending swaps that move a target pool's mid-price by more than
a threshold. Looks for a counter-pool quoting the same pair where the
post-swap price diverges enough to support an arb. Submits the bundle
`[victim_tx, first_swap, second_swap]` so the searcher's swaps execute
*after* the victim's price impact has already occurred.

**Code.** [`mevlab/strategies/backrun.py`](../engine/mevlab/strategies/backrun.py).

## 7. Liquidation

Given a `LiquidationCandidate(account, repay_amount, seize_amount,
bonus_bps, oracle_pool)`, the strategy proposes a single transaction
that repays a fraction of the unhealthy debt to seize the discounted
collateral. Net profit is `seize_amount · bonus_bps / 10000` minus gas.

**Code.** [`mevlab/strategies/liquidation.py`](../engine/mevlab/strategies/liquidation.py).
