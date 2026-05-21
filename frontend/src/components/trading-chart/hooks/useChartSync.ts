'use client'
import { useRef, useCallback } from 'react'
import type { IChartApi } from 'lightweight-charts'

export function useChartSync() {
  const charts = useRef<IChartApi[]>([])
  const isSyncing = useRef(false)

  const registerChart = useCallback((chart: IChartApi) => {
    if (charts.current.includes(chart)) return
    charts.current.push(chart)

    chart.timeScale().subscribeVisibleLogicalRangeChange(range => {
      if (isSyncing.current || !range) return
      isSyncing.current = true
      charts.current = charts.current.filter(c => {
        if (c === chart) return true
        try {
          c.timeScale().setVisibleLogicalRange(range)
          return true
        } catch {
          return false // disposed — drop it
        }
      })
      isSyncing.current = false
    })
  }, [])

  const unregisterChart = useCallback((chart: IChartApi) => {
    charts.current = charts.current.filter(c => c !== chart)
  }, [])

  return { registerChart, unregisterChart }
}
