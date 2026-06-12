import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/lib/api/market";

interface Props { components: SignalResponse["components"] }

export function IndicatorBreakdown({ components }: Props) {
  const entries = Object.entries(components);
  // Scale bars to the largest absolute contribution so they stay comparable.
  const maxAbs = Math.max(1, ...entries.map(([, d]) => Math.abs(d.points)));

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">
        Technical Indicators
      </h3>
      <div className="space-y-3">
        {entries.map(([name, data]) => {
          const widthPct = (Math.abs(data.points) / maxAbs) * 50;
          return (
            <div key={name}>
              <div className="flex items-baseline justify-between gap-2 mb-1">
                <div className="flex items-baseline gap-2 min-w-0">
                  <p className="text-sm font-medium">{name}</p>
                  {data.value !== undefined && data.value !== null && data.value !== "N/A" && (
                    <p className="text-[11px] font-mono text-muted-foreground truncate">
                      {String(data.value)}
                    </p>
                  )}
                </div>
                <span
                  className={cn(
                    "text-xs font-bold font-mono shrink-0",
                    data.points > 0 ? "text-buy" : data.points < 0 ? "text-sell" : "text-muted-foreground",
                  )}
                >
                  {data.points > 0 ? `+${data.points}` : data.points}
                </span>
              </div>
              {/* Diverging bar: bearish extends left of centre, bullish right */}
              <div className="relative h-1.5 bg-muted rounded-full">
                <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                {data.points !== 0 && (
                  <div
                    className={cn(
                      "absolute inset-y-0 rounded-full",
                      data.points > 0 ? "left-1/2 bg-buy" : "right-1/2 bg-sell",
                    )}
                    style={{ width: `${widthPct}%` }}
                  />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1 truncate">{data.signal}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
