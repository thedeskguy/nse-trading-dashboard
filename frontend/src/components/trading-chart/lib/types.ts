// frontend/src/components/trading-chart/lib/types.ts
import type { Time } from 'lightweight-charts'

export interface Candle {
  timestamp: string   // "YYYY-MM-DD"
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export type IndicatorId =
  | 'ema' | 'supertrend'
  | 'rsi' | 'macd' | 'stochastic' | 'adx'
  | 'bb' | 'atr'
  | 'obv' | 'vwap' | 'volume_profile'

export type IndicatorType = 'overlay' | 'panel'
export type IndicatorCategory = 'TREND' | 'MOMENTUM' | 'VOLATILITY' | 'VOLUME'

export interface ActiveIndicator {
  instanceId: string                   // unique: "ema-20", "ema-50", "rsi-14"
  indicatorId: IndicatorId
  params: Record<string, number>
}

export interface LinePoint { time: Time; value: number }
export interface HistPoint { time: Time; value: number; color?: string }

export interface MACDResult {
  macd: LinePoint[]
  signal: LinePoint[]
  histogram: HistPoint[]
}
export interface BBResult {
  upper: LinePoint[]
  middle: LinePoint[]
  lower: LinePoint[]
}
export interface StochasticResult { k: LinePoint[]; d: LinePoint[] }
export interface SupertrendResult  { values: LinePoint[]; bullish: boolean[] }
export interface VolumeProfileBar  { price: number; volume: number; isUp: boolean }
