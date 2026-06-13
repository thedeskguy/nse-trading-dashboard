import { renderHook, act } from '@testing-library/react'
import { useIndicators, STORAGE_KEY } from '@/components/trading-chart/hooks/useIndicators'

beforeEach(() => localStorage.clear())

describe('useIndicators', () => {
  it('adds an indicator with schema defaults', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    const inst = result.current.activeIndicators[0]
    expect(inst.instanceId).toBe('ema-20-close')
    expect(inst.inputs).toEqual({ period: 20, source: 'close' })
    expect(inst.style).toEqual({ color: '#2196f3', width: 2 })
    expect(inst.hidden).toBe(false)
  })

  it('updateStyle preserves instanceId; updateInputs regenerates it', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    act(() => result.current.updateStyle('ema-20-close', { color: '#ff0000', width: 3 }))
    expect(result.current.activeIndicators[0].instanceId).toBe('ema-20-close')
    expect(result.current.activeIndicators[0].style.color).toBe('#ff0000')
    act(() => result.current.updateInputs('ema-20-close', { period: 50, source: 'close' }))
    expect(result.current.activeIndicators[0].instanceId).toBe('ema-50-close')
  })

  it('toggleHidden flips the flag', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('vwap'))
    act(() => result.current.toggleHidden(result.current.activeIndicators[0].instanceId))
    expect(result.current.activeIndicators[0].hidden).toBe(true)
  })

  it('persists and hydrates across mounts', () => {
    const first = renderHook(() => useIndicators())
    act(() => first.result.current.addIndicator('rsi'))
    act(() => first.result.current.toggleVolume())
    first.unmount()
    const second = renderHook(() => useIndicators())
    expect(second.result.current.activeIndicators).toHaveLength(1)
    expect(second.result.current.activeIndicators[0].indicatorId).toBe('rsi')
    expect(second.result.current.volumeVisible).toBe(false)
  })

  it('resets silently on corrupt storage', () => {
    localStorage.setItem(STORAGE_KEY, '{not json')
    const { result } = renderHook(() => useIndicators())
    expect(result.current.activeIndicators).toEqual([])
    expect(result.current.volumeVisible).toBe(true)
  })

  it('drops unknown indicators and clamps bad values on hydrate', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 2, volumeVisible: true,
      indicators: [
        { indicatorId: 'banana', inputs: {}, style: {} },
        { indicatorId: 'ema', inputs: { period: 99999, source: 'nope' }, style: { color: 'red', width: 9 } },
      ],
    }))
    const { result } = renderHook(() => useIndicators())
    expect(result.current.activeIndicators).toHaveLength(1)
    const inst = result.current.activeIndicators[0]
    expect(inst.inputs).toEqual({ period: 20, source: 'close' })
    expect(inst.style).toEqual({ color: '#2196f3', width: 2 })
  })

  it('updateInputs collapsing onto an existing instance keeps instanceIds unique', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))                 // ema-20-close
    act(() => result.current.updateInputs('ema-20-close', { period: 50, source: 'close' })) // ema-50-close
    act(() => result.current.addIndicator('ema'))                 // ema-20-close again
    // Now edit the 20 to 50 → would collide with the existing ema-50-close
    act(() => result.current.updateInputs('ema-20-close', { period: 50, source: 'close' }))
    const ids = result.current.activeIndicators.map(a => a.instanceId)
    expect(new Set(ids).size).toBe(ids.length)        // all unique
    expect(ids).toContain('ema-50-close')
    expect(result.current.activeIndicators).toHaveLength(1)
  })

  it('updateStyle merges partial style without wiping other keys', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))   // style { color:'#2196f3', width:2 }
    act(() => result.current.updateStyle('ema-20-close', { color: '#00ff00' }))
    expect(result.current.activeIndicators[0].style).toEqual({ color: '#00ff00', width: 2 })
  })

  it('caps panel indicators at the limit on hydrate', () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      version: 2, volumeVisible: true,
      indicators: [
        { indicatorId: 'rsi', inputs: {}, style: {} },
        { indicatorId: 'macd', inputs: {}, style: {} },
        { indicatorId: 'adx', inputs: {}, style: {} },
      ],
    }))
    const { result } = renderHook(() => useIndicators())
    expect(result.current.panelIndicators).toHaveLength(2)
  })
})
