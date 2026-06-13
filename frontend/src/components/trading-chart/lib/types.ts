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
  | 'sma' | 'ema' | 'wma' | 'hma' | 'supertrend'
  | 'rsi' | 'macd' | 'stochastic' | 'adx'
  | 'bb' | 'atr'
  | 'obv' | 'vwap' | 'volume_profile'

export type IndicatorType = 'overlay' | 'panel'
export type IndicatorCategory = 'TREND' | 'MOMENTUM' | 'VOLATILITY' | 'VOLUME'

export const SOURCES = ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4'] as const
export type Source = typeof SOURCES[number]

// Settings field schema. 'int'/'float'/'level'/'source' are INPUTS (drive
// recomputation and instanceId); 'color'/'width' are STYLE (applied live).
export type FieldDef =
  | { kind: 'int' | 'float'; key: string; label: string; default: number; min: number; max: number; step?: number }
  | { kind: 'level'; key: string; label: string; default: number; min: number; max: number }
  | { kind: 'source'; key: string; label: string; default: Source }
  | { kind: 'color'; key: string; label: string; default: string }
  | { kind: 'width'; key: string; label: string; default: 1 | 2 | 3 }

export type InputValue = number | Source

export interface ActiveIndicator {
  instanceId: string                          // `${id}-${input values}` — inputs only, never style
  indicatorId: IndicatorId
  inputs: Record<string, InputValue>
  style: Record<string, string | number>
  hidden: boolean
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
