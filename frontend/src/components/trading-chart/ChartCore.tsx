'use client'

import { useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  LineStyle,
  type IChartApi,
} from 'lightweight-charts'
import type { ActiveIndicator, Candle } from './lib/types'
import {
  computeEMA,
  computeBB,
  computeVWAP,
  computeSupertrend,
} from './lib/computeIndicators'

interface ChartCoreProps {
  candles: Candle[]
  overlayIndicators: ActiveIndicator[]
  height?: number
  onScrollLeft?: () => void
  onChartReady?: (chart: IChartApi) => void
}

function emaColor(period: number): string {
  switch (period) {
    case 9:   return '#e040fb'
    case 20:
    case 21:  return '#f7c948'
    case 50:  return '#2196f3'
    case 100: return '#26c6da'
    case 200: return '#ff7043'
    default:  return '#888'
  }
}

export function ChartCore({
  candles,
  overlayIndicators,
  height = 500,
  onScrollLeft,
  onChartReady,
}: ChartCoreProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const scrollLeftFired = useRef(false)

  useEffect(() => {
    const container = containerRef.current
    if (!container || candles.length === 0) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { color: '#131722' },
        textColor: '#787b86',
      },
      grid: {
        vertLines: { color: '#1e2328' },
        horzLines: { color: '#1e2328' },
      },
      rightPriceScale: {
        borderColor: '#2a2e39',
      },
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

    // Candlestick series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })

    candleSeries.setData(
      candles.map(c => ({
        time: c.timestamp,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    )

    // Set visible range to last 6 months
    const lastCandle = candles[candles.length - 1]
    const lastDate = new Date(lastCandle.timestamp)
    const sixMonthsAgo = new Date(lastDate)
    sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6)
    const fromStr = sixMonthsAgo.toISOString().slice(0, 10)
    try {
      chart.timeScale().setVisibleRange({ from: fromStr as import('lightweight-charts').Time, to: lastCandle.timestamp as import('lightweight-charts').Time })
    } catch {
      chart.timeScale().fitContent()
    }

    // Overlay indicators
    for (const indicator of overlayIndicators) {
      const { indicatorId, params } = indicator

      if (indicatorId === 'ema') {
        const period = params.period ?? 20
        const data = computeEMA(candles, period)
        const series = chart.addSeries(LineSeries, {
          color: emaColor(period),
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        series.setData(data)

      } else if (indicatorId === 'bb') {
        const period = params.period ?? 20
        const stddev = params.stddev ?? 2
        const result = computeBB(candles, period, stddev)

        const upperSeries = chart.addSeries(LineSeries, {
          color: '#42a5f5',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        upperSeries.setData(result.upper)

        const middleSeries = chart.addSeries(LineSeries, {
          color: '#78909c',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        middleSeries.setData(result.middle)

        const lowerSeries = chart.addSeries(LineSeries, {
          color: '#42a5f5',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        lowerSeries.setData(result.lower)

      } else if (indicatorId === 'vwap') {
        const data = computeVWAP(candles)
        const series = chart.addSeries(LineSeries, {
          color: '#ff6d00',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        })
        series.setData(data)

      } else if (indicatorId === 'supertrend') {
        const period = params.period ?? 10
        const multiplier = params.multiplier ?? 3
        const result = computeSupertrend(candles, period, multiplier)

        const bullPoints = result.values.filter((_, i) => result.bullish[i])
        const bearPoints = result.values.filter((_, i) => !result.bullish[i])

        if (bullPoints.length > 0) {
          const bullSeries = chart.addSeries(LineSeries, {
            color: '#26a69a',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
          })
          bullSeries.setData(bullPoints)
        }

        if (bearPoints.length > 0) {
          const bearSeries = chart.addSeries(LineSeries, {
            color: '#ef5350',
            lineWidth: 2,
            priceLineVisible: false,
            lastValueVisible: false,
          })
          bearSeries.setData(bearPoints)
        }
      }
    }

    // Scroll-left detection
    scrollLeftFired.current = false
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && range.from < 10 && !scrollLeftFired.current) {
        scrollLeftFired.current = true
        onScrollLeft?.()
      }
    })

    // Notify parent
    onChartReady?.(chart)

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
      chart.remove()
      chartRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles, overlayIndicators, height])

  return (
    <div
      ref={containerRef}
      className="w-full"
      style={{ height, backgroundColor: '#131722' }}
    />
  )
}

export default ChartCore
