import { cn } from "@/lib/utils";
import type { ChainRow } from "@/lib/api/options";

interface Props {
  chain: ChainRow[];
  spot: number;
}

function fmt(v: number, decimals = 2): string {
  if (!v && v !== 0) return "—";
  return v.toLocaleString("en-IN", { maximumFractionDigits: decimals });
}

function fmtOI(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

export function OptionsChainTable({ chain, spot }: Props) {
  // Sort descending by strike
  const rows = [...chain].sort((a, b) => b.strike - a.strike);

  return (
    <div className="bg-card border border-border rounded-2xl overflow-hidden">
      <div className="px-5 pt-4 pb-3 border-b border-border flex items-center justify-between">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Options Chain</h3>
        <span className="text-xs text-muted-foreground">Spot: <span className="font-mono text-foreground">₹{fmt(spot)}</span></span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-border/50">
              <th colSpan={4} className="py-2 text-center text-sell font-medium text-[11px] tracking-wide">CALL</th>
              <th className="py-2 text-center font-semibold text-[11px] tracking-wider text-muted-foreground">STRIKE</th>
              <th colSpan={4} className="py-2 text-center text-buy font-medium text-[11px] tracking-wide">PUT</th>
            </tr>
            <tr className="border-b border-border/50 text-muted-foreground">
              {["OI", "Volume", "IV", "LTP"].map((h) => (
                <th key={`ce-${h}`} className="px-2 py-1.5 text-right font-medium">{h}</th>
              ))}
              <th className="px-3 py-1.5 text-center font-semibold">—</th>
              {["LTP", "IV", "Volume", "OI"].map((h) => (
                <th key={`pe-${h}`} className="px-2 py-1.5 text-left font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const isATM = Math.abs(row.strike - spot) < 50;
              return (
                <tr
                  key={row.strike}
                  className={cn(
                    "border-b border-border/30 last:border-0 transition-colors",
                    isATM
                      ? "bg-primary/5 border-primary/20"
                      : "hover:bg-muted/20"
                  )}
                >
                  <td className="px-2 py-1.5 text-right font-mono text-sell/80">{fmtOI(row.CE_oi)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-muted-foreground">{fmtOI(row.CE_volume)}</td>
                  <td className="px-2 py-1.5 text-right font-mono text-muted-foreground">
                    {row.CE_iv > 0 ? `${row.CE_iv.toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-2 py-1.5 text-right font-mono font-medium text-sell">
                    {row.CE_ltp > 0 ? fmt(row.CE_ltp) : "—"}
                  </td>
                  <td className={cn(
                    "px-3 py-1.5 text-center font-mono font-bold",
                    isATM ? "text-primary text-[11px]" : "text-muted-foreground"
                  )}>
                    {row.strike.toLocaleString("en-IN")}
                    {isATM && <span className="ml-1 text-[8px] text-primary/60">ATM</span>}
                  </td>
                  <td className="px-2 py-1.5 text-left font-mono font-medium text-buy">
                    {row.PE_ltp > 0 ? fmt(row.PE_ltp) : "—"}
                  </td>
                  <td className="px-2 py-1.5 text-left font-mono text-muted-foreground">
                    {row.PE_iv > 0 ? `${row.PE_iv.toFixed(1)}%` : "—"}
                  </td>
                  <td className="px-2 py-1.5 text-left font-mono text-muted-foreground">{fmtOI(row.PE_volume)}</td>
                  <td className="px-2 py-1.5 text-left font-mono text-buy/80">{fmtOI(row.PE_oi)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
