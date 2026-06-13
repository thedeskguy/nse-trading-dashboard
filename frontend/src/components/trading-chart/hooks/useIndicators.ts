'use client'
import { useState, useCallback, useEffect, useMemo } from 'react'
import {
  INDICATOR_MAP, MAX_PANEL_INDICATORS,
  inputDefaults, styleDefaults, makeInstanceId, sanitizeStored,
} from '../lib/indicators'
import type { ActiveIndicator, IndicatorId, InputValue } from '../lib/types'

export const STORAGE_KEY = 'tradedash.chart.v2'

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
      const instanceId = makeInstanceId(def, inputs)
      if (indicators.some(i => i.instanceId === instanceId)) continue
      indicators.push({ instanceId, indicatorId: def.id, inputs, style, hidden: item.hidden === true })
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

  // Hydrate after mount (avoids SSR hydration mismatch).
  useEffect(() => {
    const loaded = loadPersisted()
    if (loaded) {
      setActive(loaded.indicators)
      setVolumeVisible(loaded.volumeVisible)
    }
    setHydrated(true)
  }, [])

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

  const addIndicator = useCallback((id: IndicatorId) => {
    const def = INDICATOR_MAP[id]
    const inputs = inputDefaults(def)
    const instanceId = makeInstanceId(def, inputs)
    setActive(prev => {
      if (prev.find(a => a.instanceId === instanceId)) return prev
      const panelCount = prev.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel').length
      if (def.type === 'panel' && panelCount >= MAX_PANEL_INDICATORS) return prev
      return [...prev, { instanceId, indicatorId: id, inputs, style: styleDefaults(def), hidden: false }]
    })
  }, [])

  const removeIndicator = useCallback((instanceId: string) => {
    setActive(prev => prev.filter(a => a.instanceId !== instanceId))
  }, [])

  const updateInputs = useCallback((instanceId: string, inputs: Record<string, InputValue>) => {
    setActive(prev => {
      const target = prev.find(a => a.instanceId === instanceId)
      if (!target) return prev
      const newId = makeInstanceId(INDICATOR_MAP[target.indicatorId], inputs)
      // If the new id collides with a DIFFERENT existing instance, the edit wins:
      // drop the colliding one so instanceIds stay unique (React keys depend on it).
      return prev
        .filter(a => a.instanceId === instanceId || a.instanceId !== newId)
        .map(a => (a.instanceId === instanceId ? { ...a, inputs, instanceId: newId } : a))
    })
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
