import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/lib/api/market";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Props { data: SignalResponse }

const signalConfig = {
  BUY:  { color: "text-buy",  bg: "bg-buy/10",  border: "border-buy/20",  icon: TrendingUp,   label: "BUY" },
  SELL: { color: "text-sell", bg: "bg-sell/10", border: "border-sell/20", icon: TrendingDown, label: "SELL" },
  HOLD: { color: "text-hold", bg: "bg-hold/10", border: "border-hold/20", icon: Minus,        label: "HOLD" },
};

export function SignalCard({ data }: Props) {
  const cfg = signalConfig[data.signal];
  const Icon = cfg.icon;

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Signal</p>
          <Badge className={cn("text-base px-4 py-1.5 rounded-full font-bold border", cfg.bg, cfg.color, cfg.border)}>
            <Icon size={14} className="mr-1.5" />
            {cfg.label}
          </Badge>
        </div>
        <div className="text-right">
          <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Confidence</p>
          <p className={cn("text-3xl font-bold font-mono tabular-nums", cfg.color)}>{data.confidence}%</p>
        </div>
      </div>

      {/* Confidence bar */}
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-700", cfg.bg.replace("/10", ""))}
          style={{ width: `${data.confidence}%` }}
        />
      </div>

      {/* Price levels */}
      <div className="grid grid-cols-3 gap-3 pt-1">
        {[
          { label: "Entry", value: data.last_price, color: "text-foreground" },
          { label: "Stop Loss", value: data.stop_loss, color: "text-sell" },
          { label: "Target", value: data.target, color: "text-buy" },
        ].map((item) => (
          <div key={item.label} className="bg-muted/40 rounded-xl p-3 text-center">
            <p className="text-xs text-muted-foreground mb-1">{item.label}</p>
            <p className={cn("font-mono text-sm font-semibold tabular-nums", item.color)}>
              &#8377;{item.value.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
