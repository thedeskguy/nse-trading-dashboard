import {
  INDICATOR_MAP, inputDefaults, styleDefaults, legendTitle, sanitizeStored,
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

describe('defaults', () => {
  it('inputDefaults/styleDefaults split by kind', () => {
    const def = INDICATOR_MAP.ema
    expect(inputDefaults(def)).toEqual({ period: 20, source: 'close' })
    expect(styleDefaults(def)).toEqual({ color: '#2196f3', width: 2 })
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
