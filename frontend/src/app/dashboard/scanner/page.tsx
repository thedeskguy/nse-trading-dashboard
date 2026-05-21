"use client";
import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useScanner, type ScanResult, type ScanIndex } from "@/lib/api/scanner";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown, Minus, ArrowUpDown, RefreshCw, AlertCircle } from "lucide-react";
import { DataFreshness } from "@/components/ui/DataFreshness";

type SignalFilter = "ALL" | "BUY" | "HOLD" | "SELL";
type SortKey = "confidence" | "name" | "last_price" | "change_pct";

function SignalBadge({ signal }: { signal: ScanResult["signal"] }) {
  if (!signal) return <Badge variant="outline" className="text-xs text-muted-foreground border-border">—</Badge>;
  const styles = {
    BUY:  "bg-buy/10 text-buy border-buy/20",
    SELL: "bg-sell/10 text-sell border-sell/20",
    HOLD: "bg-hold/10 text-hold border-hold/20",
  };
  return <Badge className={`text-xs rounded-full px-2.5 border font-semibold ${styles[signal]}`}>{signal}</Badge>;
}

function ConfidenceBar({ value }: { value: number | null }) {
  if (value === null) return <span className="text-muted-foreground text-xs">—</span>;
  const color = value >= 60 ? "bg-buy" : value >= 40 ? "bg-hold" : "bg-sell";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs tabular-nums">{value}%</span>
    </div>
  );
}

const SCAN_INDICES: { key: ScanIndex; label: string; count: number }[] = [
  { key: "NIFTY50",  label: "Nifty 50",  count: 50  },
  { key: "NIFTY100", label: "Nifty 100", count: 100 },
  { key: "NIFTY200", label: "Nifty 200", count: 200 },
  { key: "NIFTY500", label: "Nifty 500", count: 500 },
];

export default function ScannerPage() {
  const router = useRouter();
  const [scanIndex, setScanIndex] = useState<ScanIndex>("NIFTY50");
  const { data, isLoading, isError, dataUpdatedAt, refetch, isFetching } = useScanner(scanIndex);
  const [filter, setFilter] = useState<SignalFilter>("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("confidence");
  const [sortAsc, setSortAsc] = useState(false);

  const stocks = useMemo(() => {
    if (!data?.stocks) return [];
    let rows = data.stocks.filter((s) => filter === "ALL" || s.signal === filter);
    rows = [...rows].sort((a, b) => {
      let av: number, bv: number;
      if (sortKey === "name") {
        av = 0; bv = a.name.localeCompare(b.name);
        return sortAsc ? bv : -bv;
      }
      av = (a[sortKey] ?? -Infinity) as number;
      bv = (b[sortKey] ?? -Infinity) as number;
      return sortAsc ? av - bv : bv - av;
    });
    return rows;
  }, [data, filter, sortKey, sortAsc]);

  const counts = useMemo(() => {
    const all = data?.stocks ?? [];
    return {
      ALL: all.length,
      BUY: all.filter((s) => s.signal === "BUY").length,
      HOLD: all.filter((s) => s.signal === "HOLD").length,
      SELL: all.filter((s) => s.signal === "SELL").length,
    };
  }, [data]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc((a) => !a);
    else { setSortKey(key); setSortAsc(false); }
  };

  return (
    <div className="space-y-5 max-w-6xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Scanner</h1>
          <p className="text-muted-foreground text-sm mt-1 flex items-center gap-2">
            Signal scan · 10-min cache
            <DataFreshness updatedAt={dataUpdatedAt} />
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors px-3 py-1.5 rounded-lg hover:bg-muted/50 disabled:opacity-50"
        >
          <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Index selector */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {SCAN_INDICES.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => { setScanIndex(key); setFilter("ALL"); }}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
              scanIndex === key
                ? "bg-primary text-primary-foreground"
                : "bg-muted/50 text-muted-foreground hover:text-foreground"
            }`}
          >
            {label}
            <span className="ml-1.5 opacity-60">{count}</span>
          </button>
        ))}
        {(scanIndex === "NIFTY200" || scanIndex === "NIFTY500") && (
          <span className="text-xs text-muted-foreground ml-1">
            · first load may take 30–60s
          </span>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 flex-wrap">
        {(["ALL", "BUY", "HOLD", "SELL"] as SignalFilter[]).map((f) => {
          const active = filter === f;
          const colors: Record<SignalFilter, string> = {
            ALL:  active ? "bg-foreground text-background" : "bg-muted/50 text-muted-foreground hover:text-foreground",
            BUY:  active ? "bg-buy/15 text-buy border border-buy/30" : "bg-muted/50 text-muted-foreground hover:text-foreground",
            HOLD: active ? "bg-hold/15 text-hold border border-hold/30" : "bg-muted/50 text-muted-foreground hover:text-foreground",
            SELL: active ? "bg-sell/15 text-sell border border-sell/30" : "bg-muted/50 text-muted-foreground hover:text-foreground",
          };
          return (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-colors ${colors[f]}`}
            >
              {f} {counts[f] > 0 && <span className="ml-1 opacity-60">{counts[f]}</span>}
            </button>
          );
        })}
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-2xl overflow-hidden overflow-x-auto">
        {isError ? (
          <div className="py-20 flex flex-col items-center gap-3 text-muted-foreground">
            <AlertCircle size={32} className="opacity-30" />
            <p className="text-sm">Scan failed — backend may be starting up. Try refreshing in 30s.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="text-left px-4 py-3 font-medium w-8">#</th>
                <th className="text-left px-4 py-3 font-medium">
                  <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort("name")}>
                    Company <ArrowUpDown size={11} />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium">
                  <button className="flex items-center gap-1 ml-auto hover:text-foreground transition-colors" onClick={() => toggleSort("last_price")}>
                    Price <ArrowUpDown size={11} />
                  </button>
                </th>
                <th className="text-right px-4 py-3 font-medium">
                  <button className="flex items-center gap-1 ml-auto hover:text-foreground transition-colors" onClick={() => toggleSort("change_pct")}>
                    Day % <ArrowUpDown size={11} />
                  </button>
                </th>
                <th className="text-center px-4 py-3 font-medium">Signal</th>
                <th className="text-left px-4 py-3 font-medium">
                  <button className="flex items-center gap-1 hover:text-foreground transition-colors" onClick={() => toggleSort("confidence")}>
                    Confidence <ArrowUpDown size={11} />
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {isLoading
                ? Array.from({ length: 10 }).map((_, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="px-4 py-3"><Skeleton className="h-3 w-4" /></td>
                      <td className="px-4 py-3"><Skeleton className="h-3 w-40" /></td>
                      <td className="px-4 py-3 text-right"><Skeleton className="h-3 w-20 ml-auto" /></td>
                      <td className="px-4 py-3 text-right"><Skeleton className="h-3 w-14 ml-auto" /></td>
                      <td className="px-4 py-3 text-center"><Skeleton className="h-5 w-12 mx-auto rounded-full" /></td>
                      <td className="px-4 py-3"><Skeleton className="h-3 w-28" /></td>
                    </tr>
                  ))
                : stocks.map((s, i) => (
                    <tr
                      key={s.ticker}
                      className="border-b border-border/50 last:border-0 hover:bg-muted/30 cursor-pointer transition-colors"
                      onClick={() => router.push(`/dashboard/stocks/${s.ticker}`)}
                    >
                      <td className="px-4 py-3 text-muted-foreground text-xs tabular-nums">{i + 1}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium leading-tight">{s.name}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{s.ticker.replace(".NS", "")}</div>
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums">
                        {s.last_price != null ? `₹${s.last_price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}` : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        {s.change_pct != null ? (
                          <span className={`flex items-center justify-end gap-0.5 text-xs font-medium tabular-nums ${s.change_pct >= 0 ? "text-buy" : "text-sell"}`}>
                            {s.change_pct >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                            {s.change_pct > 0 ? "+" : ""}{s.change_pct.toFixed(2)}%
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs flex items-center justify-end gap-0.5"><Minus size={11} />—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <SignalBadge signal={s.signal} />
                      </td>
                      <td className="px-4 py-3">
                        <ConfidenceBar value={s.confidence} />
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        )}

        {!isLoading && !isError && stocks.length === 0 && (
          <div className="py-12 text-center text-muted-foreground text-sm">
            No stocks match the <strong>{filter}</strong> filter.
          </div>
        )}
      </div>

      {isLoading && (
        <p className="text-xs text-muted-foreground text-center">
          Scanning {SCAN_INDICES.find(i => i.key === scanIndex)?.count} stocks — first load takes{" "}
          {scanIndex === "NIFTY500" ? "~60–90s" : scanIndex === "NIFTY200" ? "~30–60s" : "~15–20s"}…
        </p>
      )}
    </div>
  );
}
