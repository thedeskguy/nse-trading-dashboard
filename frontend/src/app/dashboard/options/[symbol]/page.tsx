"use client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, RefreshCw } from "lucide-react";
import { useOptionsChain, useOptionsRecommend } from "@/lib/api/options";
import { DataFreshness } from "@/components/ui/DataFreshness";
import { TradeCard } from "@/components/options/TradeCard";
import { OITornadoChart } from "@/components/options/OITornadoChart";
import { OptionsChainTable } from "@/components/options/OptionsChainTable";
import { PayoffChart } from "@/components/options/PayoffChart";
import { StatsStrip } from "@/components/options/StatsStrip";

const SYMBOLS = ["NIFTY", "BANKNIFTY", "MIDCPNIFTY"] as const;
type Symbol = typeof SYMBOLS[number];

const LOT_SIZES: Record<Symbol, number> = {
  NIFTY: 75,
  BANKNIFTY: 15,
  MIDCPNIFTY: 75,
};

function OfflineBanner({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl border border-sell/20 bg-sell/5 text-sm">
      <span className="text-sell text-xs font-medium">
        ⚡ Backend is cold-starting — first response takes ~30s on the free tier
      </span>
      <button
        onClick={onRetry}
        className="flex items-center gap-1.5 text-xs font-semibold text-sell hover:text-sell/80 transition-colors shrink-0"
      >
        <RefreshCw size={12} />
        Retry
      </button>
    </div>
  );
}

function OptionsDashboard({ symbol }: { symbol: Symbol }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [expiry, setExpiry] = useState<string | undefined>(undefined);

  const { data: chainData, isLoading: chainLoading, dataUpdatedAt: chainUpdatedAt } = useOptionsChain(symbol, expiry);
  const { data: recData, isLoading: recLoading, isError: recError, dataUpdatedAt: recUpdatedAt } = useOptionsRecommend(symbol, expiry);
  const dataUpdatedAt = recUpdatedAt || chainUpdatedAt;

  const spot = recData?.spot ?? chainData?.underlying_value ?? null;
  const expiries = recData?.expiry_dates ?? chainData?.expiry_dates ?? [];
  const isLoadingAny = chainLoading || recLoading;

  const signalColor =
    recData?.underlying_signal === "BUY" ? "bg-buy/10 text-buy border-buy/20" :
    recData?.underlying_signal === "SELL" ? "bg-sell/10 text-sell border-sell/20" :
    "bg-hold/10 text-hold border-hold/20";

  return (
    <div className="space-y-5 max-w-6xl">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Symbol switcher */}
        <div className="flex gap-1.5 pr-3 border-r border-border">
          {SYMBOLS.map((s) => (
            <button
              key={s}
              onClick={() => router.push(`/dashboard/options/${s}`)}
              className={`px-3 py-1.5 text-xs font-medium rounded-xl transition-colors ${
                s === symbol
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:text-foreground"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Spot + signal */}
        <div className="flex items-center gap-2">
          <span className="font-mono text-xl font-semibold">
            {isLoadingAny
              ? <Skeleton className="w-28 h-6 inline-block" />
              : spot != null
              ? `₹${spot.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`
              : "—"}
          </span>
          {recData && (
            <Badge className={`text-xs px-2.5 py-0.5 rounded-full border font-bold ${signalColor}`}>
              {recData.underlying_signal} {recData.confidence}%
            </Badge>
          )}
        </div>

        <DataFreshness updatedAt={dataUpdatedAt} className="ml-auto" />
      </div>

      {/* Offline banner — only shown on error */}
      {recError && (
        <OfflineBanner onRetry={() => {
          queryClient.invalidateQueries({ queryKey: ["options-recommend", symbol] });
          queryClient.invalidateQueries({ queryKey: ["options-chain", symbol] });
        }} />
      )}

      {/* Expiry picker */}
      <div className="flex flex-wrap gap-1.5 min-h-7">
        {isLoadingAny && expiries.length === 0
          ? Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="w-20 h-7 rounded-lg" />
            ))
          : expiries.slice(0, 8).map((exp) => (
              <button
                key={exp}
                onClick={() => setExpiry(exp === expiries[0] && !expiry ? undefined : exp)}
                className={`px-2.5 py-1 text-[11px] font-mono rounded-lg transition-colors ${
                  (expiry === exp) || (!expiry && exp === expiries[0])
                    ? "bg-primary/15 text-primary border border-primary/30"
                    : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >
                {exp}
              </button>
            ))}
      </div>

      {/* Stats strip — shown only when data available */}
      {recData && (
        <StatsStrip data={recData} chain={chainData?.chain} />
      )}
      {(recLoading || chainLoading) && !recData && (
        <div className="flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-24 rounded-xl" />
          ))}
        </div>
      )}

      {/* Recommendations — 2 columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recLoading ? (
          <>
            <Skeleton className="h-64 rounded-2xl" />
            <Skeleton className="h-64 rounded-2xl" />
          </>
        ) : recData ? (
          <>
            <TradeCard data={recData} style="intraday" />
            <TradeCard data={recData} style="positional" />
          </>
        ) : (
          <>
            <div className="bg-card border border-border rounded-2xl h-48 flex flex-col items-center justify-center gap-2 text-muted-foreground text-sm">
              <AlertCircle size={18} className="opacity-40" />
              <span>Trade data unavailable</span>
            </div>
            <div className="bg-card border border-border rounded-2xl h-48 flex flex-col items-center justify-center gap-2 text-muted-foreground text-sm">
              <AlertCircle size={18} className="opacity-40" />
              <span>Trade data unavailable</span>
            </div>
          </>
        )}
      </div>

      {/* OI Tornado + Chain + Payoff Tabs */}
      <Tabs defaultValue="tornado">
        <TabsList className="bg-muted/50 rounded-xl w-full flex justify-center gap-2 h-auto p-1">
          <TabsTrigger value="tornado" className="rounded-lg px-4 py-2 text-xs">OI Tornado</TabsTrigger>
          <TabsTrigger value="chain" className="rounded-lg px-4 py-2 text-xs">Options Chain</TabsTrigger>
          <TabsTrigger value="payoff" className="rounded-lg px-4 py-2 text-xs">Payoff Diagram</TabsTrigger>
        </TabsList>

        <TabsContent value="tornado" className="mt-4">
          {chainLoading ? (
            <Skeleton className="h-96 rounded-2xl" />
          ) : chainData?.chain?.length ? (
            <OITornadoChart chain={chainData.chain} spot={spot ?? 0} />
          ) : (
            <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
              <AlertCircle size={18} className="opacity-40" />
              {recError ? "Backend offline — OI data unavailable" : "No OI data available"}
            </div>
          )}
        </TabsContent>

        <TabsContent value="chain" className="mt-4">
          {chainLoading ? (
            <Skeleton className="h-96 rounded-2xl" />
          ) : chainData?.chain?.length ? (
            <OptionsChainTable chain={chainData.chain} spot={spot ?? 0} />
          ) : (
            <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
              <AlertCircle size={18} className="opacity-40" />
              {recError ? "Backend offline — chain data unavailable" : "No chain data available"}
            </div>
          )}
        </TabsContent>

        <TabsContent value="payoff" className="mt-4">
          {chainLoading ? (
            <Skeleton className="h-96 rounded-2xl" />
          ) : chainData?.chain?.length && spot != null ? (
            <PayoffChart
              chain={chainData.chain}
              spot={spot}
              lotSize={LOT_SIZES[symbol]}
            />
          ) : (
            <div className="bg-card border border-border rounded-2xl p-8 text-center text-muted-foreground text-sm flex flex-col items-center gap-2">
              <AlertCircle size={18} className="opacity-40" />
              {recError ? "Backend offline — chain data unavailable" : "No chain data to build payoff"}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function OptionsPage() {
  const params = useParams();
  const raw = Array.isArray(params.symbol) ? params.symbol[0] : params.symbol as string;
  const symbol = (raw?.toUpperCase() ?? "NIFTY") as Symbol;
  return <OptionsDashboard symbol={symbol} />;
}
