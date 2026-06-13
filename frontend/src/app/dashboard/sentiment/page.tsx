"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Search } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useMarketSentiment, useStockSentiment } from "@/lib/api/sentiment";
import { useStockSearch } from "@/lib/api/market";
import { SentimentGauge } from "@/components/sentiment/SentimentGauge";
import { HeadlineList } from "@/components/sentiment/HeadlineList";
import { MethodologyNote } from "@/components/analysis/MethodologyNote";

// ── Inline ticker search (mirrors TopBar but calls onSelect instead of routing)

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

function TickerPicker({ onSelect }: { onSelect: (ticker: string) => void }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const debouncedQuery = useDebounce(query, 300);
  const { data, isFetching } = useStockSearch(debouncedQuery);
  const results = data?.results ?? [];
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const handleSelect = useCallback(
    (ticker: string) => {
      onSelect(ticker);
      setQuery("");
      setOpen(false);
    },
    [onSelect],
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const t = query.trim().toUpperCase();
      if (!t) return;
      handleSelect(t.includes(".") ? t : `${t}.NS`);
    }
    if (e.key === "Escape") setOpen(false);
  };

  return (
    <div ref={containerRef} className="relative max-w-xs">
      <Search
        size={13}
        className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none z-10"
      />
      <Input
        placeholder="Search a stock (e.g. RELIANCE)..."
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => query && setOpen(true)}
        onKeyDown={handleKeyDown}
        className="pl-8 h-9 rounded-full bg-muted border-0 text-sm focus-visible:ring-1 focus-visible:ring-primary/50"
      />
      {open && query.trim().length >= 1 && (
        <div className="absolute top-full mt-1.5 left-0 right-0 bg-card border border-border rounded-xl shadow-lg overflow-hidden z-50">
          {isFetching && results.length === 0 ? (
            <div className="px-3 py-2.5 text-xs text-muted-foreground">Searching…</div>
          ) : results.length === 0 ? (
            <div className="px-3 py-2.5 text-xs text-muted-foreground">No matches found</div>
          ) : (
            <ul>
              {results.map((r) => (
                <li key={r.ticker}>
                  <button
                    className="w-full text-left px-3 py-2.5 hover:bg-muted/60 transition-colors flex items-center justify-between gap-3"
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelect(r.ticker);
                    }}
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium truncate">{r.name}</div>
                      <div className="text-xs text-muted-foreground">{r.ticker}</div>
                    </div>
                    <span className="text-[10px] text-muted-foreground/60 shrink-0">NSE</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ── Skeleton placeholder for a gauge card

function GaugeSkeleton() {
  return (
    <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <Skeleton className="h-8 w-20" />
      <Skeleton className="h-2.5 rounded-full" />
      <div className="grid grid-cols-2 gap-3">
        <Skeleton className="h-14 rounded-xl" />
        <Skeleton className="h-14 rounded-xl" />
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SentimentPage() {
  const [ticker, setTicker] = useState("");

  const {
    data: marketData,
    isLoading: marketLoading,
    isError: marketError,
  } = useMarketSentiment();

  const {
    data: stockData,
    isLoading: stockLoading,
    isError: stockError,
  } = useStockSentiment(ticker);

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">News Sentiment</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Real-time market mood derived from financial news.
        </p>
      </div>

      {/* Market sentiment — India + World */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Market Overview
          </h2>
          {marketData?.as_of && (
            <span className="text-[11px] text-muted-foreground">
              as of {new Date(marketData.as_of).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST
            </span>
          )}
        </div>

        {marketError ? (
          <div className="bg-card border border-border rounded-2xl p-6 text-sm text-muted-foreground">
            Unable to load market sentiment. Please try again later.
          </div>
        ) : marketLoading ? (
          <div className="grid sm:grid-cols-2 gap-4">
            <GaugeSkeleton />
            <GaugeSkeleton />
          </div>
        ) : marketData ? (
          <>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="space-y-3">
                <SentimentGauge title="India Market" readout={marketData.india} />
                <HeadlineList headlines={marketData.india.top_headlines} />
              </div>
              <div className="space-y-3">
                <SentimentGauge title="World Market" readout={marketData.world} />
                <HeadlineList headlines={marketData.world.top_headlines} />
              </div>
            </div>
          </>
        ) : null}
      </section>

      {/* Stock drill-down */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          Stock Sentiment
        </h2>

        <TickerPicker onSelect={setTicker} />

        {ticker && (
          <div className="space-y-4">
            {stockError ? (
              <div className="bg-card border border-border rounded-2xl p-6 text-sm text-muted-foreground">
                Unable to load sentiment for {ticker}. Please try another symbol.
              </div>
            ) : stockLoading ? (
              <GaugeSkeleton />
            ) : stockData ? (
              <>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-base font-semibold font-mono">
                    {stockData.ticker.replace(".NS", "")}
                  </span>
                  {/* Market context chips */}
                  <Badge
                    className={cn(
                      "text-[10px] px-2 py-0 rounded-full border font-semibold",
                      stockData.market.india_label === "Bullish"
                        ? "bg-buy/10 text-buy border-buy/20"
                        : stockData.market.india_label === "Bearish"
                          ? "bg-sell/10 text-sell border-sell/20"
                          : "bg-hold/10 text-hold border-hold/20",
                    )}
                  >
                    India: {stockData.market.india_label}
                  </Badge>
                  <Badge
                    className={cn(
                      "text-[10px] px-2 py-0 rounded-full border font-semibold",
                      stockData.market.world_label === "Bullish"
                        ? "bg-buy/10 text-buy border-buy/20"
                        : stockData.market.world_label === "Bearish"
                          ? "bg-sell/10 text-sell border-sell/20"
                          : "bg-hold/10 text-hold border-hold/20",
                    )}
                  >
                    World: {stockData.market.world_label}
                  </Badge>
                </div>
                <SentimentGauge
                  title={`${stockData.ticker.replace(".NS", "")} Sentiment`}
                  readout={stockData.sentiment}
                />
                <HeadlineList headlines={stockData.sentiment.top_headlines} />
              </>
            ) : null}
          </div>
        )}
      </section>

      {/* Disclaimer */}
      <MethodologyNote title="About this sentiment analysis">
        <p>
          Sentiment scores are derived from recent financial news headlines using NLP-based
          analysis. They reflect news bias — not price direction, fundamental value, or a
          buy/sell recommendation. Past sentiment does not predict future returns. Always
          consult a SEBI-registered advisor before making investment decisions.
        </p>
      </MethodologyNote>
    </div>
  );
}
