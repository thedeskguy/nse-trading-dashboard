"use client";
import { useEffect } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center px-6">
      <AlertCircle size={40} className="text-muted-foreground opacity-40" />
      <div>
        <p className="font-semibold text-foreground">Something went wrong</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">
          {error.message || "An unexpected error occurred. Try refreshing."}
        </p>
      </div>
      <Button onClick={reset} variant="outline" size="sm" className="gap-2 rounded-xl">
        <RefreshCw size={13} />
        Try again
      </Button>
    </div>
  );
}
