'use client'

import { useCallback, useEffect, useRef } from 'react'
import {
  createChart,
  LineSeries,
  HistogramSeries,
  BaselineSeries,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
} from 'lightweight-charts'
import { Eye, EyeOff, Settings2, X } from 'lucide-react'
import type { ActiveIndicator, Candle, LinePoint, Source } from './lib/types'
import {
  computeRSI,
  computeMACD,
  computeStochastic,
  computeADX,
  computeATR,
  computeOBV,
  toTime,
} from './lib/computeIndicators'
import { INDICATOR_MAP, legendTitle } from './lib/indicators'
import { formatVolume, PRICE_SCALE_WIDTH } from './lib/format'

interface SubChartPaneProps {
  indicator: ActiveIndicator
  candles: Candle[]
  height: number
  onRemove: (instanceId: string) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onChartReady?: (chart: IChartApi) => void
  onChartRemove?: (chart: IChartApi) => void
}

const COLORS = { bg: '#131722', grid: '#1e2328', text: '#787b86', border: '#2a2e39' }
const BTN = 'p-0.5 rounded text-[#787b86] hover:text-white opacity-0 group-hover:opacity-100 transition-opacity'

interface PaneLine { key: string; series: ISeriesApi<'Line'>; data: LinePoint[] }

// Translucent fill between two horizontal levels (e.g. RSI 30–70 zone).
// A BaselineSeries with constant data at `upper` fills down to `lower`.
function addBand(chart: IChartApi, points: LinePoint[], upper: number, lower: number, color: string) {
  if (points.length === 0) return null
  const band = chart.addSeries(BaselineSeries, {
    baseValue: { type: 'price', price: lower },
    topLineColor: 'transparent',
    bottomLineColor: 'transparent',
    topFillColor1: `${color}1f`,
    topFillColor2: `${color}1f`,
    bottomFillColor1: 'transparent',
    bottomFillColor2: 'transparent',
    priceLineVisible: false,
    lastValueVisible: false,
    crosshairMarkerVisible: false,
    autoscaleInfoProvider: () => null,   // never distort the pane's scale
  })
  band.setData(points.map(p => ({ time: p.time, value: upper })))
  return band
}

export function SubChartPane({
  indicator, candles, height,
  onRemove, onToggleHidden, onOpenSettings,
  onChartReady, onChartRemove,
}: SubChartPaneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const linesRef = useRef<PaneLine[]>([])
  const valueElsRef = useRef<Map<string, HTMLElement>>(new Map())

  const isObv = indicator.indicatorId === 'obv'

  const updateValues = useCallback((param?: MouseEventParams) => {
    for (const line of linesRef.current) {
      const el = valueElsRef.current.get(line.key)
      if (!el) continue
      let v: number | undefined
      if (param?.time) v = (param.seriesData.get(line.series) as { value: number } | undefined)?.value
      if (v === undefined && line.data.length) v = line.data[line.data.length - 1].value
      el.textContent = v !== undefined ? (isObv ? formatVolume(v) : v.toFixed(2)) : '—'
    }
  }, [isObv])

  const registerValueEl = useCallback((key: string, el: HTMLElement | null) => {
    if (el) valueElsRef.current.set(key, el)
    else valueElsRef.current.delete(key)
    queueMicrotask(() => updateValues())
  }, [updateValues])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const { indicatorId, inputs, style } = indicator

    const chart = createChart(container, {
      width: container.clientWidth,
      height,
      layout: { background: { color: COLORS.bg }, textColor: COLORS.text, attributionLogo: false },
      ...(isObv ? { localization: { priceFormatter: formatVolume } } : {}),
      grid: {
        vertLines: { color: COLORS.grid },
        horzLines: { color: COLORS.grid },
      },
      rightPriceScale: { borderColor: COLORS.border, minimumWidth: PRICE_SCALE_WIDTH },
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

    // Whitespace spacer spanning every candle so this pane's bar indices line up
    // 1:1 with the main chart. Without it the pane's first bar is the indicator's
    // warmup bar, and logical-range sync shifts the dates (RSI months drifting
    // off the price axis). Added before registering for sync so the time scale
    // is already full-range when the first synced range arrives.
    const spacer = chart.addSeries(LineSeries, {
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
      autoscaleInfoProvider: () => null,
    })
    spacer.setData(candles.map(c => ({ time: toTime(c.timestamp) })))

    onChartReady?.(chart)

    const widthOpt = ((style.width as 1 | 2 | 3 | 4) ?? 2)
    const lineOpts = { lineWidth: widthOpt, priceScaleId: 'right' as const }
    const lines: PaneLine[] = []
    const allSeries: Array<ISeriesApi<'Line'> | ISeriesApi<'Histogram'> | ISeriesApi<'Baseline'>> = []

    if (indicatorId === 'rsi') {
      const data = computeRSI(candles, inputs.period as number, inputs.source as Source)
      const color = (style.color as string) ?? '#7b61ff'
      const ob = inputs.overbought as number
      const os = inputs.oversold as number
      const band = addBand(chart, data, ob, os, color)
      if (band) allSeries.push(band)
      const series = chart.addSeries(LineSeries, { color, ...lineOpts })
      series.setData(data)
      // Dashed level lines; no axis labels (the series' own last-value badge is the single label)
      series.createPriceLine({ price: ob, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      series.createPriceLine({ price: os, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'macd') {
      const r = computeMACD(
        candles,
        inputs.fast as number, inputs.slow as number, inputs.signal as number,
        inputs.source as Source,
      )
      const hist = chart.addSeries(HistogramSeries, {
        priceScaleId: 'right', lastValueVisible: false, priceLineVisible: false,
      })
      hist.setData(r.histogram)
      allSeries.push(hist)
      const macdSeries = chart.addSeries(LineSeries, { color: (style.macdColor as string) ?? '#2962ff', ...lineOpts })
      macdSeries.setData(r.macd)
      const signalSeries = chart.addSeries(LineSeries, { color: (style.signalColor as string) ?? '#ff6d00', ...lineOpts })
      signalSeries.setData(r.signal)
      lines.push({ key: 'macd', series: macdSeries, data: r.macd })
      lines.push({ key: 'signal', series: signalSeries, data: r.signal })
      allSeries.push(macdSeries, signalSeries)

    } else if (indicatorId === 'stochastic') {
      const r = computeStochastic(candles, inputs.k as number, inputs.d as number)
      const kColor = (style.kColor as string) ?? '#2962ff'
      const ob = inputs.overbought as number
      const os = inputs.oversold as number
      const band = addBand(chart, r.k, ob, os, kColor)
      if (band) allSeries.push(band)
      const kSeries = chart.addSeries(LineSeries, { color: kColor, ...lineOpts })
      kSeries.setData(r.k)
      kSeries.createPriceLine({ price: ob, color: kColor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      kSeries.createPriceLine({ price: os, color: kColor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false })
      const dSeries = chart.addSeries(LineSeries, { color: (style.dColor as string) ?? '#ff6d00', ...lineOpts })
      dSeries.setData(r.d)
      lines.push({ key: 'k', series: kSeries, data: r.k })
      lines.push({ key: 'd', series: dSeries, data: r.d })
      allSeries.push(kSeries, dSeries)

    } else if (indicatorId === 'adx') {
      const data = computeADX(candles, inputs.period as number)
      const color = (style.color as string) ?? '#f7c948'
      const series = chart.addSeries(LineSeries, { color, ...lineOpts })
      series.setData(data)
      series.createPriceLine({
        price: inputs.threshold as number, color,
        lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false,
      })
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'atr') {
      const data = computeATR(candles, inputs.period as number)
      const series = chart.addSeries(LineSeries, { color: (style.color as string) ?? '#e040fb', ...lineOpts })
      series.setData(data)
      lines.push({ key: 'line', series, data })
      allSeries.push(series)

    } else if (indicatorId === 'obv') {
      const data = computeOBV(candles)
      const series = chart.addSeries(LineSeries, { color: (style.color as string) ?? '#00bcd4', ...lineOpts })
      series.setData(data)
      lines.push({ key: 'line', series, data })
      allSeries.push(series)
    }

    chart.timeScale().fitContent()
    for (const s of allSeries) s.applyOptions({ visible: !indicator.hidden })
    linesRef.current = lines
    chart.subscribeCrosshairMove(p => updateValues(p))
    updateValues()

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
      linesRef.current = []
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [indicator, candles, height])

  const def = INDICATOR_MAP[indicator.indicatorId]
  const title = legendTitle(def, indicator.inputs)

  const headerLines = (() => {
    switch (indicator.indicatorId) {
      case 'macd':
        return [
          { key: 'macd', color: (indicator.style.macdColor as string) ?? '#2962ff' },
          { key: 'signal', color: (indicator.style.signalColor as string) ?? '#ff6d00' },
        ]
      case 'stochastic':
        return [
          { key: 'k', color: (indicator.style.kColor as string) ?? '#2962ff' },
          { key: 'd', color: (indicator.style.dColor as string) ?? '#ff6d00' },
        ]
      default:
        return [{ key: 'line', color: (indicator.style.color as string) ?? '#888888' }]
    }
  })()

  return (
    <div className="relative w-full" style={{ height, backgroundColor: COLORS.bg, borderTop: `1px solid ${COLORS.border}` }}>
      <div className={`group absolute top-1 left-2 z-10 flex items-center gap-1.5 select-none text-[11px] font-mono ${indicator.hidden ? 'opacity-40' : ''}`}>
        <span style={{ color: COLORS.text }}>{title}</span>
        {!indicator.hidden && headerLines.map(l => (
          <span key={l.key} ref={el => registerValueEl(l.key, el)} style={{ color: l.color }} />
        ))}
        <button
          aria-label={`${indicator.hidden ? 'Show' : 'Hide'} ${title}`}
          title={indicator.hidden ? 'Show' : 'Hide'}
          className={BTN}
          onClick={() => onToggleHidden(indicator.instanceId)}
        >
          {indicator.hidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
        </button>
        <button aria-label={`Settings ${title}`} title="Settings" className={BTN}
                onClick={() => onOpenSettings(indicator.instanceId)}>
          <Settings2 className="h-3 w-3" />
        </button>
        <button aria-label={`Remove ${title}`} title="Remove" className={BTN}
                onClick={() => onRemove(indicator.instanceId)}>
          <X className="h-3 w-3" />
        </button>
      </div>
      <div ref={containerRef} className="w-full h-full" />
    </div>
  )
}

export default SubChartPane
