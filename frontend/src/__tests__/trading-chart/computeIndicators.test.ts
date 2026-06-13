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
  computeATR, computeStochastic,
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
    expect(result[0].value).toBeCloseTo(614 / 6, 4)
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
    expect(computeHMA(makeCandles(30), 9)).toHaveLength(20)
  })
  it('leads SMA on rising data (lower lag)', () => {
    const candles = makeCandles(60)
    const hma = computeHMA(candles, 20)
    const sma = computeSMA(candles, 20)
    expect(hma[hma.length - 1].value).toBeGreaterThan(sma[sma.length - 1].value)
  })
  it('preserves the exact slope on a linear ramp (zero-lag property)', () => {
    // makeCandles closes form a linear ramp 101,102,103,... (slope 1).
    // HMA of a linear series is itself linear with the SAME slope, so every
    // consecutive HMA value must differ by exactly the ramp slope (1).
    const hma = computeHMA(makeCandles(60), 16)
    expect(hma.length).toBeGreaterThan(2)
    for (let i = 1; i < hma.length; i++) {
      expect(hma[i].value - hma[i - 1].value).toBeCloseTo(1, 6)
    }
  })
  it('returns empty when not enough candles', () => {
    expect(computeHMA(makeCandles(5), 9)).toHaveLength(0)
  })
})

describe('source-aware indicators', () => {
  it('EMA on hl2 differs from close by the fixture offset', () => {
    const candles = makeCandles(30)
    const closeEMA = computeEMA(candles, 5)
    const hl2EMA = computeEMA(candles, 5, 'hl2')
    hl2EMA.forEach((p, i) => expect(p.value).toBeCloseTo(closeEMA[i].value - 1, 6))
  })
  it('RSI source changes the result (flat high → RSI 100, zigzag close → not 100)', () => {
    const candles = makeZigzagCandles(40)
    const rsiHigh = computeRSI(candles, 14, 'high')
    const rsiClose = computeRSI(candles, 14, 'close')
    rsiHigh.forEach(p => expect(p.value).toBe(100))
    expect(rsiClose.some(p => p.value < 100)).toBe(true)
  })
  it('BB middle on open differs from close', () => {
    const candles = makeCandles(40)
    const bbClose = computeBB(candles, 20, 2)
    const bbOpen = computeBB(candles, 20, 2, 'open')
    expect(bbOpen.middle[0].value).toBeCloseTo(bbClose.middle[0].value - 1, 6)
  })
  it('MACD accepts a source param and stays aligned', () => {
    const candles = makeCandles(100)
    const close = computeMACD(candles, 12, 26, 9)
    const hl2 = computeMACD(candles, 12, 26, 9, 'hl2')
    expect(hl2.macd.length).toBe(close.macd.length)
    expect(hl2.macd.length).toBeGreaterThan(0)
    hl2.macd.forEach((p, i) => expect(p.time).toBe(close.macd[i].time))
  })
})
