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
    lineWidth: ((style.width ?? 2) as 1 | 2 | 3 | 4),
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
