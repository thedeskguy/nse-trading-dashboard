// frontend/src/components/trading-chart/lib/indicators.ts
import { SOURCES } from './types'
import type { IndicatorId, IndicatorType, IndicatorCategory, FieldDef, InputValue, Source } from './types'

export interface IndicatorDef {
  id: IndicatorId
  name: string
  category: IndicatorCategory
  type: IndicatorType
  fields: FieldDef[]
}

const period = (def: number, min = 1, max = 500, label = 'Period'): FieldDef =>
  ({ kind: 'int', key: 'period', label, default: def, min, max })
const int = (key: string, label: string, def: number, min: number, max: number): FieldDef =>
  ({ kind: 'int', key, label, default: def, min, max })
const source = (): FieldDef => ({ kind: 'source', key: 'source', label: 'Source', default: 'close' })
const color = (key: string, label: string, def: string): FieldDef => ({ kind: 'color', key, label, default: def })
const width = (def: 1 | 2 | 3 = 2): FieldDef => ({ kind: 'width', key: 'width', label: 'Line Width', default: def })
const level = (key: string, label: string, def: number, min: number, max: number): FieldDef =>
  ({ kind: 'level', key, label, default: def, min, max })

export const INDICATORS: IndicatorDef[] = [
  // TREND
  { id: 'sma', name: 'SMA', category: 'TREND', type: 'overlay',
    fields: [period(20), source(), color('color', 'Color', '#f7c948'), width()] },
  { id: 'ema', name: 'EMA', category: 'TREND', type: 'overlay',
    fields: [period(20), source(), color('color', 'Color', '#2196f3'), width()] },
  { id: 'wma', name: 'WMA', category: 'TREND', type: 'overlay',
    fields: [period(20), source(), color('color', 'Color', '#26c6da'), width()] },
  { id: 'hma', name: 'HMA', category: 'TREND', type: 'overlay',
    fields: [{ kind: 'int', key: 'period', label: 'Period', default: 9, min: 2, max: 500 }, source(),
             color('color', 'Color', '#e040fb'), width()] },
  { id: 'supertrend', name: 'Supertrend', category: 'TREND', type: 'overlay',
    fields: [period(10, 1, 100),
             { kind: 'float', key: 'multiplier', label: 'Multiplier', default: 3, min: 0.5, max: 10, step: 0.5 },
             color('bullColor', 'Up Color', '#26a69a'), color('bearColor', 'Down Color', '#ef5350'), width()] },
  // MOMENTUM
  { id: 'rsi', name: 'RSI', category: 'MOMENTUM', type: 'panel',
    fields: [period(14, 2, 100), source(),
             level('overbought', 'Overbought', 70, 50, 100), level('oversold', 'Oversold', 30, 0, 50),
             color('color', 'Color', '#7b61ff'), width()] },
  { id: 'macd', name: 'MACD', category: 'MOMENTUM', type: 'panel',
    fields: [int('fast', 'Fast', 12, 1, 100), int('slow', 'Slow', 26, 1, 200), int('signal', 'Signal', 9, 1, 100),
             source(), color('macdColor', 'MACD Color', '#2962ff'), color('signalColor', 'Signal Color', '#ff6d00'), width()] },
  { id: 'stochastic', name: 'Stochastic', category: 'MOMENTUM', type: 'panel',
    fields: [int('k', '%K Period', 14, 1, 100), int('d', '%D Period', 3, 1, 50),
             level('overbought', 'Overbought', 80, 50, 100), level('oversold', 'Oversold', 20, 0, 50),
             color('kColor', '%K Color', '#2962ff'), color('dColor', '%D Color', '#ff6d00'), width()] },
  { id: 'adx', name: 'ADX', category: 'MOMENTUM', type: 'panel',
    fields: [period(14, 2, 100), level('threshold', 'Threshold', 25, 0, 100),
             color('color', 'Color', '#f7c948'), width()] },
  // VOLATILITY
  { id: 'bb', name: 'Bollinger Bands', category: 'VOLATILITY', type: 'overlay',
    fields: [period(20, 2, 500),
             { kind: 'float', key: 'stddev', label: 'Std Dev', default: 2, min: 0.1, max: 5, step: 0.1 },
             source(), color('upperColor', 'Upper Color', '#42a5f5'), color('middleColor', 'Middle Color', '#78909c'),
             color('lowerColor', 'Lower Color', '#42a5f5'), width(1)] },
  { id: 'atr', name: 'ATR', category: 'VOLATILITY', type: 'panel',
    fields: [period(14, 1, 100), color('color', 'Color', '#e040fb'), width()] },
  // VOLUME
  { id: 'obv', name: 'OBV', category: 'VOLUME', type: 'panel',
    fields: [color('color', 'Color', '#00bcd4'), width()] },
  { id: 'vwap', name: 'VWAP', category: 'VOLUME', type: 'overlay',
    fields: [color('color', 'Color', '#ff6d00'), width()] },
  // NOTE: volume_profile is registered but has no renderer in ChartCore (pre-existing gap, out of scope).
  { id: 'volume_profile', name: 'Volume Profile', category: 'VOLUME', type: 'overlay',
    fields: [int('bins', 'Bins', 20, 5, 50)] },
]

export const INDICATOR_MAP = Object.fromEntries(INDICATORS.map(d => [d.id, d])) as Record<IndicatorId, IndicatorDef>

export const MAX_PANEL_INDICATORS = 2

const INPUT_KINDS = new Set(['int', 'float', 'level', 'source'])
export const isInputField = (f: FieldDef) => INPUT_KINDS.has(f.kind)
export const isStyleField = (f: FieldDef) => f.kind === 'color' || f.kind === 'width'

export function inputDefaults(def: IndicatorDef): Record<string, InputValue> {
  return Object.fromEntries(def.fields.filter(isInputField).map(f => [f.key, f.default])) as Record<string, InputValue>
}

export function styleDefaults(def: IndicatorDef): Record<string, string | number> {
  return Object.fromEntries(def.fields.filter(isStyleField).map(f => [f.key, f.default]))
}

export function makeInstanceId(def: IndicatorDef, inputs: Record<string, InputValue>): string {
  const suffix = def.fields.filter(isInputField).map(f => String(inputs[f.key])).join('-')
  return suffix ? `${def.id}-${suffix}` : def.id
}

// Legend text: name + numeric inputs (levels excluded) + source when not close.
export function legendTitle(def: IndicatorDef, inputs: Record<string, InputValue>): string {
  const nums = def.fields
    .filter(f => f.kind === 'int' || f.kind === 'float')
    .map(f => inputs[f.key])
    .join(' ')
  const hasSource = def.fields.some(f => f.kind === 'source')
  const src = hasSource && inputs.source !== 'close' ? ` ${inputs.source}` : ''
  return `${def.name}${nums ? ' ' + nums : ''}${src}`
}

// Validate values loaded from localStorage against the schema.
export function sanitizeStored(
  def: IndicatorDef,
  storedInputs: Record<string, unknown>,
  storedStyle: Record<string, unknown>,
): { inputs: Record<string, InputValue>; style: Record<string, string | number> } {
  const inputs: Record<string, InputValue> = {}
  const style: Record<string, string | number> = {}
  for (const f of def.fields) {
    if (f.kind === 'int' || f.kind === 'float' || f.kind === 'level') {
      const v = storedInputs[f.key]
      inputs[f.key] = typeof v === 'number' && isFinite(v) && v >= f.min && v <= f.max ? v : f.default
    } else if (f.kind === 'source') {
      const v = storedInputs[f.key]
      inputs[f.key] = typeof v === 'string' && (SOURCES as readonly string[]).includes(v) ? (v as Source) : f.default
    } else if (f.kind === 'color') {
      const v = storedStyle[f.key]
      style[f.key] = typeof v === 'string' && /^#[0-9a-fA-F]{6}$/.test(v) ? v : f.default
    } else if (f.kind === 'width') {
      const v = storedStyle[f.key]
      style[f.key] = v === 1 || v === 2 || v === 3 ? v : f.default
    }
  }
  return { inputs, style }
}
