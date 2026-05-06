"""Smoke tests for the FastAPI app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_strategies_endpoint_returns_six_strategies():
    r = client.get("/strategies")
    assert r.status_code == 200
    body = r.json()
    names = {s["name"] for s in body}
    assert {"arb-2pool", "arb-tri", "sandwich", "jit", "backrun", "liquidation"} <= names


def test_pools_endpoint():
    r = client.get("/pools")
    assert r.status_code == 200
    pools = r.json()
    assert any(p["token0_symbol"] == "WETH" for p in pools)


def test_backtest_lifecycle():
    r = client.post("/backtests", json={"n_blocks": 5, "seed": 7, "notes": ["smoke"]})
    assert r.status_code == 200, r.text
    body = r.json()
    backtest_id = body["id"]
    assert body["n_blocks"] == 5

    r = client.get(f"/backtests/{backtest_id}")
    assert r.status_code == 200

    r = client.get(f"/backtests/{backtest_id}/report.html")
    assert r.status_code == 200
    assert b"</html>" in r.content

    r = client.get(f"/backtests/{backtest_id}/report.json")
    assert r.status_code == 200


def test_simulate_block():
    r = client.post("/simulate-block", json={"seed": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tx_count"] >= 0
