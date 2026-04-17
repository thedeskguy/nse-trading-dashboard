"use client";
import { useSubscription } from "@/lib/api/payments";
import { UpgradeModal } from "@/components/payments/UpgradeModal";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Zap } from "lucide-react";

function formatDate(unix: number | null): string {
  if (!unix) return "—";
  return new Date(unix * 1000).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function SettingsPage() {
  const { data: sub, isLoading } = useSubscription();

  const isPro = sub?.plan === "pro";

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
          {isLoading ? (
            <Skeleton className="h-6 w-16 rounded-full" />
          ) : (
            <Badge
              className={`text-xs px-2.5 py-0.5 rounded-full border-0 ${
                isPro
                  ? "bg-primary/10 text-primary"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              {isPro ? "Pro" : "Free"}
            </Badge>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-40" />
            <Skeleton className="h-4 w-56" />
          </div>
        ) : isPro ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-sm text-green-500">
              <CheckCircle2 className="w-4 h-4" />
              <span>Active — renews {formatDate(sub?.current_period_end ?? null)}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              You have full access to all Pro features including live options chain, OI analytics,
              and trade recommendations.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <XCircle className="w-4 h-4" />
              <span>Free plan — limited access</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Upgrade to Pro to unlock the options dashboard, OI Tornado chart, trade
              recommendations, and upcoming scanner features.
            </p>
            <UpgradeModal
              trigger={
                <Button className="rounded-xl bg-primary hover:bg-primary/90 h-10 px-5 text-sm font-medium">
                  <Zap className="w-4 h-4 mr-2" />
                  Upgrade to Pro
                </Button>
              }
            />
          </div>
        )}
      </div>

      {/* Feature comparison */}
      <div className="bg-card border border-border rounded-2xl p-6 space-y-4">
        <h2 className="font-semibold text-base">What&apos;s included</h2>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
          {[
            { label: "Stock signals (BUY / HOLD / SELL)", free: true },
            { label: "Candlestick price chart", free: true },
            { label: "Fundamentals panel", free: true },
            { label: "Live index overview", free: true },
            { label: "Options chain (NIFTY, BANKNIFTY)", free: false },
            { label: "OI Tornado + PCR analysis", free: false },
            { label: "AI trade recommendations", free: false },
            { label: "Nifty 100 scanner", free: false },
          ].map(({ label, free }) => {
            const included = free || isPro;
            return (
              <div key={label} className={`flex items-center gap-2 ${included ? "" : "opacity-40"}`}>
                <CheckCircle2
                  className={`w-3.5 h-3.5 shrink-0 ${included ? "text-primary" : "text-muted-foreground"}`}
                />
                <span className="text-muted-foreground">{label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
