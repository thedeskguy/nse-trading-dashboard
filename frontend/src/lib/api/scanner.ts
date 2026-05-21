import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";
import { useMarketStatus } from "./market";

export type ScanIndex = "NIFTY50" | "NIFTY100" | "NIFTY200" | "NIFTY500";

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
  index: string;
}

export function useScanner(index: ScanIndex = "NIFTY50") {
  const { data: status } = useMarketStatus();
  const interval = status?.is_open === false ? 30 * 60 * 1000 : 10 * 60 * 1000;
  return useQuery({
    queryKey: ["scanner", index],
    queryFn: () => apiFetch<ScanResponse>(`/api/v1/market/scan?index=${index}`),
    staleTime: interval,
    refetchInterval: interval,
    retry: 1,
  });
}
