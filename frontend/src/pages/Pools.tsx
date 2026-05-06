import { useEffect, useState } from "react";

import { api, PoolDescriptor } from "../api";

export default function Pools() {
  const [list, setList] = useState<PoolDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.pools().then(setList).catch((e) => setError(e.message));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Pools</h1>
        <p className="text-slate-400 text-sm">
          Configured pool fixtures used by the demo scenarios. Reserves are denominated in raw
          base units (no scaling for token decimals).
        </p>
      </header>
      {error && <p className="text-rose-400 text-sm">{error}</p>}
      <div className="rounded-lg border border-slate-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Address</th>
              <th className="text-left px-4 py-2 font-medium">Kind</th>
              <th className="text-left px-4 py-2 font-medium">Pair</th>
              <th className="text-right px-4 py-2 font-medium">Mid price</th>
              <th className="text-right px-4 py-2 font-medium">Fee</th>
              <th className="text-right px-4 py-2 font-medium">Reserves</th>
            </tr>
          </thead>
          <tbody>
            {list.map((p) => (
              <tr key={p.address} className="border-t border-slate-800/60">
                <td className="px-4 py-2 font-mono text-cyan-300">{p.address}</td>
                <td className="px-4 py-2">{p.kind}</td>
                <td className="px-4 py-2">
                  {p.token0_symbol} / {p.token1_symbol}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">
                  {p.mid_price.toExponential(4)}
                </td>
                <td className="px-4 py-2 text-right tabular-nums">{p.fee_bps} bps</td>
                <td className="px-4 py-2 text-right font-mono text-xs text-slate-400">
                  {p.reserve0} / {p.reserve1}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
