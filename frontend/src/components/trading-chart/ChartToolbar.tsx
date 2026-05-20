'use client'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

const TIMEFRAMES = ['1D', '5D', '1M', '3M', '6M', '1Y', '2Y', 'All'] as const
export type Timeframe = typeof TIMEFRAMES[number]

export const TIMEFRAME_TO_PERIOD: Record<Timeframe, string> = {
  '1D': '1d', '5D': '5d', '1M': '1mo', '3M': '3mo',
  '6M': '6mo', '1Y': '1y', '2Y': '2y', 'All': 'max',
}

interface Props {
  ticker: string
  companyName?: string
  activeTimeframe: Timeframe
  onTimeframeChange: (tf: Timeframe) => void
  onIndicatorsClick: () => void
}

export function ChartToolbar({ ticker, companyName, activeTimeframe, onTimeframeChange, onIndicatorsClick }: Props) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b border-[#2a2e39] bg-[#131722]">
      <div className="flex flex-col min-w-0">
        <span className="text-white font-semibold text-sm leading-tight">{ticker}</span>
        {companyName && <span className="text-[#787b86] text-xs truncate">{companyName}</span>}
      </div>
      <div className="flex items-center gap-1 ml-2">
        {TIMEFRAMES.map(tf => (
          <button
            key={tf}
            onClick={() => onTimeframeChange(tf)}
            className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
              activeTimeframe === tf
                ? 'bg-[#2962ff] text-white'
                : 'text-[#787b86] hover:text-white hover:bg-[#2a2e39]'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>
      <div className="ml-auto">
        <Button
          size="sm"
          variant="outline"
          onClick={onIndicatorsClick}
          className="border-[#2a2e39] bg-[#1e2330] text-[#b2b5be] hover:text-white hover:bg-[#2a2e39] text-xs h-7 gap-1"
        >
          <Plus className="h-3 w-3" /> Indicators
        </Button>
      </div>
    </div>
  )
}
