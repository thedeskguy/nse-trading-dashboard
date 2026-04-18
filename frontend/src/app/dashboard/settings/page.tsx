"use client";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Account & subscription management</p>
      </div>

      {/* Subscription card */}
      <div className="bg-card border border-border rounded-2xl p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-base">Subscription</h2>
          <Badge className="text-xs px-2.5 py-0.5 rounded-full border-0 bg-green-500/10 text-green-400">
            Beta — Free
          </Badge>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-green-400">
            <CheckCircle2 className="w-4 h-4" />
            <span>All features included during beta</span>
          </div>
          <p className="text-xs text-muted-foreground">
            TradeDash is free during the beta period. All features — including live options chain,
            OI analytics, and trade recommendations — are available to every account.
          </p>
        </div>
      </div>

      {/* Feature list */}
      <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
        <h2 className="font-semibold text-base">What&apos;s included</h2>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
          {[
            "Stock signals (BUY / HOLD / SELL)",
            "Candlestick price chart",
            "Fundamentals panel",
            "Live index overview",
            "Options chain (NIFTY, BANKNIFTY)",
            "OI Tornado + PCR analysis",
            "AI trade recommendations",
            "Nifty 50 scanner",
          ].map((label) => (
            <div key={label} className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-primary" />
              <span className="text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
