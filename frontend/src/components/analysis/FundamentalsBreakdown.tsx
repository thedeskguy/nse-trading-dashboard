import { cn } from "@/lib/utils";
import type { FundamentalsBreakdownItem } from "@/lib/api/analysis";

interface Props { breakdown: Record<string, FundamentalsBreakdownItem> }

export function FundamentalsBreakdown({ breakdown }: Props) {
  const entries = Object.entries(breakdown);
  if (entries.length === 0) return null;

  return (
    <div className="bg-card border border-border rounded-2xl p-6">
      <h3 className="text-sm font-semibold mb-4 text-muted-foreground uppercase tracking-wider">
        Fundamental Scoring
      </h3>
      <div className="space-y-3">
        {entries.map(([name, item]) => {
          const pct = item.max > 0 ? (item.points / item.max) * 100 : 0;
          const tone = pct >= 66 ? "bg-buy" : pct >= 33 ? "bg-hold" : "bg-sell";
          return (
            <div key={name}>
              <div className="flex items-center justify-between mb-1">
                <p className="text-sm font-medium">{name}</p>
                <p className="text-xs font-mono text-muted-foreground">
                  {item.points}/{item.max}
                </p>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", tone)}
                  style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
                />
              </div>
              <p className="text-xs text-muted-foreground mt-1">{item.label}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
