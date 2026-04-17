import { cn } from "@/lib/utils";

interface Props { data: Record<string, number | string | null>; ticker: string }

function fmt(val: number | string | null, type: "num" | "pct" | "cr" | "str"): string {
  if (val === null || val === undefined) return "\u2014";
  if (type === "str") return String(val);
  const n = Number(val);
  if (isNaN(n)) return "\u2014";
  if (type === "pct") return `${(n * 100).toFixed(1)}%`;
  if (type === "cr") {
    if (n >= 1e7) return `\u20B9${(n / 1e7).toFixed(2)}Cr`;
    return `\u20B9${n.toFixed(2)}`;
  }
  return n.toFixed(2);
}

export function FundamentalsPanel({ data, ticker }: Props) {
  const metrics = [
    { label: "P/E (TTM)", value: fmt(data.pe_trailing, "num") },
    { label: "P/E (Fwd)", value: fmt(data.pe_forward, "num") },
    { label: "P/B Ratio", value: fmt(data.pb_ratio, "num") },
    { label: "ROE", value: fmt(data.roe, "pct") },
    { label: "ROA", value: fmt(data.roa, "pct") },
    { label: "D/E Ratio", value: fmt(data.debt_to_equity, "num") },
    { label: "Revenue Growth", value: fmt(data.revenue_growth, "pct") },
    { label: "Profit Growth", value: fmt(data.profit_growth, "pct") },
    { label: "Market Cap", value: fmt(data.market_cap, "cr") },
    { label: "Div Yield", value: fmt(data.dividend_yield, "pct") },
    { label: "Beta", value: fmt(data.beta, "num") },
    { label: "52W High", value: data.high_52w != null ? `\u20B9${Number(data.high_52w).toFixed(2)}` : "\u2014" },
    { label: "52W Low", value: data.low_52w != null ? `\u20B9${Number(data.low_52w).toFixed(2)}` : "\u2014" },
    { label: "52W Change", value: fmt(data.week52_change, "pct") },
  ];

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Fundamentals</h3>
        {data.sector && <span className="text-xs text-muted-foreground">{String(data.sector)}</span>}
      </div>
      {data.name && <p className="text-base font-semibold mb-4">{String(data.name)}</p>}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="bg-muted/40 rounded-xl p-3">
            <p className="text-xs text-muted-foreground mb-0.5">{m.label}</p>
            <p className="text-sm font-semibold font-mono tabular-nums">{m.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
