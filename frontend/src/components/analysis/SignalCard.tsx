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

function ScoreGauge({ score }: { score: number }) {
  return (
    <div>
      <div className="relative h-2.5 rounded-full overflow-visible flex">
        <div className="h-full bg-sell/25 rounded-l-full" style={{ width: "40%" }} />
        <div className="h-full bg-hold/25" style={{ width: "20%" }} />
        <div className="h-full bg-buy/25 rounded-r-full" style={{ width: "40%" }} />
        <div
          className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-foreground border-2 border-card shadow"
          style={{ left: `${Math.min(100, Math.max(0, score))}%` }}
          aria-label={`Score ${score} of 100`}
        />
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground mt-1.5">
        <span>SELL &lt; 40</span>
        <span>40–60</span>
        <span>BUY &gt; 60</span>
      </div>
    </div>
  );
}

function PriceLevelRail({ entry, stopLoss, target }: { entry: number; stopLoss: number; target: number }) {
  const lo = Math.min(entry, stopLoss, target);
  const hi = Math.max(entry, stopLoss, target);
  const span = hi - lo || 1;
  const pos = (v: number) => ((v - lo) / span) * 100;
  const levels = [
    { label: "Stop Loss", value: stopLoss, dot: "bg-sell", text: "text-sell" },
    { label: "Entry", value: entry, dot: "bg-foreground", text: "text-foreground" },
    { label: "Target", value: target, dot: "bg-buy", text: "text-buy" },
  ];
  return (
    <div className="pt-1">
      <div className="relative h-1.5 bg-muted rounded-full mx-2">
        {levels.map((l) => (
          <div
            key={l.label}
            className={cn("absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full border-2 border-card shadow", l.dot)}
            style={{ left: `${pos(l.value)}%` }}
          />
        ))}
      </div>
      <div className="relative h-9 mx-2 mt-1.5">
        {levels.map((l) => (
          <div
            key={l.label}
            className="absolute -translate-x-1/2 text-center"
            style={{ left: `${Math.min(92, Math.max(8, pos(l.value)))}%` }}
          >
            <p className="text-[10px] text-muted-foreground whitespace-nowrap">{l.label}</p>
            <p className={cn("font-mono text-xs font-semibold tabular-nums whitespace-nowrap", l.text)}>
              &#8377;{l.value.toFixed(2)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

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

      <ScoreGauge score={data.confidence} />

      <PriceLevelRail entry={data.last_price} stopLoss={data.stop_loss} target={data.target} />
    </div>
  );
}
