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
