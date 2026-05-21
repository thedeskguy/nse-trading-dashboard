'use client'

import { useState } from 'react'
import { ChartToolbar, type Timeframe } from './ChartToolbar'
import { ChartCore } from './ChartCore'
import { SubChartPane } from './SubChartPane'
import { IndicatorSearch } from './IndicatorSearch'
import { useChartData } from './hooks/useChartData'
import { useIndicators } from './hooks/useIndicators'
import { useChartSync } from './hooks/useChartSync'
import { useCompanyInfo } from '@/lib/api/market'

const TIMEFRAME_TO_INTERVAL: Record<Timeframe, string> = {
  '1D': '1d',
  '5D': '1d',
  '1M': '1d',
  '3M': '1d',
  '6M': '1d',
  '1Y': '1d',
  '2Y': '1wk',
  'All': '1wk',
}

interface TradingChartProps {
  ticker: string
}

export function TradingChart({ ticker }: TradingChartProps) {
  const [activeTimeframe, setActiveTimeframe] = useState<Timeframe>('6M')
  const [indicatorSearchOpen, setIndicatorSearchOpen] = useState(false)

  const interval = TIMEFRAME_TO_INTERVAL[activeTimeframe]

  const { candles, isLoading, loadFullHistory } = useChartData(ticker, interval)
  const {
    activeIndicators,
    addIndicator,
    removeIndicator,
    overlayIndicators,
    panelIndicators,
    canAddPanel,
  } = useIndicators()
  const { registerChart, unregisterChart } = useChartSync()

  const { data: companyInfo } = useCompanyInfo(ticker)

  return (
    <div className="flex flex-col bg-[#131722] rounded-lg overflow-hidden border border-[#2a2e39]">
      <ChartToolbar
        ticker={ticker}
        companyName={companyInfo?.name}
        activeTimeframe={activeTimeframe}
        onTimeframeChange={setActiveTimeframe}
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
            onScrollLeft={loadFullHistory}
            onChartReady={registerChart}
            onChartRemove={unregisterChart}
          />

          {panelIndicators.map(ind => (
            <SubChartPane
              key={ind.instanceId}
              indicator={ind}
              candles={candles}
              height={120}
              onRemove={removeIndicator}
              onChartReady={registerChart}
              onChartRemove={unregisterChart}
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
        canAddPanel={canAddPanel}
      />
    </div>
  )
}

export default TradingChart
