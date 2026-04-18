import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useMarketStatus } from "./market";

export interface ScanResult {
  ticker: string;
  name: string;
  signal: "BUY" | "SELL" | "HOLD" | null;
  confidence: number | null;
  last_price: number | null;
  change_pct: number | null;
}

export interface ScanResponse {
  stocks: ScanResult[];
  count: number;
}

export function useScanner() {
  const { data: status } = useMarketStatus();
  const interval = status?.is_open === false ? 30 * 60 * 1000 : 10 * 60 * 1000;
  return useQuery({
    queryKey: ["scanner", "nifty50"],
    queryFn: () => apiFetch<ScanResponse>("/api/v1/market/scan"),
    staleTime: interval,
    refetchInterval: interval,
    retry: 1,
  });
}
