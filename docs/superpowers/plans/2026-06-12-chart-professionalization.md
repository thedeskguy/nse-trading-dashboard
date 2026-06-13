# Chart Professionalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the TradingView-style chart with SMA/WMA/HMA, a schema-driven settings system (source/colors/widths/levels), volume histogram, professional legends with eye/gear/✕ controls, panel polish, chrome cleanup, and localStorage persistence.

**Architecture:** The indicator registry (`lib/indicators.ts`) moves from numeric `defaultParams` to a typed `fields` schema; `ActiveIndicator` splits into `inputs` (recompute, drive `instanceId`) and `style` (applied live via `applyOptions`). New `ChartLegend` overlay renders OHLC/volume/indicator rows whose value spans are updated imperatively by `ChartCore` on crosshair moves. `useIndicators` hydrates from and persists to one versioned localStorage key.

**Tech Stack:** Next.js + React, lightweight-charts v5, Tailwind, Vitest + Testing Library. Frontend only.

**Spec:** `docs/superpowers/specs/2026-06-12-chart-professionalization-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/components/trading-chart/lib/computeIndicators.ts` | Modify | + `sourceValues`, `computeSMA/WMA/HMA`, `_wma`; source params on EMA/RSI/BB/MACD |
| `frontend/src/components/trading-chart/lib/types.ts` | Rewrite | `Source`, `SOURCES`, `FieldDef`, `InputValue`, new `ActiveIndicator` |
| `frontend/src/components/trading-chart/lib/indicators.ts` | Rewrite | Field-schema registry (14 indicators) + helpers (`inputDefaults`, `styleDefaults`, `makeInstanceId`, `legendTitle`, `sanitizeStored`) |
| `frontend/src/components/trading-chart/lib/format.ts` | Create | `formatINR`, `formatVolume` |
| `frontend/src/components/trading-chart/lib/overlaySeries.ts` | Create | `addOverlaySeries`, `overlayLineSpec`, `OverlayHandle` |
| `frontend/src/components/trading-chart/hooks/useIndicators.ts` | Rewrite | inputs/style/hidden state, volume visibility, localStorage persistence |
| `frontend/src/components/trading-chart/IndicatorSearch.tsx` | Rewrite | Schema-driven settings panel (number/source/color/width) |
| `frontend/src/components/trading-chart/ChartLegend.tsx` | Create | OHLC + volume + indicator legend rows with eye/gear/✕ |
| `frontend/src/components/trading-chart/ChartCore.tsx` | Rewrite | Volume series, legend wiring, style-without-rebuild, chrome |
| `frontend/src/components/trading-chart/SubChartPane.tsx` | Rewrite | OB/OS bands, level lines without axis labels, header value readouts + controls |
| `frontend/src/components/trading-chart/index.tsx` | Modify | New hook API, settings-target routing, card wrapper |
| `frontend/src/components/trading-chart/RangeSelector.tsx` | Modify | Attribution link |
| `frontend/src/__tests__/trading-chart/computeIndicators.test.ts` | Modify | + SMA/WMA/HMA/source tests |
| `frontend/src/__tests__/trading-chart/indicators.test.ts` | Create | Registry helper tests |
| `frontend/src/__tests__/trading-chart/format.test.ts` | Create | Formatter tests |
| `frontend/src/__tests__/trading-chart/useIndicators.test.ts` | Create | Persistence/hydration tests |
| `frontend/src/test/ChartLegend.test.tsx` | Create | Legend interaction tests |
| `README.md` | Modify | Chart section |

**Mid-branch type errors are planned.** Tasks 2–7 leave specific files type-broken until Task 8 wires everything; each task lists the exact expected residual `tsc` errors. Vitest stays green throughout (tests never import the broken UI files). `frontend/AGENTS.md` warns the Next.js version may differ from training data — these tasks don't touch Next APIs, only React + lightweight-charts.

---

### Task 0: Worktree + branch

- [ ] **Step 1: Create worktree and install frontend deps**

```bash
cd "/Users/divyanshuagarwal/Downloads/frist workflow"
git worktree add -b feature/chart-professionalization "/Users/divyanshuagarwal/Downloads/frist-workflow-chart" main
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart/frontend && npm ci --no-audit --no-fund
npx vitest run   # baseline: all pass
```

All subsequent tasks work in `/Users/divyanshuagarwal/Downloads/frist-workflow-chart`. Commit messages end with a blank line + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Compute layer — sourceValues, SMA, WMA, HMA, source params

**Files:**
- Modify: `frontend/src/components/trading-chart/lib/computeIndicators.ts`
- Modify: `frontend/src/components/trading-chart/lib/types.ts` (additive only in this task)
- Test: `frontend/src/__tests__/trading-chart/computeIndicators.test.ts` (append)

- [ ] **Step 1: Add `Source` type (additive).** In `lib/types.ts`, after the `Candle` interface, add:

```ts
export const SOURCES = ['close', 'open', 'high', 'low', 'hl2', 'hlc3', 'ohlc4'] as const
export type Source = typeof SOURCES[number]
```

- [ ] **Step 2: Append failing tests** to `computeIndicators.test.ts` (it already defines `makeCandles`; note `makeCandles(n).close = 100 + i + 1`):

```ts
import {
  sourceValues, computeSMA, computeWMA, computeHMA,
} from '@/components/trading-chart/lib/computeIndicators'

function makeFlatCandles(n: number, price = 100): Candle[] {
  return Array.from({ length: n }, (_, i) => ({
    timestamp: `2024-02-${String(i + 1).padStart(2, '0')}`,
    open: price, high: price, low: price, close: price, volume: 1000,
  }))
}

function makeZigzagCandles(n: number): Candle[] {
  // close alternates up/down; high is constant
  return Array.from({ length: n }, (_, i) => ({
    timestamp: `2024-03-${String(i + 1).padStart(2, '0')}`,
    open: 100, high: 120, low: 80,
    close: i % 2 === 0 ? 100 + 2 : 100 - 1,
    volume: 1000,
  }))
}

describe('sourceValues', () => {
  const c: Candle = { timestamp: '2024-01-01', open: 10, high: 20, low: 5, close: 15, volume: 1 }
  it('extracts each source correctly', () => {
    expect(sourceValues([c], 'close')[0]).toBe(15)
    expect(sourceValues([c], 'open')[0]).toBe(10)
    expect(sourceValues([c], 'high')[0]).toBe(20)
    expect(sourceValues([c], 'low')[0]).toBe(5)
    expect(sourceValues([c], 'hl2')[0]).toBeCloseTo(12.5)
    expect(sourceValues([c], 'hlc3')[0]).toBeCloseTo(40 / 3)
    expect(sourceValues([c], 'ohlc4')[0]).toBeCloseTo(12.5)
  })
  it('defaults to close', () => {
    expect(sourceValues([c])[0]).toBe(15)
  })
})

describe('computeSMA', () => {
  it('returns empty when candles < period', () => {
    expect(computeSMA(makeCandles(3), 14)).toHaveLength(0)
  })
  it('computes the simple average (closes 101..105, SMA3 = 102,103,104)', () => {
    const result = computeSMA(makeCandles(5), 3)
    expect(result.map(p => p.value)).toEqual([102, 103, 104])
  })
  it('returns candles.length - period + 1 points', () => {
    expect(computeSMA(makeCandles(30), 10)).toHaveLength(21)
  })
})

describe('computeWMA', () => {
  it('weights recent values more (closes 101..105, WMA3 = 102.33, 103.33, 104.33)', () => {
    const result = computeWMA(makeCandles(5), 3)
    expect(result[0].value).toBeCloseTo(614 / 6, 4)   // (101·1 + 102·2 + 103·3) / 6
    expect(result[1].value).toBeCloseTo(620 / 6, 4)
    expect(result[2].value).toBeCloseTo(626 / 6, 4)
  })
  it('returns empty when candles < period', () => {
    expect(computeWMA(makeCandles(2), 3)).toHaveLength(0)
  })
})

describe('computeHMA', () => {
  it('equals the constant on flat data', () => {
    computeHMA(makeFlatCandles(30), 9).forEach(p => expect(p.value).toBeCloseTo(100, 6))
  })
  it('has length n - (period - 1) - (floor(sqrt(period)) - 1)', () => {
    // period 9 → sqrt 3 → 30 - 8 - 2 = 20
    expect(computeHMA(makeCandles(30), 9)).toHaveLength(20)
  })
  it('leads SMA on rising data (lower lag)', () => {
    const candles = makeCandles(60)
    const hma = computeHMA(candles, 20)
    const sma = computeSMA(candles, 20)
    expect(hma[hma.length - 1].value).toBeGreaterThan(sma[sma.length - 1].value)
  })
  it('returns empty when not enough candles', () => {
    expect(computeHMA(makeCandles(5), 9)).toHaveLength(0)
  })
})

describe('source-aware indicators', () => {
  it('EMA on hl2 differs from close by the fixture offset', () => {
    // makeCandles: hl2 = 100+i, close = 100+i+1 → EMA(hl2) = EMA(close) - 1
    const candles = makeCandles(30)
    const closeEMA = computeEMA(candles, 5)
    const hl2EMA = computeEMA(candles, 5, 'hl2')
    hl2EMA.forEach((p, i) => expect(p.value).toBeCloseTo(closeEMA[i].value - 1, 6))
  })
  it('RSI source changes the result (flat high → RSI 100, zigzag close → not 100)', () => {
    const candles = makeZigzagCandles(40)
    const rsiHigh = computeRSI(candles, 14, 'high')
    const rsiClose = computeRSI(candles, 14, 'close')
    rsiHigh.forEach(p => expect(p.value).toBe(100))   // no losses on a flat series
    expect(rsiClose.some(p => p.value < 100)).toBe(true)
  })
  it('BB middle on open differs from close', () => {
    const candles = makeCandles(40)
    const bbClose = computeBB(candles, 20, 2)
    const bbOpen = computeBB(candles, 20, 2, 'open')
    expect(bbOpen.middle[0].value).toBeCloseTo(bbClose.middle[0].value - 1, 6)
  })
  it('MACD accepts a source param', () => {
    const r = computeMACD(makeCandles(100), 12, 26, 9, 'hl2')
    expect(r.macd.length).toBeGreaterThan(0)
  })
})
```

Add `import type { Candle } from '@/components/trading-chart/lib/types'` only if not already imported (it is — line 2).

- [ ] **Step 3: Run to verify failures**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart/frontend && npx vitest run src/__tests__/trading-chart/computeIndicators.test.ts
```

Expected: FAIL — `sourceValues`, `computeSMA`, `computeWMA`, `computeHMA` not exported; source-param tests fail.

- [ ] **Step 4: Implement.** In `lib/computeIndicators.ts`:

(a) Update the type import (line 3) to also import `Source`:

```ts
import type { Candle, LinePoint, HistPoint, MACDResult, BBResult, StochasticResult, SupertrendResult, VolumeProfileBar, Source } from './types'
```

(b) Add after `toTime`:

```ts
// ── Price source extraction ──────────────────────────────────────────────────
export function sourceValues(candles: Candle[], source: Source = 'close'): number[] {
  switch (source) {
    case 'open':  return candles.map(c => c.open)
    case 'high':  return candles.map(c => c.high)
    case 'low':   return candles.map(c => c.low)
    case 'hl2':   return candles.map(c => (c.high + c.low) / 2)
    case 'hlc3':  return candles.map(c => (c.high + c.low + c.close) / 3)
    case 'ohlc4': return candles.map(c => (c.open + c.high + c.low + c.close) / 4)
    default:      return candles.map(c => c.close)
  }
}

// ── SMA ──────────────────────────────────────────────────────────────────────
export function computeSMA(candles: Candle[], period: number, source: Source = 'close'): LinePoint[] {
  if (candles.length < period || period < 1) return []
  const src = sourceValues(candles, source)
  const result: LinePoint[] = []
  let sum = src.slice(0, period).reduce((s, v) => s + v, 0)
  result.push({ time: toTime(candles[period - 1].timestamp), value: sum / period })
  for (let i = period; i < src.length; i++) {
    sum += src[i] - src[i - period]
    result.push({ time: toTime(candles[i].timestamp), value: sum / period })
  }
  return result
}

// ── WMA (weights 1..period, most recent heaviest) ────────────────────────────
export function _wma(values: number[], period: number): number[] {
  if (values.length < period || period < 1) return []
  const denom = (period * (period + 1)) / 2
  const out: number[] = []
  for (let i = period - 1; i < values.length; i++) {
    let s = 0
    for (let j = 0; j < period; j++) s += values[i - period + 1 + j] * (j + 1)
    out.push(s / denom)
  }
  return out
}

export function computeWMA(candles: Candle[], period: number, source: Source = 'close'): LinePoint[] {
  const values = _wma(sourceValues(candles, source), period)
  return values.map((v, i) => ({ time: toTime(candles[period - 1 + i].timestamp), value: v }))
}

// ── HMA: WMA(2·WMA(src, n/2) − WMA(src, n), floor(√n)) ───────────────────────
export function computeHMA(candles: Candle[], period: number, source: Source = 'close'): LinePoint[] {
  const sqrtP = Math.max(1, Math.floor(Math.sqrt(period)))
  if (period < 2 || candles.length < period + sqrtP - 1) return []
  const src = sourceValues(candles, source)
  const half = _wma(src, Math.max(1, Math.floor(period / 2)))   // starts at candle floor(period/2)-1
  const full = _wma(src, period)                                // starts at candle period-1
  const offset = half.length - full.length
  const diff = full.map((f, i) => 2 * half[i + offset] - f)     // aligned at candle period-1+i
  const smoothed = _wma(diff, sqrtP)
  return smoothed.map((v, i) => ({
    time: toTime(candles[period - 1 + sqrtP - 1 + i].timestamp),
    value: v,
  }))
}
```

(c) Make EMA/RSI/BB/MACD source-aware — replace each function with:

```ts
export function computeEMA(candles: Candle[], period: number, source: Source = 'close'): LinePoint[] {
  if (candles.length < period) return []
  const src = sourceValues(candles, source)
  const k = 2 / (period + 1)
  const result: LinePoint[] = []
  let ema = src.slice(0, period).reduce((s, v) => s + v, 0) / period
  result.push({ time: toTime(candles[period - 1].timestamp), value: ema })
  for (let i = period; i < candles.length; i++) {
    ema = src[i] * k + ema * (1 - k)
    result.push({ time: toTime(candles[i].timestamp), value: ema })
  }
  return result
}

export function computeRSI(candles: Candle[], period: number, source: Source = 'close'): LinePoint[] {
  if (candles.length <= period) return []
  const src = sourceValues(candles, source)
  let avgGain = 0, avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = src[i] - src[i - 1]
    if (diff > 0) avgGain += diff; else avgLoss += Math.abs(diff)
  }
  avgGain /= period
  avgLoss /= period
  const result: LinePoint[] = []
  for (let i = period; i < candles.length; i++) {
    if (i > period) {
      const diff = src[i] - src[i - 1]
      avgGain = (avgGain * (period - 1) + Math.max(0, diff)) / period
      avgLoss = (avgLoss * (period - 1) + Math.max(0, -diff)) / period
    }
    const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss
    result.push({ time: toTime(candles[i].timestamp), value: avgLoss === 0 ? 100 : 100 - 100 / (1 + rs) })
  }
  return result
}

export function computeBB(candles: Candle[], period: number, stddev: number, source: Source = 'close'): BBResult {
  if (candles.length < period) return { upper: [], middle: [], lower: [] }
  const src = sourceValues(candles, source)
  const upper: LinePoint[] = [], middle: LinePoint[] = [], lower: LinePoint[] = []
  for (let i = period - 1; i < candles.length; i++) {
    const slice = src.slice(i - period + 1, i + 1)
    const mean = slice.reduce((s, v) => s + v, 0) / period
    const std = Math.sqrt(slice.reduce((s, v) => s + (v - mean) ** 2, 0) / period)
    const t = toTime(candles[i].timestamp)
    upper.push({ time: t, value: mean + stddev * std })
    middle.push({ time: t, value: mean })
    lower.push({ time: t, value: mean - stddev * std })
  }
  return { upper, middle, lower }
}
```

For MACD, change only the signature and the two EMA calls (body otherwise unchanged):

```ts
export function computeMACD(candles: Candle[], fast: number, slow: number, signal: number, source: Source = 'close'): MACDResult {
  const emaFast = computeEMA(candles, fast, source)
  const emaSlow = computeEMA(candles, slow, source)
  // ... rest of the existing body unchanged ...
}
```

- [ ] **Step 5: Run the full compute test file**

```bash
npx vitest run src/__tests__/trading-chart/computeIndicators.test.ts
```

Expected: ALL pass (existing tests + new). Then `npx tsc --noEmit` — clean — and `npm run lint` — clean.

- [ ] **Step 6: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/lib/computeIndicators.ts frontend/src/components/trading-chart/lib/types.ts frontend/src/__tests__/trading-chart/computeIndicators.test.ts
git commit -m "feat(chart): SMA/WMA/HMA + price-source support in compute layer"
```

---

### Task 2: Types, field-schema registry, format helpers

**Files:**
- Rewrite: `frontend/src/components/trading-chart/lib/types.ts`
- Rewrite: `frontend/src/components/trading-chart/lib/indicators.ts`
- Create: `frontend/src/components/trading-chart/lib/format.ts`
- Test: `frontend/src/__tests__/trading-chart/indicators.test.ts` (create), `frontend/src/__tests__/trading-chart/format.test.ts` (create)

- [ ] **Step 1: Write failing tests.** Create `frontend/src/__tests__/trading-chart/indicators.test.ts`:

```ts
import {
  INDICATOR_MAP, inputDefaults, styleDefaults, makeInstanceId, legendTitle, sanitizeStored,
} from '@/components/trading-chart/lib/indicators'

describe('registry schema', () => {
  it('includes the MA family with source + color + width fields', () => {
    for (const id of ['sma', 'ema', 'wma', 'hma'] as const) {
      const kinds = INDICATOR_MAP[id].fields.map(f => f.kind)
      expect(kinds).toEqual(expect.arrayContaining(['int', 'source', 'color', 'width']))
    }
  })
  it('rsi has overbought/oversold level fields', () => {
    const keys = INDICATOR_MAP.rsi.fields.map(f => f.key)
    expect(keys).toEqual(expect.arrayContaining(['overbought', 'oversold']))
  })
})

describe('defaults + instanceId', () => {
  it('inputDefaults/styleDefaults split by kind', () => {
    const def = INDICATOR_MAP.ema
    expect(inputDefaults(def)).toEqual({ period: 20, source: 'close' })
    expect(styleDefaults(def)).toEqual({ color: '#2196f3', width: 2 })
  })
  it('instanceId derives from inputs only, in field order', () => {
    const def = INDICATOR_MAP.ema
    expect(makeInstanceId(def, { period: 50, source: 'close' })).toBe('ema-50-close')
  })
})

describe('legendTitle', () => {
  it('shows numeric inputs, hides levels, shows non-close source', () => {
    expect(legendTitle(INDICATOR_MAP.ema, { period: 20, source: 'close' })).toBe('EMA 20')
    expect(legendTitle(INDICATOR_MAP.ema, { period: 20, source: 'hl2' })).toBe('EMA 20 hl2')
    expect(legendTitle(INDICATOR_MAP.rsi, { period: 14, source: 'close', overbought: 70, oversold: 30 })).toBe('RSI 14')
    expect(legendTitle(INDICATOR_MAP.bb, { period: 20, stddev: 2, source: 'close' })).toBe('Bollinger Bands 20 2')
  })
})

describe('sanitizeStored', () => {
  const def = INDICATOR_MAP.ema
  it('keeps valid values', () => {
    const r = sanitizeStored(def, { period: 50, source: 'hl2' }, { color: '#abcdef', width: 3 })
    expect(r.inputs).toEqual({ period: 50, source: 'hl2' })
    expect(r.style).toEqual({ color: '#abcdef', width: 3 })
  })
  it('falls back to defaults for out-of-range, wrong-typed, or missing values', () => {
    const r = sanitizeStored(def, { period: 99999, source: 'banana' }, { color: 'red', width: 7 })
    expect(r.inputs).toEqual({ period: 20, source: 'close' })
    expect(r.style).toEqual({ color: '#2196f3', width: 2 })
  })
})
```

Create `frontend/src/__tests__/trading-chart/format.test.ts`:

```ts
import { formatINR, formatVolume } from '@/components/trading-chart/lib/format'

describe('formatINR', () => {
  it('uses the rupee sign and Indian grouping', () => {
    expect(formatINR(1018.6)).toBe('₹1,018.60')
    expect(formatINR(1234567.891)).toBe('₹12,34,567.89')
  })
})

describe('formatVolume', () => {
  it('formats K/M/Cr', () => {
    expect(formatVolume(567030)).toBe('567.03K')
    expect(formatVolume(1520000)).toBe('1.52M')
    expect(formatVolume(25000000)).toBe('2.50Cr')
    expect(formatVolume(950)).toBe('950')
  })
})
```

- [ ] **Step 2: Run to verify failures**

```bash
npx vitest run src/__tests__/trading-chart/indicators.test.ts src/__tests__/trading-chart/format.test.ts
```

Expected: FAIL — helpers and `format.ts` don't exist.

- [ ] **Step 3: Rewrite `lib/types.ts`** (full file):

```ts
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
```

- [ ] **Step 4: Rewrite `lib/indicators.ts`** (full file):

```ts
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
```

(The old `DEFAULT_ACTIVE` export is removed.)

- [ ] **Step 5: Create `lib/format.ts`:**

```ts
// frontend/src/components/trading-chart/lib/format.ts
export function formatINR(price: number): string {
  return '₹' + price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatVolume(v: number): string {
  const a = Math.abs(v)
  if (a >= 1e7) return `${(v / 1e7).toFixed(2)}Cr`
  if (a >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (a >= 1e3) return `${(v / 1e3).toFixed(2)}K`
  return String(Math.round(v))
}
```

- [ ] **Step 6: Verify**

```bash
npx vitest run src/__tests__/trading-chart/
```

Expected: indicators/format/compute tests all PASS.

```bash
npx tsc --noEmit
```

Expected errors ONLY in: `hooks/useIndicators.ts`, `IndicatorSearch.tsx`, `ChartCore.tsx`, `SubChartPane.tsx` (they still use `defaultParams`/`paramLabels`/`params` — fixed in Tasks 3–7). Any error elsewhere is yours.

- [ ] **Step 7: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/lib frontend/src/__tests__/trading-chart
git commit -m "feat(chart): field-schema indicator registry + format helpers"
```

---

### Task 3: useIndicators rewrite — inputs/style/hidden + persistence

**Files:**
- Rewrite: `frontend/src/components/trading-chart/hooks/useIndicators.ts`
- Test: `frontend/src/__tests__/trading-chart/useIndicators.test.ts` (create)

- [ ] **Step 1: Write failing tests.** Create `frontend/src/__tests__/trading-chart/useIndicators.test.ts`:

```ts
import { renderHook, act } from '@testing-library/react'
import { useIndicators, STORAGE_KEY } from '@/components/trading-chart/hooks/useIndicators'

beforeEach(() => localStorage.clear())

describe('useIndicators', () => {
  it('adds an indicator with schema defaults', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    const inst = result.current.activeIndicators[0]
    expect(inst.instanceId).toBe('ema-20-close')
    expect(inst.inputs).toEqual({ period: 20, source: 'close' })
    expect(inst.style).toEqual({ color: '#2196f3', width: 2 })
    expect(inst.hidden).toBe(false)
  })

  it('updateStyle preserves instanceId; updateInputs regenerates it', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    act(() => result.current.updateStyle('ema-20-close', { color: '#ff0000', width: 3 }))
    expect(result.current.activeIndicators[0].instanceId).toBe('ema-20-close')
    expect(result.current.activeIndicators[0].style.color).toBe('#ff0000')
    act(() => result.current.updateInputs('ema-20-close', { period: 50, source: 'close' }))
    expect(result.current.activeIndicators[0].instanceId).toBe('ema-50-close')
  })

  it('toggleHidden flips the flag', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('vwap'))
    act(() => result.current.toggleHidden(result.current.activeIndicators[0].instanceId))
    expect(result.current.activeIndicators[0].hidden).toBe(true)
  })

  it('persists and hydrates across mounts', () => {
    const first = renderHook(() => useIndicators())
    act(() => first.result.current.addIndicator('rsi'))
    act(() => first.result.current.toggleVolume())
    first.unmount()
    const second = renderHook(() => useIndicators())
    expect(second.result.current.activeIndicators).toHaveLength(1)
    expect(second.result.current.activeIndicators[0].indicatorId).toBe('rsi')
    expect(second.result.current.volumeVisible).toBe(false)
  })

  it('resets silently on corrupt storage', () => {
    localStorage.setItem(STORAGE_KEY, '{not json')
    const { result } = renderHook(() => useIndicators())
    expect(result.current.activeIndicators).toEqual([])
    expect(result.current.volumeVisible).toBe(true)
  })

  it('drops unknown indicators and clamps bad values on hydrate', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 2, volumeVisible: true,
      indicators: [
        { indicatorId: 'banana', inputs: {}, style: {} },
        { indicatorId: 'ema', inputs: { period: 99999, source: 'nope' }, style: { color: 'red', width: 9 } },
      ],
    }))
    const { result } = renderHook(() => useIndicators())
    expect(result.current.activeIndicators).toHaveLength(1)
    const inst = result.current.activeIndicators[0]
    expect(inst.inputs).toEqual({ period: 20, source: 'close' })
    expect(inst.style).toEqual({ color: '#2196f3', width: 2 })
  })

  it('caps panel indicators at the limit on hydrate', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 2, volumeVisible: true,
      indicators: [
        { indicatorId: 'rsi', inputs: {}, style: {} },
        { indicatorId: 'macd', inputs: {}, style: {} },
        { indicatorId: 'adx', inputs: {}, style: {} },
      ],
    }))
    const { result } = renderHook(() => useIndicators())
    expect(result.current.panelIndicators).toHaveLength(2)
  })
})
```

- [ ] **Step 2: Run to verify failure**

```bash
npx vitest run src/__tests__/trading-chart/useIndicators.test.ts
```

Expected: FAIL (`STORAGE_KEY` not exported; old API).

- [ ] **Step 3: Rewrite `hooks/useIndicators.ts`** (full file):

```ts
'use client'
import { useState, useCallback, useEffect, useMemo } from 'react'
import {
  INDICATOR_MAP, MAX_PANEL_INDICATORS,
  inputDefaults, styleDefaults, makeInstanceId, sanitizeStored,
} from '../lib/indicators'
import type { ActiveIndicator, IndicatorId, InputValue } from '../lib/types'

export const STORAGE_KEY = 'tradedash.chart.v2'

interface PersistedV2 {
  version: 2
  volumeVisible: boolean
  indicators: Array<{
    indicatorId: string
    inputs: Record<string, unknown>
    style: Record<string, unknown>
    hidden?: boolean
  }>
}

function loadPersisted(): { volumeVisible: boolean; indicators: ActiveIndicator[] } | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedV2
    if (parsed?.version !== 2 || !Array.isArray(parsed.indicators)) return null
    const indicators: ActiveIndicator[] = []
    let panelCount = 0
    for (const item of parsed.indicators) {
      const def = INDICATOR_MAP[item.indicatorId as IndicatorId]
      if (!def) continue
      if (def.type === 'panel') {
        if (panelCount >= MAX_PANEL_INDICATORS) continue
        panelCount++
      }
      const { inputs, style } = sanitizeStored(def, item.inputs ?? {}, item.style ?? {})
      const instanceId = makeInstanceId(def, inputs)
      if (indicators.some(i => i.instanceId === instanceId)) continue
      indicators.push({ instanceId, indicatorId: def.id, inputs, style, hidden: item.hidden === true })
    }
    return { volumeVisible: parsed.volumeVisible !== false, indicators }
  } catch {
    return null  // corrupt storage — fall back to defaults
  }
}

export function useIndicators() {
  const [active, setActive] = useState<ActiveIndicator[]>([])
  const [volumeVisible, setVolumeVisible] = useState(true)
  const [hydrated, setHydrated] = useState(false)

  // Hydrate after mount (avoids SSR hydration mismatch).
  useEffect(() => {
    const loaded = loadPersisted()
    if (loaded) {
      setActive(loaded.indicators)
      setVolumeVisible(loaded.volumeVisible)
    }
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (!hydrated || typeof window === 'undefined') return
    const payload: PersistedV2 = {
      version: 2,
      volumeVisible,
      indicators: active.map(a => ({
        indicatorId: a.indicatorId, inputs: a.inputs, style: a.style, hidden: a.hidden,
      })),
    }
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch { /* storage full or blocked — non-fatal */ }
  }, [active, volumeVisible, hydrated])

  const addIndicator = useCallback((id: IndicatorId) => {
    const def = INDICATOR_MAP[id]
    const inputs = inputDefaults(def)
    const instanceId = makeInstanceId(def, inputs)
    setActive(prev => {
      if (prev.find(a => a.instanceId === instanceId)) return prev
      const panelCount = prev.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel').length
      if (def.type === 'panel' && panelCount >= MAX_PANEL_INDICATORS) return prev
      return [...prev, { instanceId, indicatorId: id, inputs, style: styleDefaults(def), hidden: false }]
    })
  }, [])

  const removeIndicator = useCallback((instanceId: string) => {
    setActive(prev => prev.filter(a => a.instanceId !== instanceId))
  }, [])

  const updateInputs = useCallback((instanceId: string, inputs: Record<string, InputValue>) => {
    setActive(prev => prev.map(a =>
      a.instanceId === instanceId
        ? { ...a, inputs, instanceId: makeInstanceId(INDICATOR_MAP[a.indicatorId], inputs) }
        : a
    ))
  }, [])

  const updateStyle = useCallback((instanceId: string, style: Record<string, string | number>) => {
    setActive(prev => prev.map(a => (a.instanceId === instanceId ? { ...a, style } : a)))
  }, [])

  const toggleHidden = useCallback((instanceId: string) => {
    setActive(prev => prev.map(a => (a.instanceId === instanceId ? { ...a, hidden: !a.hidden } : a)))
  }, [])

  const toggleVolume = useCallback(() => setVolumeVisible(v => !v), [])

  const overlayIndicators = useMemo(
    () => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'overlay'), [active])
  const panelIndicators = useMemo(
    () => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel'), [active])
  const canAddPanel = panelIndicators.length < MAX_PANEL_INDICATORS

  return {
    activeIndicators: active,
    addIndicator, removeIndicator,
    updateInputs, updateStyle, toggleHidden,
    overlayIndicators, panelIndicators, canAddPanel,
    volumeVisible, toggleVolume,
  }
}
```

- [ ] **Step 4: Run tests**

```bash
npx vitest run src/__tests__/trading-chart/useIndicators.test.ts && npx vitest run
```

Expected: PASS (all suites — UI test files don't import the still-broken components).

`npx tsc --noEmit` — expected errors ONLY in: `IndicatorSearch.tsx`, `ChartCore.tsx`, `SubChartPane.tsx`, `index.tsx` (old hook API / old `params` access).

- [ ] **Step 5: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/hooks/useIndicators.ts frontend/src/__tests__/trading-chart/useIndicators.test.ts
git commit -m "feat(chart): inputs/style/hidden indicator state with localStorage persistence"
```

---

### Task 4: IndicatorSearch — schema-driven settings panel

**Files:**
- Rewrite: `frontend/src/components/trading-chart/IndicatorSearch.tsx`

- [ ] **Step 1: Rewrite the file** (full contents):

```tsx
'use client'
import { useState, useMemo, useEffect } from 'react'
import { X, Check, Search, Settings2, ChevronUp } from 'lucide-react'
import { INDICATORS, INDICATOR_MAP, MAX_PANEL_INDICATORS } from './lib/indicators'
import { SOURCES } from './lib/types'
import type { ActiveIndicator, IndicatorId, IndicatorCategory, InputValue, Source, FieldDef } from './lib/types'

const CATEGORIES: IndicatorCategory[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME']
const SWATCHES = ['#f7c948', '#2196f3', '#26c6da', '#ff7043', '#e040fb', '#26a69a', '#ef5350', '#ff6d00']

interface Props {
  isOpen: boolean
  onClose: () => void
  activeIndicators: ActiveIndicator[]
  onAdd: (id: IndicatorId) => void
  onRemove: (instanceId: string) => void
  onUpdateInputs: (instanceId: string, inputs: Record<string, InputValue>) => void
  onUpdateStyle: (instanceId: string, style: Record<string, string | number>) => void
  canAddPanel: boolean
  initialOpenInstanceId?: string | null
}

function draftFrom(inst: ActiveIndicator): Record<string, string> {
  return Object.fromEntries(Object.entries(inst.inputs).map(([k, v]) => [k, String(v)]))
}

export function IndicatorSearch({
  isOpen, onClose, activeIndicators, onAdd, onRemove,
  onUpdateInputs, onUpdateStyle, canAddPanel, initialOpenInstanceId,
}: Props) {
  const [query, setQuery] = useState('')
  const [openSettings, setOpenSettings] = useState<string | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})

  // Gear click in a legend routes here: open that instance's settings.
  useEffect(() => {
    if (!isOpen || !initialOpenInstanceId) return
    const inst = activeIndicators.find(a => a.instanceId === initialOpenInstanceId)
    if (inst) {
      setOpenSettings(inst.instanceId)
      setDraft(draftFrom(inst))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialOpenInstanceId])

  const filtered = useMemo(() => {
    if (!query) return INDICATORS
    return INDICATORS.filter(d => d.name.toLowerCase().includes(query.toLowerCase()))
  }, [query])

  function handleToggle(id: IndicatorId) {
    const def = INDICATOR_MAP[id]
    const existing = activeIndicators.filter(a => a.indicatorId === id)
    if (existing.length > 0) {
      onRemove(existing[0].instanceId)
      setOpenSettings(null)
      return
    }
    if (def.type === 'panel' && !canAddPanel) {
      alert(`Panel limit reached. Remove an existing panel indicator first (max ${MAX_PANEL_INDICATORS}).`)
      return
    }
    onAdd(id)
  }

  function openIndicatorSettings(inst: ActiveIndicator) {
    setOpenSettings(prev => (prev === inst.instanceId ? null : inst.instanceId))
    setDraft(draftFrom(inst))
  }

  function applyInputs(inst: ActiveIndicator) {
    const def = INDICATOR_MAP[inst.indicatorId]
    const inputs: Record<string, InputValue> = { ...inst.inputs }
    for (const f of def.fields) {
      if (f.kind === 'int' || f.kind === 'float' || f.kind === 'level') {
        const raw = draft[f.key]
        const n = f.kind === 'int' ? parseInt(raw, 10) : parseFloat(raw)
        if (!isNaN(n)) inputs[f.key] = Math.min(f.max, Math.max(f.min, n))
      } else if (f.kind === 'source') {
        const v = draft[f.key]
        if ((SOURCES as readonly string[]).includes(v)) inputs[f.key] = v as Source
      }
    }
    onUpdateInputs(inst.instanceId, inputs)
    setOpenSettings(null)
  }

  function setStyleField(inst: ActiveIndicator, key: string, value: string | number) {
    onUpdateStyle(inst.instanceId, { ...inst.style, [key]: value })
  }

  function renderField(inst: ActiveIndicator, f: FieldDef) {
    if (f.kind === 'color') {
      const current = (inst.style[f.key] as string) ?? f.default
      return (
        <div key={f.key} className="mb-2">
          <div className="flex items-center justify-between gap-2">
            <label className="text-[#787b86] text-xs">{f.label}</label>
            <input
              type="color"
              value={current}
              aria-label={f.label}
              onChange={e => setStyleField(inst, f.key, e.target.value)}
              className="w-8 h-6 bg-transparent border border-[#2a2e39] rounded cursor-pointer"
            />
          </div>
          <div className="flex gap-1 mt-1 justify-end">
            {SWATCHES.map(c => (
              <button
                key={c}
                aria-label={`Set ${f.label} ${c}`}
                onClick={() => setStyleField(inst, f.key, c)}
                className="w-4 h-4 rounded-sm border border-[#2a2e39]"
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      )
    }
    if (f.kind === 'width') {
      const current = (inst.style[f.key] as number) ?? f.default
      return (
        <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
          <label className="text-[#787b86] text-xs">{f.label}</label>
          <div className="flex gap-1">
            {([1, 2, 3] as const).map(w => (
              <button
                key={w}
                onClick={() => setStyleField(inst, f.key, w)}
                className={`px-2 py-0.5 rounded text-xs ${
                  current === w ? 'bg-[#2962ff] text-white' : 'bg-[#1e2330] text-[#787b86] border border-[#2a2e39]'
                }`}
              >
                {w}px
              </button>
            ))}
          </div>
        </div>
      )
    }
    if (f.kind === 'source') {
      return (
        <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
          <label className="text-[#787b86] text-xs">{f.label}</label>
          <select
            value={draft[f.key] ?? 'close'}
            onChange={e => setDraft(prev => ({ ...prev, [f.key]: e.target.value }))}
            className="bg-[#1e2330] border border-[#2a2e39] text-white text-xs rounded px-2 py-1 outline-none focus:border-[#2962ff]"
          >
            {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      )
    }
    // int | float | level
    return (
      <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
        <label className="text-[#787b86] text-xs">{f.label}</label>
        <input
          type="number"
          value={draft[f.key] ?? ''}
          min={f.min}
          max={f.max}
          step={f.kind === 'float' ? (f.step ?? 0.1) : 1}
          onChange={e => setDraft(prev => ({ ...prev, [f.key]: e.target.value }))}
          className="w-16 bg-[#1e2330] border border-[#2a2e39] text-white text-xs rounded px-2 py-1 outline-none focus:border-[#2962ff]"
        />
      </div>
    )
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-72 z-50 bg-[#1e2330] border-l border-[#2a2e39] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2e39]">
          <span className="text-white font-medium text-sm">Indicators</span>
          <button onClick={onClose} className="text-[#787b86] hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-3 py-2 border-b border-[#2a2e39]">
          <div className="flex items-center gap-2 bg-[#131722] rounded px-2 py-1.5">
            <Search className="h-3.5 w-3.5 text-[#787b86]" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search indicators..."
              className="bg-transparent text-white text-xs outline-none flex-1 placeholder:text-[#787b86]"
              autoFocus
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {CATEGORIES.map(cat => {
            const items = filtered.filter(d => d.category === cat)
            if (!items.length) return null
            return (
              <div key={cat} className="mb-2">
                <div className="px-4 py-1 text-[#787b86] text-[10px] font-semibold tracking-wider uppercase">{cat}</div>
                {items.map(def => {
                  const activeInstances = activeIndicators.filter(a => a.indicatorId === def.id)
                  const isActive = activeInstances.length > 0

                  return (
                    <div key={def.id}>
                      <div className="flex items-center px-4 py-2 hover:bg-[#2a2e39] transition-colors">
                        <button
                          onClick={() => handleToggle(def.id)}
                          className="flex items-center gap-2 flex-1 min-w-0"
                        >
                          <span className={`text-sm ${isActive ? 'text-white' : 'text-[#b2b5be]'}`}>{def.name}</span>
                          {isActive && <Check className="h-3.5 w-3.5 text-[#2962ff] shrink-0" />}
                        </button>
                        {isActive && activeInstances.map(inst => (
                          <button
                            key={inst.instanceId}
                            onClick={() => openIndicatorSettings(inst)}
                            className="ml-1 text-[#787b86] hover:text-white p-0.5"
                            title="Settings"
                          >
                            {openSettings === inst.instanceId
                              ? <ChevronUp className="h-3.5 w-3.5" />
                              : <Settings2 className="h-3.5 w-3.5" />
                            }
                          </button>
                        ))}
                      </div>

                      {isActive && activeInstances.map(inst => openSettings === inst.instanceId && (
                        <div key={inst.instanceId} className="mx-4 mb-2 p-3 bg-[#131722] rounded border border-[#2a2e39]">
                          {def.fields.map(f => renderField(inst, f))}
                          {def.fields.some(f => f.kind !== 'color' && f.kind !== 'width') && (
                            <button
                              onClick={() => applyInputs(inst)}
                              className="mt-2 w-full text-xs bg-[#2962ff] hover:bg-[#1e53e5] text-white rounded py-1 transition-colors"
                            >
                              Apply
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Verify**

```bash
npx vitest run && npx tsc --noEmit
```

Vitest: PASS. tsc: errors ONLY in `ChartCore.tsx`, `SubChartPane.tsx`, `index.tsx`.

- [ ] **Step 3: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/IndicatorSearch.tsx
git commit -m "feat(chart): schema-driven indicator settings panel (source/color/width/levels)"
```

---

### Task 5: overlaySeries + ChartLegend (TDD for legend)

**Files:**
- Create: `frontend/src/components/trading-chart/lib/overlaySeries.ts`
- Create: `frontend/src/components/trading-chart/ChartLegend.tsx`
- Test: `frontend/src/test/ChartLegend.test.tsx` (create)

- [ ] **Step 1: Write failing test.** Create `frontend/src/test/ChartLegend.test.tsx`:

```tsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChartLegend, type LegendRowData } from "@/components/trading-chart/ChartLegend";

const row: LegendRowData = {
  instanceId: "ema-20-close",
  title: "EMA 20",
  lines: [{ lineKey: "line", color: "#2196f3" }],
  hidden: false,
};

const noop = () => {};
const baseProps = {
  volumeVisible: true,
  registerValueEl: noop,
  onToggleHidden: noop,
  onOpenSettings: noop,
  onRemove: noop,
  onToggleVolume: noop,
};

describe("ChartLegend", () => {
  it("renders a row per indicator and a volume row", () => {
    render(<ChartLegend rows={[row]} {...baseProps} />);
    expect(screen.getByText("EMA 20")).toBeInTheDocument();
    expect(screen.getByText("Vol")).toBeInTheDocument();
  });

  it("eye / gear / remove fire callbacks with the instanceId", () => {
    const onToggleHidden = vi.fn();
    const onOpenSettings = vi.fn();
    const onRemove = vi.fn();
    render(
      <ChartLegend rows={[row]} {...baseProps}
        onToggleHidden={onToggleHidden} onOpenSettings={onOpenSettings} onRemove={onRemove} />
    );
    fireEvent.click(screen.getByLabelText("Hide EMA 20"));
    fireEvent.click(screen.getByLabelText("Settings EMA 20"));
    fireEvent.click(screen.getByLabelText("Remove EMA 20"));
    expect(onToggleHidden).toHaveBeenCalledWith("ema-20-close");
    expect(onOpenSettings).toHaveBeenCalledWith("ema-20-close");
    expect(onRemove).toHaveBeenCalledWith("ema-20-close");
  });

  it("volume eye fires onToggleVolume", () => {
    const onToggleVolume = vi.fn();
    render(<ChartLegend rows={[]} {...baseProps} onToggleVolume={onToggleVolume} />);
    fireEvent.click(screen.getByLabelText("Toggle volume"));
    expect(onToggleVolume).toHaveBeenCalledOnce();
  });

  it("hidden rows dim and show the Show label", () => {
    render(<ChartLegend rows={[{ ...row, hidden: true }]} {...baseProps} />);
    expect(screen.getByLabelText("Show EMA 20")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run to verify failure**

```bash
npx vitest run src/test/ChartLegend.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create `ChartLegend.tsx`:**

```tsx
'use client'
import { Eye, EyeOff, Settings2, X } from 'lucide-react'

export interface LegendRowData {
  instanceId: string
  title: string
  lines: Array<{ lineKey: string; color: string }>
  hidden: boolean
}

interface Props {
  rows: LegendRowData[]
  volumeVisible: boolean
  registerValueEl: (id: string, el: HTMLElement | null) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onRemove: (instanceId: string) => void
  onToggleVolume: () => void
}

const BTN = 'p-0.5 rounded text-[#787b86] hover:text-white opacity-0 group-hover:opacity-100 transition-opacity'

export function ChartLegend({
  rows, volumeVisible, registerValueEl,
  onToggleHidden, onOpenSettings, onRemove, onToggleVolume,
}: Props) {
  return (
    <div className="absolute top-2 left-2 z-10 flex flex-col gap-0.5 text-[11px] font-mono pointer-events-none max-w-[75%]">
      {/* OHLC row — innerHTML managed imperatively by ChartCore */}
      <div ref={el => registerValueEl('ohlc', el)} className="flex flex-wrap items-center leading-tight" />

      {/* Volume row */}
      <div className={`group flex items-center gap-1.5 pointer-events-auto w-fit ${volumeVisible ? '' : 'opacity-40'}`}>
        <span className="text-[#b2b5be]">Vol</span>
        {volumeVisible && <span ref={el => registerValueEl('volume', el)} className="text-[#26a69a]" />}
        <button aria-label="Toggle volume" title="Toggle volume" className={BTN} onClick={onToggleVolume}>
          {volumeVisible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
        </button>
      </div>

      {/* Indicator rows */}
      {rows.map(row => (
        <div
          key={row.instanceId}
          className={`group flex items-center gap-1.5 pointer-events-auto w-fit ${row.hidden ? 'opacity-40' : ''}`}
        >
          <span className="text-[#b2b5be]">{row.title}</span>
          {!row.hidden && row.lines.map(l => (
            <span
              key={l.lineKey}
              ref={el => registerValueEl(`${row.instanceId}:${l.lineKey}`, el)}
              style={{ color: l.color }}
            />
          ))}
          <span className="flex items-center gap-0.5">
            <button
              aria-label={`${row.hidden ? 'Show' : 'Hide'} ${row.title}`}
              title={row.hidden ? 'Show' : 'Hide'}
              className={BTN}
              onClick={() => onToggleHidden(row.instanceId)}
            >
              {row.hidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </button>
            <button aria-label={`Settings ${row.title}`} title="Settings" className={BTN}
                    onClick={() => onOpenSettings(row.instanceId)}>
              <Settings2 className="h-3 w-3" />
            </button>
            <button aria-label={`Remove ${row.title}`} title="Remove" className={BTN}
                    onClick={() => onRemove(row.instanceId)}>
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create `lib/overlaySeries.ts`:**

```ts
// frontend/src/components/trading-chart/lib/overlaySeries.ts
import { LineSeries, LineStyle, type IChartApi, type ISeriesApi } from 'lightweight-charts'
import type { ActiveIndicator, Candle, IndicatorId, LinePoint, Source } from './types'
import {
  computeSMA, computeEMA, computeWMA, computeHMA,
  computeBB, computeVWAP, computeSupertrend,
} from './computeIndicators'

export interface OverlayHandle {
  lineKey: string
  colorKey: string
  series: ISeriesApi<'Line'>
  data: LinePoint[]
}

// Single source of truth for which lines an overlay renders and which style
// key colors each line. Used by ChartCore (series) and ChartLegend (rows).
export function overlayLineSpec(id: IndicatorId): Array<{ lineKey: string; colorKey: string }> {
  switch (id) {
    case 'sma': case 'ema': case 'wma': case 'hma': case 'vwap':
      return [{ lineKey: 'line', colorKey: 'color' }]
    case 'bb':
      return [
        { lineKey: 'upper', colorKey: 'upperColor' },
        { lineKey: 'middle', colorKey: 'middleColor' },
        { lineKey: 'lower', colorKey: 'lowerColor' },
      ]
    case 'supertrend':
      return [
        { lineKey: 'bull', colorKey: 'bullColor' },
        { lineKey: 'bear', colorKey: 'bearColor' },
      ]
    default:
      return []  // volume_profile has no line renderer (pre-existing gap)
  }
}

const MA_COMPUTE = { sma: computeSMA, ema: computeEMA, wma: computeWMA, hma: computeHMA } as const

export function addOverlaySeries(chart: IChartApi, ind: ActiveIndicator, candles: Candle[]): OverlayHandle[] {
  const { indicatorId, inputs, style, hidden } = ind
  const base = {
    lineWidth: ((style.width as 1 | 2 | 3) ?? 2),
    priceLineVisible: false,
    lastValueVisible: false,
    visible: !hidden,
  }
  const mk = (colorKey: string, extra: Record<string, unknown> = {}) =>
    chart.addSeries(LineSeries, { color: (style[colorKey] as string) ?? '#888888', ...base, ...extra })

  if (indicatorId === 'sma' || indicatorId === 'ema' || indicatorId === 'wma' || indicatorId === 'hma') {
    const data = MA_COMPUTE[indicatorId](candles, inputs.period as number, inputs.source as Source)
    const series = mk('color')
    series.setData(data)
    return [{ lineKey: 'line', colorKey: 'color', series, data }]
  }

  if (indicatorId === 'vwap') {
    const data = computeVWAP(candles)
    const series = mk('color')
    series.setData(data)
    return [{ lineKey: 'line', colorKey: 'color', series, data }]
  }

  if (indicatorId === 'bb') {
    const r = computeBB(candles, inputs.period as number, inputs.stddev as number, inputs.source as Source)
    const upper = mk('upperColor'); upper.setData(r.upper)
    const middle = mk('middleColor', { lineStyle: LineStyle.Dashed }); middle.setData(r.middle)
    const lower = mk('lowerColor'); lower.setData(r.lower)
    return [
      { lineKey: 'upper', colorKey: 'upperColor', series: upper, data: r.upper },
      { lineKey: 'middle', colorKey: 'middleColor', series: middle, data: r.middle },
      { lineKey: 'lower', colorKey: 'lowerColor', series: lower, data: r.lower },
    ]
  }

  if (indicatorId === 'supertrend') {
    const r = computeSupertrend(candles, inputs.period as number, inputs.multiplier as number)
    const bullPoints = r.values.filter((_, i) => r.bullish[i])
    const bearPoints = r.values.filter((_, i) => !r.bullish[i])
    const bull = mk('bullColor'); bull.setData(bullPoints)
    const bear = mk('bearColor'); bear.setData(bearPoints)
    return [
      { lineKey: 'bull', colorKey: 'bullColor', series: bull, data: bullPoints },
      { lineKey: 'bear', colorKey: 'bearColor', series: bear, data: bearPoints },
    ]
  }

  return []
}
```

- [ ] **Step 5: Verify**

```bash
npx vitest run src/test/ChartLegend.test.tsx && npx vitest run && npx tsc --noEmit
```

Legend tests PASS; all suites PASS; tsc errors still ONLY in `ChartCore.tsx`, `SubChartPane.tsx`, `index.tsx`.

- [ ] **Step 6: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/ChartLegend.tsx frontend/src/components/trading-chart/lib/overlaySeries.ts frontend/src/test/ChartLegend.test.tsx
git commit -m "feat(chart): legend rows component + overlay series builder"
```

---

### Task 6: ChartCore rewrite — volume, legend wiring, style-without-rebuild, chrome

**Files:**
- Rewrite: `frontend/src/components/trading-chart/ChartCore.tsx`

- [ ] **Step 1: Rewrite the file** (full contents):

```tsx
'use client'

import { useCallback, useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { ActiveIndicator, Candle } from './lib/types'
import type { Range } from './ChartToolbar'
import { addOverlaySeries, overlayLineSpec, type OverlayHandle } from './lib/overlaySeries'
import { ChartLegend, type LegendRowData } from './ChartLegend'
import { INDICATOR_MAP, legendTitle } from './lib/indicators'
import { formatINR, formatVolume } from './lib/format'

// IST is UTC+05:30 = 19800 seconds ahead of UTC
const IST_OFFSET_SECONDS = 5 * 3600 + 30 * 60

function toChartTime(timestamp: string): Time {
  if (timestamp.length <= 10) return timestamp
  // yfinance daily candles have midnight timestamps (T00:00:00+05:30).
  if (timestamp.includes('T00:00:00')) return timestamp.slice(0, 10)
  const utcSeconds = Math.floor(new Date(timestamp).getTime() / 1000)
  return (utcSeconds + IST_OFFSET_SECONDS) as UTCTimestamp
}

interface ChartCoreProps {
  candles: Candle[]
  overlayIndicators: ActiveIndicator[]
  volumeVisible: boolean
  visibleRange?: Range
  height?: number
  onScrollLeft?: () => void
  onChartReady?: (chart: IChartApi) => void
  onChartRemove?: (chart: IChartApi) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onRemoveIndicator: (instanceId: string) => void
  onToggleVolume: () => void
}

function computeFromDate(lastDate: Date, range: Range): Date {
  const from = new Date(lastDate)
  switch (range) {
    case '1D':  from.setDate(from.getDate() - 1);         break
    case '5D':  from.setDate(from.getDate() - 5);         break
    case '1M':  from.setMonth(from.getMonth() - 1);       break
    case '3M':  from.setMonth(from.getMonth() - 3);       break
    case '6M':  from.setMonth(from.getMonth() - 6);       break
    case '1Y':  from.setFullYear(from.getFullYear() - 1); break
    case '5Y':  from.setFullYear(from.getFullYear() - 5); break
    case 'All': from.setFullYear(1970);                   break
  }
  return from
}

function ohlcHtml(d: { open: number; high: number; low: number; close: number }): string {
  const fmt = (n: number) => n.toFixed(2)
  const chg = d.close - d.open
  const pct = d.open !== 0 ? ((chg / d.open) * 100).toFixed(2) : '0.00'
  const cc = chg >= 0 ? '#26a69a' : '#ef5350'
  const sign = chg >= 0 ? '+' : ''
  return (
    `<span style="color:#9598a1">O&nbsp;</span><span style="color:${cc}">${fmt(d.open)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">H&nbsp;</span><span style="color:${cc}">${fmt(d.high)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">L&nbsp;</span><span style="color:${cc}">${fmt(d.low)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">C&nbsp;</span><span style="color:${cc}">${fmt(d.close)}</span>&nbsp;&nbsp;` +
    `<span style="color:${cc}">${sign}${fmt(chg)} (${sign}${pct}%)</span>`
  )
}

export function ChartCore({
  candles,
  overlayIndicators,
  volumeVisible,
  visibleRange = '6M',
  height = 500,
  onScrollLeft,
  onChartReady,
  onChartRemove,
  onToggleHidden,
  onOpenSettings,
  onRemoveIndicator,
  onToggleVolume,
}: ChartCoreProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const scrollLeftFired = useRef(false)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const handlesRef = useRef<Map<string, OverlayHandle[]>>(new Map())
  const valueElsRef = useRef<Map<string, HTMLElement>>(new Map())
  const candlesRef = useRef<Candle[]>(candles)
  candlesRef.current = candles

  // Writes current (hovered or last-bar) values into the legend's spans.
  const updateLegendValues = useCallback((param?: MouseEventParams) => {
    const els = valueElsRef.current
    const last = candlesRef.current[candlesRef.current.length - 1]
    const hovering = !!param?.time

    const ohlcEl = els.get('ohlc')
    if (ohlcEl) {
      let d: { open: number; high: number; low: number; close: number } | undefined
      if (hovering && candleSeriesRef.current) {
        d = param!.seriesData.get(candleSeriesRef.current) as typeof d
      }
      if (!d && last) d = last
      ohlcEl.innerHTML = d ? ohlcHtml(d) : ''
    }

    const volEl = els.get('volume')
    if (volEl) {
      let v: number | undefined
      if (hovering && volumeSeriesRef.current) {
        v = (param!.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)?.value
      }
      if (v === undefined && last) v = last.volume
      volEl.textContent = v !== undefined ? formatVolume(v) : '—'
    }

    handlesRef.current.forEach((handles, instanceId) => {
      for (const h of handles) {
        const el = els.get(`${instanceId}:${h.lineKey}`)
        if (!el) continue
        let v: number | undefined
        if (hovering) v = (param!.seriesData.get(h.series) as { value: number } | undefined)?.value
        if (v === undefined && h.data.length) v = h.data[h.data.length - 1].value
        el.textContent = v !== undefined ? v.toFixed(2) : '—'
      }
    })
  }, [])

  const registerValueEl = useCallback((id: string, el: HTMLElement | null) => {
    if (el) valueElsRef.current.set(id, el)
    else valueElsRef.current.delete(id)
    queueMicrotask(() => updateLegendValues())
  }, [updateLegendValues])

  // Rebuild key: add/remove/input changes only. Style and hidden are applied
  // in the lightweight effect below without recreating the chart.
  const overlayKey = overlayIndicators.map(i => i.instanceId).join('|')

  useEffect(() => {
    const container = containerRef.current
    if (!container || candles.length === 0) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { color: '#131722' },
        textColor: '#787b86',
        attributionLogo: false,
      },
      localization: { priceFormatter: formatINR },
      grid: {
        vertLines: { color: '#1e2328' },
        horzLines: { color: '#1e2328' },
      },
      rightPriceScale: { borderColor: '#2a2e39' },
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: '#555', labelBackgroundColor: '#2a2e39' },
        horzLine: { color: '#555', labelBackgroundColor: '#2a2e39' },
      },
    })
    chartRef.current = chart

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })
    candleSeriesRef.current = candleSeries
    candleSeries.setData(
      candles.map(c => ({
        time: toChartTime(c.timestamp),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    )

    // Volume histogram in the bottom 20% of the pane.
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      priceFormat: { type: 'volume' },
      lastValueVisible: false,
      priceLineVisible: false,
      visible: volumeVisible,
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
    volumeSeries.setData(
      candles.map(c => ({
        time: toChartTime(c.timestamp),
        value: c.volume,
        color: c.close >= c.open ? '#26a69a80' : '#ef535080',
      }))
    )
    volumeSeriesRef.current = volumeSeries

    // Visible range
    const lastCandle = candles[candles.length - 1]
    const isIntraday = lastCandle.timestamp.length > 10 && !lastCandle.timestamp.includes('T00:00:00')
    const lastDate = new Date(lastCandle.timestamp)
    const fromDate = computeFromDate(lastDate, visibleRange)
    try {
      if (visibleRange === 'All') {
        chart.timeScale().fitContent()
      } else if (isIntraday) {
        chart.timeScale().setVisibleRange({
          from: (Math.floor(fromDate.getTime() / 1000) + IST_OFFSET_SECONDS) as UTCTimestamp,
          to: (Math.floor(lastDate.getTime() / 1000) + IST_OFFSET_SECONDS) as UTCTimestamp,
        })
      } else {
        chart.timeScale().setVisibleRange({
          from: fromDate.toISOString().slice(0, 10) as Time,
          to: lastCandle.timestamp.slice(0, 10) as Time,
        })
      }
    } catch {
      chart.timeScale().fitContent()
    }

    // Overlay indicators
    handlesRef.current = new Map()
    for (const ind of overlayIndicators) {
      handlesRef.current.set(ind.instanceId, addOverlaySeries(chart, ind, candles))
    }

    // Scroll-left detection
    scrollLeftFired.current = false
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && range.from < 10 && !scrollLeftFired.current) {
        scrollLeftFired.current = true
        onScrollLeft?.()
      }
    })

    chart.subscribeCrosshairMove(param => updateLegendValues(param))
    updateLegendValues()

    onChartReady?.(chart)

    const ro = new ResizeObserver(entries => {
      const entry = entries[0]
      if (entry && chartRef.current) {
        chartRef.current.applyOptions({ width: entry.contentRect.width })
      }
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      onChartRemove?.(chart)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      handlesRef.current = new Map()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles, overlayKey, height, visibleRange])

  // Style / visibility pass — no chart rebuild.
  useEffect(() => {
    if (!chartRef.current) return
    for (const ind of overlayIndicators) {
      const handles = handlesRef.current.get(ind.instanceId)
      if (!handles) continue
      for (const h of handles) {
        h.series.applyOptions({
          visible: !ind.hidden,
          color: (ind.style[h.colorKey] as string) ?? '#888888',
          lineWidth: ((ind.style.width as 1 | 2 | 3) ?? 2),
        })
      }
    }
    volumeSeriesRef.current?.applyOptions({ visible: volumeVisible })
    updateLegendValues()
  }, [overlayIndicators, volumeVisible, updateLegendValues])

  const rows: LegendRowData[] = overlayIndicators.map(ind => {
    const def = INDICATOR_MAP[ind.indicatorId]
    return {
      instanceId: ind.instanceId,
      title: legendTitle(def, ind.inputs),
      lines: overlayLineSpec(ind.indicatorId).map(s => ({
        lineKey: s.lineKey,
        color: (ind.style[s.colorKey] as string) ?? '#888888',
      })),
      hidden: ind.hidden,
    }
  })

  return (
    <div className="relative w-full" style={{ height, backgroundColor: '#131722' }}>
      <ChartLegend
        rows={rows}
        volumeVisible={volumeVisible}
        registerValueEl={registerValueEl}
        onToggleHidden={onToggleHidden}
        onOpenSettings={onOpenSettings}
        onRemove={onRemoveIndicator}
        onToggleVolume={onToggleVolume}
      />
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

export default ChartCore
```

If the installed lightweight-charts v5 typings reject `attributionLogo` inside `layout`, check `node_modules/lightweight-charts/dist/typings.d.ts` for the correct location (it is a `layout` option in v5) — do not cast to `any`; report what you find if it genuinely differs.

- [ ] **Step 2: Verify**

```bash
npx vitest run && npx tsc --noEmit
```

Vitest PASS. tsc errors ONLY in `SubChartPane.tsx` and `index.tsx`.

- [ ] **Step 3: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/ChartCore.tsx
git commit -m "feat(chart): volume histogram, legend wiring, live style updates, INR axis"
```

---

### Task 7: SubChartPane rewrite — bands, level lines, header controls

**Files:**
- Rewrite: `frontend/src/components/trading-chart/SubChartPane.tsx`

- [ ] **Step 1: Rewrite the file** (full contents):

```tsx
'use client'

import { useCallback, useEffect, useRef } from 'react'
import {
  createChart,
  LineSeries,
  HistogramSeries,
  BaselineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
} from 'lightweight-charts'
import { Eye, EyeOff, Settings2, X } from 'lucide-react'
import type { ActiveIndicator, Candle, LinePoint, Source } from './lib/types'
import {
  computeRSI,
  computeMACD,
  computeStochastic,
  computeADX,
  computeATR,
  computeOBV,
} from './lib/computeIndicators'
import { INDICATOR_MAP, legendTitle } from './lib/indicators'
import { formatVolume } from './lib/format'

interface SubChartPaneProps {
  indicator: ActiveIndicator
  candles: Candle[]
  height: number
  onRemove: (instanceId: string) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onChartReady?: (chart: IChartApi) => void
  onChartRemove?: (chart: IChartApi) => void
}

const COLORS = { bg: '#131722', grid: '#1e2328', text: '#787b86', border: '#2a2e39' }
const BTN = 'p-0.5 rounded text-[#787b86] hover:text-white opacity-0 group-hover:opacity-100 transition-opacity'

interface PaneLine { key: string; series: ISeriesApi<'Line'>; data: LinePoint[] }

// Translucent fill between two horizontal levels (e.g. RSI 30–70 zone).
// A BaselineSeries with constant data at `upper` fills down to `lower`.
function addBand(chart: IChartApi, points: LinePoint[], upper: number, lower: number, color: string) {
  if (points.length === 0) return null
  const band = chart.addSeries(BaselineSeries, {
    baseValue: { type: 'price', price: lower },
    topLineColor: 'transparent',
    bottomLineColor: 'transparent',
    topFillColor1: `${color}1f`,
    topFillColor2: `${color}1f`,
    bottomFillColor1: 'transparent',
    bottomFillColor2: 'transparent',
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    autoscaleInfoProvider: () => null,   // never distort the pane's scale
  })
  band.setData(points.map(p => ({ time: p.time, value: upper })))
  return band
}

export function SubChartPane({
  indicator, candles, height,
  onRemove, onToggleHidden, onOpenSettings,
  onChartReady, onChartRemove,
}: SubChartPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const linesRef = useRef<PaneLine[]>([])
  const valueElsRef = useRef<Map<string, HTMLElement>>(new Map())

  const isObv = indicator.indicatorId === 'obv'

  const updateValues = useCallback((param?: MouseEventParams) => {
    for (const line of linesRef.current) {
      const el = valueElsRef.current.get(line.key)
      if (!el) continue
      let v: number | undefined
      if (param?.time) v = (param.seriesData.get(line.series) as { value: number } | undefined)?.value
      if (v === undefined && line.data.length) v = line.data[line.data.length - 1].value
      el.textContent = v !== undefined ? (isObv ? formatVolume(v) : v.toFixed(2)) : '—'
    }
  }, [isObv])

  const registerValueEl = useCallback((key: string, el: HTMLElement | null) => {
    if (el) valueElsRef.current.set(key, el)
    else valueElsRef.current.delete(key)
    queueMicrotask(() => updateValues())
  }, [updateValues])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const { indicatorId, inputs, style } = indicator

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text, attributionLogo: false },
      ...(isObv ? { localization: { priceFormatter: formatVolume } } : {}),
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      rightPriceScale: { borderColor: COLORS.border },
      timeScale: {
        borderColor: COLORS.border,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: COLORS.border, labelBackgroundColor: '#2a2e39' },
        horzLine: { color: COLORS.border, labelBackgroundColor: '#2a2e39' },
      },
    })
    chartRef.current = chart
    onChartReady?.(chart)

    const widthOpt = ((style.width as 1 | 2 | 3) ?? 2)
    const lineOpts = { lineWidth: widthOpt, priceScaleId: 'right' as const }
    const lines: PaneLine[] = []
    const allSeries: Array<ISeriesApi<'Line'> | ISeriesApi<'Histogram'> | ISeriesApi<'Baseline'>> = []

    if (indicatorId === 'rsi') {
      const data = computeRSI(candles, inputs.period as number, inputs.source as Source)
      const color = (style.color as string) ?? '#7b61ff'
      const ob = inputs.overbought as number
      const os = inputs.oversold as number
      const band = addBand(chart, data, ob, os, color)
      if (band) allSeries.push(band)
      const series = chart.addSeries(LineSeries, { color, ...lineOpts })
      series.setData(data)
      // Dashed level lines; no axis labels (the series' own last-value badge is the single label)
      series.createPriceLine({ price: ob, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      series.createPriceLine({ price: os, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'macd') {
      const r = computeMACD(
        candles,
        inputs.fast as number, inputs.slow as number, inputs.signal as number,
        inputs.source as Source,
      )
      const hist = chart.addSeries(HistogramSeries, {
        priceScaleId: 'right', lastValueVisible: false, priceLineVisible: false,
      })
      hist.setData(r.histogram)
      allSeries.push(hist)
      const macdSeries = chart.addSeries(LineSeries, { color: (style.macdColor as string) ?? '#2962ff', ...lineOpts })
      macdSeries.setData(r.macd)
      const signalSeries = chart.addSeries(LineSeries, { color: (style.signalColor as string) ?? '#ff6d00', ...lineOpts })
      signalSeries.setData(r.signal)
      lines.push({ key: 'macd', series: macdSeries, data: r.macd })
      lines.push({ key: 'signal', series: signalSeries, data: r.signal })
      allSeries.push(macdSeries, signalSeries)

    } else if (indicatorId === 'stochastic') {
      const r = computeStochastic(candles, inputs.k as number, inputs.d as number)
      const kColor = (style.kColor as string) ?? '#2962ff'
      const ob = inputs.overbought as number
      const os = inputs.oversold as number
      const band = addBand(chart, r.k, ob, os, kColor)
      if (band) allSeries.push(band)
      const kSeries = chart.addSeries(LineSeries, { color: kColor, ...lineOpts })
      kSeries.setData(r.k)
      kSeries.createPriceLine({ price: ob, color: kColor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      kSeries.createPriceLine({ price: os, color: kColor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      const dSeries = chart.addSeries(LineSeries, { color: (style.dColor as string) ?? '#ff6d00', ...lineOpts })
      dSeries.setData(r.d)
      lines.push({ key: 'k', series: kSeries, data: r.k })
      lines.push({ key: 'd', series: dSeries, data: r.d })
      allSeries.push(kSeries, dSeries)

    } else if (indicatorId === 'adx') {
      const data = computeADX(candles, inputs.period as number)
      const color = (style.color as string) ?? '#f7c948'
      const series = chart.addSeries(LineSeries, { color, ...lineOpts })
      series.setData(data)
      series.createPriceLine({
        price: inputs.threshold as number, color,
        lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
      })
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'atr') {
      const data = computeATR(candles, inputs.period as number)
      const series = chart.addSeries(LineSeries, { color: (style.color as string) ?? '#e040fb', ...lineOpts })
      series.setData(data)
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'obv') {
      const data = computeOBV(candles)
      const series = chart.addSeries(LineSeries, { color: (style.color as string) ?? '#00bcd4', ...lineOpts })
      series.setData(data)
      lines.push({ key: 'line', series, data })
      allSeries.push(series)
    }

    chart.timeScale().fitContent()
    for (const s of allSeries) s.applyOptions({ visible: !indicator.hidden })
    linesRef.current = lines
    chart.subscribeCrosshairMove(p => updateValues(p))
    updateValues()

    const ro = new ResizeObserver(entries => {
      const entry = entries[0]
      if (entry && chartRef.current) {
        chartRef.current.applyOptions({ width: entry.contentRect.width })
      }
    })
    ro.observe(container)

    return () => {
      ro.disconnect()
      onChartRemove?.(chart)
      chart.remove()
      chartRef.current = null
      linesRef.current = []
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indicator, candles, height])

  const def = INDICATOR_MAP[indicator.indicatorId]
  const title = legendTitle(def, indicator.inputs)

  const headerLines = (() => {
    switch (indicator.indicatorId) {
      case 'macd':
        return [
          { key: 'macd', color: (indicator.style.macdColor as string) ?? '#2962ff' },
          { key: 'signal', color: (indicator.style.signalColor as string) ?? '#ff6d00' },
        ]
      case 'stochastic':
        return [
          { key: 'k', color: (indicator.style.kColor as string) ?? '#2962ff' },
          { key: 'd', color: (indicator.style.dColor as string) ?? '#ff6d00' },
        ]
      default:
        return [{ key: 'line', color: (indicator.style.color as string) ?? '#888888' }]
    }
  })()

  return (
    <div className="relative w-full" style={{ height, backgroundColor: COLORS.bg, borderTop: `1px solid ${COLORS.border}` }}>
      <div className={`group absolute top-1 left-2 z-10 flex items-center gap-1.5 select-none text-[11px] font-mono ${indicator.hidden ? 'opacity-40' : ''}`}>
        <span style={{ color: COLORS.text }}>{title}</span>
        {!indicator.hidden && headerLines.map(l => (
          <span key={l.key} ref={el => registerValueEl(l.key, el)} style={{ color: l.color }} />
        ))}
        <button
          aria-label={`${indicator.hidden ? 'Show' : 'Hide'} ${title}`}
          title={indicator.hidden ? 'Show' : 'Hide'}
          className={BTN}
          onClick={() => onToggleHidden(indicator.instanceId)}
        >
          {indicator.hidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
        </button>
        <button aria-label={`Settings ${title}`} title="Settings" className={BTN}
                onClick={() => onOpenSettings(indicator.instanceId)}>
          <Settings2 className="h-3 w-3" />
        </button>
        <button aria-label={`Remove ${title}`} title="Remove" className={BTN}
                onClick={() => onRemove(indicator.instanceId)}>
          <X className="h-3 w-3" />
        </button>
      </div>
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

export default SubChartPane
```

Note: the pane intentionally rebuilds on any `indicator` change (including style) — panes are small (120 px) and this keeps the code simple; only the main chart avoids rebuilds for style.

- [ ] **Step 2: Verify**

```bash
npx vitest run && npx tsc --noEmit
```

Vitest PASS. tsc errors ONLY in `index.tsx` (old hook API / missing new props).

- [ ] **Step 3: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/SubChartPane.tsx
git commit -m "feat(chart): panel OB/OS bands, label-collision fix, header value readouts"
```

---

### Task 8: index.tsx + RangeSelector wiring — tsc green

**Files:**
- Modify: `frontend/src/components/trading-chart/index.tsx`
- Modify: `frontend/src/components/trading-chart/RangeSelector.tsx`

- [ ] **Step 1: Update `index.tsx`.** Replace the component body (full file):

```tsx
'use client'

import { useState } from 'react'
import { ChartToolbar, type Interval, type Range, INTERVAL_CONFIG } from './ChartToolbar'
import { ChartCore } from './ChartCore'
import { SubChartPane } from './SubChartPane'
import { IndicatorSearch } from './IndicatorSearch'
import { RangeSelector } from './RangeSelector'
import { useChartData } from './hooks/useChartData'
import { useIndicators } from './hooks/useIndicators'
import { useChartSync } from './hooks/useChartSync'
import { useCompanyInfo } from '@/lib/api/market'
import type { IChartApi } from 'lightweight-charts'

interface TradingChartProps {
  ticker: string
}

export function TradingChart({ ticker }: TradingChartProps) {
  const [activeInterval, setActiveInterval] = useState<Interval>('1D')
  const [activeRange, setActiveRange] = useState<Range>('6M')
  const [indicatorSearchOpen, setIndicatorSearchOpen] = useState(false)
  const [settingsTarget, setSettingsTarget] = useState<string | null>(null)

  const { apiInterval, period } = INTERVAL_CONFIG[activeInterval]

  const { candles, isLoading } = useChartData(ticker, apiInterval, period)
  const {
    activeIndicators,
    addIndicator,
    removeIndicator,
    updateInputs,
    updateStyle,
    toggleHidden,
    overlayIndicators,
    panelIndicators,
    canAddPanel,
    volumeVisible,
    toggleVolume,
  } = useIndicators()
  const { registerChart, unregisterChart } = useChartSync()

  const { data: companyInfo } = useCompanyInfo(ticker)

  const handleChartReady = (chart: IChartApi) => registerChart(chart)
  const handleChartRemove = (chart: IChartApi) => unregisterChart(chart)

  // When interval changes, reset range to a sensible default
  function handleIntervalChange(iv: Interval) {
    setActiveInterval(iv)
    if (iv === '1m') setActiveRange('1D')
    else if (['5m', '15m', '30m'].includes(iv)) setActiveRange('5D')
    else if (iv === '1H') setActiveRange('1M')
    else setActiveRange('6M')
  }

  // Gear in any legend → open the drawer with that instance's settings expanded
  function openSettingsFor(instanceId: string) {
    setSettingsTarget(instanceId)
    setIndicatorSearchOpen(true)
  }

  function closeSearch() {
    setIndicatorSearchOpen(false)
    setSettingsTarget(null)
  }

  return (
    <div className="flex flex-col bg-[#131722] rounded-2xl overflow-hidden border border-border">
      <ChartToolbar
        ticker={ticker}
        companyName={companyInfo?.name}
        activeInterval={activeInterval}
        onIntervalChange={handleIntervalChange}
        onIndicatorsClick={() => setIndicatorSearchOpen(true)}
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-[#787b86] text-sm">
          Loading chart data…
        </div>
      ) : (
        <>
          <ChartCore
            candles={candles}
            overlayIndicators={overlayIndicators}
            volumeVisible={volumeVisible}
            visibleRange={activeRange}
            onChartReady={handleChartReady}
            onChartRemove={handleChartRemove}
            onToggleHidden={toggleHidden}
            onOpenSettings={openSettingsFor}
            onRemoveIndicator={removeIndicator}
            onToggleVolume={toggleVolume}
          />

          {panelIndicators.map(ind => (
            <SubChartPane
              key={ind.instanceId}
              indicator={ind}
              candles={candles}
              height={120}
              onRemove={removeIndicator}
              onToggleHidden={toggleHidden}
              onOpenSettings={openSettingsFor}
              onChartReady={handleChartReady}
              onChartRemove={handleChartRemove}
            />
          ))}

          <RangeSelector activeRange={activeRange} onRangeChange={setActiveRange} />
        </>
      )}

      <IndicatorSearch
        isOpen={indicatorSearchOpen}
        onClose={closeSearch}
        activeIndicators={activeIndicators}
        onAdd={addIndicator}
        onRemove={removeIndicator}
        onUpdateInputs={updateInputs}
        onUpdateStyle={updateStyle}
        canAddPanel={canAddPanel}
        initialOpenInstanceId={settingsTarget}
      />
    </div>
  )
}

export default TradingChart
```

- [ ] **Step 2: Add the attribution link to `RangeSelector.tsx`** (full file):

```tsx
'use client'
import { RANGES, type Range } from './ChartToolbar'

interface Props {
  activeRange: Range
  onRangeChange: (r: Range) => void
}

export function RangeSelector({ activeRange, onRangeChange }: Props) {
  return (
    <div className="flex items-center gap-0.5 px-2 py-1.5 border-t border-[#2a2e39] bg-[#131722]">
      {RANGES.map(r => (
        <button
          key={r}
          onClick={() => onRangeChange(r)}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
            activeRange === r
              ? 'bg-[#2962ff] text-white'
              : 'text-[#787b86] hover:text-white hover:bg-[#2a2e39]'
          }`}
        >
          {r}
        </button>
      ))}
      {/* License-compliant attribution — per-pane watermark logos are disabled */}
      <a
        href="https://www.tradingview.com/lightweight-charts/"
        target="_blank"
        rel="noopener noreferrer"
        className="ml-auto text-[10px] text-[#787b86] hover:text-white transition-colors pr-1"
      >
        Powered by TradingView Lightweight Charts
      </a>
    </div>
  )
}
```

- [ ] **Step 3: Full frontend verification — first fully-green commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart/frontend
npx tsc --noEmit && npm run lint && npx vitest run && npm run build
```

Expected: ALL green, zero tsc errors anywhere.

- [ ] **Step 4: Commit**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
git add frontend/src/components/trading-chart/index.tsx frontend/src/components/trading-chart/RangeSelector.tsx
git commit -m "feat(chart): wire settings routing, volume toggle, attribution footer"
```

---

### Task 9: README, manual verification, PR

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README.** Find the section describing the dashboard/chart (grep -ni "chart" README.md); update or add under the frontend features section:

```markdown
### Trading Chart

TradingView-style chart (lightweight-charts) on each stock page:

- 14 indicators — SMA, EMA, WMA, HMA, Supertrend, Bollinger, VWAP (overlays);
  RSI, MACD, Stochastic, ADX, ATR, OBV (panels, max 2)
- Full per-indicator settings: periods, price source (close/open/hl2/hlc3/ohlc4),
  per-line colors, line width, and editable overbought/oversold levels
- Volume histogram, TradingView-style legends with live values and
  hide/settings/remove controls, shaded OB/OS bands in oscillator panes
- Layout persists in localStorage across sessions and tickers
```

- [ ] **Step 2: Manual smoke check (visual).** Start the dev server against the worktree and verify in a browser (or report what you could not verify):

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart/frontend && npm run dev
```

Open `http://localhost:3000/dashboard/stocks/RELIANCE.NS` (login with guest@localtest.dev / 12345678 if auth blocks). Verify: volume bars render; OHLC legend shows last bar by default; adding SMA shows a legend row with live value; eye hides the line instantly; color change applies without chart flicker; RSI shows shaded 30–70 band with no duplicate axis badges; only one attribution link, no watermark logos; reload preserves indicators. Stop the server after.

- [ ] **Step 3: Final verification + commit + push + PR**

```bash
cd /Users/divyanshuagarwal/Downloads/frist-workflow-chart
"/Users/divyanshuagarwal/Downloads/frist workflow/.venv/bin/python" -m pytest tests/ -q   # backend untouched: expect baseline (2 known AngelFallbackTest failures)
cd frontend && npx tsc --noEmit && npm run lint && npx vitest run && npm run build && cd ..
git add README.md
git commit -m "docs: document chart indicators and settings"
git push -u origin feature/chart-professionalization
gh pr create --title "Chart professionalization: indicator settings, SMA/WMA/HMA, volume, legends" --body "$(cat <<'EOF'
## Summary
- Schema-driven indicator settings: price source, per-line colors, line width, editable OB/OS levels; instant style apply (no recompute); persisted to localStorage
- New indicators: SMA, WMA, HMA (source-aware, like EMA/RSI/BB/MACD now)
- Volume histogram in the main pane with legend row + eye toggle
- TradingView-style legends: OHLC row (last bar by default), per-indicator rows with live colored values and hide/settings/remove controls; same for panel headers
- Panel polish: shaded overbought/oversold bands, fixed duplicate axis-label collision
- Chrome: single attribution link instead of per-pane watermarks, ₹ + en-IN price axis, card-style wrapper

## Test plan
- computeIndicators: SMA/WMA/HMA fixtures, source extraction, source-aware EMA/RSI/BB/MACD
- useIndicators: persistence round-trip, corrupt-storage reset, validation clamps, panel cap
- ChartLegend: row rendering + eye/gear/remove interactions
- tsc, eslint, vitest, next build all green; manual visual check on /dashboard/stocks

Spec: docs/superpowers/specs/2026-06-12-chart-professionalization-design.md
Plan: docs/superpowers/plans/2026-06-12-chart-professionalization.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

After merge: delete the branch and remove the worktree (`git worktree remove /Users/divyanshuagarwal/Downloads/frist-workflow-chart --force && git branch -d feature/chart-professionalization`).
