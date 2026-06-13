'use client'

import { useState } from 'react'
import { ChartToolbar, type Interval, type Range, INTERVAL_CONFIG } from './ChartToolbar'
import { ChartCore } from './ChartCore'
import { SubChartPane } from './SubChartPane'
import { IndicatorSearch } from './IndicatorSearch'
import { RangeSelector } from './RangeSelector'
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
  const [activeRange, setActiveRange] = useState<Range>('6M')
  const [indicatorSearchOpen, setIndicatorSearchOpen] = useState(false)
  const [settingsTarget, setSettingsTarget] = useState<string | null>(null)

  const { apiInterval, period } = INTERVAL_CONFIG[activeInterval]

  const { candles, isLoading } = useChartData(ticker, apiInterval, period)
  const {
    activeIndicators,
    addIndicator,
    removeIndicator,
    updateInputs,
    updateStyle,
    toggleHidden,
    overlayIndicators,
    panelIndicators,
    canAddPanel,
    volumeVisible,
    toggleVolume,
  } = useIndicators()
  const { registerChart, unregisterChart } = useChartSync()

  const { data: companyInfo } = useCompanyInfo(ticker)

  const handleChartReady = (chart: IChartApi) => registerChart(chart)
  const handleChartRemove = (chart: IChartApi) => unregisterChart(chart)

  // When interval changes, reset range to a sensible default
  function handleIntervalChange(iv: Interval) {
    setActiveInterval(iv)
    if (iv === '1m') setActiveRange('1D')
    else if (['5m', '15m', '30m'].includes(iv)) setActiveRange('5D')
    else if (iv === '1H') setActiveRange('1M')
    else setActiveRange('6M')
  }

  // Gear in any legend → open the drawer with that instance's settings expanded
  function openSettingsFor(instanceId: string) {
    setSettingsTarget(instanceId)
    setIndicatorSearchOpen(true)
  }

  function closeSearch() {
    setIndicatorSearchOpen(false)
    setSettingsTarget(null)
  }

  return (
    <div className="flex flex-col bg-[#131722] rounded-2xl overflow-hidden border border-border">
      <ChartToolbar
        ticker={ticker}
        companyName={companyInfo?.name}
        activeInterval={activeInterval}
        onIntervalChange={handleIntervalChange}
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
            volumeVisible={volumeVisible}
            visibleRange={activeRange}
            onChartReady={handleChartReady}
            onChartRemove={handleChartRemove}
            onToggleHidden={toggleHidden}
            onOpenSettings={openSettingsFor}
            onRemoveIndicator={removeIndicator}
            onToggleVolume={toggleVolume}
          />

          {panelIndicators.map(ind => (
            <SubChartPane
              key={ind.instanceId}
              indicator={ind}
              candles={candles}
              height={120}
              onRemove={removeIndicator}
              onToggleHidden={toggleHidden}
              onOpenSettings={openSettingsFor}
              onChartReady={handleChartReady}
              onChartRemove={handleChartRemove}
            />
          ))}

          <RangeSelector activeRange={activeRange} onRangeChange={setActiveRange} />
        </>
      )}

      <IndicatorSearch
        isOpen={indicatorSearchOpen}
        onClose={closeSearch}
        activeIndicators={activeIndicators}
        onAdd={addIndicator}
        onRemove={removeIndicator}
        onUpdateInputs={updateInputs}
        onUpdateStyle={updateStyle}
        canAddPanel={canAddPanel}
        initialOpenInstanceId={settingsTarget}
      />
    </div>
  )
}

export default TradingChart
