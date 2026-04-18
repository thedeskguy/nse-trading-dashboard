"use client";
import { useState, useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ChainRow } from "@/lib/api/options";

// ── Types ────────────────────────────────────────────────────────────────────

type OptionSide = "long" | "short";
type OptionType = "call" | "put";

interface Leg {
  side: OptionSide;
  type: OptionType;
  strike: number;
  premium: number;
  lots: number;
}

type Strategy =
  | "long_call"
  | "long_put"
  | "bull_call_spread"
  | "bear_put_spread"
  | "iron_condor"
  | "custom";

const STRATEGY_LABELS: Record<Strategy, string> = {
  long_call:       "Long Call",
  long_put:        "Long Put",
  bull_call_spread:"Bull Call Spread",
  bear_put_spread: "Bear Put Spread",
  iron_condor:     "Iron Condor",
  custom:          "Custom",
};

// ── Payoff math ──────────────────────────────────────────────────────────────

function legPayoff(leg: Leg, price: number): number {
  const intrinsic =
    leg.type === "call"
      ? Math.max(0, price - leg.strike)
      : Math.max(0, leg.strike - price);
  const perUnit = leg.side === "long" ? intrinsic - leg.premium : leg.premium - intrinsic;
  return perUnit * leg.lots;
}

function totalPayoff(legs: Leg[], price: number): number {
  return legs.reduce((sum, leg) => sum + legPayoff(leg, price), 0);
}

// Find breakeven points by sign changes
function breakevenPoints(prices: number[], payoffs: number[]): number[] {
  const result: number[] = [];
  for (let i = 0; i < payoffs.length - 1; i++) {
    if (
      payoffs[i] !== undefined &&
      payoffs[i + 1] !== undefined &&
      payoffs[i] * payoffs[i + 1] < 0
    ) {
      const t = -payoffs[i] / (payoffs[i + 1] - payoffs[i]);
      result.push(Math.round((prices[i] + t * (prices[i + 1] - prices[i])) * 100) / 100);
    }
  }
  return result;
}

// ── Strike helpers ───────────────────────────────────────────────────────────

function sortedStrikes(chain: ChainRow[]): number[] {
  return [...new Set(chain.map((r) => r.strike))].sort((a, b) => a - b);
}

function atmIndex(strikes: number[], spot: number): number {
  let best = 0;
  let bestDist = Infinity;
  strikes.forEach((s, i) => {
    const d = Math.abs(s - spot);
    if (d < bestDist) { bestDist = d; best = i; }
  });
  return best;
}

function premiumFor(chain: ChainRow[], strike: number, type: "call" | "put"): number {
  const row = chain.find((r) => r.strike === strike);
  if (!row) return 0;
  return type === "call" ? (row.CE_ltp || 0) : (row.PE_ltp || 0);
}

// ── Build default legs for a strategy ────────────────────────────────────────

function buildLegs(
  strategy: Strategy,
  strikes: number[],
  atm: number,
  chain: ChainRow[],
  lotSize: number,
): Leg[] {
  const s = (offset: number) => strikes[Math.min(Math.max(atm + offset, 0), strikes.length - 1)];
  const pr = (strike: number, type: "call" | "put") => premiumFor(chain, strike, type);

  switch (strategy) {
    case "long_call":
      return [{ side: "long", type: "call", strike: s(0), premium: pr(s(0), "call"), lots: lotSize }];
    case "long_put":
      return [{ side: "long", type: "put", strike: s(0), premium: pr(s(0), "put"), lots: lotSize }];
    case "bull_call_spread":
      return [
        { side: "long",  type: "call", strike: s(0), premium: pr(s(0), "call"), lots: lotSize },
        { side: "short", type: "call", strike: s(2), premium: pr(s(2), "call"), lots: lotSize },
      ];
    case "bear_put_spread":
      return [
        { side: "long",  type: "put", strike: s(0),  premium: pr(s(0),  "put"), lots: lotSize },
        { side: "short", type: "put", strike: s(-2), premium: pr(s(-2), "put"), lots: lotSize },
      ];
    case "iron_condor":
      return [
        { side: "short", type: "put",  strike: s(-2), premium: pr(s(-2), "put"),  lots: lotSize },
        { side: "long",  type: "put",  strike: s(-4), premium: pr(s(-4), "put"),  lots: lotSize },
        { side: "short", type: "call", strike: s(2),  premium: pr(s(2),  "call"), lots: lotSize },
        { side: "long",  type: "call", strike: s(4),  premium: pr(s(4),  "call"), lots: lotSize },
      ];
    default:
      return [];
  }
}

// ── Tooltip ──────────────────────────────────────────────────────────────────

function ChartTooltip({ active, payload }: { active?: boolean; payload?: Array<{ value: number; payload: { price: number } }> }) {
  if (!active || !payload?.length) return null;
  const { price } = payload[0].payload;
  const pnl = payload[0].value;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-xs shadow-md">
      <div className="text-muted-foreground">Spot: <span className="text-foreground font-mono">₹{price.toLocaleString("en-IN")}</span></div>
      <div className={pnl >= 0 ? "text-buy font-semibold" : "text-sell font-semibold"}>
        P&L: {pnl >= 0 ? "+" : ""}₹{Math.round(pnl).toLocaleString("en-IN")}
      </div>
    </div>
  );
}

// ── Main component ───────────────────────────────────────────────────────────

interface Props {
  chain: ChainRow[];
  spot: number;
  lotSize?: number;
}

export function PayoffChart({ chain, spot, lotSize = 75 }: Props) {
  const [strategy, setStrategy] = useState<Strategy>("long_call");

  const strikes = useMemo(() => sortedStrikes(chain), [chain]);
  const atm = useMemo(() => atmIndex(strikes, spot), [strikes, spot]);

  const legs = useMemo(
    () => buildLegs(strategy, strikes, atm, chain, lotSize),
    [strategy, strikes, atm, chain, lotSize],
  );

  // Price range: ±15% around spot
  const priceRange = useMemo(() => {
    const lo = Math.round(spot * 0.85);
    const hi = Math.round(spot * 1.15);
    const step = Math.max(1, Math.round((hi - lo) / 100));
    const pts: number[] = [];
    for (let p = lo; p <= hi; p += step) pts.push(p);
    return pts;
  }, [spot]);

  const chartData = useMemo(
    () => priceRange.map((price) => ({ price, pnl: Math.round(totalPayoff(legs, price)) })),
    [priceRange, legs],
  );

  const payoffs = chartData.map((d) => d.pnl);
  const maxProfit = Math.max(...payoffs);
  const maxLoss   = Math.min(...payoffs);
  const beVec     = breakevenPoints(priceRange, payoffs);

  const netPremium = legs.reduce((sum, l) => {
    return sum + (l.side === "long" ? -l.premium : l.premium) * l.lots;
  }, 0);

  return (
    <div className="space-y-4">
      {/* Strategy selector */}
      <div className="flex flex-wrap gap-1.5">
        {(Object.keys(STRATEGY_LABELS) as Strategy[])
          .filter((s) => s !== "custom")
          .map((s) => (
            <button
              key={s}
              onClick={() => setStrategy(s)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                strategy === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:text-foreground"
              }`}
            >
              {STRATEGY_LABELS[s]}
            </button>
          ))}
      </div>

      {/* Legs table */}
      {legs.length > 0 && (
        <div className="bg-muted/30 rounded-xl border border-border overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50 text-muted-foreground">
                <th className="text-left px-3 py-2 font-medium">Action</th>
                <th className="text-left px-3 py-2 font-medium">Type</th>
                <th className="text-right px-3 py-2 font-medium">Strike</th>
                <th className="text-right px-3 py-2 font-medium">Premium</th>
                <th className="text-right px-3 py-2 font-medium">Lots</th>
              </tr>
            </thead>
            <tbody>
              {legs.map((leg, i) => (
                <tr key={i} className="border-b border-border/30 last:border-0">
                  <td className={`px-3 py-1.5 font-semibold ${leg.side === "long" ? "text-buy" : "text-sell"}`}>
                    {leg.side === "long" ? "BUY" : "SELL"}
                  </td>
                  <td className="px-3 py-1.5 uppercase">{leg.type}</td>
                  <td className="px-3 py-1.5 text-right font-mono">₹{leg.strike.toLocaleString("en-IN")}</td>
                  <td className="px-3 py-1.5 text-right font-mono">₹{leg.premium.toFixed(2)}</td>
                  <td className="px-3 py-1.5 text-right">{leg.lots}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: "Net Premium", value: `${netPremium >= 0 ? "+" : ""}₹${Math.round(Math.abs(netPremium)).toLocaleString("en-IN")}`, color: netPremium >= 0 ? "text-buy" : "text-sell" },
          { label: "Max Profit",  value: maxProfit === Infinity ? "Unlimited" : `₹${maxProfit.toLocaleString("en-IN")}`, color: "text-buy" },
          { label: "Max Loss",    value: maxLoss === -Infinity ? "Unlimited" : `₹${Math.abs(maxLoss).toLocaleString("en-IN")}`, color: "text-sell" },
          { label: "Breakeven",   value: beVec.length ? beVec.map(b => `₹${b.toLocaleString("en-IN")}`).join(" / ") : "—", color: "text-foreground" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-card border border-border rounded-xl px-3 py-3">
            <div className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">{label}</div>
            <div className={`text-sm font-semibold font-mono ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Chart */}
      <div className="bg-card border border-border rounded-2xl p-4">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border/40" />
            <XAxis
              dataKey="price"
              tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
              tick={{ fontSize: 10 }}
              className="text-muted-foreground"
            />
            <YAxis
              tickFormatter={(v) => v >= 1000 || v <= -1000 ? `${(v / 1000).toFixed(1)}k` : String(v)}
              tick={{ fontSize: 10 }}
              className="text-muted-foreground"
            />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={0} stroke="hsl(var(--border))" strokeWidth={1.5} />
            <ReferenceLine
              x={spot}
              stroke="hsl(var(--primary))"
              strokeDasharray="4 2"
              strokeWidth={1.5}
              label={{ value: "Spot", position: "top", fontSize: 10, fill: "hsl(var(--primary))" }}
            />
            {beVec.map((be) => (
              <ReferenceLine
                key={be}
                x={be}
                stroke="hsl(var(--muted-foreground))"
                strokeDasharray="2 2"
                strokeWidth={1}
              />
            ))}
            <Line
              type="monotone"
              dataKey="pnl"
              stroke="hsl(var(--primary))"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
        <p className="text-[10px] text-muted-foreground text-center mt-2">
          At-expiry P&L in ₹ · Dashed vertical = spot price · Premiums from live chain
        </p>
      </div>
    </div>
  );
}
