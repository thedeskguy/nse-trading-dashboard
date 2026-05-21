'use client'

import { useEffect, useRef } from 'react'
import {
  createChart,
  LineSeries,
  HistogramSeries,
  LineStyle,
  type IChartApi,
} from 'lightweight-charts'
import type { ActiveIndicator, Candle } from './lib/types'
import {
  computeRSI,
  computeMACD,
  computeStochastic,
  computeADX,
  computeATR,
  computeOBV,
} from './lib/computeIndicators'
import { INDICATOR_MAP } from './lib/indicators'

interface SubChartPaneProps {
  indicator: ActiveIndicator
  candles: Candle[]
  height: number
  onRemove: (instanceId: string) => void
  onChartReady?: (chart: IChartApi) => void
  onChartRemove?: (chart: IChartApi) => void
}

const COLORS = {
  bg: '#131722',
  grid: '#1e2328',
  text: '#787b86',
  border: '#2a2e39',
  rsi: '#7b61ff',
  macdLine: '#2962ff',
  macdSignal: '#ff6d00',
  stochK: '#2962ff',
  stochD: '#ff6d00',
  adx: '#f7c948',
  atr: '#e040fb',
  obv: '#00bcd4',
}

export function SubChartPane({ indicator, candles, height, onRemove, onChartReady, onChartRemove }: SubChartPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { color: COLORS.bg },
        textColor: COLORS.text,
      },
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      rightPriceScale: {
        borderColor: COLORS.border,
      },
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

    const { indicatorId, params } = indicator

    if (indicatorId === 'rsi') {
      const period = params.period ?? 14
      const data = computeRSI(candles, period)
      const series = chart.addSeries(LineSeries, {
        color: COLORS.rsi,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      series.setData(data)
      series.createPriceLine({ price: 70, color: COLORS.rsi, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '70' })
      series.createPriceLine({ price: 30, color: COLORS.rsi, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '30' })

    } else if (indicatorId === 'macd') {
      const { fast = 12, slow = 26, signal = 9 } = params
      const result = computeMACD(candles, fast, slow, signal)

      const histSeries = chart.addSeries(HistogramSeries, {
        priceScaleId: 'right',
        lastValueVisible: false,
        priceLineVisible: false,
      })
      histSeries.setData(result.histogram)

      const macdSeries = chart.addSeries(LineSeries, {
        color: COLORS.macdLine,
        lineWidth: 2,
        priceScaleId: 'right',
        lastValueVisible: true,
      })
      macdSeries.setData(result.macd)

      const signalSeries = chart.addSeries(LineSeries, {
        color: COLORS.macdSignal,
        lineWidth: 2,
        priceScaleId: 'right',
        lastValueVisible: true,
      })
      signalSeries.setData(result.signal)

    } else if (indicatorId === 'stochastic') {
      const { k: kPeriod = 14, d: dPeriod = 3 } = params
      const result = computeStochastic(candles, kPeriod, dPeriod)

      const kSeries = chart.addSeries(LineSeries, {
        color: COLORS.stochK,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      kSeries.setData(result.k)
      kSeries.createPriceLine({ price: 80, color: COLORS.stochK, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '80' })
      kSeries.createPriceLine({ price: 20, color: COLORS.stochK, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '20' })

      const dSeries = chart.addSeries(LineSeries, {
        color: COLORS.stochD,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      dSeries.setData(result.d)

    } else if (indicatorId === 'adx') {
      const period = params.period ?? 14
      const data = computeADX(candles, period)
      const series = chart.addSeries(LineSeries, {
        color: COLORS.adx,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      series.setData(data)
      series.createPriceLine({ price: 25, color: COLORS.adx, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: '25' })

    } else if (indicatorId === 'atr') {
      const period = params.period ?? 14
      const data = computeATR(candles, period)
      const series = chart.addSeries(LineSeries, {
        color: COLORS.atr,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      series.setData(data)

    } else if (indicatorId === 'obv') {
      const data = computeOBV(candles)
      const series = chart.addSeries(LineSeries, {
        color: COLORS.obv,
        lineWidth: 2,
        priceScaleId: 'right',
      })
      series.setData(data)
    }

    chart.timeScale().fitContent()

    // ResizeObserver
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indicator.instanceId, candles, height])

  const def = INDICATOR_MAP[indicator.indicatorId]
  const paramStr = Object.entries(indicator.params)
    .map(([, v]) => v)
    .join(', ')
  const label = def ? `${def.name}${paramStr ? ` (${paramStr})` : ''}` : indicator.indicatorId

  return (
    <div className="relative w-full" style={{ height, backgroundColor: COLORS.bg, borderTop: `1px solid ${COLORS.border}` }}>
      {/* Header overlay */}
      <div
        className="absolute top-1 left-2 z-10 flex items-center gap-2 select-none"
        style={{ pointerEvents: 'none' }}
      >
        <span className="text-xs font-medium" style={{ color: COLORS.text }}>
          {label}
        </span>
      </div>
      <button
        className="absolute top-1 right-2 z-10 flex items-center justify-center rounded hover:opacity-80 transition-opacity"
        style={{ color: COLORS.text, lineHeight: 1 }}
        onClick={() => onRemove(indicator.instanceId)}
        aria-label={`Remove ${label}`}
        title={`Remove ${label}`}
      >
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M1 1L11 11M11 1L1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </button>
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

export default SubChartPane
