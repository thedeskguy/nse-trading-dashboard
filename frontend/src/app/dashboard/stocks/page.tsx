"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search } from "lucide-react";

const POPULAR = [
  "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
  "BHARTIARTL.NS", "SBIN.NS", "KOTAKBANK.NS", "ITC.NS", "LT.NS",
  "HINDUNILVR.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS",
];

export default function StocksPage() {
  const [query, setQuery] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      const ticker = query.trim().toUpperCase();
      const formatted = ticker.includes(".") ? ticker : `${ticker}.NS`;
      router.push(`/dashboard/stocks/${formatted}`);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <div>
        <h1 className="font-display text-2xl font-bold">Stocks</h1>
        <p className="text-muted-foreground text-sm mt-1">Search any NSE stock for live signals and analysis</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search ticker (e.g. RELIANCE, TCS, INFY)..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-10 h-11 rounded-xl border-border bg-muted/30 text-sm"
          />
        </div>
        <Button type="submit" className="h-11 px-6 rounded-xl bg-primary hover:bg-primary/90">
          Analyse
        </Button>
      </form>

      <div>
        <p className="text-xs text-muted-foreground uppercase tracking-wider mb-3">Popular Stocks</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR.map((ticker) => (
            <button
              key={ticker}
              onClick={() => router.push(`/dashboard/stocks/${ticker}`)}
              className="text-xs px-3 py-1.5 rounded-full bg-muted hover:bg-muted/70 text-muted-foreground hover:text-foreground transition-colors font-mono"
            >
              {ticker.replace(".NS", "")}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
