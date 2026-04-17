"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { TrendingUp, TrendingDown } from "lucide-react";
import { useIndices } from "@/lib/api/market";

function fmt(v: number | null): string {
  if (v === null) return "—";
  return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function fmtPct(v: number | null): string {
  if (v === null) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export default function DashboardPage() {
  const { data, isLoading, isError } = useIndices();

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">Market overview · Live data</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {isLoading
          ? Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-2xl" />
            ))
          : isError
          ? [
              { key: "NIFTY50", name: "NIFTY 50" },
              { key: "BANKNIFTY", name: "BANKNIFTY" },
              { key: "SENSEX", name: "SENSEX" },
            ].map((idx) => (
              <Card key={idx.key} className="rounded-2xl border-border opacity-60">
                <CardHeader className="pb-2 pt-5 px-5">
                  <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {idx.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5">
                  <div className="font-mono text-2xl font-semibold tabular-nums text-muted-foreground">—</div>
                  <Badge className="mt-2 text-xs rounded-full px-2.5 py-0.5 border bg-muted text-muted-foreground border-border">
                    Backend offline
                  </Badge>
                </CardContent>
              </Card>
            ))
          : (data?.indices ?? []).map((idx) => (
              <Card key={idx.key} className="rounded-2xl border-border">
                <CardHeader className="pb-2 pt-5 px-5">
                  <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    {idx.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-5">
                  <div className="font-mono text-2xl font-semibold tabular-nums">
                    {fmt(idx.value)}
                  </div>
                  <Badge
                    className={`mt-2 text-xs rounded-full px-2.5 py-0.5 border ${
                      idx.up === null
                        ? "bg-muted text-muted-foreground border-border"
                        : idx.up
                        ? "bg-buy/10 text-buy border-buy/20"
                        : "bg-sell/10 text-sell border-sell/20"
                    }`}
                  >
                    {idx.up === true && <TrendingUp size={10} className="mr-1 inline" />}
                    {idx.up === false && <TrendingDown size={10} className="mr-1 inline" />}
                    {fmtPct(idx.change_pct)}
                  </Badge>
                </CardContent>
              </Card>
            ))}
      </div>

      <Card className="rounded-2xl border-border">
        <CardContent className="py-16 text-center">
          <p className="text-muted-foreground text-sm">
            Search for a stock above or use the{" "}
            <span className="text-foreground font-medium">Scanner</span> to view signals
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
