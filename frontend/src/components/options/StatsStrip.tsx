import type { RecommendResponse, ChainRow } from "@/lib/api/options";

interface Props {
  data: RecommendResponse;
  chain?: ChainRow[];
}

function pcrColor(pcr: number | null): string {
  if (pcr === null) return "text-muted-foreground";
  if (pcr > 1.2) return "text-buy";
  if (pcr < 0.8) return "text-sell";
  return "text-hold";
}

function fmtOI(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

export function StatsStrip({ data, chain }: Props) {
  const pcr = data.pcr?.pcr ?? null;
  const sentiment = data.pcr?.signal ?? "—";
  const maxPain = data.max_pain;

  const isBullish = sentiment.toLowerCase().includes("bullish");
  const isBearish = sentiment.toLowerCase().includes("bearish");
  const sentimentColor = data.pcr?.signal == null
    ? "text-muted-foreground"
    : isBullish ? "text-buy" : isBearish ? "text-sell" : "text-hold";

  const callOI = chain
    ? chain.reduce((sum, r) => sum + (r.CE_oi ?? 0), 0)
    : null;
  const putOI = chain
    ? chain.reduce((sum, r) => sum + (r.PE_oi ?? 0), 0)
    : null;

  const chips: { label: string; value: string; color: string }[] = [
    {
      label: "PCR",
      value: pcr !== null ? pcr.toFixed(2) : "—",
      color: pcrColor(pcr),
    },
    {
      label: "Max Pain",
      value: maxPain != null
        ? `₹${maxPain.toLocaleString("en-IN")}`
        : "—",
      color: "text-foreground",
    },
    {
      label: "Sentiment",
      value: sentiment,
      color: sentimentColor,
    },
    {
      label: "Call OI",
      value: callOI !== null ? fmtOI(callOI) : "—",
      color: "text-sell",
    },
    {
      label: "Put OI",
      value: putOI !== null ? fmtOI(putOI) : "—",
      color: "text-buy",
    },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {chips.map(({ label, value, color }) => (
        <div
          key={label}
          className="bg-card border border-border rounded-xl px-3 py-2 min-w-0"
        >
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium mb-0.5">
            {label}
          </div>
          <div className={`font-mono text-sm font-semibold tabular-nums ${color}`}>
            {value}
          </div>
        </div>
      ))}
    </div>
  );
}
