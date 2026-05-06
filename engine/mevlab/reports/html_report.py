"""Static HTML report generator.

We avoid heavy templating engines (Jinja2 etc.) because we want the engine
package to have a slim dependency footprint. The HTML is a single-file dark
report including a sparkline per strategy.
"""

from __future__ import annotations

from html import escape

from mevlab.backtest.engine import BacktestResult

_STYLE = """
<style>
  body { background:#0b0e14; color:#d3dadf; font-family: ui-sans-serif, system-ui, sans-serif;
         margin:0; padding:32px; }
  h1 { color:#7dd3fc; margin-bottom:4px; }
  h2 { color:#fde68a; margin-top:32px; }
  table { width:100%; border-collapse:collapse; margin-top:8px; font-size:14px; }
  th, td { padding:6px 12px; text-align:left; border-bottom:1px solid #1f2937; }
  th { color:#94a3b8; font-weight:500; }
  td.num { font-variant-numeric:tabular-nums; text-align:right; }
  .pos { color:#34d399; }
  .neg { color:#f87171; }
  .spark { display:block; }
  .small { color:#64748b; font-size:12px; }
</style>
"""


def _format_eth(wei: int) -> str:
    eth = wei / 1e18
    color = "pos" if wei >= 0 else "neg"
    return f'<span class="{color}">{eth:+,.6f}</span>'


def _sparkline(values: list[int], width: int = 320, height: int = 40) -> str:
    if not values:
        return ""
    vmin = min(values)
    vmax = max(values)
    span = max(1, vmax - vmin)
    points = []
    for i, v in enumerate(values):
        x = i / max(1, len(values) - 1) * width
        y = height - ((v - vmin) / span) * height
        points.append(f"{x:.1f},{y:.1f}")
    path = " ".join(points)
    return (
        f'<svg class="spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f'<polyline points="{path}" fill="none" stroke="#7dd3fc" stroke-width="1.5" />'
        f"</svg>"
    )


def render_html_report(result: BacktestResult, *, title: str = "MEV Backtest") -> str:
    rows = []
    for name, metric in sorted(result.metrics.items(), key=lambda kv: -kv[1].total_pnl_wei):
        ledger_entry = result.ledger.get(name)
        spark = _sparkline(ledger_entry.block_profits_wei)
        rows.append(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f'<td class="num">{_format_eth(metric.total_pnl_wei)}</td>'
            f'<td class="num">{metric.mean_per_block_wei / 1e18:+.6f}</td>'
            f'<td class="num">{metric.sharpe:,.2f}</td>'
            f'<td class="num">{metric.max_drawdown_fraction:.2%}</td>'
            f'<td class="num">{metric.hit_rate:.1%}</td>'
            f'<td class="num">{ledger_entry.bundles_landed}/'
            f"{ledger_entry.bundles_landed + ledger_entry.bundles_lost}</td>"
            f"<td>{spark}</td>"
            "</tr>"
        )

    blocks_summary = (
        f"{len(result.blocks)} blocks &middot; "
        f"avg gas {sum(b.total_gas_used for b in result.blocks) // max(1, len(result.blocks)):,} "
        f"&middot; tip total {sum(b.fees_paid_wei for b in result.blocks) / 1e18:.4f} ETH"
    )
    body = (
        f"{_STYLE}"
        f"<h1>{escape(title)}</h1>"
        f'<div class="small">{blocks_summary}</div>'
        "<h2>Per-strategy P&amp;L</h2>"
        "<table><thead><tr>"
        "<th>Strategy</th><th class='num'>Net P&amp;L (ETH)</th>"
        "<th class='num'>Avg/block</th>"
        "<th class='num'>Sharpe (annl.)</th>"
        "<th class='num'>Max DD</th>"
        "<th class='num'>Hit rate</th>"
        "<th class='num'>Landed/total</th>"
        "<th>Equity curve</th>"
        "</tr></thead>"
        "<tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{escape(title)}</title></head><body>{body}</body></html>"


__all__ = ["render_html_report"]
