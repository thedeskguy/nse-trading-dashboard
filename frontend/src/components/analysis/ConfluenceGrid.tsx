"use client";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle } from "lucide-react";
import type { ConfluenceResponse } from "@/lib/api/analysis";

const INDICATORS = [
  "RSI",
  "MACD",
  "EMA Trend",
  "Bollinger Bands",
  "Support/Resistance",
  "OBV",
];

const SHORT_LABELS: Record<string, string> = {
  "RSI": "RSI",
  "MACD": "MACD",
  "EMA Trend": "EMA",
  "Bollinger Bands": "BB",
  "Support/Resistance": "S/R",
  "OBV": "OBV",
};

function pointsToColor(points: number): string {
  if (points > 0) return "bg-buy/15 text-buy border-buy/20";
  if (points < 0) return "bg-sell/15 text-sell border-sell/20";
  return "bg-muted/60 text-muted-foreground border-border";
}

function SignalBadge({ signal }: { signal: string | null }) {
  if (!signal) return <span className="text-xs text-muted-foreground">—</span>;
  const colors: Record<string, string> = {
    BUY: "text-buy font-bold",
    SELL: "text-sell font-bold",
    HOLD: "text-hold font-semibold",
  };
  return <span className={`text-sm ${colors[signal] ?? ""}`}>{signal}</span>;
}

function StrengthBar({ count, total, color }: { count: number; total: number; color: string }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 w-4 rounded-full ${i < count ? color : "bg-muted"}`}
        />
      ))}
    </div>
  );
}

interface Props {
  data: ConfluenceResponse;
}

export function ConfluenceGrid({ data }: Props) {
  const { timeframes, summary } = data;

  const summaryColor =
    summary.strength.includes("BUY")  ? "text-buy" :
    summary.strength.includes("SELL") ? "text-sell" : "text-muted-foreground";

  return (
    <div className="space-y-5">
      {/* Summary banner */}
      <div className="bg-card border border-border rounded-2xl px-5 py-4 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">
            Confluence Signal
          </div>
          <div className={`text-xl font-bold ${summaryColor}`}>{summary.strength}</div>
        </div>
        <div className="flex gap-5">
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1.5">BUY</div>
            <StrengthBar count={summary.buy_count} total={3} color="bg-buy" />
            <div className="text-xs text-buy font-semibold mt-1">{summary.buy_count}/3</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1.5">HOLD</div>
            <StrengthBar count={summary.hold_count} total={3} color="bg-hold" />
            <div className="text-xs text-hold font-semibold mt-1">{summary.hold_count}/3</div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1.5">SELL</div>
            <StrengthBar count={summary.sell_count} total={3} color="bg-sell" />
            <div className="text-xs text-sell font-semibold mt-1">{summary.sell_count}/3</div>
          </div>
        </div>
      </div>

      {/* Heatmap grid */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[480px]">
          <thead>
            <tr className="border-b border-border text-xs text-muted-foreground bg-muted/30">
              <th className="text-left px-4 py-2.5 font-medium w-16">TF</th>
              <th className="text-center px-3 py-2.5 font-medium w-20">Signal</th>
              {INDICATORS.map((ind) => (
                <th key={ind} className="text-center px-2 py-2.5 font-medium">
                  {SHORT_LABELS[ind]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {timeframes.map((tf) => (
              <tr key={tf.timeframe} className="border-b border-border/50 last:border-0">
                <td className="px-4 py-3 font-mono text-xs font-semibold text-muted-foreground">
                  {tf.timeframe}
                </td>
                <td className="px-3 py-3 text-center">
                  <SignalBadge signal={tf.signal} />
                  {tf.confidence != null && (
                    <div className="text-[10px] text-muted-foreground mt-0.5">{tf.confidence}%</div>
                  )}
                </td>
                {INDICATORS.map((ind) => {
                  const comp = tf.components[ind];
                  if (!comp) {
                    return (
                      <td key={ind} className="px-2 py-3 text-center">
                        <span className="text-xs text-muted-foreground">—</span>
                      </td>
                    );
                  }
                  return (
                    <td key={ind} className="px-2 py-3 text-center">
                      <div
                        className={`inline-flex items-center justify-center w-9 h-7 rounded-lg border text-[11px] font-semibold ${pointsToColor(comp.points)}`}
                        title={comp.label}
                      >
                        {comp.points > 0 ? `+${comp.points}` : comp.points}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-muted-foreground">
        Green = bullish points, Red = bearish. Hover cells for indicator detail. Cached 10 min.
      </p>
    </div>
  );
}

export function ConfluenceGridSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-24 rounded-2xl" />
      <Skeleton className="h-48 rounded-2xl" />
    </div>
  );
}

export function ConfluenceGridError() {
  return (
    <div className="bg-card border border-border rounded-2xl py-16 flex flex-col items-center gap-2 text-muted-foreground text-sm">
      <AlertCircle size={18} className="opacity-40" />
      <span>Confluence data unavailable</span>
    </div>
  );
}
