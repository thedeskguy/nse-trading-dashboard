'use client'
import { RANGES, type Range } from './ChartToolbar'

interface Props {
  activeRange: Range
  onRangeChange: (r: Range) => void
}

export function RangeSelector({ activeRange, onRangeChange }: Props) {
  return (
    <div className="flex items-center gap-0.5 px-2 py-1.5 border-t border-[#2a2e39] bg-[#131722]">
      {RANGES.map(r => (
        <button
          key={r}
          onClick={() => onRangeChange(r)}
          className={`px-2 py-0.5 rounded text-[11px] font-medium transition-colors ${
            activeRange === r
              ? 'bg-[#2962ff] text-white'
              : 'text-[#787b86] hover:text-white hover:bg-[#2a2e39]'
          }`}
        >
          {r}
        </button>
      ))}
      {/* License-compliant attribution — per-pane watermark logos are disabled */}
      <a
        href="https://www.tradingview.com/lightweight-charts/"
        target="_blank"
        rel="noopener noreferrer"
        className="ml-auto text-[10px] text-[#787b86] hover:text-white transition-colors pr-1"
      >
        Powered by TradingView Lightweight Charts
      </a>
    </div>
  )
}
