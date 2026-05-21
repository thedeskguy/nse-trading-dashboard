import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { MLResponse } from "@/lib/api/analysis";

interface Props { data: MLResponse }

export function MLPredictionCard({ data }: Props) {
  const isUp = data.direction === "UP";
  const pct = Math.round((data.probability ?? 0) * 100);
  const accuracy = Math.round((data.accuracy ?? 0) * 100);

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">ML Prediction</h3>

      <div className="flex items-center gap-4">
        <div className={cn(
          "w-14 h-14 rounded-2xl flex items-center justify-center",
          isUp ? "bg-buy/10" : "bg-sell/10"
        )}>
          {isUp
            ? <TrendingUp size={24} className="text-buy" />
            : <TrendingDown size={24} className="text-sell" />}
        </div>
        <div>
          <p className={cn("text-2xl font-bold font-display", isUp ? "text-buy" : "text-sell")}>
            {data.direction ?? "N/A"}
          </p>
          <p className="text-xs text-muted-foreground">Next day direction</p>
        </div>
        <div className="ml-auto text-right">
          <p className="text-2xl font-bold font-mono tabular-nums">{pct}%</p>
          <p className="text-xs text-muted-foreground">Probability</p>
        </div>
      </div>

      {/* Probability bar */}
      <div>
        <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
          <span>Probability</span>
          <span>Model accuracy: {accuracy}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-700", isUp ? "bg-buy" : "bg-sell")}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Top feature importances */}
      {data.feature_importance && Object.keys(data.feature_importance).length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Top Features</p>
          <div className="space-y-1.5">
            {Object.entries(data.feature_importance)
              .sort((a, b) => b[1] - a[1])
              .slice(0, 4)
              .map(([feat, imp]) => (
                <div key={feat} className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground w-24 truncate">{feat}</span>
                  <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                    <div className="h-full bg-primary/60 rounded-full" style={{ width: `${Math.round(imp * 100)}%` }} />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground w-8 text-right">{(imp * 100).toFixed(0)}%</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
