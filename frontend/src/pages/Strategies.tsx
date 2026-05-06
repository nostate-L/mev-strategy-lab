import { useEffect, useState } from "react";

import { api, StrategyDescriptor } from "../api";

export default function Strategies() {
  const [list, setList] = useState<StrategyDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.strategies().then(setList).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Strategies</h1>
        <p className="text-slate-400 text-sm">
          Built-in searcher strategies. The lab simulates each one against the same mempool feed
          so their P&L is directly comparable.
        </p>
      </header>
      {error && <p className="text-rose-400 text-sm">{error}</p>}
      <div className="grid sm:grid-cols-2 gap-4">
        {list.map((s) => (
          <div
            key={s.name}
            className="rounded-lg border border-slate-800 bg-slate-900/50 p-4"
          >
            <div className="flex items-center justify-between">
              <div className="font-mono text-cyan-300">{s.name}</div>
              {s.requires_v3 && (
                <span className="text-xs rounded-full bg-fuchsia-900/40 text-fuchsia-300 px-2 py-0.5">
                  V3
                </span>
              )}
            </div>
            <h2 className="mt-1 text-lg font-semibold">{s.title}</h2>
            <p className="mt-2 text-sm text-slate-400">{s.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
