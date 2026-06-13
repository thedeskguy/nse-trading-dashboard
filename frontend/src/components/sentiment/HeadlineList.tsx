import { cn } from "@/lib/utils";
import type { Headline } from "@/lib/api/sentiment";

interface Props {
  headlines: Headline[];
}

function sentimentChip(score: number) {
  if (score > 0.05)
    return { label: "Positive", className: "bg-buy/10 text-buy border-buy/30" };
  if (score < -0.05)
    return { label: "Negative", className: "bg-sell/10 text-sell border-sell/30" };
  return { label: "Neutral", className: "bg-hold/10 text-hold border-hold/30" };
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function HeadlineList({ headlines }: Props) {
  if (headlines.length === 0) {
    return (
      <p className="text-xs text-muted-foreground px-1 py-2">No headlines available.</p>
    );
  }

  return (
    <div className="space-y-2">
      {headlines.map((h, i) => {
        const chip = sentimentChip(h.sentiment);
        return (
          <div
            key={`${h.url}-${i}`}
            className="flex items-start gap-3 rounded-xl bg-muted/30 border border-border/50 px-3 py-2.5 hover:bg-muted/50 transition-colors"
          >
            <div className="flex-1 min-w-0 space-y-0.5">
              <a
                href={h.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium leading-snug hover:underline line-clamp-2 break-words"
              >
                {h.title}
              </a>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] text-muted-foreground font-medium">{h.source}</span>
                <span className="text-[10px] text-muted-foreground/60">{formatDate(h.published_at)}</span>
              </div>
            </div>
            <span
              className={cn(
                "shrink-0 mt-0.5 text-[10px] font-bold px-2 py-0.5 rounded-full border",
                chip.className,
              )}
            >
              {chip.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
