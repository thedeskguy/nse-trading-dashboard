import { cn } from "@/lib/utils";
import type { RecommendResponse } from "@/lib/api/options";

interface Props {
  data: RecommendResponse;
}

export function PCRCard({ data }: Props) {
  const pcr = data.pcr?.pcr;
  const pcrSignal = data.pcr?.signal ?? "";
  const isBullish = pcrSignal.toLowerCase().includes("bullish");
  const isBearish = pcrSignal.toLowerCase().includes("bearish");

  const signalColor = isBullish ? "text-buy" : isBearish ? "text-sell" : "text-hold";
  const signalBg = isBullish ? "bg-buy/10" : isBearish ? "bg-sell/10" : "bg-hold/10";

  return (
    <div className="bg-card border border-border rounded-2xl p-5 space-y-4">
      <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Market Sentiment</h3>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-muted/40 rounded-xl p-3">
          <p className="text-xs text-muted-foreground mb-1">Put-Call Ratio</p>
          <p className="text-2xl font-bold font-mono tabular-nums">
            {pcr !== null && pcr !== undefined ? pcr.toFixed(2) : "—"}
          </p>
        </div>
        <div className="bg-muted/40 rounded-xl p-3">
          <p className="text-xs text-muted-foreground mb-1">Max Pain</p>
          <p className="text-2xl font-bold font-mono tabular-nums">
            {data.max_pain !== null && data.max_pain !== undefined
              ? `₹${data.max_pain.toLocaleString("en-IN")}`
              : "—"}
          </p>
        </div>
      </div>

      <div className={cn("rounded-xl px-3 py-2.5 text-xs font-medium", signalBg, signalColor)}>
        {pcrSignal || "No signal"}
      </div>

      <div className="grid grid-cols-3 gap-2 pt-1">
        {["pcr < 0.8 → Bearish", "0.8–1.2 → Neutral", "pcr > 1.2 → Bullish"].map((label, i) => (
          <div key={i} className="text-center">
            <div className={cn(
              "h-1 rounded-full mb-1",
              i === 0 ? "bg-sell/40" : i === 1 ? "bg-hold/40" : "bg-buy/40"
            )} />
            <p className="text-[10px] text-muted-foreground leading-tight">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
