"use client";
import { cn } from "@/lib/utils";
import { INDICATOR_META, type IndicatorKey } from "./CandlestickChart";

const OVERLAY_ORDER: IndicatorKey[] = [
  "ema_9", "ema_21", "ema_50", "ema_200",
  "bb_upper", "bb_middle", "bb_lower",
];

const PANEL_ORDER: IndicatorKey[] = ["rsi", "macd", "obv"];

interface Props {
  selected: IndicatorKey[];
  onToggle: (key: IndicatorKey) => void;
}

function Chip({ k, on, onToggle }: { k: IndicatorKey; on: boolean; onToggle: () => void }) {
  const meta = INDICATOR_META[k];
  return (
    <button
      key={k}
      type="button"
      onClick={onToggle}
      aria-pressed={on}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium transition-colors",
        on
          ? "bg-foreground/10 text-foreground ring-1 ring-foreground/20"
          : "bg-muted/40 text-muted-foreground hover:bg-muted/70",
      )}
    >
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{ backgroundColor: on ? meta.color : "rgba(255,255,255,0.25)" }}
      />
      {meta.label}
    </button>
  );
}

export function IndicatorToggles({ selected, onToggle }: Props) {
  const active = new Set(selected);
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {OVERLAY_ORDER.map((k) => (
        <Chip key={k} k={k} on={active.has(k)} onToggle={() => onToggle(k)} />
      ))}
      <span className="mx-1 h-4 w-px bg-border" />
      {PANEL_ORDER.map((k) => (
        <Chip key={k} k={k} on={active.has(k)} onToggle={() => onToggle(k)} />
      ))}
    </div>
  );
}
