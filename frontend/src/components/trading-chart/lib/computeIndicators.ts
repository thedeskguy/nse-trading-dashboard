// frontend/src/components/trading-chart/lib/computeIndicators.ts
import type { Candle, LinePoint, HistPoint, MACDResult, BBResult, StochasticResult, SupertrendResult, VolumeProfileBar } from './types'

function toTime(timestamp: string): string { return timestamp }

// ── EMA ──────────────────────────────────────────────────────────────────────
export function computeEMA(candles: Candle[], period: number): LinePoint[] {
  if (candles.length < period) return []
  const k = 2 / (period + 1)
  const result: LinePoint[] = []
  let ema = candles.slice(0, period).reduce((s, c) => s + c.close, 0) / period
  result.push({ time: toTime(candles[period - 1].timestamp), value: ema })
  for (let i = period; i < candles.length; i++) {
    ema = candles[i].close * k + ema * (1 - k)
    result.push({ time: toTime(candles[i].timestamp), value: ema })
  }
  return result
}

// ── RSI ──────────────────────────────────────────────────────────────────────
export function computeRSI(candles: Candle[], period: number): LinePoint[] {
  if (candles.length <= period) return []
  let avgGain = 0, avgLoss = 0
  for (let i = 1; i <= period; i++) {
    const diff = candles[i].close - candles[i - 1].close
    if (diff > 0) avgGain += diff; else avgLoss += Math.abs(diff)
  }
  avgGain /= period
  avgLoss /= period
  const result: LinePoint[] = []
  for (let i = period; i < candles.length; i++) {
    if (i > period) {
      const diff = candles[i].close - candles[i - 1].close
      avgGain = (avgGain * (period - 1) + Math.max(0, diff)) / period
      avgLoss = (avgLoss * (period - 1) + Math.max(0, -diff)) / period
    }
    const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss
    result.push({ time: toTime(candles[i].timestamp), value: avgLoss === 0 ? 100 : 100 - 100 / (1 + rs) })
  }
  return result
}

// ── Internal EMA helper (operates on number array) ───────────────────────────
export function _ema(values: number[], period: number): number[] {
  if (values.length < period) return []
  const k = 2 / (period + 1)
  const result: number[] = [values.slice(0, period).reduce((s, v) => s + v, 0) / period]
  for (let i = period; i < values.length; i++) {
    result.push(values[i] * k + result[result.length - 1] * (1 - k))
  }
  return result
}

// ── MACD ─────────────────────────────────────────────────────────────────────
export function computeMACD(candles: Candle[], fast: number, slow: number, signal: number): MACDResult {
  const emaFast = computeEMA(candles, fast)
  const emaSlow = computeEMA(candles, slow)
  const offset = slow - fast
  const macdLine: LinePoint[] = emaSlow.map((s, i) => ({
    time: s.time,
    value: emaFast[i + offset].value - s.value,
  }))
  const signalRaw = _ema(macdLine.map(p => p.value), signal)
  const signalLine: LinePoint[] = signalRaw.map((v, i) => ({
    time: macdLine[i + signal - 1].time,
    value: v,
  }))
  const macdTrimmed = macdLine.slice(signal - 1)
  const histogram: HistPoint[] = macdTrimmed.map((m, i) => ({
    time: m.time,
    value: m.value - signalLine[i].value,
    color: m.value - signalLine[i].value >= 0 ? '#26a69a' : '#ef5350',
  }))
  return { macd: macdTrimmed, signal: signalLine, histogram }
}

// ── Bollinger Bands ───────────────────────────────────────────────────────────
export function computeBB(candles: Candle[], period: number, stddev: number): BBResult {
  if (candles.length < period) return { upper: [], middle: [], lower: [] }
  const upper: LinePoint[] = [], middle: LinePoint[] = [], lower: LinePoint[] = []
  for (let i = period - 1; i < candles.length; i++) {
    const slice = candles.slice(i - period + 1, i + 1).map(c => c.close)
    const mean = slice.reduce((s, v) => s + v, 0) / period
    const std = Math.sqrt(slice.reduce((s, v) => s + (v - mean) ** 2, 0) / period)
    const t = toTime(candles[i].timestamp)
    upper.push({ time: t, value: mean + stddev * std })
    middle.push({ time: t, value: mean })
    lower.push({ time: t, value: mean - stddev * std })
  }
  return { upper, middle, lower }
}

// ── ATR ───────────────────────────────────────────────────────────────────────
export function computeATR(candles: Candle[], period: number): LinePoint[] {
  if (candles.length <= period) return []
  const trs: number[] = []
  for (let i = 1; i < candles.length; i++) {
    const hl = candles[i].high - candles[i].low
    const hpc = Math.abs(candles[i].high - candles[i - 1].close)
    const lpc = Math.abs(candles[i].low - candles[i - 1].close)
    trs.push(Math.max(hl, hpc, lpc))
  }
  let atr = trs.slice(0, period).reduce((s, v) => s + v, 0) / period
  const result: LinePoint[] = [{ time: toTime(candles[period].timestamp), value: atr }]
  for (let i = period; i < trs.length; i++) {
    atr = (atr * (period - 1) + trs[i]) / period
    result.push({ time: toTime(candles[i + 1].timestamp), value: atr })
  }
  return result
}

// ── Stochastic ────────────────────────────────────────────────────────────────
export function computeStochastic(candles: Candle[], kPeriod: number, dPeriod: number): StochasticResult {
  const kValues: LinePoint[] = []
  for (let i = kPeriod - 1; i < candles.length; i++) {
    const slice = candles.slice(i - kPeriod + 1, i + 1)
    const lowest = Math.min(...slice.map(c => c.low))
    const highest = Math.max(...slice.map(c => c.high))
    const range = highest - lowest
    kValues.push({ time: toTime(candles[i].timestamp), value: range === 0 ? 50 : ((candles[i].close - lowest) / range) * 100 })
  }
  const dRaw = _ema(kValues.map(p => p.value), dPeriod)
  const d: LinePoint[] = dRaw.map((v, i) => ({ time: kValues[i + dPeriod - 1].time, value: v }))
  const k = kValues.slice(dPeriod - 1)
  return { k, d }
}

// ── ADX ───────────────────────────────────────────────────────────────────────
export function computeADX(candles: Candle[], period: number): LinePoint[] {
  if (candles.length <= period * 2) return []
  const plusDM: number[] = [], minusDM: number[] = [], tr: number[] = []
  for (let i = 1; i < candles.length; i++) {
    const upMove = candles[i].high - candles[i - 1].high
    const downMove = candles[i - 1].low - candles[i].low
    plusDM.push(upMove > downMove && upMove > 0 ? upMove : 0)
    minusDM.push(downMove > upMove && downMove > 0 ? downMove : 0)
    tr.push(Math.max(
      candles[i].high - candles[i].low,
      Math.abs(candles[i].high - candles[i - 1].close),
      Math.abs(candles[i].low - candles[i - 1].close),
    ))
  }
  const smoothed = (arr: number[]) => {
    let s = arr.slice(0, period).reduce((a, b) => a + b, 0)
    const r = [s]
    for (let i = period; i < arr.length; i++) { s = s - s / period + arr[i]; r.push(s) }
    return r
  }
  const sTR = smoothed(tr), sPDM = smoothed(plusDM), sMDM = smoothed(minusDM)
  const dx: number[] = sTR.map((t, i) => {
    const pdi = t === 0 ? 0 : (sPDM[i] / t) * 100
    const mdi = t === 0 ? 0 : (sMDM[i] / t) * 100
    const sum = pdi + mdi
    return sum === 0 ? 0 : (Math.abs(pdi - mdi) / sum) * 100
  })
  const adxRaw = _ema(dx, period)
  return adxRaw.map((v, i) => ({ time: toTime(candles[i + period].timestamp), value: v }))
}

// ── OBV ───────────────────────────────────────────────────────────────────────
export function computeOBV(candles: Candle[]): LinePoint[] {
  if (candles.length < 2) return []
  let obv = 0
  return candles.slice(1).map((c, i) => {
    const prev = candles[i]
    if (c.close > prev.close) obv += c.volume
    else if (c.close < prev.close) obv -= c.volume
    return { time: toTime(c.timestamp), value: obv }
  })
}

// ── VWAP ──────────────────────────────────────────────────────────────────────
export function computeVWAP(candles: Candle[]): LinePoint[] {
  let cumTPV = 0, cumVol = 0
  return candles.map(c => {
    const tp = (c.high + c.low + c.close) / 3
    cumTPV += tp * c.volume
    cumVol += c.volume
    return { time: toTime(c.timestamp), value: cumVol === 0 ? tp : cumTPV / cumVol }
  })
}

// ── Supertrend ────────────────────────────────────────────────────────────────
export function computeSupertrend(candles: Candle[], period: number, multiplier: number): SupertrendResult {
  const atrs = computeATR(candles, period)
  if (atrs.length === 0) return { values: [], bullish: [] }
  const offset = candles.length - atrs.length
  const values: LinePoint[] = []
  const bullish: boolean[] = []
  let prevST = 0, prevIsBull = true
  atrs.forEach((atr, idx) => {
    const i = idx + offset
    const hl2 = (candles[i].high + candles[i].low) / 2
    const upper = hl2 + multiplier * atr.value
    const lower = hl2 - multiplier * atr.value
    const isBull = candles[i].close > prevST ? true : candles[i].close < prevST ? false : prevIsBull
    const st = isBull ? lower : upper
    values.push({ time: toTime(candles[i].timestamp), value: st })
    bullish.push(isBull)
    prevST = st
    prevIsBull = isBull
  })
  return { values, bullish }
}

// ── Volume Profile ────────────────────────────────────────────────────────────
export function computeVolumeProfile(candles: Candle[], bins: number): VolumeProfileBar[] {
  if (candles.length === 0) return Array.from({ length: bins }, (_, i) => ({ price: i, volume: 0, isUp: true }))
  const prices = candles.map(c => c.close)
  const minP = Math.min(...prices), maxP = Math.max(...prices)
  const range = maxP - minP || 1
  const buckets = Array.from({ length: bins }, (_, i) => ({ price: minP + (i + 0.5) * (range / bins), volume: 0, isUp: true }))
  candles.forEach(c => {
    const idx = Math.min(bins - 1, Math.floor(((c.close - minP) / range) * bins))
    buckets[idx].volume += c.volume
    buckets[idx].isUp = c.close >= c.open
  })
  return buckets
}
