// frontend/src/components/trading-chart/lib/indicators.ts
import type { IndicatorId, IndicatorType, IndicatorCategory } from './types'

export interface IndicatorDef {
  id: IndicatorId
  name: string
  category: IndicatorCategory
  type: IndicatorType
  defaultParams: Record<string, number>
  paramLabels: Record<string, string>
}

export const INDICATORS: IndicatorDef[] = [
  // TREND
  { id: 'ema',           name: 'EMA',            category: 'TREND',      type: 'overlay', defaultParams: { period: 20 },                        paramLabels: { period: 'Period' } },
  { id: 'supertrend',    name: 'Supertrend',      category: 'TREND',      type: 'overlay', defaultParams: { period: 10, multiplier: 3 },          paramLabels: { period: 'Period', multiplier: 'Multiplier' } },
  // MOMENTUM
  { id: 'rsi',           name: 'RSI',             category: 'MOMENTUM',   type: 'panel',   defaultParams: { period: 14 },                        paramLabels: { period: 'Period' } },
  { id: 'macd',          name: 'MACD',            category: 'MOMENTUM',   type: 'panel',   defaultParams: { fast: 12, slow: 26, signal: 9 },      paramLabels: { fast: 'Fast', slow: 'Slow', signal: 'Signal' } },
  { id: 'stochastic',    name: 'Stochastic',      category: 'MOMENTUM',   type: 'panel',   defaultParams: { k: 14, d: 3 },                       paramLabels: { k: '%K Period', d: '%D Period' } },
  { id: 'adx',           name: 'ADX',             category: 'MOMENTUM',   type: 'panel',   defaultParams: { period: 14 },                        paramLabels: { period: 'Period' } },
  // VOLATILITY
  { id: 'bb',            name: 'Bollinger Bands', category: 'VOLATILITY', type: 'overlay', defaultParams: { period: 20, stddev: 2 },              paramLabels: { period: 'Period', stddev: 'Std Dev' } },
  { id: 'atr',           name: 'ATR',             category: 'VOLATILITY', type: 'panel',   defaultParams: { period: 14 },                        paramLabels: { period: 'Period' } },
  // VOLUME
  { id: 'obv',           name: 'OBV',             category: 'VOLUME',     type: 'panel',   defaultParams: {},                                    paramLabels: {} },
  { id: 'vwap',          name: 'VWAP',            category: 'VOLUME',     type: 'overlay', defaultParams: {},                                    paramLabels: {} },
  { id: 'volume_profile',name: 'Volume Profile',  category: 'VOLUME',     type: 'overlay', defaultParams: { bins: 20 },                          paramLabels: { bins: 'Bins' } },
]

export const INDICATOR_MAP = Object.fromEntries(INDICATORS.map(d => [d.id, d])) as Record<IndicatorId, IndicatorDef>

export const MAX_PANEL_INDICATORS = 2

export const DEFAULT_ACTIVE: Array<{ id: IndicatorId; params: Record<string, number> }> = [
  { id: 'ema',  params: { period: 20 } },
  { id: 'ema',  params: { period: 50 } },
  { id: 'ema',  params: { period: 200 } },
  { id: 'rsi',  params: { period: 14 } },
]
