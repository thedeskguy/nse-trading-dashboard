'use client'
import { useState, useCallback, useEffect, useMemo } from 'react'
import {
  INDICATOR_MAP, MAX_PANEL_INDICATORS,
  inputDefaults, styleDefaults, sanitizeStored,
} from '../lib/indicators'
import type { ActiveIndicator, IndicatorId, InputValue } from '../lib/types'

export const STORAGE_KEY = 'tradedash.chart.v2'

// Each active indicator gets a unique id independent of its inputs, so a user
// can stack several of the same indicator (e.g. SMA 20 + SMA 50 + SMA 200).
// The id only needs to be stable for the lifetime of the page; it is not
// persisted — instances are re-keyed on hydrate.
let instanceCounter = 0
function nextInstanceId(id: IndicatorId): string {
  instanceCounter += 1
  return `${id}#${instanceCounter}`
}

interface PersistedV2 {
  version: 2
  volumeVisible: boolean
  indicators: Array<{
    indicatorId: string
    inputs: Record<string, unknown>
    style: Record<string, unknown>
    hidden?: boolean
  }>
}

function loadPersisted(): { volumeVisible: boolean; indicators: ActiveIndicator[] } | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as PersistedV2
    if (parsed?.version !== 2 || !Array.isArray(parsed.indicators)) return null
    const indicators: ActiveIndicator[] = []
    let panelCount = 0
    for (const item of parsed.indicators) {
      const def = INDICATOR_MAP[item.indicatorId as IndicatorId]
      if (!def) continue
      if (def.type === 'panel') {
        if (panelCount >= MAX_PANEL_INDICATORS) continue
        panelCount++
      }
      const { inputs, style } = sanitizeStored(def, item.inputs ?? {}, item.style ?? {})
      indicators.push({ instanceId: nextInstanceId(def.id), indicatorId: def.id, inputs, style, hidden: item.hidden === true })
    }
    return { volumeVisible: parsed.volumeVisible !== false, indicators }
  } catch {
    return null  // corrupt storage — fall back to defaults
  }
}

export function useIndicators() {
  const [active, setActive] = useState<ActiveIndicator[]>([])
  const [volumeVisible, setVolumeVisible] = useState(true)
  const [hydrated, setHydrated] = useState(false)

  // Hydrate from localStorage AFTER mount, not during render: reading storage
  // in render would make the client's first paint differ from the server's
  // (empty) markup and trip a hydration mismatch. Synchronous setState here is
  // the intended pattern for that, so the set-state-in-effect rule is disabled.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    const loaded = loadPersisted()
    if (loaded) {
      setActive(loaded.indicators)
      setVolumeVisible(loaded.volumeVisible)
    }
    setHydrated(true)
  }, [])
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!hydrated || typeof window === 'undefined') return
    const payload: PersistedV2 = {
      version: 2,
      volumeVisible,
      indicators: active.map(a => ({
        indicatorId: a.indicatorId, inputs: a.inputs, style: a.style, hidden: a.hidden,
      })),
    }
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch { /* storage full or blocked — non-fatal */ }
  }, [active, volumeVisible, hydrated])

  // Always appends a new instance (overlays unlimited; panels capped). This is
  // what lets the user stack multiple SMAs/EMAs — each is its own instance.
  const addIndicator = useCallback((id: IndicatorId) => {
    const def = INDICATOR_MAP[id]
    setActive(prev => {
      const panelCount = prev.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel').length
      if (def.type === 'panel' && panelCount >= MAX_PANEL_INDICATORS) return prev
      return [...prev, {
        instanceId: nextInstanceId(id),
        indicatorId: id,
        inputs: inputDefaults(def),
        style: styleDefaults(def),
        hidden: false,
      }]
    })
  }, [])

  const removeIndicator = useCallback((instanceId: string) => {
    setActive(prev => prev.filter(a => a.instanceId !== instanceId))
  }, [])

  // instanceId is stable across input edits now, so editing SMA 20 → SMA 50
  // mutates that one instance in place; it never collides with another.
  const updateInputs = useCallback((instanceId: string, inputs: Record<string, InputValue>) => {
    setActive(prev => prev.map(a => (a.instanceId === instanceId ? { ...a, inputs } : a)))
  }, [])

  const updateStyle = useCallback((instanceId: string, style: Record<string, string | number>) => {
    setActive(prev => prev.map(a => (a.instanceId === instanceId ? { ...a, style: { ...a.style, ...style } } : a)))
  }, [])

  const toggleHidden = useCallback((instanceId: string) => {
    setActive(prev => prev.map(a => (a.instanceId === instanceId ? { ...a, hidden: !a.hidden } : a)))
  }, [])

  const toggleVolume = useCallback(() => setVolumeVisible(v => !v), [])

  const overlayIndicators = useMemo(
    () => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'overlay'), [active])
  const panelIndicators = useMemo(
    () => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel'), [active])
  const canAddPanel = panelIndicators.length < MAX_PANEL_INDICATORS

  return {
    activeIndicators: active,
    addIndicator, removeIndicator,
    updateInputs, updateStyle, toggleHidden,
    overlayIndicators, panelIndicators, canAddPanel,
    volumeVisible, toggleVolume,
  }
}
