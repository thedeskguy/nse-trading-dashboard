'use client'
import { useState, useRef, useEffect } from 'react'
import { Plus, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'

export const INTERVALS = ['1m', '5m', '15m', '30m', '1H', '1D', '1W', '1M'] as const
export type Interval = typeof INTERVALS[number]

export const RANGES = ['1D', '5D', '1M', '3M', '6M', '1Y', '5Y', 'All'] as const
export type Range = typeof RANGES[number]

const INTERVAL_GROUPS: Array<{ label: string; intervals: Interval[] }> = [
  { label: 'MINUTES', intervals: ['1m', '5m', '15m', '30m'] },
  { label: 'HOURS',   intervals: ['1H'] },
  { label: 'DAYS',    intervals: ['1D', '1W', '1M'] },
]

// apiInterval = yfinance interval param; period = max valid period for that interval
// yfinance restricts ALL intraday data to last ~60 days, so max safe period is 1mo.
export const INTERVAL_CONFIG: Record<Interval, { apiInterval: string; period: string }> = {
  '1m':  { apiInterval: '1m',   period: '5d'  },
  '5m':  { apiInterval: '5m',   period: '1mo' },
  '15m': { apiInterval: '15m',  period: '1mo' },
  '30m': { apiInterval: '30m',  period: '1mo' },
  '1H':  { apiInterval: '1h',   period: '1mo' },
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
  const [open, setOpen] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b border-[#2a2e39] bg-[#131722]">
      {/* Ticker info */}
      <div className="flex flex-col min-w-0">
        <span className="text-white font-semibold text-sm leading-tight">{ticker}</span>
        {companyName && <span className="text-[#787b86] text-xs truncate max-w-[120px]">{companyName}</span>}
      </div>

      {/* Interval dropdown */}
      <div className="relative" ref={dropRef}>
        <button
          onClick={() => setOpen(v => !v)}
          className="flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold text-white bg-[#2a2e39] hover:bg-[#363a45] transition-colors"
        >
          {activeInterval}
          <ChevronDown className="h-3 w-3 text-[#787b86]" />
        </button>

        {open && (
          <div className="absolute top-full left-0 mt-1 z-50 bg-[#1e2330] border border-[#2a2e39] rounded shadow-2xl py-1 min-w-[140px]">
            {INTERVAL_GROUPS.map(group => (
              <div key={group.label}>
                <div className="px-3 pt-2 pb-0.5 text-[#787b86] text-[9px] font-bold tracking-widest uppercase">
                  {group.label}
                </div>
                {group.intervals.map(iv => (
                  <button
                    key={iv}
                    onClick={() => { onIntervalChange(iv); setOpen(false) }}
                    className={`w-full text-left px-3 py-1.5 text-xs transition-colors ${
                      activeInterval === iv
                        ? 'text-[#2962ff] bg-[#2a2e39]'
                        : 'text-[#b2b5be] hover:text-white hover:bg-[#2a2e39]'
                    }`}
                  >
                    {iv}
                  </button>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Indicators button */}
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
