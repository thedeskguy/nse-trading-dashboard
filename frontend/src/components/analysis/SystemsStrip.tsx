import { cn } from "@/lib/utils";
import { Activity, Building2, Cpu } from "lucide-react";

interface Props {
  technical: { signal: string; confidence: number } | null;
  fundamental: { grade: string; score?: number } | null;
  ml: { direction: string | null; probability: number | null } | null;
  onSelectTab: (tab: string) => void;
}

function toneClass(value: string | null | undefined): string {
  if (!value) return "text-muted-foreground";
  if (["BUY", "UP", "Strong"].includes(value)) return "text-buy";
  if (["SELL", "DOWN", "Weak"].includes(value)) return "text-sell";
  return "text-hold";
}

export function SystemsStrip({ technical, fundamental, ml, onSelectTab }: Props) {
  const systems = [
    {
      tab: "technical",
      label: "Technical",
      icon: Activity,
      key: technical?.signal ?? null,
      value: technical ? `${technical.signal} · ${technical.confidence}%` : "—",
    },
    {
      tab: "fundamental",
      label: "Fundamental",
      icon: Building2,
      key: fundamental?.grade ?? null,
      value: fundamental
        ? `${fundamental.grade}${fundamental.score != null ? ` · ${Math.round(fundamental.score)}` : ""}`
        : "—",
    },
    {
      tab: "ml",
      label: "ML Model",
      icon: Cpu,
      key: ml?.direction ?? null,
      value: ml?.direction
        ? `${ml.direction}${ml.probability != null ? ` · ${Math.round(ml.probability * 100)}%` : ""}`
        : "—",
    },
  ];

  return (
    <div className="grid grid-cols-3 gap-3">
      {systems.map(({ tab, label, icon: Icon, key, value }) => (
        <button
          key={tab}
          onClick={() => onSelectTab(tab)}
          className="bg-card border border-border rounded-xl px-3 py-2.5 text-left hover:border-foreground/20 transition-colors"
        >
          <span className="flex items-center gap-1.5 text-[10px] text-muted-foreground uppercase tracking-wider">
            <Icon size={11} />
            {label}
          </span>
          <span className={cn("block text-sm font-semibold mt-0.5", toneClass(key))}>{value}</span>
        </button>
      ))}
    </div>
  );
}
