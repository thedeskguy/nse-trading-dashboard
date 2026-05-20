'use client'
import { useRef, useCallback } from 'react'
import type { IChartApi } from 'lightweight-charts'

export function useChartSync() {
  const charts = useRef<IChartApi[]>([])

  const registerChart = useCallback((chart: IChartApi) => {
    if (!charts.current.includes(chart)) charts.current.push(chart)

    chart.subscribeCrosshairMove(param => {
      charts.current.forEach(other => {
        if (other === chart) return
        if (param.time !== undefined) {
          const otherSeries = other.getSeries()
          if (otherSeries.length > 0) {
            // Price will be fetched from crosshair data; use 0 as placeholder when unavailable
            const seriesRef = otherSeries[0]
            other.setCrosshairPosition(0, param.time, seriesRef)
          }
        } else {
          other.clearCrosshairPosition()
        }
      })
    })

    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (!range) return
      charts.current.forEach(other => {
        if (other === chart) return
        other.timeScale().setVisibleLogicalRange(range)
      })
    })
  }, [])

  const unregisterChart = useCallback((chart: IChartApi) => {
    charts.current = charts.current.filter(c => c !== chart)
  }, [])

  return { registerChart, unregisterChart }
}
