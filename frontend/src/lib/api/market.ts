import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

// Polls market status once, then every 5 min. Used to adapt staleTime elsewhere.
export function useMarketStatus() {
  return useQuery({
    queryKey: ["market-status"],
    queryFn: () => apiFetch<{ is_open: boolean }>("/api/v1/market/status"),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    retry: false,
  });
}

// 5 min when market is open, 30 min when closed.
function adaptiveMs(isOpen: boolean | undefined, openMs: number): number {
  return isOpen === false ? 30 * 60 * 1000 : openMs;
}

export interface IndexData {
  key: string;
  name: string;
  value: number | null;
  change_pct: number | null;
  up: boolean | null;
}

export interface IndicesResponse {
  indices: IndexData[];
}

export function useIndices() {
  const { data: status } = useMarketStatus();
  const interval = adaptiveMs(status?.is_open, 5 * 60 * 1000);
  return useQuery({
    queryKey: ["indices"],
    queryFn: () => apiFetch<IndicesResponse>("/api/v1/market/indices"),
    staleTime: interval,
    refetchInterval: interval,
  });
}

export interface Candle {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  ema_9?: number | null;
  ema_21?: number | null;
  ema_50?: number | null;
  ema_200?: number | null;
  bb_upper?: number | null;
  bb_middle?: number | null;
  bb_lower?: number | null;
  rsi_14?: number | null;
  macd?: number | null;
  macd_signal?: number | null;
  macd_hist?: number | null;
  obv?: number | null;
}

export interface OHLCVResponse {
  ticker: string;
  candles: Candle[];
}

export interface SignalResponse {
  ticker: string;
  signal: "BUY" | "SELL" | "HOLD";
  confidence: number;
  last_price: number;
  stop_loss: number;
  target: number;
  components: Record<string, { signal: string; points: number; value?: string | number }>;
}

export function useSignal(ticker: string, interval = "1d", period = "3mo") {
  return useQuery({
    queryKey: ["signal", ticker, interval, period],
    queryFn: () => apiFetch<SignalResponse>("/api/v1/market/signal", { ticker, interval, period }),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker,
  });
}

export interface StockSearchResult {
  ticker: string;
  name: string;
}

export interface StockSearchResponse {
  results: StockSearchResult[];
}

export interface CompanyInfo {
  ticker: string;
  name: string;
}

export function useStockSearch(query: string) {
  return useQuery({
    queryKey: ["stock-search", query],
    queryFn: () => apiFetch<StockSearchResponse>("/api/v1/market/search", { q: query }),
    enabled: query.trim().length >= 1,
    staleTime: 60 * 1000,
  });
}

export function useCompanyInfo(ticker: string) {
  return useQuery({
    queryKey: ["company-info", ticker],
    queryFn: () => apiFetch<CompanyInfo>("/api/v1/market/company-info", { ticker }),
    enabled: !!ticker,
    staleTime: 24 * 60 * 60 * 1000, // 24h — company names don't change
  });
}

export function useOHLCV(
  ticker: string,
  interval = "1d",
  period = "3mo",
  withIndicators = false,
) {
  return useQuery({
    queryKey: ["ohlcv", ticker, interval, period, withIndicators],
    queryFn: () =>
      apiFetch<OHLCVResponse>("/api/v1/market/ohlcv", {
        ticker,
        interval,
        period,
        ...(withIndicators ? { with_indicators: "true" } : {}),
      }),
    staleTime: 5 * 60 * 1000,
    enabled: !!ticker,
  });
}
