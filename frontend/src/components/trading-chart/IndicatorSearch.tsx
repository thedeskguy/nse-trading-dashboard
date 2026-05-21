'use client'
import { useState, useMemo } from 'react'
import { X, Check, Search, Settings2, ChevronUp } from 'lucide-react'
import { INDICATORS, INDICATOR_MAP, MAX_PANEL_INDICATORS } from './lib/indicators'
import type { ActiveIndicator, IndicatorId, IndicatorCategory } from './lib/types'

const CATEGORIES: IndicatorCategory[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME']

interface Props {
  isOpen: boolean
  onClose: () => void
  activeIndicators: ActiveIndicator[]
  onAdd: (id: IndicatorId, params?: Record<string, number>) => void
  onRemove: (instanceId: string) => void
  onUpdateParams: (instanceId: string, params: Record<string, number>) => void
  canAddPanel: boolean
}

export function IndicatorSearch({ isOpen, onClose, activeIndicators, onAdd, onRemove, onUpdateParams, canAddPanel }: Props) {
  const [query, setQuery] = useState('')
  const [openSettings, setOpenSettings] = useState<string | null>(null) // instanceId of expanded settings
  const [draftParams, setDraftParams] = useState<Record<string, string>>({})

  const filtered = useMemo(() => {
    if (!query) return INDICATORS
    return INDICATORS.filter(d => d.name.toLowerCase().includes(query.toLowerCase()))
  }, [query])

  function handleToggle(id: IndicatorId) {
    const def = INDICATOR_MAP[id]
    const existing = activeIndicators.filter(a => a.indicatorId === id)
    if (existing.length > 0) {
      onRemove(existing[0].instanceId)
      setOpenSettings(null)
      return
    }
    if (def.type === 'panel' && !canAddPanel) {
      alert(`Panel limit reached. Remove an existing panel indicator first (max ${MAX_PANEL_INDICATORS}).`)
      return
    }
    onAdd(id)
  }

  function openIndicatorSettings(instanceId: string, params: Record<string, number>) {
    setOpenSettings(prev => prev === instanceId ? null : instanceId)
    setDraftParams(Object.fromEntries(Object.entries(params).map(([k, v]) => [k, String(v)])))
  }

  function applySettings(instanceId: string) {
    const parsed: Record<string, number> = {}
    for (const [k, v] of Object.entries(draftParams)) {
      const n = parseFloat(v)
      if (!isNaN(n) && n > 0) parsed[k] = n
    }
    onUpdateParams(instanceId, parsed)
    setOpenSettings(null)
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
                  const activeInstances = activeIndicators.filter(a => a.indicatorId === def.id)
                  const isActive = activeInstances.length > 0

                  return (
                    <div key={def.id}>
                      <div className="flex items-center px-4 py-2 hover:bg-[#2a2e39] transition-colors">
                        <button
                          onClick={() => handleToggle(def.id)}
                          className="flex items-center gap-2 flex-1 min-w-0"
                        >
                          <span className={`text-sm ${isActive ? 'text-white' : 'text-[#b2b5be]'}`}>{def.name}</span>
                          {isActive && <Check className="h-3.5 w-3.5 text-[#2962ff] shrink-0" />}
                        </button>
                        {isActive && activeInstances.map(inst => (
                          <button
                            key={inst.instanceId}
                            onClick={() => openIndicatorSettings(inst.instanceId, inst.params)}
                            className="ml-1 text-[#787b86] hover:text-white p-0.5"
                            title="Settings"
                          >
                            {openSettings === inst.instanceId
                              ? <ChevronUp className="h-3.5 w-3.5" />
                              : <Settings2 className="h-3.5 w-3.5" />
                            }
                          </button>
                        ))}
                      </div>

                      {/* Inline settings panel */}
                      {isActive && activeInstances.map(inst => openSettings === inst.instanceId && (
                        <div key={inst.instanceId} className="mx-4 mb-2 p-3 bg-[#131722] rounded border border-[#2a2e39]">
                          {Object.entries(def.paramLabels).map(([key, label]) => (
                            <div key={key} className="flex items-center justify-between gap-2 mb-2 last:mb-0">
                              <label className="text-[#787b86] text-xs">{label}</label>
                              <input
                                type="number"
                                value={draftParams[key] ?? ''}
                                onChange={e => setDraftParams(prev => ({ ...prev, [key]: e.target.value }))}
                                className="w-16 bg-[#1e2330] border border-[#2a2e39] text-white text-xs rounded px-2 py-1 outline-none focus:border-[#2962ff]"
                                min="1"
                              />
                            </div>
                          ))}
                          {Object.keys(def.paramLabels).length > 0 && (
                            <button
                              onClick={() => applySettings(inst.instanceId)}
                              className="mt-2 w-full text-xs bg-[#2962ff] hover:bg-[#1e53e5] text-white rounded py-1 transition-colors"
                            >
                              Apply
                            </button>
                          )}
                        </div>
                      ))}
                    </div>
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
