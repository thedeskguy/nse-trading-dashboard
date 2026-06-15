import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, AlertCircle } from "lucide-react";
import type { SentimentReadout } from "@/lib/api/sentiment";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface Props {
  title: string;
  readout: SentimentReadout;
}

const cfg = {
  Bullish: {
    color: "text-buy",
    bg: "bg-buy/10",
    border: "border-buy/30",
    icon: TrendingUp,
  },
  Bearish: {
    color: "text-sell",
    bg: "bg-sell/10",
    border: "border-sell/30",
    icon: TrendingDown,
  },
  Neutral: {
    color: "text-hold",
    bg: "bg-hold/10",
    border: "border-hold/30",
    icon: Minus,
  },
};

export function SentimentGauge({ title, readout }: Props) {
  const c = cfg[readout.label];
  const Icon = c.icon;

  // Score is -100..100; normalise to 0..100 for the bar
  const barPct = Math.min(100, Math.max(0, (readout.score + 100) / 2));

  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider truncate">
            {title}
          </h3>
          {readout.scored_by && (
            <span
              className="shrink-0 text-[9px] font-semibold uppercase tracking-wide text-muted-foreground/60 border border-border rounded px-1 py-0.5"
              title={`Scored by ${readout.scored_by === "finbert" ? "FinBERT (finance-trained)" : "VADER"}`}
            >
              {readout.scored_by === "finbert" ? "FinBERT" : "VADER"}
            </span>
          )}
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full border",
            c.bg,
            c.color,
            c.border,
          )}
        >
          <Icon size={11} />
          {readout.label}
        </span>
      </div>

      {readout.insufficient ? (
        /* Insufficient data state */
        <div className="flex items-start gap-2 rounded-xl border border-border bg-muted/30 px-4 py-3">
          <AlertCircle size={14} className="mt-0.5 shrink-0 text-muted-foreground" />
          <p className="text-xs text-muted-foreground leading-relaxed">
            Insufficient recent news — sentiment may not be reliable.
          </p>
        </div>
      ) : (
        <>
          {/* Score */}
          <div className="flex items-end gap-2">
            <p className={cn("text-3xl font-bold font-mono tabular-nums", c.color)}>
              {readout.score > 0 ? "+" : ""}
              {Math.round(readout.score)}
            </p>
            <p className="text-xs text-muted-foreground mb-1">on −100…+100</p>
          </div>

          {/* Sentiment bar (-100 → 0 → +100) */}
          <div>
            <div className="relative h-2.5 rounded-full overflow-hidden flex">
              <div className="h-full bg-sell/25 rounded-l-full" style={{ width: "50%" }} />
              <div className="h-full bg-buy/25 rounded-r-full" style={{ width: "50%" }} />
              <div
                className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 rounded-full bg-foreground border-2 border-card shadow"
                style={{ left: `${barPct}%` }}
                aria-label={`Sentiment score ${readout.score}`}
              />
            </div>
            <div className="flex justify-between text-[10px] text-muted-foreground mt-1.5">
              <span>Bearish −100</span>
              <span>Neutral 0</span>
              <span>+100 Bullish</span>
            </div>
          </div>

          {/* Confidence + article count */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-muted/40 border border-transparent px-3 py-2.5">
              <TooltipProvider delay={100}>
                <Tooltip>
                  <TooltipTrigger className="text-xs text-muted-foreground mb-0.5 inline-flex items-center gap-1 cursor-help w-fit bg-transparent border-0 p-0 font-normal">
                    Confidence <span className="opacity-50">ⓘ</span>
                  </TooltipTrigger>
                  <TooltipContent className="max-w-[230px] leading-relaxed">
                    How reliable this reading is — higher when there are many articles and they
                    mostly agree in direction; lower with few articles or conflicting headlines.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
              <div className="flex items-center gap-1.5">
                <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn("h-full rounded-full", c.bg.replace("/10", "/60"))}
                    style={{ width: `${readout.confidence}%` }}
                  />
                </div>
                <span className="text-xs font-mono font-semibold tabular-nums shrink-0">
                  {Math.round(readout.confidence)}%
                </span>
              </div>
            </div>
            <div className="rounded-xl bg-muted/40 border border-transparent px-3 py-2.5">
              <p className="text-xs text-muted-foreground mb-0.5">Articles</p>
              <p className="text-sm font-mono font-semibold tabular-nums">
                {readout.article_count}
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
