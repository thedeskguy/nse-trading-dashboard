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
