"use client";
import { useSubscription } from "@/lib/api/payments";
import { UpgradeModal } from "./UpgradeModal";
import { Skeleton } from "@/components/ui/skeleton";
import { Lock } from "lucide-react";

interface PaywallGateProps {
  feature?: string; // e.g. "Options Dashboard"
  children: React.ReactNode;
}

export function PaywallGate({ feature = "this feature", children }: PaywallGateProps) {
  const { data, isLoading } = useSubscription();

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    );
  }

  if (data?.plan === "pro") {
    return <>{children}</>;
  }

  // Free tier — show upgrade prompt
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 p-8 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
        <Lock className="w-7 h-7 text-primary" />
      </div>
      <div className="space-y-2 max-w-sm">
        <h2 className="font-display text-xl font-semibold">Pro Feature</h2>
        <p className="text-muted-foreground text-sm leading-relaxed">
          {feature} is available on the Pro plan. Upgrade to get access to live options
          chain data, OI analysis, and trade recommendations.
        </p>
      </div>
      <UpgradeModal />
    </div>
  );
}
