"""FastAPI entrypoint.

The API surface is intentionally small but production-shaped:

    GET  /healthz               health check
    GET  /strategies            list built-in strategies
    POST /backtests             enqueue (or run inline) a backtest
    GET  /backtests/{id}        fetch a previous result
    GET  /backtests/{id}/report HTML report
    POST /simulate-block        simulate one block from a snapshot
    GET  /pools                 list configured pools (demo data)
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import backtests, pools, simulate, strategies

app = FastAPI(
    title="MEV Strategy Lab",
    version="0.1.0",
    description="REST API for the MEV Strategy Lab engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(strategies.router)
app.include_router(backtests.router)
app.include_router(simulate.router)
app.include_router(pools.router)


@app.get("/healthz", tags=["health"])
def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
