import { computeEMA, computeRSI, computeMACD, computeBB } from '@/components/trading-chart/lib/computeIndicators'
import type { Candle } from '@/components/trading-chart/lib/types'

function makeCandles(n: number, startPrice = 100): Candle[] {
  return Array.from({ length: n }, (_, i) => ({
    timestamp: `2024-01-${String(i + 1).padStart(2, '0')}`,
    open: startPrice + i,
    high: startPrice + i + 5,
    low: Math.max(1, startPrice + i - 5),
    close: startPrice + i + 1,
    volume: 1000 + i * 10,
  }))
}

describe('computeEMA', () => {
  it('returns empty array when candles < period', () => {
    expect(computeEMA(makeCandles(3), 14)).toHaveLength(0)
  })
  it('first value equals SMA of first period candles', () => {
    const candles = makeCandles(20)
    const result = computeEMA(candles, 5)
    const sma5 = (candles[0].close + candles[1].close + candles[2].close + candles[3].close + candles[4].close) / 5
    expect(result[0].value).toBeCloseTo(sma5, 4)
  })
  it('returns candles.length - period + 1 points', () => {
    const candles = makeCandles(30)
    expect(computeEMA(candles, 10)).toHaveLength(21)
  })
  it('each point has a valid time string', () => {
    const candles = makeCandles(20)
    computeEMA(candles, 5).forEach(p => expect(typeof p.time).toBe('string'))
  })
})

describe('computeRSI', () => {
  it('returns empty for fewer candles than period + 1', () => {
    expect(computeRSI(makeCandles(10), 14)).toHaveLength(0)
  })
  it('values are between 0 and 100', () => {
    computeRSI(makeCandles(50), 14).forEach(p => {
      expect(p.value).toBeGreaterThanOrEqual(0)
      expect(p.value).toBeLessThanOrEqual(100)
    })
  })
})

describe('computeMACD', () => {
  it('macd, signal, histogram arrays have equal length', () => {
    const result = computeMACD(makeCandles(100), 12, 26, 9)
    expect(result.macd.length).toBe(result.signal.length)
    expect(result.signal.length).toBe(result.histogram.length)
  })
  it('histogram[i].value === macd[i].value - signal[i].value', () => {
    const result = computeMACD(makeCandles(100), 12, 26, 9)
    result.histogram.forEach((h, i) => {
      expect(h.value).toBeCloseTo(result.macd[i].value - result.signal[i].value, 6)
    })
  })
})

describe('computeBB', () => {
  it('upper >= middle >= lower for each point', () => {
    const candles = makeCandles(50)
    const bb = computeBB(candles, 20, 2)
    bb.upper.forEach((u, i) => {
      expect(u.value).toBeGreaterThanOrEqual(bb.middle[i].value)
      expect(bb.middle[i].value).toBeGreaterThanOrEqual(bb.lower[i].value)
    })
  })
})

import {
  computeATR, computeStochastic, computeADX,
  computeOBV, computeVWAP, computeSupertrend, computeVolumeProfile
} from '@/components/trading-chart/lib/computeIndicators'

describe('computeATR', () => {
  it('returns empty for fewer candles than period', () => {
    expect(computeATR(makeCandles(5), 14)).toHaveLength(0)
  })
  it('all values are positive', () => {
    computeATR(makeCandles(50), 14).forEach(p => expect(p.value).toBeGreaterThan(0))
  })
})

describe('computeStochastic', () => {
  it('k and d arrays have equal length', () => {
    const result = computeStochastic(makeCandles(50), 14, 3)
    expect(result.k.length).toBe(result.d.length)
  })
  it('k values are between 0 and 100', () => {
    computeStochastic(makeCandles(50), 14, 3).k.forEach(p => {
      expect(p.value).toBeGreaterThanOrEqual(0)
      expect(p.value).toBeLessThanOrEqual(100)
    })
  })
})

describe('computeOBV', () => {
  it('returns candles.length - 1 points', () => {
    expect(computeOBV(makeCandles(20))).toHaveLength(19)
  })
})

describe('computeVWAP', () => {
  it('returns candles.length points', () => {
    expect(computeVWAP(makeCandles(20))).toHaveLength(20)
  })
  it('vwap values are positive', () => {
    computeVWAP(makeCandles(20)).forEach(p => expect(p.value).toBeGreaterThan(0))
  })
})

describe('computeSupertrend', () => {
  it('values length equals bullish length', () => {
    const result = computeSupertrend(makeCandles(50), 10, 3)
    expect(result.values.length).toBeGreaterThan(0)
    expect(result.values.length).toBe(result.bullish.length)
  })
})

describe('computeVolumeProfile', () => {
  it('returns exactly bins bars', () => {
    expect(computeVolumeProfile(makeCandles(50), 10)).toHaveLength(10)
  })
  it('all volumes are non-negative', () => {
    computeVolumeProfile(makeCandles(50), 10).forEach(b => expect(b.volume).toBeGreaterThanOrEqual(0))
  })
})
