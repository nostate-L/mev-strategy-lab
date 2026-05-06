---
name: testing-mev-lab
description: End-to-end test the MEV Strategy Lab. Use whenever you need to verify the integrated stack (engine + FastAPI + React UI) actually runs, beyond unit tests.
---

# Testing MEV Strategy Lab

## Layout

- `engine/` — Python package `mevlab` (pool math, solvers, strategies, backtest engine, reports). 51 pytest tests under `engine/tests/`.
- `api/` — FastAPI service exposing `/healthz`, `/strategies`, `/pools`, `/backtests`, `/backtests/{id}`, `/backtests/{id}/report.html`, `/simulate-block`. 5 pytest tests under `api/tests/`.
- `frontend/` — Vite + React + TS, pages: Dashboard / Strategies / Backtests / Pools. Vite proxy in `frontend/vite.config.ts` rewrites `/api/*` → `http://localhost:8000/`.
- Demo fixtures live in `api/app/scenarios.py` (currently 2 V2 pools, no V3/Curve).

## Setup commands

```bash
# from repo root
pip install -e ./engine -e ./api
cd frontend && npm install --no-audit --no-fund
```

Or just `make install`.

## Unit tests + lint (cheap, do first)

```bash
cd engine && python -m pytest --timeout=15 -q   # expect 51 passed
cd api    && python -m pytest --timeout=15 -q   # expect 5 passed
cd engine && ruff check .                       # expect clean
cd api    && ruff check .                       # expect clean
cd frontend && npx tsc -b --noEmit              # expect clean
cd frontend && npm run build                    # expect clean Vite build
```

Or just `make test && make lint && make typecheck`.

`pytest --timeout=15` requires `pytest-timeout`, declared as a dev dep in both `engine/pyproject.toml` and `api/pyproject.toml`. If a future change drops `--timeout`, update both `pyproject.toml` files in lockstep or move to `[tool.pytest.ini_options].timeout`.

## End-to-end runtime test

Start both servers in **background** shells (do NOT block on them):

```bash
cd api      && uvicorn app.main:app --host 0.0.0.0 --port 8000 &  # shell A
cd frontend && npm run dev -- --host 0.0.0.0 &                    # shell B (Vite on :5173)
```

Smoke-test API directly first:

```bash
curl -s http://localhost:8000/healthz                        # expect {"status":"ok"}
curl -s http://localhost:8000/strategies | jq 'length'       # expect 6
curl -s http://localhost:8000/pools      | jq 'length'       # expect 2
```

### Primary GUI flow (record this)

Maximize the browser before recording:
```bash
sudo apt-get install -y wmctrl 2>/dev/null
wmctrl -r :ACTIVE: -b add,maximized_vert,maximized_horz
```

1. Open `http://localhost:5173` → Dashboard renders empty state until a backtest exists.
2. Click `Strategies` → expect exactly **6** entries: `arb-2pool`, `arb-tri`, `sandwich`, `jit` (V3 chip), `backrun`, `liquidation`.
3. Click `Pools` → expect 2 V2 pools (`0xaaaa`, `0xbbbb`) with mid-prices ~`2e-9` USDC/WETH-base-unit and 30 bps fee.
4. Click `Backtests` → form pre-fills `Blocks=200, Seed=42`. Set `Blocks=60` (faster, easier to read), click `Run backtest`. Expect a history row + a `BarChart` titled "P&L per strategy" within ~6–10 s.
5. Click `Dashboard` → expect 4 stat cards populated (Net P&L > 0 ETH, Blocks=60, Bundles landed=N/N, Strategies active >= 1) + per-strategy table.
6. Open `http://localhost:8000/backtests/{id}/report.html` (copy id from `GET /backtests` JSON or from the in-page link — the in-page link truncates the ID with `…`, so use the API list to get the full UUID). Expect dark-themed page with per-strategy table + SVG equity curve sparkline.

### Adversarial assertions

- Net P&L value must be a real number, not blank/`NaN`. With `seed=42` and the default 2-pool V2 fixture, `arb-2pool` lands ~39 ETH net over 60 blocks (Sharpe ~435K, 100 % hit rate). If it's 0 or NaN, something in the engine→API serialization or solver is broken.
- The chart on `/backtests` is **per-strategy**, not per-block. Don't expect 60 bars; expect 1 bar per landing strategy. With the default fixture only `arb-2pool` lands, so only 1 bar appears — that's expected.
- The dashboard is empty until at least one backtest exists; the empty-state link must navigate to `/backtests`.

## Common pitfalls / future-proofing

- Backtest history is stored in-process (`api/app/state.py`). If you restart uvicorn between running a backtest and fetching its report, the ID will 404. Re-run the backtest first.
- The Vite dev server proxies `/api/*` → `:8000`. If you hit the API directly via `localhost:8000/...` from the browser, CORS is permissive (set in `api/app/main.py`), so both work.
- The HTML report link in `frontend/src/pages/Backtests.tsx` truncates the UUID visually but the underlying `href` is full. If the visible truncation makes copy-paste tricky, fetch `GET /backtests` to grab the full ID.
- If sandwich/JIT/backrun/liquidation strategies always show 0 landed bundles, that may mean the demo fixture is too small to trigger them — not a bug. Adding V3 + Curve pools and a richer mempool to `api/app/scenarios.py` activates them.

## Devin secrets needed

- None for testing locally. (For pushing changes, the standard GitHub auth is provided by the platform.)
