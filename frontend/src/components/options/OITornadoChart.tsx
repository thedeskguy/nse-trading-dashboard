"use client";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell, ReferenceLine,
} from "recharts";
import type { ChainRow } from "@/lib/api/options";

interface Props {
  chain: ChainRow[];
  spot: number;
  maxStrikes?: number;
}

function fmtOI(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`;
  return String(v);
}

export function OITornadoChart({ chain, spot, maxStrikes = 20 }: Props) {
  // Pick the N strikes closest to spot
  const sorted = [...chain].sort(
    (a, b) => Math.abs(a.strike - spot) - Math.abs(b.strike - spot)
  );
  const nearby = sorted.slice(0, maxStrikes);
  nearby.sort((a, b) => b.strike - a.strike); // descending so ATM is near top

  const data = nearby.map((row) => ({
    strike: row.strike,
    CE: -row.CE_oi,   // negative → goes left
    PE: row.PE_oi,    // positive → goes right
    atm: Math.abs(row.strike - spot) < 50,
  }));

  const maxOI = Math.max(...data.flatMap((d) => [Math.abs(d.CE), d.PE]));

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const ceOI = Math.abs(payload.find((p: any) => p.dataKey === "CE")?.value ?? 0);
    const peOI = payload.find((p: any) => p.dataKey === "PE")?.value ?? 0;
    return (
      <div className="bg-card border border-border rounded-xl px-3 py-2 text-xs space-y-1">
        <p className="font-semibold">Strike {label}</p>
        <p className="text-sell">CE OI: {ceOI.toLocaleString("en-IN")}</p>
        <p className="text-buy">PE OI: {peOI.toLocaleString("en-IN")}</p>
      </div>
    );
  };

  return (
    <div className="bg-card border border-border rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">OI Tornado</h3>
        <div className="flex items-center gap-4 text-[10px] text-muted-foreground">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm inline-block bg-sell/70" />CE OI</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm inline-block bg-buy/70" />PE OI</span>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={Math.max(300, nearby.length * 22)}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 0, right: 8, left: 0, bottom: 0 }}
          barCategoryGap="20%"
          barGap={0}
        >
          <XAxis
            type="number"
            domain={[-maxOI * 1.05, maxOI * 1.05]}
            tickFormatter={(v) => fmtOI(Math.abs(v))}
            tick={{ fontSize: 10, fill: "rgba(255,255,255,0.35)" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="strike"
            tick={({ x, y, payload }) => {
              const isAtm = Math.abs(payload.value - spot) < 50;
              return (
                <text x={x} y={y} dy={4} textAnchor="end" fontSize={10}
                  fill={isAtm ? "hsl(var(--primary))" : "rgba(255,255,255,0.5)"}
                  fontWeight={isAtm ? 700 : 400}
                >
                  {payload.value}
                </text>
              );
            }}
            width={50}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "rgba(255,255,255,0.03)" }} />
          <ReferenceLine x={0} stroke="rgba(255,255,255,0.15)" />
          <Bar dataKey="CE" radius={[0, 2, 2, 0]} maxBarSize={14}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.atm ? "#FF6B6B" : "#FF453A80"} />
            ))}
          </Bar>
          <Bar dataKey="PE" radius={[2, 0, 0, 2]} maxBarSize={14}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.atm ? "#4ADE80" : "#30D15880"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
