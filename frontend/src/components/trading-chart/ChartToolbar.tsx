'use client'
import { Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'

export const INTERVALS = ['1m', '5m', '15m', '30m', '1H', '4H', '1D', '1W', '1M'] as const
export type Interval = typeof INTERVALS[number]

// Map display interval → { apiInterval, period }
export const INTERVAL_CONFIG: Record<Interval, { apiInterval: string; period: string }> = {
  '1m':  { apiInterval: '1m',   period: '7d'  },
  '5m':  { apiInterval: '5m',   period: '60d' },
  '15m': { apiInterval: '15m',  period: '60d' },
  '30m': { apiInterval: '30m',  period: '60d' },
  '1H':  { apiInterval: '60m',  period: '2y'  },
  '4H':  { apiInterval: '90m',  period: '2y'  },
  '1D':  { apiInterval: '1d',   period: 'max' },
  '1W':  { apiInterval: '1wk',  period: 'max' },
  '1M':  { apiInterval: '1mo',  period: 'max' },
}

interface Props {
  ticker: string
  companyName?: string
  activeInterval: Interval
  onIntervalChange: (iv: Interval) => void
  onIndicatorsClick: () => void
}

export function ChartToolbar({ ticker, companyName, activeInterval, onIntervalChange, onIndicatorsClick }: Props) {
  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b border-[#2a2e39] bg-[#131722]">
      <div className="flex flex-col min-w-0">
        <span className="text-white font-semibold text-sm leading-tight">{ticker}</span>
        {companyName && <span className="text-[#787b86] text-xs truncate">{companyName}</span>}
      </div>
      <div className="flex items-center gap-1 ml-2 flex-wrap">
        {INTERVALS.map(iv => (
          <button
            key={iv}
            onClick={() => onIntervalChange(iv)}
            className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
              activeInterval === iv
                ? 'bg-[#2962ff] text-white'
                : 'text-[#787b86] hover:text-white hover:bg-[#2a2e39]'
            }`}
          >
            {iv}
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
