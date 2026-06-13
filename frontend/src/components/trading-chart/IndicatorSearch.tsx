'use client'
import { useState, useMemo, useEffect } from 'react'
import { X, Check, Search, Settings2, ChevronUp } from 'lucide-react'
import { INDICATORS, INDICATOR_MAP, MAX_PANEL_INDICATORS } from './lib/indicators'
import { SOURCES } from './lib/types'
import type { ActiveIndicator, IndicatorId, IndicatorCategory, InputValue, Source, FieldDef } from './lib/types'

const CATEGORIES: IndicatorCategory[] = ['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME']
const SWATCHES = ['#f7c948', '#2196f3', '#26c6da', '#ff7043', '#e040fb', '#26a69a', '#ef5350', '#ff6d00']

interface Props {
  isOpen: boolean
  onClose: () => void
  activeIndicators: ActiveIndicator[]
  onAdd: (id: IndicatorId) => void
  onRemove: (instanceId: string) => void
  onUpdateInputs: (instanceId: string, inputs: Record<string, InputValue>) => void
  onUpdateStyle: (instanceId: string, style: Record<string, string | number>) => void
  canAddPanel: boolean
  initialOpenInstanceId?: string | null
}

function draftFrom(inst: ActiveIndicator): Record<string, string> {
  return Object.fromEntries(Object.entries(inst.inputs).map(([k, v]) => [k, String(v)]))
}

export function IndicatorSearch({
  isOpen, onClose, activeIndicators, onAdd, onRemove,
  onUpdateInputs, onUpdateStyle, canAddPanel, initialOpenInstanceId,
}: Props) {
  const [query, setQuery] = useState('')
  const [openSettings, setOpenSettings] = useState<string | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})

  // Gear click in a legend routes here: open that instance's settings.
  useEffect(() => {
    if (!isOpen || !initialOpenInstanceId) return
    const inst = activeIndicators.find(a => a.instanceId === initialOpenInstanceId)
    if (inst) {
      setOpenSettings(inst.instanceId)
      setDraft(draftFrom(inst))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, initialOpenInstanceId])

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

  function openIndicatorSettings(inst: ActiveIndicator) {
    setOpenSettings(prev => (prev === inst.instanceId ? null : inst.instanceId))
    setDraft(draftFrom(inst))
  }

  function applyInputs(inst: ActiveIndicator) {
    const def = INDICATOR_MAP[inst.indicatorId]
    const inputs: Record<string, InputValue> = { ...inst.inputs }
    for (const f of def.fields) {
      if (f.kind === 'int' || f.kind === 'float' || f.kind === 'level') {
        const raw = draft[f.key]
        const n = f.kind === 'int' ? parseInt(raw, 10) : parseFloat(raw)
        if (!isNaN(n)) inputs[f.key] = Math.min(f.max, Math.max(f.min, n))
      } else if (f.kind === 'source') {
        const v = draft[f.key]
        if ((SOURCES as readonly string[]).includes(v)) inputs[f.key] = v as Source
      }
    }
    onUpdateInputs(inst.instanceId, inputs)
    setOpenSettings(null)
  }

  function setStyleField(inst: ActiveIndicator, key: string, value: string | number) {
    onUpdateStyle(inst.instanceId, { ...inst.style, [key]: value })
  }

  function renderField(inst: ActiveIndicator, f: FieldDef) {
    if (f.kind === 'color') {
      const current = (inst.style[f.key] as string) ?? f.default
      return (
        <div key={f.key} className="mb-2">
          <div className="flex items-center justify-between gap-2">
            <label className="text-[#787b86] text-xs">{f.label}</label>
            <input
              type="color"
              value={current}
              aria-label={f.label}
              onChange={e => setStyleField(inst, f.key, e.target.value)}
              className="w-8 h-6 bg-transparent border border-[#2a2e39] rounded cursor-pointer"
            />
          </div>
          <div className="flex gap-1 mt-1 justify-end">
            {SWATCHES.map(c => (
              <button
                key={c}
                aria-label={`Set ${f.label} ${c}`}
                onClick={() => setStyleField(inst, f.key, c)}
                className="w-4 h-4 rounded-sm border border-[#2a2e39]"
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      )
    }
    if (f.kind === 'width') {
      const current = (inst.style[f.key] as number) ?? f.default
      return (
        <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
          <label className="text-[#787b86] text-xs">{f.label}</label>
          <div className="flex gap-1">
            {([1, 2, 3] as const).map(w => (
              <button
                key={w}
                onClick={() => setStyleField(inst, f.key, w)}
                className={`px-2 py-0.5 rounded text-xs ${
                  current === w ? 'bg-[#2962ff] text-white' : 'bg-[#1e2330] text-[#787b86] border border-[#2a2e39]'
                }`}
              >
                {w}px
              </button>
            ))}
          </div>
        </div>
      )
    }
    if (f.kind === 'source') {
      return (
        <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
          <label className="text-[#787b86] text-xs">{f.label}</label>
          <select
            value={draft[f.key] ?? 'close'}
            onChange={e => setDraft(prev => ({ ...prev, [f.key]: e.target.value }))}
            className="bg-[#1e2330] border border-[#2a2e39] text-white text-xs rounded px-2 py-1 outline-none focus:border-[#2962ff]"
          >
            {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      )
    }
    // int | float | level
    return (
      <div key={f.key} className="flex items-center justify-between gap-2 mb-2">
        <label className="text-[#787b86] text-xs">{f.label}</label>
        <input
          type="number"
          value={draft[f.key] ?? ''}
          min={f.min}
          max={f.max}
          step={f.kind === 'float' ? (f.step ?? 0.1) : 1}
          onChange={e => setDraft(prev => ({ ...prev, [f.key]: e.target.value }))}
          className="w-16 bg-[#1e2330] border border-[#2a2e39] text-white text-xs rounded px-2 py-1 outline-none focus:border-[#2962ff]"
        />
      </div>
    )
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
                            onClick={() => openIndicatorSettings(inst)}
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

                      {isActive && activeInstances.map(inst => openSettings === inst.instanceId && (
                        <div key={inst.instanceId} className="mx-4 mb-2 p-3 bg-[#131722] rounded border border-[#2a2e39]">
                          {def.fields.map(f => renderField(inst, f))}
                          {def.fields.some(f => f.kind !== 'color' && f.kind !== 'width') && (
                            <button
                              onClick={() => applyInputs(inst)}
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
