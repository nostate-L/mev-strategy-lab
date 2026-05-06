# API reference

The FastAPI service is a thin wrapper over the engine. All endpoints
return JSON unless noted.

## `GET /healthz`

Liveness probe.

```json
{ "status": "ok" }
```

## `GET /strategies`

List built-in strategies.

```json
[
  { "name": "arb-2pool", "title": "2-Pool Arbitrage", "description": "..." },
  ...
]
```

## `GET /pools`

List demo pool fixtures with reserves and mid-price.

## `POST /backtests`

Run a synthetic-mempool backtest.

**Body:**

```json
{ "n_blocks": 200, "seed": 42, "notes": ["my run"] }
```

**Response:** a `BacktestResponse` with per-strategy metrics.

## `GET /backtests/{id}`

Fetch a previously-run backtest by id.

## `GET /backtests/{id}/report.html`

Returns a single-file dark-themed HTML report.

## `GET /backtests/{id}/report.json`

Returns the raw structured report (per-block series, per-strategy
metrics, ledger entries).

## `POST /simulate-block`

Simulate one block and return its summary (block number, base-fee, gas
used, fees / coinbase payment in ETH).

```json
{ "seed": 42 }
```
