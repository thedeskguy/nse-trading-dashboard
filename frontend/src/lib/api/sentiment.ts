import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface Headline {
  title: string;
  source: string;
  url: string;
  published_at: string;
  sentiment: number; // -1..1
}

export interface SentimentReadout {
  score: number;        // -100..100
  label: "Bullish" | "Bearish" | "Neutral";
  confidence: number;   // 0..100
  article_count: number;
  insufficient: boolean;
  top_headlines: Headline[];
  scored_by?: "finbert" | "vader";
}

export interface MarketSentimentResponse {
  india: SentimentReadout;
  world: SentimentReadout;
  as_of: string;
}

export interface StockSentimentResponse {
  ticker: string;
  sentiment: SentimentReadout;
  sector: string | null;
  industry: SentimentReadout | null;
  market: { india_label: string; world_label: string };
}

export function useMarketSentiment() {
  return useQuery({
    queryKey: ["sentiment", "market"],
    queryFn: () => apiFetch<MarketSentimentResponse>("/api/v1/sentiment/market"),
    staleTime: 30 * 60 * 1000,
    retry: 2,
  });
}

export function useStockSentiment(ticker: string) {
  return useQuery({
    queryKey: ["sentiment", "stock", ticker],
    queryFn: () =>
      apiFetch<StockSentimentResponse>("/api/v1/sentiment/stock", { ticker }),
    staleTime: 60 * 60 * 1000,
    enabled: !!ticker,
  });
}
