import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "./client";

export interface ChainRow {
  strike: number;
  expiry: string;
  CE_ltp: number; CE_oi: number; CE_chg_oi: number; CE_iv: number; CE_volume: number; CE_bid: number; CE_ask: number;
  PE_ltp: number; PE_oi: number; PE_chg_oi: number; PE_iv: number; PE_volume: number; PE_bid: number; PE_ask: number;
}

export interface OptionsChainResponse {
  symbol: string;
  underlying_value: number;
  timestamp: string;
  expiry_dates: string[];
  chain: ChainRow[];
}

export interface TradeRec {
  option: string;
  option_type: string;
  strike: number;
  expiry: string;
  premium: number;
  bid: number;
  ask: number;
  iv: number;
  oi: number;
  lot_size: number;
  capital_1_lot: number;
  stop_loss: number;
  target: number;
  sl_pct: number;
  target_pct: number;
  sl_points: number;
  target_points: number;
  max_loss_1_lot: number;
  max_profit_1_lot: number;
  error?: string;
}

export interface RecommendResponse {
  symbol: string;
  spot: number;
  timestamp: string;
  underlying_signal: "BUY" | "SELL" | "HOLD";
  confidence: number;
  option_type: "CALL" | "PUT" | null;
  pcr: { pcr: number | null; signal: string };
  max_pain: number | null;
  expiry_dates: string[];
  selected_expiry: string;
  signal_components: Record<string, { signal: string; points: number }>;
  recommendations: Record<string, TradeRec> | null;
  message: string;
}

export function useOptionsChain(symbol: string, expiry?: string) {
  const params: Record<string, string> = { symbol };
  if (expiry) params.expiry = expiry;
  return useQuery({
    queryKey: ["options-chain", symbol, expiry ?? "nearest"],
    queryFn: () => apiFetch<OptionsChainResponse>("/api/v1/options/chain", params),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
    enabled: !!symbol,
  });
}

export function useOptionsRecommend(symbol: string, expiry?: string) {
  const params: Record<string, string> = { symbol, style: "both" };
  if (expiry) params.expiry = expiry;
  return useQuery({
    queryKey: ["options-recommend", symbol, expiry ?? "nearest"],
    queryFn: () => apiFetch<RecommendResponse>("/api/v1/options/recommend", params),
    staleTime: 60 * 1000,
    refetchInterval: 60 * 1000,
    enabled: !!symbol,
  });
}
