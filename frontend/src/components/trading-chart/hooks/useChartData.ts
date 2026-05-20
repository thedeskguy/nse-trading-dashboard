'use client'
import { useState, useCallback } from 'react'
import { useOHLCV } from '@/lib/api/market'
import type { Candle } from '../lib/types'

interface UseChartDataReturn {
  candles: Candle[]
  isLoading: boolean
  hasMoreHistory: boolean
  loadFullHistory: () => void
}

export function useChartData(ticker: string, interval: string): UseChartDataReturn {
  const [loadMax, setLoadMax] = useState(false)
  const period = loadMax ? 'max' : '2y'
  const { data, isLoading } = useOHLCV(ticker, interval, period, false)
  const loadFullHistory = useCallback(() => {
    if (!loadMax) setLoadMax(true)
  }, [loadMax])
  return {
    candles: (data?.candles ?? []) as Candle[],
    isLoading,
    hasMoreHistory: !loadMax,
    loadFullHistory,
  }
}
