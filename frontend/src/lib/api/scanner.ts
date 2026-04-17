import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

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
  return useQuery({
    queryKey: ["scanner", "nifty50"],
    queryFn: () => apiFetch<ScanResponse>("/api/v1/market/scan"),
    staleTime: 10 * 60 * 1000,
    refetchInterval: 10 * 60 * 1000,
    retry: 1,
  });
}
