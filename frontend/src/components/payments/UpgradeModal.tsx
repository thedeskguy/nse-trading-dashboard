"use client";
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useCreateSubscription } from "@/lib/api/payments";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Check, Zap } from "lucide-react";

declare global {
  interface Window {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    Razorpay: any;
  }
}

const PLANS = [
  {
    id: "monthly" as const,
    label: "Monthly",
    price: "₹499",
    period: "/month",
    badge: null,
  },
  {
    id: "annual" as const,
    label: "Annual",
    price: "₹3,999",
    period: "/year",
    badge: "Save 33%",
  },
];

const FEATURES = [
  "Live options chain (NIFTY, BANKNIFTY, MIDCPNIFTY)",
  "OI Tornado chart + PCR analysis",
  "AI trade recommendations with SL & targets",
  "Nifty 100 scanner (Phase 8)",
  "All stock signals + ML predictions",
];

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

interface UpgradeModalProps {
  trigger?: React.ReactNode;
}

export function UpgradeModal({ trigger }: UpgradeModalProps) {
  const [open, setOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<"monthly" | "annual">("monthly");
  const [scriptError, setScriptError] = useState(false);
  const queryClient = useQueryClient();
  const { mutateAsync: createSubscription, isPending } = useCreateSubscription();

  const handleUpgrade = async () => {
    setScriptError(false);
    const loaded = await loadRazorpayScript();
    if (!loaded) {
      setScriptError(true);
      return;
    }

    try {
      const { subscription_id } = await createSubscription(selectedPlan);
      const rzp = new window.Razorpay({
        key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID,
        subscription_id,
        name: "TradeDash",
        description: `Pro Plan — ${selectedPlan === "monthly" ? "Monthly" : "Annual"}`,
        theme: { color: "#2563eb" },
        handler: () => {
          // Payment successful — refetch subscription status
          queryClient.invalidateQueries({ queryKey: ["subscription"] });
          setOpen(false);
        },
      });
      rzp.open();
    } catch {
      setScriptError(true);
    }
  };

  return (
    <>
      <div onClick={() => setOpen(true)}>
        {trigger ?? (
          <Button className="rounded-xl bg-primary hover:bg-primary/90 px-6">
            <Zap className="w-4 h-4 mr-2" />
            Upgrade to Pro
          </Button>
        )}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md rounded-2xl border-border bg-card">
          <DialogHeader className="pb-2">
            <DialogTitle className="font-display text-xl">Upgrade to Pro</DialogTitle>
            <DialogDescription className="text-sm text-muted-foreground">
              Unlock the full platform — options, OI analytics, and more.
            </DialogDescription>
          </DialogHeader>

          {/* Plan picker */}
          <div className="flex gap-3">
            {PLANS.map((plan) => (
              <button
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={`flex-1 rounded-xl border p-4 text-left transition-colors ${
                  selectedPlan === plan.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-border/80"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-muted-foreground">{plan.label}</span>
                  {plan.badge && (
                    <Badge className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary border-0">
                      {plan.badge}
                    </Badge>
                  )}
                </div>
                <div className="flex items-baseline gap-0.5">
                  <span className="text-lg font-bold">{plan.price}</span>
                  <span className="text-xs text-muted-foreground">{plan.period}</span>
                </div>
              </button>
            ))}
          </div>

          {/* Features */}
          <ul className="space-y-2">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-start gap-2 text-sm">
                <Check className="w-4 h-4 text-primary mt-0.5 shrink-0" />
                <span>{f}</span>
              </li>
            ))}
          </ul>

          {scriptError && (
            <p className="text-xs text-destructive bg-destructive/10 border border-destructive/20 rounded-lg px-3 py-2">
              Payment service unavailable. Please try again or contact support.
            </p>
          )}

          <Button
            onClick={handleUpgrade}
            disabled={isPending}
            className="w-full rounded-xl h-11 bg-primary hover:bg-primary/90 font-medium"
          >
            {isPending ? "Setting up…" : `Subscribe — ${PLANS.find((p) => p.id === selectedPlan)?.price}`}
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Secured by Razorpay · Cancel anytime
          </p>
        </DialogContent>
      </Dialog>
    </>
  );
}
