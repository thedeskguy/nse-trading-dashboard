"use client";
import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { AlertCircle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktest } from "@/lib/api/analysis";

const PERIODS = ["6mo", "1y", "2y"] as const;
type Period = typeof PERIODS[number];
const PERIOD_LABELS: Record<Period, string> = { "6mo": "6M", "1y": "1Y", "2y": "2Y" };

function EquityTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ value: number; payload: { date: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const { date } = payload[0].payload;
  const equity = payload[0].value;
  const ret = equity - 100;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-xs shadow-md">
      <div className="text-muted-foreground">{date}</div>
      <div className={ret >= 0 ? "text-buy font-semibold" : "text-sell font-semibold"}>
        {ret >= 0 ? "+" : ""}
        {ret.toFixed(1)}% return
      </div>
    </div>
  );
}

interface Props {
  ticker: string;
  enabled?: boolean;
}

export function BacktestPanel({ ticker, enabled = true }: Props) {
  const [period, setPeriod] = useState<Period>("1y");
  const { data, isLoading, isError } = useBacktest(ticker, period, enabled);

  return (
    <div className="space-y-4">
      {/* Period selector */}
      <div className="flex gap-1.5">
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
              period === p
                ? "bg-primary text-primary-foreground"
                : "bg-muted/60 text-muted-foreground hover:text-foreground"
            }`}
          >
            {PERIOD_LABELS[p]}
          </button>
        ))}
      </div>

      {isLoading ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-xl" />
            ))}
          </div>
          <Skeleton className="h-60 rounded-2xl" />
        </>
      ) : isError || !data ? (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
          <AlertCircle size={18} className="opacity-40" />
          <span>Backtest data unavailable</span>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {(
              [
                {
                  label: "Total Return",
                  value: `${data.stats.total_return_pct >= 0 ? "+" : ""}${data.stats.total_return_pct.toFixed(1)}%`,
                  color: data.stats.total_return_pct >= 0 ? "text-buy" : "text-sell",
                },
                {
                  label: "Win Rate",
                  value: `${(data.stats.win_rate * 100).toFixed(0)}%`,
                  color: "text-foreground",
                },
                {
                  label: "# Trades",
                  value: String(data.stats.num_trades),
                  color: "text-foreground",
                },
                {
                  label: "Avg Gain",
                  value: `+${data.stats.avg_gain_pct.toFixed(1)}%`,
                  color: "text-buy",
                },
                {
                  label: "Avg Loss",
                  value: `${data.stats.avg_loss_pct.toFixed(1)}%`,
                  color: "text-sell",
                },
                {
                  label: "Max Drawdown",
                  value: `${data.stats.max_drawdown_pct.toFixed(1)}%`,
                  color: "text-sell",
                },
              ] as const
            ).map(({ label, value, color }) => (
              <div key={label} className="bg-card border border-border rounded-xl px-3 py-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                  {label}
                </div>
                <div className={`text-sm font-semibold font-mono ${color}`}>{value}</div>
              </div>
            ))}
          </div>

          {/* Equity curve */}
          {data.equity_curve.length > 1 ? (
            <div className="bg-card border border-border rounded-2xl p-4">
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart
                  data={data.equity_curve}
                  margin={{ top: 8, right: 16, bottom: 0, left: 8 }}
                >
                  <defs>
                    <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-buy)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-buy)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={["auto", "auto"]}
                    tickFormatter={(v: number) => `${(v - 100).toFixed(0)}%`}
                    tick={{ fontSize: 10 }}
                    className="text-muted-foreground"
                  />
                  <Tooltip content={<EquityTooltip />} />
                  <ReferenceLine y={100} stroke="var(--color-border)" strokeWidth={1.5} />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="var(--color-buy)"
                    strokeWidth={2}
                    fill="url(#equityGrad)"
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
              <p className="text-[10px] text-muted-foreground text-center mt-2">
                Equity curve starts at ₹100 · BUY→SELL indicator strategy ·{" "}
                {data.stats.num_trades} trades · {PERIOD_LABELS[period]} window
              </p>
            </div>
          ) : (
            <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm">
              No trades generated in this period
            </div>
          )}

          {/* Trade log */}
          {data.trades.length > 0 && (
            <div className="bg-muted/30 rounded-xl border border-border overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/50 text-muted-foreground">
                    <th className="text-left px-3 py-2 font-medium">Entry</th>
                    <th className="text-left px-3 py-2 font-medium">Exit</th>
                    <th className="text-right px-3 py-2 font-medium">Entry ₹</th>
                    <th className="text-right px-3 py-2 font-medium">Exit ₹</th>
                    <th className="text-right px-3 py-2 font-medium">P&amp;L %</th>
                  </tr>
                </thead>
                <tbody>
                  {data.trades.map((t, i) => (
                    <tr key={i} className="border-b border-border/30 last:border-0">
                      <td className="px-3 py-1.5 font-mono">{t.date_entry}</td>
                      <td className="px-3 py-1.5 font-mono">{t.date_exit}</td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        ₹{t.entry_price.toLocaleString("en-IN")}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        ₹{t.exit_price.toLocaleString("en-IN")}
                      </td>
                      <td
                        className={`px-3 py-1.5 text-right font-mono font-semibold ${
                          t.pnl_pct >= 0 ? "text-buy" : "text-sell"
                        }`}
                      >
                        {t.pnl_pct >= 0 ? "+" : ""}
                        {t.pnl_pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
