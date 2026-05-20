'use client'
import { useState, useMemo } from 'react'
import { X, Check, Search } from 'lucide-react'
import { INDICATORS, INDICATOR_MAP, MAX_PANEL_INDICATORS } from './lib/indicators'
import type { ActiveIndicator, IndicatorId, IndicatorCategory } from './lib/types'

const CATEGORIES: IndicatorCategory[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME']

interface Props {
  isOpen: boolean
  onClose: () => void
  activeIndicators: ActiveIndicator[]
  onAdd: (id: IndicatorId, params?: Record<string, number>) => void
  onRemove: (instanceId: string) => void
  canAddPanel: boolean
}

export function IndicatorSearch({ isOpen, onClose, activeIndicators, onAdd, onRemove, canAddPanel }: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    if (!query) return INDICATORS
    return INDICATORS.filter(d => d.name.toLowerCase().includes(query.toLowerCase()))
  }, [query])

  function handleToggle(id: IndicatorId) {
    const def = INDICATOR_MAP[id]
    const existing = activeIndicators.filter(a => a.indicatorId === id)
    if (existing.length > 0) {
      onRemove(existing[0].instanceId)
      return
    }
    if (def.type === 'panel' && !canAddPanel) {
      alert(`Panel limit reached. Remove an existing panel indicator first (max ${MAX_PANEL_INDICATORS}).`)
      return
    }
    onAdd(id)
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="fixed top-0 right-0 h-full w-72 z-50 bg-[#1e2330] border-l border-[#2a2e39] flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2e39]">
          <span className="text-white font-medium text-sm">Indicators</span>
          <button onClick={onClose} className="text-[#787b86] hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-3 py-2 border-b border-[#2a2e39]">
          <div className="flex items-center gap-2 bg-[#131722] rounded px-2 py-1.5">
            <Search className="h-3.5 w-3.5 text-[#787b86]" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search indicators..."
              className="bg-transparent text-white text-xs outline-none flex-1 placeholder:text-[#787b86]"
              autoFocus
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto py-2">
          {CATEGORIES.map(cat => {
            const items = filtered.filter(d => d.category === cat)
            if (!items.length) return null
            return (
              <div key={cat} className="mb-2">
                <div className="px-4 py-1 text-[#787b86] text-[10px] font-semibold tracking-wider uppercase">{cat}</div>
                {items.map(def => {
                  const isActive = activeIndicators.some(a => a.indicatorId === def.id)
                  return (
                    <button
                      key={def.id}
                      onClick={() => handleToggle(def.id)}
                      className="w-full flex items-center justify-between px-4 py-2 hover:bg-[#2a2e39] transition-colors"
                    >
                      <span className={`text-sm ${isActive ? 'text-white' : 'text-[#b2b5be]'}`}>{def.name}</span>
                      {isActive && <Check className="h-3.5 w-3.5 text-[#2962ff]" />}
                    </button>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}
