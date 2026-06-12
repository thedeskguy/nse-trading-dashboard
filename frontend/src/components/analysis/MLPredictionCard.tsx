import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, FlaskConical } from "lucide-react";
import type { MLResponse } from "@/lib/api/analysis";

interface Props {
  data: MLResponse;
  onBacktestModel: () => void;
}

export const FEATURE_LABELS: Record<string, string> = {
  rsi: "RSI (14)",
  macd_hist: "MACD histogram",
  bb_pct: "Bollinger %B",
  ema9_dist: "Distance from EMA 9",
  ema21_dist: "Distance from EMA 21",
  ema50_dist: "Distance from EMA 50",
  ema200_dist: "Distance from EMA 200",
  atr_pct: "ATR % of price",
  vol_change: "Volume vs 10-day avg",
  ret_1d: "1-day return",
  ret_5d: "5-day return",
  obv_slope: "OBV slope",
};

export function MLPredictionCard({ data, onBacktestModel }: Props) {
  const isUp = data.direction === "UP";
  const pct = Math.round((data.probability ?? 0) * 100);
  const accuracy = Math.round((data.accuracy ?? 0) * 100);
  const features = Object.entries(data.feature_importance ?? {}).sort((a, b) => b[1] - a[1]);
  const maxImp = Math.max(0.0001, ...features.map(([, imp]) => imp));

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">ML Prediction</h3>
        <button
          onClick={onBacktestModel}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
        >
          <FlaskConical size={13} />
          Backtest this model &rarr;
        </button>
      </div>

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

      {/* Confidence gauge with 50% coin-flip anchor */}
      <div>
        <div className="relative h-2 bg-muted rounded-full">
          <div
            className={cn("absolute inset-y-0 left-0 rounded-full transition-all duration-700", isUp ? "bg-buy" : "bg-sell")}
            style={{ width: `${pct}%` }}
          />
          <div className="absolute inset-y-[-3px] left-1/2 w-px bg-foreground/40" />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
          <span>0%</span>
          <span>50% = coin flip</span>
          <span>100%</span>
        </div>
      </div>

      {/* Honest accuracy context */}
      <div className="bg-muted/40 rounded-xl px-3 py-2.5 text-xs text-muted-foreground leading-relaxed">
        <span className="font-semibold text-foreground/80">{accuracy}% accuracy on the last {data.test_samples ?? "?"} sessions</span>{" "}
        (time-ordered hold-out; trained on {data.train_samples ?? "?"} sessions). Next-day direction is
        near-random &mdash; treat accuracy below 55% as noise.
      </div>

      {/* All feature importances */}
      {features.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Feature Importance</p>
          <div className="space-y-1.5">
            {features.map(([feat, imp]) => (
              <div key={feat} className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground w-40 truncate">
                  {FEATURE_LABELS[feat] ?? feat}
                </span>
                <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary/60 rounded-full"
                    style={{ width: `${Math.round((imp / maxImp) * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-muted-foreground w-10 text-right">
                  {(imp * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
