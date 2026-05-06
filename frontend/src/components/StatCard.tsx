interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  tone?: "default" | "positive" | "negative";
}

export default function StatCard({ title, value, subtitle, tone = "default" }: StatCardProps) {
  const toneClass =
    tone === "positive"
      ? "text-emerald-400"
      : tone === "negative"
      ? "text-rose-400"
      : "text-slate-100";
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="text-xs uppercase tracking-wider text-slate-500">{title}</div>
      <div className={`mt-2 text-2xl font-semibold tabular-nums ${toneClass}`}>{value}</div>
      {subtitle && <div className="mt-1 text-xs text-slate-500">{subtitle}</div>}
    </div>
  );
}
