// Thin wrapper around the FastAPI backend.

const BASE = "/api";

export interface StrategyDescriptor {
  name: string;
  title: string;
  description: string;
  requires_v3?: boolean;
  builtin?: boolean;
}

export interface PoolDescriptor {
  address: string;
  kind: string;
  token0_symbol: string;
  token1_symbol: string;
  reserve0: string;
  reserve1: string;
  mid_price: number;
  fee_bps: number;
}

export interface StrategyMetricView {
  name: string;
  total_pnl_eth: number;
  mean_per_block_eth: number;
  sharpe: number;
  hit_rate: number;
  max_drawdown_eth: number;
  bundles_landed: number;
  bundles_lost: number;
}

export interface BacktestResponse {
  id: string;
  created_at: string;
  n_blocks: number;
  strategies: StrategyMetricView[];
  notes: string[];
}

export interface SimulatedBlockResponse {
  block_number: number;
  base_fee_per_gas_wei: string;
  tx_count: number;
  gas_used: number;
  fees_paid_eth: number;
  coinbase_payment_eth: number;
}

async function getJSON<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`);
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<{ status: string }>("/healthz"),
  strategies: () => getJSON<StrategyDescriptor[]>("/strategies"),
  pools: () => getJSON<PoolDescriptor[]>("/pools"),
  listBacktests: () => getJSON<BacktestResponse[]>("/backtests"),
  getBacktest: (id: string) => getJSON<BacktestResponse>(`/backtests/${id}`),
  runBacktest: (req: { n_blocks: number; seed: number; notes: string[] }) =>
    postJSON<BacktestResponse>("/backtests", req),
  simulateBlock: (req: { seed: number }) =>
    postJSON<SimulatedBlockResponse>("/simulate-block", req),
};
