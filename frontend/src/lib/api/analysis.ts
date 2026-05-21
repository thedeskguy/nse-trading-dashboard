import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface FundamentalsBreakdownItem {
  points: number;
  max: number;
  label: string;
}

export interface FundamentalsResponse {
  ticker: string;
  fundamentals: Record<string, number | string | null>;
  score?: number;
  grade?: "Strong" | "Fair" | "Weak";
  breakdown?: Record<string, FundamentalsBreakdownItem>;
}

export interface MLResponse {
  ticker: string;
  direction: "UP" | "DOWN" | null;
  probability: number;
  accuracy: number;
  feature_importance: Record<string, number>;
  error: string | null;
}

export function useFundamentals(ticker: string) {
  return useQuery({
    queryKey: ["fundamentals", ticker],
    queryFn: () => apiFetch<FundamentalsResponse>("/api/v1/analysis/fundamentals", { ticker }),
    staleTime: 4 * 60 * 60 * 1000,
    retry: 2,
    retryDelay: 1000,
    enabled: !!ticker,
  });
}

export function useMLPredict(ticker: string) {
  return useQuery({
    queryKey: ["ml-predict", ticker],
    queryFn: () => apiFetch<MLResponse>("/api/v1/analysis/ml-predict", { ticker }),
    staleTime: 60 * 60 * 1000,
    enabled: !!ticker,
  });
}

export interface ConfluenceComponent {
  points: number;
  label: string;
}

export interface ConfluenceTimeframe {
  timeframe: "1D" | "1W" | "1M";
  signal: "BUY" | "SELL" | "HOLD" | null;
  confidence: number | null;
  components: Record<string, ConfluenceComponent>;
}

export interface ConfluenceResponse {
  ticker: string;
  timeframes: ConfluenceTimeframe[];
  summary: {
    strength: string;
    buy_count: number;
    sell_count: number;
    hold_count: number;
  };
}

export function useConfluence(ticker: string) {
  return useQuery({
    queryKey: ["confluence", ticker],
    queryFn: () => apiFetch<ConfluenceResponse>("/api/v1/analysis/confluence", { ticker }),
    staleTime: 10 * 60 * 1000,
    enabled: !!ticker,
  });
}
