import { cn } from "@/lib/utils";
import type { SignalResponse } from "@/lib/api/market";

interface Props { components: SignalResponse["components"] }

export function IndicatorBreakdown({ components }: Props) {
  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">
        Technical Indicators
      </h3>
      <div className="space-y-2">
        {Object.entries(components).map(([name, data]) => (
          <div
            key={name}
            className="flex items-center justify-between gap-3 py-2 border-b border-border/50 last:border-0"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                <p className="text-sm font-medium">{name}</p>
                {data.value !== undefined && data.value !== null && data.value !== "N/A" && (
                  <p className="text-[11px] font-mono text-muted-foreground truncate">
                    {String(data.value)}
                  </p>
                )}
              </div>
              <p className="text-xs text-muted-foreground truncate">{data.signal}</p>
            </div>
            <div
              className={cn(
                "text-xs font-bold px-2.5 py-1 rounded-full shrink-0",
                data.points > 0
                  ? "bg-buy/10 text-buy"
                  : data.points < 0
                  ? "bg-sell/10 text-sell"
                  : "bg-muted text-muted-foreground",
              )}
            >
              {data.points > 0 ? `+${data.points}` : data.points}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
