// frontend/src/components/trading-chart/lib/format.ts

// Shared right price-scale width (px) applied to the main chart and every
// sub-pane so their plot areas — and therefore their time axes — align exactly.
// Comfortably fits typical ₹ price labels (e.g. ₹1,200.00) and the narrower
// oscillator value labels, so all panes render at the same width.
export const PRICE_SCALE_WIDTH = 80

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
