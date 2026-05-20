// frontend/src/components/trading-chart/lib/computeIndicators.ts
import type { Candle, LinePoint, HistPoint, MACDResult, BBResult } from './types'

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
