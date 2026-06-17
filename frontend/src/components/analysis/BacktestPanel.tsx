"use client";
import { useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from "recharts";
import { AlertCircle, Cpu, Activity } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useBacktest, type BacktestStrategy, type OpenPosition } from "@/lib/api/analysis";
import { MethodologyNote } from "@/components/analysis/MethodologyNote";

const PERIODS = ["6mo", "1y", "2y"] as const;
type Period = typeof PERIODS[number];
const PERIOD_LABELS: Record<Period, string> = { "6mo": "6M", "1y": "1Y", "2y": "2Y" };

const STRATEGIES: Array<{ value: BacktestStrategy; label: string; icon: typeof Activity }> = [
  { value: "indicator", label: "Indicator", icon: Activity },
  { value: "ml", label: "ML Model", icon: Cpu },
  { value: "trend", label: "Trend", icon: Activity },
  { value: "meanrev", label: "Mean-Rev", icon: Activity },
  { value: "breakout", label: "Breakout", icon: Activity },
];

function OpenPositionCard({ position }: { position: OpenPosition }) {
  const pnlColor = position.unrealized_pnl_pct >= 0 ? "text-buy" : "text-sell";
  const stopDistPct = ((position.stop - position.current_price) / position.current_price * 100).toFixed(1);
  const targetDistPct = ((position.target - position.current_price) / position.current_price * 100).toFixed(1);
  return (
    <div className="bg-card border-2 border-primary/40 rounded-xl px-4 py-3 space-y-2">
      <div className="text-[10px] text-primary uppercase tracking-wider font-semibold">
        Open position
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Entry date</div>
          <div className="text-sm font-mono font-semibold">{position.date_entry}</div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Entry ₹</div>
          <div className="text-sm font-mono font-semibold">
            ₹{position.entry_price.toLocaleString("en-IN")}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Current ₹</div>
          <div className="text-sm font-mono font-semibold">
            ₹{position.current_price.toLocaleString("en-IN")}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Unrealised P&amp;L</div>
          <div className={`text-sm font-mono font-semibold ${pnlColor}`}>
            {position.unrealized_pnl_pct >= 0 ? "+" : ""}{position.unrealized_pnl_pct.toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Days held</div>
          <div className="text-sm font-mono font-semibold">{position.days_held}d</div>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Stop / Target</div>
          <div className="text-sm font-mono font-semibold">
            <span className="text-sell">₹{position.stop.toLocaleString("en-IN")}</span>
            <span className="text-[10px] text-muted-foreground ml-1">({stopDistPct}%)</span>
            {" / "}
            <span className="text-buy">₹{position.target.toLocaleString("en-IN")}</span>
            <span className="text-[10px] text-muted-foreground ml-1">(+{targetDistPct}%)</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function EquityTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; payload: { date: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const { date } = payload[0].payload;
  const equity = payload.find((p) => p.dataKey === "equity")?.value;
  const benchmark = payload.find((p) => p.dataKey === "benchmark")?.value;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-xs shadow-md space-y-0.5">
      <div className="text-muted-foreground">{date}</div>
      {equity != null && (
        <div className={equity - 100 >= 0 ? "text-buy font-semibold" : "text-sell font-semibold"}>
          Strategy: {equity - 100 >= 0 ? "+" : ""}{(equity - 100).toFixed(1)}%
        </div>
      )}
      {benchmark != null && (
        <div className="text-muted-foreground">
          Buy &amp; hold: {benchmark - 100 >= 0 ? "+" : ""}{(benchmark - 100).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

interface Props {
  ticker: string;
  enabled?: boolean;
  strategy: BacktestStrategy;
  onStrategyChange: (s: BacktestStrategy) => void;
}

export function BacktestPanel({ ticker, enabled = true, strategy, onStrategyChange }: Props) {
  const [period, setPeriod] = useState<Period>("1y");
  const { data, isLoading, isError } = useBacktest(ticker, period, strategy, enabled);

  const eqByDate = new Map((data?.equity_curve ?? []).map((p) => [p.date, p.equity]));

  const fmtPct = (v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;

  const statCards = data
    ? [
        {
          label: "Total Return",
          value: fmtPct(data.stats.total_return_pct),
          sub: `Buy & hold ${fmtPct(data.stats.buy_hold_return_pct)}`,
          color: data.stats.total_return_pct >= 0 ? "text-buy" : "text-sell",
        },
        {
          label: "Win Rate",
          value: `${(data.stats.win_rate * 100).toFixed(0)}%`,
          sub: "Winning round trips",
          color: "text-foreground",
        },
        {
          label: "# Trades",
          value: String(data.stats.num_trades),
          sub: "Round trips",
          color: "text-foreground",
        },
        {
          label: "Avg Gain",
          value: `+${data.stats.avg_gain_pct.toFixed(1)}%`,
          sub: "Mean winning trade",
          color: "text-buy",
        },
        {
          label: "Avg Loss",
          value: `${data.stats.avg_loss_pct.toFixed(1)}%`,
          sub: "Mean losing trade",
          color: "text-sell",
        },
        {
          label: "Max Drawdown",
          value: `${data.stats.max_drawdown_pct.toFixed(1)}%`,
          sub: "Peak-to-trough equity",
          color: "text-sell",
        },
        {
          label: "Sharpe",
          value: data.stats.sharpe_ratio.toFixed(2),
          sub: "Annualised, daily returns",
          color: "text-foreground",
        },
        {
          label: "Profit Factor",
          value: data.stats.profit_factor != null ? data.stats.profit_factor.toFixed(2) : "∞",
          sub: "Gross gains ÷ losses",
          color: "text-foreground",
        },
        {
          label: "Exposure",
          value: `${data.stats.exposure_pct.toFixed(0)}%`,
          sub: "Time in market",
          color: "text-foreground",
        },
        {
          label: "Avg Hold",
          value: `${data.stats.avg_hold_days.toFixed(0)}d`,
          sub: "Calendar days per trade",
          color: "text-foreground",
        },
        {
          label: "CAGR",
          value: fmtPct(data.stats.cagr_pct),
          sub: "Annualised return",
          color: data.stats.cagr_pct >= 0 ? "text-buy" : "text-sell",
        },
        {
          label: "Sortino",
          value: data.stats.sortino_ratio.toFixed(2),
          sub: "Downside-adjusted return",
          color: "text-foreground",
        },
        {
          label: "Calmar",
          value: data.stats.calmar_ratio != null ? data.stats.calmar_ratio.toFixed(2) : "—",
          sub: "CAGR ÷ max drawdown",
          color: "text-foreground",
        },
      ]
    : [];

  return (
    <div className="space-y-4">
      {/* Strategy + period selectors */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex gap-1.5">
          {STRATEGIES.map(({ value, label, icon: Icon }) => (
            <button
              key={value}
              onClick={() => onStrategyChange(value)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                strategy === value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
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
      </div>

      {/* What is this trading? */}
      {data?.strategy_description && (
        <p className="text-xs text-muted-foreground bg-muted/30 border border-border rounded-xl px-4 py-2.5">
          {data.strategy_description}
        </p>
      )}

      {isLoading ? (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {Array.from({ length: 10 }).map((_, i) => (
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
      ) : data.error ? (
        <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
          <AlertCircle size={18} className="opacity-40" />
          <span>{data.error}</span>
        </div>
      ) : (
        <>
          {/* Stats cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {statCards.map(({ label, value, sub, color }) => (
              <div key={label} className="bg-card border border-border rounded-xl px-3 py-3">
                <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">
                  {label}
                </div>
                <div className={`text-sm font-semibold font-mono ${color}`}>{value}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{sub}</div>
              </div>
            ))}
          </div>

          {/* Open position card */}
          {data.open_position && (
            <OpenPositionCard position={data.open_position} />
          )}

          {/* Equity curve vs benchmark with trade markers */}
          {data.equity_curve.length > 1 ? (
            <div className="bg-card border border-border rounded-2xl p-4">
              <ResponsiveContainer width="100%" height={240}>
                <ComposedChart
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
                  <Line
                    type="monotone"
                    dataKey="benchmark"
                    stroke="var(--color-muted-foreground)"
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    dot={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="var(--color-buy)"
                    strokeWidth={2}
                    fill="url(#equityGrad)"
                    dot={false}
                    activeDot={{ r: 3 }}
                  />
                  {data.trades.map((t, i) =>
                    eqByDate.has(t.date_entry) ? (
                      <ReferenceDot
                        key={`entry-${i}`}
                        x={t.date_entry}
                        y={eqByDate.get(t.date_entry)!}
                        r={4}
                        fill="var(--color-buy)"
                        stroke="var(--color-card)"
                        strokeWidth={1.5}
                      />
                    ) : null
                  )}
                  {data.trades.map((t, i) =>
                    eqByDate.has(t.date_exit) ? (
                      <ReferenceDot
                        key={`exit-${i}`}
                        x={t.date_exit}
                        y={eqByDate.get(t.date_exit)!}
                        r={4}
                        fill="var(--color-sell)"
                        stroke="var(--color-card)"
                        strokeWidth={1.5}
                      />
                    ) : null
                  )}
                </ComposedChart>
              </ResponsiveContainer>
              <p className="text-[10px] text-muted-foreground text-center mt-2">
                Green area = strategy equity (starts at ₹100) · dashed grey = buy &amp; hold ·
                dots = trade entries/exits · {data.stats.num_trades} trades · {PERIOD_LABELS[period]} window
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
                    <th className="text-left px-3 py-2 font-medium">Exit</th>
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
                      <td
                        className={`px-3 py-1.5 font-mono text-xs capitalize ${
                          t.exit_reason === "target"
                            ? "text-buy"
                            : t.exit_reason === "stop" || t.exit_reason === "trail"
                            ? "text-sell"
                            : "text-muted-foreground"
                        }`}
                      >
                        {t.exit_reason.charAt(0).toUpperCase() + t.exit_reason.slice(1)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <MethodologyNote title="How this backtest works">
            <p>
              Walk-forward simulation: each day the strategy sees only data up to that day
              (no look-ahead). Long-only, one position at a time, filled at the daily close.
              Entries are taken only when price is above the 200-day EMA (uptrend filter).
            </p>
            <p>
              Risk management: 2×ATR stop-loss (capped at 10% below entry), 1:3 ATR take-profit
              target, and SELL-signal exit — no trailing stop. Position sizing uses 1%-risk per trade.
            </p>
            <p>
              Not modelled: transaction costs, slippage, dividends, taxes. Past performance
              does not predict future results.
            </p>
          </MethodologyNote>
        </>
      )}
    </div>
  );
}
