'use client'

import { useCallback, useEffect, useRef } from 'react'
import {
  createChart,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from 'lightweight-charts'
import type { ActiveIndicator, Candle } from './lib/types'
import type { Range } from './ChartToolbar'
import { addOverlaySeries, overlayLineSpec, type OverlayHandle } from './lib/overlaySeries'
import { ChartLegend, type LegendRowData } from './ChartLegend'
import { INDICATOR_MAP, legendTitle } from './lib/indicators'
import { formatINR, formatVolume, PRICE_SCALE_WIDTH } from './lib/format'

// IST is UTC+05:30 = 19800 seconds ahead of UTC
const IST_OFFSET_SECONDS = 5 * 3600 + 30 * 60

function toChartTime(timestamp: string): Time {
  if (timestamp.length <= 10) return timestamp
  // yfinance daily candles have midnight timestamps (T00:00:00+05:30).
  if (timestamp.includes('T00:00:00')) return timestamp.slice(0, 10)
  const utcSeconds = Math.floor(new Date(timestamp).getTime() / 1000)
  return (utcSeconds + IST_OFFSET_SECONDS) as UTCTimestamp
}

interface ChartCoreProps {
  candles: Candle[]
  overlayIndicators: ActiveIndicator[]
  volumeVisible: boolean
  visibleRange?: Range
  height?: number
  onScrollLeft?: () => void
  onChartReady?: (chart: IChartApi) => void
  onChartRemove?: (chart: IChartApi) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onRemoveIndicator: (instanceId: string) => void
  onToggleVolume: () => void
}

function computeFromDate(lastDate: Date, range: Range): Date {
  const from = new Date(lastDate)
  switch (range) {
    case '1D':  from.setDate(from.getDate() - 1);         break
    case '5D':  from.setDate(from.getDate() - 5);         break
    case '1M':  from.setMonth(from.getMonth() - 1);       break
    case '3M':  from.setMonth(from.getMonth() - 3);       break
    case '6M':  from.setMonth(from.getMonth() - 6);       break
    case '1Y':  from.setFullYear(from.getFullYear() - 1); break
    case '5Y':  from.setFullYear(from.getFullYear() - 5); break
    case 'All': from.setFullYear(1970);                   break
  }
  return from
}

function ohlcHtml(d: { open: number; high: number; low: number; close: number }): string {
  const fmt = (n: number) => n.toFixed(2)
  const chg = d.close - d.open
  const pct = d.open !== 0 ? ((chg / d.open) * 100).toFixed(2) : '0.00'
  const cc = chg >= 0 ? '#26a69a' : '#ef5350'
  const sign = chg >= 0 ? '+' : ''
  return (
    `<span style="color:#9598a1">O&nbsp;</span><span style="color:${cc}">${fmt(d.open)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">H&nbsp;</span><span style="color:${cc}">${fmt(d.high)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">L&nbsp;</span><span style="color:${cc}">${fmt(d.low)}</span>&nbsp;&nbsp;` +
    `<span style="color:#9598a1">C&nbsp;</span><span style="color:${cc}">${fmt(d.close)}</span>&nbsp;&nbsp;` +
    `<span style="color:${cc}">${sign}${fmt(chg)} (${sign}${pct}%)</span>`
  )
}

export function ChartCore({
  candles,
  overlayIndicators,
  volumeVisible,
  visibleRange = '6M',
  height = 500,
  onScrollLeft,
  onChartReady,
  onChartRemove,
  onToggleHidden,
  onOpenSettings,
  onRemoveIndicator,
  onToggleVolume,
}: ChartCoreProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const scrollLeftFired = useRef(false)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  const handlesRef = useRef<Map<string, OverlayHandle[]>>(new Map())
  const valueElsRef = useRef<Map<string, HTMLElement>>(new Map())
  const candlesRef = useRef<Candle[]>(candles)
  candlesRef.current = candles

  // Writes current (hovered or last-bar) values into the legend's spans.
  const updateLegendValues = useCallback((param?: MouseEventParams) => {
    const els = valueElsRef.current
    const last = candlesRef.current[candlesRef.current.length - 1]
    const hovering = !!param?.time

    const ohlcEl = els.get('ohlc')
    if (ohlcEl) {
      let d: { open: number; high: number; low: number; close: number } | undefined
      if (hovering && candleSeriesRef.current) {
        d = param!.seriesData.get(candleSeriesRef.current) as typeof d
      }
      if (!d && last) d = last
      ohlcEl.innerHTML = d ? ohlcHtml(d) : ''
    }

    const volEl = els.get('volume')
    if (volEl) {
      let v: number | undefined
      if (hovering && volumeSeriesRef.current) {
        v = (param!.seriesData.get(volumeSeriesRef.current) as { value: number } | undefined)?.value
      }
      if (v === undefined && last) v = last.volume
      volEl.textContent = v !== undefined ? formatVolume(v) : '—'
    }

    handlesRef.current.forEach((handles, instanceId) => {
      for (const h of handles) {
        const el = els.get(`${instanceId}:${h.lineKey}`)
        if (!el) continue
        let v: number | undefined
        if (hovering) v = (param!.seriesData.get(h.series) as { value: number } | undefined)?.value
        if (v === undefined && h.data.length) v = h.data[h.data.length - 1].value
        el.textContent = v !== undefined ? v.toFixed(2) : '—'
      }
    })
  }, [])

  const registerValueEl = useCallback((id: string, el: HTMLElement | null) => {
    if (el) valueElsRef.current.set(id, el)
    else valueElsRef.current.delete(id)
    queueMicrotask(() => updateLegendValues())
  }, [updateLegendValues])

  // Rebuild key: add/remove/input changes only. instanceId is now stable across
  // input edits, so the inputs are folded into the key to trigger a recompute.
  // Style and hidden are applied in the lightweight effect below (no rebuild).
  const overlayKey = overlayIndicators
    .map(i => `${i.instanceId}:${JSON.stringify(i.inputs)}`)
    .join('|')

  useEffect(() => {
    const container = containerRef.current
    if (!container || candles.length === 0) return

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: {
        background: { color: '#131722' },
        textColor: '#787b86',
        attributionLogo: false,
      },
      localization: { priceFormatter: formatINR },
      grid: {
        vertLines: { color: '#1e2328' },
        horzLines: { color: '#1e2328' },
      },
      // Fixed price-scale width so the plot area lines up exactly with the
      // sub-panes (whose value labels are narrower), keeping the time axes aligned.
      rightPriceScale: { borderColor: '#2a2e39', minimumWidth: PRICE_SCALE_WIDTH },
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

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })
    candleSeriesRef.current = candleSeries
    candleSeries.setData(
      candles.map(c => ({
        time: toChartTime(c.timestamp),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    )

    // Volume histogram in the bottom 20% of the pane.
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceScaleId: 'volume',
      priceFormat: { type: 'volume' },
      lastValueVisible: false,
      priceLineVisible: false,
      visible: volumeVisible,
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
    volumeSeries.setData(
      candles.map(c => ({
        time: toChartTime(c.timestamp),
        value: c.volume,
        color: c.close >= c.open ? '#26a69a80' : '#ef535080',
      }))
    )
    volumeSeriesRef.current = volumeSeries

    // Visible range
    const lastCandle = candles[candles.length - 1]
    const isIntraday = lastCandle.timestamp.length > 10 && !lastCandle.timestamp.includes('T00:00:00')
    const lastDate = new Date(lastCandle.timestamp)
    const fromDate = computeFromDate(lastDate, visibleRange)
    try {
      if (visibleRange === 'All') {
        chart.timeScale().fitContent()
      } else if (isIntraday) {
        chart.timeScale().setVisibleRange({
          from: (Math.floor(fromDate.getTime() / 1000) + IST_OFFSET_SECONDS) as UTCTimestamp,
          to: (Math.floor(lastDate.getTime() / 1000) + IST_OFFSET_SECONDS) as UTCTimestamp,
        })
      } else {
        chart.timeScale().setVisibleRange({
          from: fromDate.toISOString().slice(0, 10) as Time,
          to: lastCandle.timestamp.slice(0, 10) as Time,
        })
      }
    } catch {
      chart.timeScale().fitContent()
    }

    // Overlay indicators
    handlesRef.current = new Map()
    for (const ind of overlayIndicators) {
      handlesRef.current.set(ind.instanceId, addOverlaySeries(chart, ind, candles))
    }

    // Scroll-left detection
    scrollLeftFired.current = false
    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (range && range.from < 10 && !scrollLeftFired.current) {
        scrollLeftFired.current = true
        onScrollLeft?.()
      }
    })

    chart.subscribeCrosshairMove(param => updateLegendValues(param))
    updateLegendValues()

    onChartReady?.(chart)

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
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      handlesRef.current = new Map()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [candles, overlayKey, height, visibleRange])

  // Style / visibility pass — no chart rebuild.
  useEffect(() => {
    if (!chartRef.current) return
    for (const ind of overlayIndicators) {
      const handles = handlesRef.current.get(ind.instanceId)
      if (!handles) continue
      for (const h of handles) {
        h.series.applyOptions({
          visible: !ind.hidden,
          color: (ind.style[h.colorKey] as string) ?? '#888888',
          lineWidth: ((ind.style.width as 1 | 2 | 3 | 4) ?? 2),
        })
      }
    }
    volumeSeriesRef.current?.applyOptions({ visible: volumeVisible })
    updateLegendValues()
  }, [overlayIndicators, volumeVisible, updateLegendValues])

  const rows: LegendRowData[] = overlayIndicators.map(ind => {
    const def = INDICATOR_MAP[ind.indicatorId]
    return {
      instanceId: ind.instanceId,
      title: legendTitle(def, ind.inputs),
      lines: overlayLineSpec(ind.indicatorId).map(s => ({
        lineKey: s.lineKey,
        color: (ind.style[s.colorKey] as string) ?? '#888888',
      })),
      hidden: ind.hidden,
    }
  })

  return (
    <div className="relative w-full" style={{ height, backgroundColor: '#131722' }}>
      <ChartLegend
        rows={rows}
        volumeVisible={volumeVisible}
        registerValueEl={registerValueEl}
        onToggleHidden={onToggleHidden}
        onOpenSettings={onOpenSettings}
        onRemove={onRemoveIndicator}
        onToggleVolume={onToggleVolume}
      />
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

export default ChartCore
