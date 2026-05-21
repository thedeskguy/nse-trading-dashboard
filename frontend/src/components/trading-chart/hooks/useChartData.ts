'use client'
import { useOHLCV } from '@/lib/api/market'
import type { Candle } from '../lib/types'

interface UseChartDataReturn {
  candles: Candle[]
  isLoading: boolean
}

export function useChartData(ticker: string, interval: string, period: string): UseChartDataReturn {
  const { data, isLoading } = useOHLCV(ticker, interval, period, false)
  return {
    candles: (data?.candles ?? []) as Candle[],
    isLoading,
  }
}
