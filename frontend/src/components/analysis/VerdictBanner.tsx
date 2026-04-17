import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export type Verdict = "BULLISH" | "BEARISH" | "NEUTRAL";

export function classifyVerdict(score: number | null | undefined): Verdict {
  if (score == null) return "NEUTRAL";
  if (score >= 60) return "BULLISH";
  if (score <= 40) return "BEARISH";
  return "NEUTRAL";
}

interface Props {
  verdict: Verdict;
  headline: string;
  sublabel?: string;
  score?: number;
}

const cfg = {
  BULLISH: { color: "text-buy", bg: "bg-buy/10", border: "border-buy/30", icon: TrendingUp, label: "Bullish" },
  BEARISH: { color: "text-sell", bg: "bg-sell/10", border: "border-sell/30", icon: TrendingDown, label: "Bearish" },
  NEUTRAL: { color: "text-hold", bg: "bg-hold/10", border: "border-hold/30", icon: Minus, label: "Neutral" },
};

export function VerdictBanner({ verdict, headline, sublabel, score }: Props) {
  const c = cfg[verdict];
  const Icon = c.icon;
  return (
    <div className={cn("flex items-center gap-4 rounded-2xl border p-4", c.bg, c.border)}>
      <div className={cn("w-12 h-12 rounded-xl flex items-center justify-center", c.bg)}>
        <Icon className={c.color} size={22} />
      </div>
      <div className="flex-1 min-w-0">
        <p className={cn("text-xs uppercase tracking-wider font-semibold", c.color)}>
          {c.label} Outlook
        </p>
        <p className="text-base font-semibold truncate">{headline}</p>
        {sublabel && <p className="text-xs text-muted-foreground truncate">{sublabel}</p>}
      </div>
      {score != null && (
        <div className="text-right">
          <p className={cn("text-2xl font-bold font-mono tabular-nums", c.color)}>{Math.round(score)}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">/ 100</p>
        </div>
      )}
    </div>
  );
}
