"use client";
import { cn } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ChevronDown } from "lucide-react";
import {
  INTERVALS,
  PERIODS,
  INTERVAL_LABELS,
  PERIOD_LABELS,
  VALID_COMBOS,
  coercePeriod,
  type Interval,
  type Period,
} from "@/lib/chartRanges";

interface Props {
  interval: Interval;
  period: Period;
  onChange: (next: { interval: Interval; period: Period }) => void;
}

export function ChartControls({ interval, period, onChange }: Props) {
  const validPeriods = VALID_COMBOS[interval];

  const selectInterval = (next: Interval) => {
    onChange({ interval: next, period: coercePeriod(next, period) });
  };

  const selectPeriod = (next: Period) => {
    onChange({ interval, period: next });
  };

  return (
    <div className="flex items-center gap-2">
      <Picker
        label="Candle"
        value={INTERVAL_LABELS[interval]}
        options={INTERVALS.map((i) => ({
          key: i,
          label: INTERVAL_LABELS[i],
          selected: i === interval,
          onSelect: () => selectInterval(i),
        }))}
      />
      <Picker
        label="Range"
        value={PERIOD_LABELS[period]}
        options={PERIODS.map((p) => {
          const enabled = validPeriods.includes(p);
          return {
            key: p,
            label: PERIOD_LABELS[p],
            selected: p === period,
            disabled: !enabled,
            onSelect: enabled ? () => selectPeriod(p) : undefined,
          };
        })}
      />
    </div>
  );
}

interface PickerOption {
  key: string;
  label: string;
  selected: boolean;
  disabled?: boolean;
  onSelect?: () => void;
}

function Picker({ label, value, options }: { label: string; value: string; options: PickerOption[] }) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-muted/60 hover:bg-muted text-foreground transition-colors"
      >
        <span className="text-muted-foreground">{label}:</span>
        <span className="font-semibold">{value}</span>
        <ChevronDown size={12} className="text-muted-foreground" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-32">
        {options.map((opt) => (
          <DropdownMenuItem
            key={opt.key}
            disabled={opt.disabled}
            onClick={opt.onSelect}
            className={cn(
              "text-xs cursor-pointer",
              opt.selected && "bg-accent font-semibold",
              opt.disabled && "opacity-40 cursor-not-allowed",
            )}
          >
            {opt.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
