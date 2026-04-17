import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, AlertCircle } from "lucide-react";
import type { TradeRec, RecommendResponse } from "@/lib/api/options";

interface Props {
  data: RecommendResponse;
  style: "intraday" | "positional";
}

function fmt(v: number) {
  return `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export function TradeCard({ data, style }: Props) {
  const rec: TradeRec | undefined = data.recommendations?.[style];
  const isCall = data.option_type === "CALL";
  const dirColor = isCall ? "text-buy" : "text-sell";
  const dirBg = isCall ? "bg-buy/10" : "bg-sell/10";
  const DirIcon = isCall ? TrendingUp : TrendingDown;

  const label = style === "intraday" ? "Intraday Trade" : "Positional Trade";

  if (data.underlying_signal === "HOLD") {
    return (
      <div className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</h3>
          <span className="text-xs px-2.5 py-1 rounded-full bg-hold/10 text-hold font-medium">HOLD</span>
        </div>
        <div className="flex items-start gap-2 text-muted-foreground text-sm py-4">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>{data.message}</p>
        </div>
      </div>
    );
  }

  if (!rec || rec.error) {
    return (
      <div className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-3">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</h3>
        <p className="text-sm text-muted-foreground py-4">{rec?.error ?? "No data available"}</p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">{label}</h3>
        <span className={cn("flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium border", dirBg, dirColor,
          isCall ? "border-buy/20" : "border-sell/20"
        )}>
          <DirIcon size={10} />
          Buy {rec.option_type}
        </span>
      </div>

      {/* Option name */}
      <div className="bg-muted/40 rounded-xl px-3 py-2.5">
        <p className="text-xs text-muted-foreground mb-0.5">Option</p>
        <p className="font-mono text-sm font-semibold">{rec.option}</p>
      </div>

      {/* Premium + SL + Target */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "Premium", value: fmt(rec.premium), color: "text-foreground" },
          { label: `SL (−${rec.sl_pct}%)`, value: fmt(rec.stop_loss), color: "text-sell" },
          { label: `Target (+${rec.target_pct}%)`, value: fmt(rec.target), color: "text-buy" },
        ].map((item) => (
          <div key={item.label} className="bg-muted/40 rounded-xl p-3 text-center">
            <p className="text-[10px] text-muted-foreground mb-1 leading-tight">{item.label}</p>
            <p className={cn("font-mono text-xs font-semibold tabular-nums", item.color)}>{item.value}</p>
          </div>
        ))}
      </div>

      {/* Capital + P&L */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-muted/40 rounded-xl p-3">
          <p className="text-xs text-muted-foreground mb-0.5">Capital (1 lot)</p>
          <p className="font-mono text-sm font-semibold">{fmt(rec.capital_1_lot)}</p>
          <p className="text-[10px] text-muted-foreground mt-0.5">{rec.lot_size} units</p>
        </div>
        <div className="bg-muted/40 rounded-xl p-3">
          <p className="text-xs text-muted-foreground mb-0.5">Max P&L (1 lot)</p>
          <p className="font-mono text-sm font-semibold text-buy">+{fmt(rec.max_profit_1_lot)}</p>
          <p className="font-mono text-xs text-sell">−{fmt(rec.max_loss_1_lot)}</p>
        </div>
      </div>

      {/* IV + OI */}
      {(rec.iv > 0 || rec.oi > 0) && (
        <div className="flex gap-4 text-xs text-muted-foreground pt-1 border-t border-border/50">
          {rec.iv > 0 && <span>IV: <span className="text-foreground font-mono">{rec.iv.toFixed(1)}%</span></span>}
          {rec.oi > 0 && <span>OI: <span className="text-foreground font-mono">{rec.oi.toLocaleString("en-IN")}</span></span>}
          <span>Bid/Ask: <span className="text-foreground font-mono">{fmt(rec.bid)} / {fmt(rec.ask)}</span></span>
        </div>
      )}
    </div>
  );
}
