import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api, BacktestResponse } from "../api";

export default function Backtests() {
  const [history, setHistory] = useState<BacktestResponse[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState(200);
  const [seed, setSeed] = useState(42);
  const [selected, setSelected] = useState<BacktestResponse | null>(null);

  const refresh = () =>
    api
      .listBacktests()
      .then((list) => {
        setHistory(list.slice().reverse());
        if (!selected && list.length) setSelected(list[list.length - 1]);
      })
      .catch((e) => setError((e as Error).message));

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runBacktest = async () => {
    setRunning(true);
    setError(null);
    try {
      const r = await api.runBacktest({ n_blocks: n, seed, notes: ["ui"] });
      setSelected(r);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  const chartData = selected
    ? selected.strategies.map((s) => ({
        strategy: s.name,
        pnl_eth: parseFloat(s.total_pnl_eth.toFixed(6)),
        sharpe: parseFloat(s.sharpe.toFixed(2)),
      }))
    : [];

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">Backtests</h1>
        <p className="text-slate-400 text-sm">
          Run a synthetic-mempool backtest against the bundled strategies. All traffic and pools
          are deterministic given the seed.
        </p>
      </header>

      <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 flex flex-wrap items-end gap-4">
        <label className="flex flex-col text-xs uppercase tracking-wider text-slate-400">
          Blocks
          <input
            type="number"
            min={1}
            max={2000}
            value={n}
            onChange={(e) => setN(parseInt(e.target.value, 10) || 1)}
            className="mt-1 w-32 rounded-md bg-slate-950 border border-slate-700 px-2 py-1 text-sm"
          />
        </label>
        <label className="flex flex-col text-xs uppercase tracking-wider text-slate-400">
          Seed
          <input
            type="number"
            value={seed}
            onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
            className="mt-1 w-32 rounded-md bg-slate-950 border border-slate-700 px-2 py-1 text-sm"
          />
        </label>
        <button
          onClick={runBacktest}
          disabled={running}
          className="rounded-md bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-medium px-4 py-2 text-sm"
        >
          {running ? "Running…" : "Run backtest"}
        </button>
        {error && <span className="text-rose-400 text-sm">{error}</span>}
      </section>

      <section className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1 rounded-lg border border-slate-800 bg-slate-900/40 max-h-[420px] overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-900 text-slate-400">
              <tr>
                <th className="text-left px-3 py-2 font-medium">When</th>
                <th className="text-right px-3 py-2 font-medium">Blocks</th>
              </tr>
            </thead>
            <tbody>
              {history.map((r) => (
                <tr
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className={`cursor-pointer border-t border-slate-800/60 ${
                    selected?.id === r.id ? "bg-slate-800/60" : "hover:bg-slate-800/30"
                  }`}
                >
                  <td className="px-3 py-2 font-mono text-xs text-slate-400">
                    {new Date(r.created_at).toLocaleString()}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{r.n_blocks}</td>
                </tr>
              ))}
              {history.length === 0 && (
                <tr>
                  <td colSpan={2} className="px-3 py-6 text-center text-slate-500 text-sm">
                    No backtests yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="lg:col-span-2 rounded-lg border border-slate-800 bg-slate-900/40 p-4 min-h-[420px]">
          {selected ? (
            <>
              <div className="flex items-baseline justify-between">
                <h2 className="text-lg font-semibold">P&L per strategy</h2>
                <a
                  href={`/api/backtests/${selected.id}/report.html`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-cyan-300 underline"
                >
                  Open HTML report
                </a>
              </div>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="strategy" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b" }}
                  />
                  <Legend />
                  <Bar dataKey="pnl_eth" fill="#22d3ee" name="P&L (ETH)" />
                </BarChart>
              </ResponsiveContainer>
            </>
          ) : (
            <p className="text-slate-500 text-sm">Select a backtest to see metrics.</p>
          )}
        </div>
      </section>
    </div>
  );
}
