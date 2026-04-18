"use client";
import { useEffect, useState } from "react";
import { Clock } from "lucide-react";

interface DataFreshnessProps {
  updatedAt: number | undefined; // ms timestamp from react-query dataUpdatedAt
  className?: string;
}

function elapsed(updatedAt: number): string {
  const diffMs = Date.now() - updatedAt;
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins === 1) return "1 min ago";
  return `${mins} min ago`;
}

export function DataFreshness({ updatedAt, className = "" }: DataFreshnessProps) {
  const [label, setLabel] = useState<string>("");

  useEffect(() => {
    if (!updatedAt) return;
    setLabel(elapsed(updatedAt));
    const id = setInterval(() => setLabel(elapsed(updatedAt)), 30_000);
    return () => clearInterval(id);
  }, [updatedAt]);

  if (!updatedAt || !label) return null;

  return (
    <span className={`inline-flex items-center gap-1 text-xs text-muted-foreground ${className}`}>
      <Clock className="w-3 h-3" />
      {label}
    </span>
  );
}
