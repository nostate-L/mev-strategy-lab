import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, BacktestResponse } from "../api";
import StatCard from "../components/StatCard";

export default function Dashboard() {
  const [latest, setLatest] = useState<BacktestResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listBacktests();
      setLatest(list[list.length - 1] ?? null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const runQuickBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.runBacktest({ n_blocks: 50, seed: Date.now() & 0xffff, notes: ["dashboard quick run"] });
      setLatest(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const totalPnl = latest?.strategies.reduce((acc, s) => acc + s.total_pnl_eth, 0) ?? 0;
  const totalLanded =
    latest?.strategies.reduce((acc, s) => acc + s.bundles_landed, 0) ?? 0;
  const totalAttempts =
    latest?.strategies.reduce((acc, s) => acc + s.bundles_landed + s.bundles_lost, 0) ?? 0;

  return (
    <div className="space-y-8">
      <section>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">Dashboard</h1>
            <p className="text-slate-400 text-sm">Latest synthetic backtest summary.</p>
          </div>
          <button
            onClick={runQuickBacktest}
            disabled={loading}
            className="rounded-md bg-cyan-500 hover:bg-cyan-400 disabled:opacity-50 text-slate-950 font-medium px-4 py-2 text-sm"
          >
            {loading ? "Running…" : "Run quick backtest"}
          </button>
        </div>
        {error && <p className="mt-4 text-rose-400 text-sm">{error}</p>}
      </section>

      {latest ? (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Net P&L"
            value={`${totalPnl.toFixed(6)} ETH`}
            tone={totalPnl >= 0 ? "positive" : "negative"}
          />
          <StatCard title="Blocks" value={String(latest.n_blocks)} />
          <StatCard
            title="Bundles landed"
            value={`${totalLanded}/${totalAttempts}`}
            subtitle={`${((totalLanded / Math.max(1, totalAttempts)) * 100).toFixed(1)}% hit rate`}
          />
          <StatCard
            title="Strategies active"
            value={String(latest.strategies.length)}
            subtitle="see Strategies tab"
          />
        </section>
      ) : (
        <p className="text-slate-400">
          No backtests yet. <Link className="text-cyan-300 underline" to="/backtests">Run one</Link> to populate the dashboard.
        </p>
      )}

      {latest && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Per-strategy</h2>
          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Strategy</th>
                  <th className="text-right px-4 py-2 font-medium">Net P&L (ETH)</th>
                  <th className="text-right px-4 py-2 font-medium">Sharpe</th>
                  <th className="text-right px-4 py-2 font-medium">Hit rate</th>
                  <th className="text-right px-4 py-2 font-medium">Landed/Total</th>
                </tr>
              </thead>
              <tbody>
                {latest.strategies.map((s) => (
                  <tr key={s.name} className="border-t border-slate-800/60">
                    <td className="px-4 py-2 font-mono text-cyan-300">{s.name}</td>
                    <td
                      className={`px-4 py-2 text-right tabular-nums ${
                        s.total_pnl_eth >= 0 ? "text-emerald-400" : "text-rose-400"
                      }`}
                    >
                      {s.total_pnl_eth.toFixed(6)}
                    </td>
                    <td className="px-4 py-2 text-right tabular-nums">{s.sharpe.toFixed(2)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{(s.hit_rate * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2 text-right tabular-nums">
                      {s.bundles_landed}/{s.bundles_landed + s.bundles_lost}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
