'use client'
import { useState, useCallback, useMemo } from 'react'
import { INDICATOR_MAP, MAX_PANEL_INDICATORS, DEFAULT_ACTIVE } from '../lib/indicators'
import type { ActiveIndicator, IndicatorId } from '../lib/types'

interface UseIndicatorsReturn {
  activeIndicators: ActiveIndicator[]
  addIndicator: (id: IndicatorId, params?: Record<string, number>) => void
  removeIndicator: (instanceId: string) => void
  updateParams: (instanceId: string, params: Record<string, number>) => void
  overlayIndicators: ActiveIndicator[]
  panelIndicators: ActiveIndicator[]
  canAddPanel: boolean
}

function makeInstanceId(id: IndicatorId, params: Record<string, number>): string {
  const suffix = Object.values(params).join('-')
  return suffix ? `${id}-${suffix}` : id
}

export function useIndicators(): UseIndicatorsReturn {
  const [active, setActive] = useState<ActiveIndicator[]>(() =>
    DEFAULT_ACTIVE.map(({ id, params }) => ({ instanceId: makeInstanceId(id, params), indicatorId: id, params }))
  )

  const addIndicator = useCallback((id: IndicatorId, params?: Record<string, number>) => {
    const def = INDICATOR_MAP[id]
    const p = params ?? def.defaultParams
    const instanceId = makeInstanceId(id, p)
    setActive(prev => {
      if (prev.find(a => a.instanceId === instanceId)) return prev
      const panelCount = prev.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel').length
      if (def.type === 'panel' && panelCount >= MAX_PANEL_INDICATORS) return prev
      return [...prev, { instanceId, indicatorId: id, params: p }]
    })
  }, [])

  const removeIndicator = useCallback((instanceId: string) => {
    setActive(prev => prev.filter(a => a.instanceId !== instanceId))
  }, [])

  const updateParams = useCallback((instanceId: string, params: Record<string, number>) => {
    setActive(prev => prev.map(a =>
      a.instanceId === instanceId ? { ...a, params, instanceId: makeInstanceId(a.indicatorId, params) } : a
    ))
  }, [])

  const overlayIndicators = useMemo(() => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'overlay'), [active])
  const panelIndicators   = useMemo(() => active.filter(a => INDICATOR_MAP[a.indicatorId].type === 'panel'), [active])
  const canAddPanel       = panelIndicators.length < MAX_PANEL_INDICATORS

  return { activeIndicators: active, addIndicator, removeIndicator, updateParams, overlayIndicators, panelIndicators, canAddPanel }
}
