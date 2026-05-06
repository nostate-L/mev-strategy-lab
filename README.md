# MEV Strategy Lab

A research-grade simulator and back-testing framework for searcher
strategies on EVM-style decentralised exchanges. The lab models pool
math, mempool flow, block-builder auctions, and per-strategy P&L
end-to-end so that a strategy can be evaluated *before* a single wei is
risked on-chain.

> **Not a trading bot.** The lab does not connect to mainnet, does not
> hold keys, and does not submit transactions. It is a deterministic
> simulator.

---

## Why

The published reference repo (`defi-dashboard`) is a small read-only
front end. This project goes the other direction: a heavy-on-algorithms
engine, plus a thin API and UI on top of it. The goal is to make the
*math* of MEV first-class, with code you can step through.

## Features

- **Pool math** — production-faithful implementations of:
  - Uniswap V2 (constant product `x·y = k`, 30 bps fee)
  - Uniswap V3 (concentrated liquidity, full tick traversal, Q64.96 fixed-point)
  - Curve StableSwap (Newton iteration on the StableSwap invariant)
- **Solvers** for searcher problems:
  - Closed-form 2-pool V2↔V2 arbitrage (tries both directions)
  - Ternary search over arbitrary multi-hop cycles
  - Bellman-Ford negative-cycle detection on log-price graphs
  - Constrained ternary search for sandwich sizing (respects victim slippage)
- **Strategies** — `arb-2pool`, `arb-tri`, `sandwich`, `jit`, `backrun`, `liquidation`
- **Mempool layer** — synthetic Poisson generator + JSONL replay, PGA & FCFS ordering
- **Block builder** — greedy bundle auction (à la Flashbots), revert protection, gas-limit accounting
- **Backtest engine** — event-driven, per-block ledger, Sharpe / drawdown / hit-rate metrics, HTML / JSON / terminal reports
- **API + UI** — FastAPI service exposing all of the above; React + Tailwind dashboard with Recharts

## Quickstart

```bash
# 1. install everything (creates a venv if you wish; otherwise uses current env)
make install

# 2. run the test suite
make test

# 3. start the API on :8000
make api

# 4. (in another shell) start the UI on :5173
make frontend
```

Or with Docker:

```bash
docker compose up --build
# API on http://localhost:8000  · UI on http://localhost:5173
```

## CLI

```bash
mevlab list-strategies
mevlab generate-fixture --out fixtures/demo.jsonl --blocks 200 --seed 42
mevlab run-backtest --fixture fixtures/demo.jsonl --html report.html
mevlab simulate-block --fixture fixtures/demo.jsonl --index 0
```

## Project layout

```
engine/      Pure-Python engine (mevlab package, all algorithms)
api/         FastAPI service wrapping the engine
frontend/    React + TS + Tailwind UI
docker/      Container build files
docs/        ARCHITECTURE / STRATEGIES / API
fixtures/    Generated mempool snapshots (gitignored)
examples/    Example scripts and notebooks
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the high-level data
flow and [docs/STRATEGIES.md](docs/STRATEGIES.md) for derivations of each
solver.

## License

MIT. See [LICENSE](LICENSE).
