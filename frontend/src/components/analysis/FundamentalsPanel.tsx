import { cn } from "@/lib/utils";
import type { FundamentalsBreakdownItem } from "@/lib/api/analysis";

interface Props {
  data: Record<string, number | string | null>;
  ticker: string;
  breakdown?: Record<string, FundamentalsBreakdownItem>;
}

function fmt(val: number | string | null, type: "num" | "pct" | "cr" | "str"): string {
  if (val === null || val === undefined) return "—";
  if (type === "str") return String(val);
  const n = Number(val);
  if (isNaN(n)) return "—";
  if (type === "pct") return `${(n * 100).toFixed(1)}%`;
  if (type === "cr") {
    if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)}Cr`;
    return `₹${n.toFixed(2)}`;
  }
  return n.toFixed(2);
}

// Metric label → score_fundamentals breakdown key (tools/fetch_fundamentals.py)
const BREAKDOWN_KEY: Record<string, string> = {
  "P/E (TTM)": "PE Ratio",
  "ROE": "ROE",
  "D/E Ratio": "Debt / Equity",
  "Revenue Growth": "Revenue Growth",
};

function tone(item?: FundamentalsBreakdownItem) {
  if (!item || item.max <= 0) return { card: "", bar: "bg-muted" };
  const pct = (item.points / item.max) * 100;
  if (pct >= 66) return { card: "border-buy/30 bg-buy/5", bar: "bg-buy" };
  if (pct >= 33) return { card: "border-hold/30 bg-hold/5", bar: "bg-hold" };
  return { card: "border-sell/30 bg-sell/5", bar: "bg-sell" };
}

export function FundamentalsPanel({ data, breakdown = {} }: Props) {
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
    { label: "52W High", value: data.high_52w != null ? `₹${Number(data.high_52w).toFixed(2)}` : "—" },
    { label: "52W Low", value: data.low_52w != null ? `₹${Number(data.low_52w).toFixed(2)}` : "—" },
    { label: "52W Change", value: fmt(data.week52_change, "pct") },
  ];

  // Scoring components without a metric card (e.g. Net Margin, Analyst View)
  const mappedKeys = new Set(Object.values(BREAKDOWN_KEY));
  const drivers = Object.entries(breakdown).filter(([key]) => !mappedKeys.has(key));

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">Fundamentals</h3>
        {data.sector && <span className="text-xs text-muted-foreground">{String(data.sector)}</span>}
      </div>
      {data.name && <p className="text-base font-semibold mb-4">{String(data.name)}</p>}

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {metrics.map((m) => {
          const item = breakdown[BREAKDOWN_KEY[m.label]];
          const t = tone(item);
          return (
            <div key={m.label} className={cn("rounded-xl p-3 border border-transparent bg-muted/40", t.card)}>
              <p className="text-xs text-muted-foreground mb-0.5">{m.label}</p>
              <p className="text-sm font-semibold font-mono tabular-nums">{m.value}</p>
              {item && (
                <p className="text-[10px] text-muted-foreground mt-1 leading-snug">{item.label}</p>
              )}
            </div>
          );
        })}
      </div>

      {drivers.length > 0 && (
        <div className="mt-5 pt-4 border-t border-border/50">
          <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-3">
            Other Score Drivers
          </p>
          <div className="space-y-3">
            {drivers.map(([name, item]) => {
              const pct = item.max > 0 ? Math.max(0, Math.min(100, (item.points / item.max) * 100)) : 0;
              const t = tone(item);
              return (
                <div key={name}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium">{name}</p>
                    <p className="text-xs font-mono text-muted-foreground">{item.points}/{item.max}</p>
                  </div>
                  <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className={cn("h-full rounded-full transition-all", t.bar)} style={{ width: `${pct}%` }} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
