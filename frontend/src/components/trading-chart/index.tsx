'use client'

import { useState } from 'react'
import { ChartToolbar, type Interval, INTERVAL_CONFIG } from './ChartToolbar'
import { ChartCore } from './ChartCore'
import { SubChartPane } from './SubChartPane'
import { IndicatorSearch } from './IndicatorSearch'
import { useChartData } from './hooks/useChartData'
import { useIndicators } from './hooks/useIndicators'
import { useChartSync } from './hooks/useChartSync'
import { useCompanyInfo } from '@/lib/api/market'
import type { IChartApi } from 'lightweight-charts'

interface TradingChartProps {
  ticker: string
}

export function TradingChart({ ticker }: TradingChartProps) {
  const [activeInterval, setActiveInterval] = useState<Interval>('1D')
  const [indicatorSearchOpen, setIndicatorSearchOpen] = useState(false)

  const { apiInterval, period } = INTERVAL_CONFIG[activeInterval]

  const { candles, isLoading } = useChartData(ticker, apiInterval, period)
  const {
    activeIndicators,
    addIndicator,
    removeIndicator,
    updateParams,
    overlayIndicators,
    panelIndicators,
    canAddPanel,
  } = useIndicators()
  const { registerChart, unregisterChart } = useChartSync()

  const { data: companyInfo } = useCompanyInfo(ticker)

  const handleChartReady = (chart: IChartApi) => registerChart(chart)
  const handleChartRemove = (chart: IChartApi) => unregisterChart(chart)

  return (
    <div className="flex flex-col bg-[#131722] rounded-lg overflow-hidden border border-[#2a2e39]">
      <ChartToolbar
        ticker={ticker}
        companyName={companyInfo?.name}
        activeInterval={activeInterval}
        onIntervalChange={setActiveInterval}
        onIndicatorsClick={() => setIndicatorSearchOpen(true)}
      />

      {isLoading ? (
        <div className="flex items-center justify-center h-64 text-[#787b86] text-sm">
          Loading chart data…
        </div>
      ) : (
        <>
          <ChartCore
            candles={candles}
            overlayIndicators={overlayIndicators}
            onChartReady={handleChartReady}
            onChartRemove={handleChartRemove}
          />

          {panelIndicators.map(ind => (
            <SubChartPane
              key={ind.instanceId}
              indicator={ind}
              candles={candles}
              height={120}
              onRemove={removeIndicator}
              onChartReady={handleChartReady}
              onChartRemove={handleChartRemove}
            />
          ))}
        </>
      )}

      <IndicatorSearch
        isOpen={indicatorSearchOpen}
        onClose={() => setIndicatorSearchOpen(false)}
        activeIndicators={activeIndicators}
        onAdd={addIndicator}
        onRemove={removeIndicator}
        onUpdateParams={updateParams}
        canAddPanel={canAddPanel}
      />
    </div>
  )
}

export default TradingChart
