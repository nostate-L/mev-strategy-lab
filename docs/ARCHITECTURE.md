# Architecture

```
                ┌──────────────────────────┐
                │       UI (React)         │
                └─────────────┬────────────┘
                              │ /api/*
                ┌─────────────▼────────────┐
                │     API (FastAPI)        │
                │  routers: strategies,    │
                │  pools, simulate-block,  │
                │  backtests               │
                └─────────────┬────────────┘
                              │ in-process calls
            ┌─────────────────▼────────────────────┐
            │           mevlab engine              │
            │                                      │
            │  ┌──────────┐  ┌────────────────┐    │
            │  │  pools   │  │     core       │    │
            │  │ V2/V3/Cv │  │ types, numeric │    │
            │  └────┬─────┘  │ gas, chain     │    │
            │       │        └────────────────┘    │
            │       │                              │
            │  ┌────▼────┐  ┌──────────────────┐   │
            │  │ solver  │  │     mempool      │   │
            │  │ arb/sand│  │ replay/synthetic │   │
            │  └────┬────┘  └────────┬─────────┘   │
            │       │                │             │
            │  ┌────▼─────────┐  ┌───▼─────────┐   │
            │  │  strategies  │  │   builder   │   │
            │  │ arb/sand/jit │  │ pga/auction │   │
            │  │ backrun/liq │   └─────────────┘   │
            │  └────┬─────────┘                    │
            │       │                              │
            │  ┌────▼──────────┐                   │
            │  │   backtest    │                   │
            │  │ engine/ledger/│                   │
            │  │ metrics       │                   │
            │  └────┬──────────┘                   │
            │       │                              │
            │  ┌────▼────┐                         │
            │  │ reports │ html / json / term      │
            │  └─────────┘                         │
            └──────────────────────────────────────┘
```

## Data flow (per backtest)

1. **Inputs.** A list of pools, a list of strategy instances, an
   iterable of `MempoolSnapshot`s (one per simulated block), and a
   `BacktestConfig`.
2. **Loop.** For each snapshot:
   1. Each strategy is shown the snapshot (via `Strategy.observe`) and
      returns zero or more candidate `Bundle`s.
   2. The `BlockBuilder` ranks candidate bundles plus regular
      transactions in the snapshot using a Flashbots-style auction
      (highest *direct payment + effective tip* per gas wins),
      respecting bundle revert-protection rules.
   3. The block is "executed": pool state mutates, the ledger records
      P&L per strategy, and a `BlockResult` is appended.
3. **Output.** A `BacktestResult` containing the full per-block ledger
   and aggregate metrics (Sharpe, max drawdown, hit rate). Reports can
   be rendered to terminal, JSON, or HTML.

## Type contracts

- All core types are immutable frozen dataclasses with `slots=True`.
  Mutation only ever happens explicitly through `Pool.swap` and
  `Ledger.record_*`.
- `BasePool` (in `mevlab.pools.base`) is the abstract surface. Every
  concrete pool exposes `quote`, `swap`, `clone`, and `mid_price`.
- Numeric primitives in `mevlab.core.numeric` mirror Solidity exactly
  (`mul_div`, `mul_div_round_up`, `isqrt256`, Q64.96 encoding) so the
  V3 swap loop is byte-equivalent to the on-chain contract on the
  paths it covers.

## Determinism

Given the same `(pools, strategies, snapshots, config, RNG seed)` the
engine always produces bit-identical results. This is enforced by
keeping randomness inside explicit `random.Random(seed)` instances and
by not depending on dict iteration order.
