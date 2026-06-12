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
  train_samples?: number;
  test_samples?: number;
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

export interface BacktestTrade {
  date_entry: string;
  date_exit: string;
  entry_price: number;
  exit_price: number;
  pnl_pct: number;
}

export interface BacktestStats {
  num_trades: number;
  win_rate: number;
  total_return_pct: number;
  avg_gain_pct: number;
  avg_loss_pct: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  profit_factor: number | null;
  exposure_pct: number;
  avg_hold_days: number;
  buy_hold_return_pct: number;
}

export type BacktestStrategy = "indicator" | "ml";

export interface BacktestResponse {
  ticker: string;
  trades: BacktestTrade[];
  equity_curve: Array<{ date: string; equity: number; benchmark: number }>;
  stats: BacktestStats;
  strategy: BacktestStrategy;
  strategy_description: string;
  error: string | null;
}

export function useBacktest(
  ticker: string,
  period = "1y",
  strategy: BacktestStrategy = "indicator",
  enabled = true,
) {
  return useQuery({
    queryKey: ["backtest", ticker, period, strategy],
    queryFn: () =>
      apiFetch<BacktestResponse>("/api/v1/analysis/backtest", { ticker, period, strategy }),
    staleTime: 6 * 60 * 60 * 1000,
    enabled: !!ticker && enabled,
  });
}
