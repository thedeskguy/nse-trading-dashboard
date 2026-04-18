"use client";
import Link from "next/link";
import { useMemo } from "react";
import { TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useIndices } from "@/lib/api/market";
import { useScanner, type ScanResult } from "@/lib/api/scanner";
import { useMarketStatus } from "@/lib/api/market";

// ── Formatters ──────────────────────────────────────────────────────────────

function fmt(v: number | null): string {
  if (v === null) return "—";
  return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function fmtPct(v: number | null): string {
  if (v === null) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtPrice(v: number | null): string {
  if (v === null) return "—";
  return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

// ── Index card ───────────────────────────────────────────────────────────────

function IndexCard({ name, value, change_pct, up }: {
  name: string;
  value: number | null;
  change_pct: number | null;
  up: boolean | null;
}) {
  const isUp = up === true;
  const isDown = up === false;

  return (
    <div className="bg-card border border-border rounded-2xl px-5 py-4 flex flex-col gap-1.5">
      <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">{name}</div>
      <div className="font-mono text-2xl font-semibold tabular-nums">{fmt(value)}</div>
      <div className={`flex items-center gap-1 text-sm font-medium ${
        isUp ? "text-buy" : isDown ? "text-sell" : "text-muted-foreground"
      }`}>
        {isUp && <TrendingUp size={13} />}
        {isDown && <TrendingDown size={13} />}
        <span>{fmtPct(change_pct)}</span>
      </div>
    </div>
  );
}

// ── Signal badge ─────────────────────────────────────────────────────────────

function SignalBadge({ signal }: { signal: ScanResult["signal"] }) {
  if (!signal) return <span className="w-10" />;
  const styles: Record<string, string> = {
    BUY:  "bg-buy/10 text-buy border-buy/20",
    SELL: "bg-sell/10 text-sell border-sell/20",
    HOLD: "bg-hold/10 text-hold border-hold/20",
  };
  return (
    <Badge className={`text-[10px] px-2 py-0 rounded-full border font-bold shrink-0 ${styles[signal]}`}>
      {signal}
    </Badge>
  );
}

// ── Stock row ────────────────────────────────────────────────────────────────

function StockRow({ stock }: { stock: ScanResult }) {
  const isUp = (stock.change_pct ?? 0) > 0;
  const isDown = (stock.change_pct ?? 0) < 0;

  return (
    <Link
      href={`/dashboard/stocks/${stock.ticker}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors rounded-xl group"
    >
      <SignalBadge signal={stock.signal} />
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium truncate">{stock.name}</div>
        <div className="text-[11px] text-muted-foreground font-mono">{stock.ticker.replace(".NS", "")}</div>
      </div>
      <div className="text-right shrink-0">
        <div className="text-sm font-mono font-semibold tabular-nums">{fmtPrice(stock.last_price)}</div>
        <div className={`text-xs font-mono font-semibold tabular-nums ${
          isUp ? "text-buy" : isDown ? "text-sell" : "text-muted-foreground"
        }`}>
          {isUp && "▲ "}{isDown && "▼ "}{fmtPct(stock.change_pct)}
        </div>
      </div>
    </Link>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { data: indicesData, isLoading: indicesLoading } = useIndices();
  const { data: scanData, isLoading: scanLoading } = useScanner();
  const { data: marketStatus } = useMarketStatus();

  const isMarketOpen = marketStatus?.is_open ?? null;

  // Sort by absolute % change, biggest movers first
  const movers = useMemo(() => {
    if (!scanData?.stocks) return [];
    return [...scanData.stocks].sort(
      (a, b) => Math.abs(b.change_pct ?? 0) - Math.abs(a.change_pct ?? 0),
    );
  }, [scanData]);

  const gainers = movers.filter((s) => (s.change_pct ?? 0) > 0).slice(0, 10);
  const losers  = movers.filter((s) => (s.change_pct ?? 0) < 0).slice(0, 10);

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">NSE · Live market overview</p>
        </div>
        {isMarketOpen !== null && (
          <div className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-full border ${
            isMarketOpen
              ? "bg-buy/10 text-buy border-buy/20"
              : "bg-muted text-muted-foreground border-border"
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isMarketOpen ? "bg-buy animate-pulse" : "bg-muted-foreground"}`} />
            {isMarketOpen ? "Market Open" : "Market Closed"}
          </div>
        )}
      </div>

      {/* Indices */}
      <div className="grid grid-cols-3 gap-3">
        {indicesLoading
          ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)
          : (indicesData?.indices ?? [
              { key: "NIFTY50", name: "NIFTY 50", value: null, change_pct: null, up: null },
              { key: "BANKNIFTY", name: "BANKNIFTY", value: null, change_pct: null, up: null },
              { key: "SENSEX", name: "SENSEX", value: null, change_pct: null, up: null },
            ]).map(({ key, ...rest }) => (
              <IndexCard key={key} {...rest} />
            ))}
      </div>

      {/* Nifty 50 Movers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-base">Nifty 50 Movers</h2>
            <p className="text-muted-foreground text-xs mt-0.5">Biggest moves in today's session · click any stock to analyse</p>
          </div>
          <Link
            href="/dashboard/scanner"
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            View all 50
            <ArrowRight size={12} />
          </Link>
        </div>

        {scanLoading ? (
          <div className="grid md:grid-cols-2 gap-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="bg-card border border-border rounded-2xl overflow-hidden">
                <div className="px-4 py-3 border-b border-border">
                  <Skeleton className="h-4 w-20" />
                </div>
                {Array.from({ length: 6 }).map((_, j) => (
                  <div key={j} className="px-4 py-3 flex items-center gap-3">
                    <Skeleton className="h-5 w-10 rounded-full" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-3.5 w-32" />
                      <Skeleton className="h-3 w-16" />
                    </div>
                    <div className="space-y-1.5 text-right">
                      <Skeleton className="h-3.5 w-20 ml-auto" />
                      <Skeleton className="h-3 w-12 ml-auto" />
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : movers.length === 0 ? (
          <div className="bg-card border border-border rounded-2xl py-12 text-center text-muted-foreground text-sm">
            No data yet — scanner runs every 10 minutes
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-3">
            {/* Gainers */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center gap-2">
                <TrendingUp size={13} className="text-buy" />
                <span className="text-xs font-semibold text-buy uppercase tracking-wider">Top Gainers</span>
              </div>
              <div className="divide-y divide-border/50">
                {gainers.map((s) => <StockRow key={s.ticker} stock={s} />)}
              </div>
            </div>

            {/* Losers */}
            <div className="bg-card border border-border rounded-2xl overflow-hidden">
              <div className="px-4 py-3 border-b border-border flex items-center gap-2">
                <TrendingDown size={13} className="text-sell" />
                <span className="text-xs font-semibold text-sell uppercase tracking-wider">Top Losers</span>
              </div>
              <div className="divide-y divide-border/50">
                {losers.map((s) => <StockRow key={s.ticker} stock={s} />)}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
