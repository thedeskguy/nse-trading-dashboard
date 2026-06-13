import { renderHook, act } from '@testing-library/react'
import { useIndicators, STORAGE_KEY } from '@/components/trading-chart/hooks/useIndicators'

beforeEach(() => localStorage.clear())

describe('useIndicators', () => {
  it('adds an indicator with schema defaults', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    const inst = result.current.activeIndicators[0]
    expect(inst.instanceId).toMatch(/^ema#/)
    expect(inst.indicatorId).toBe('ema')
    expect(inst.inputs).toEqual({ period: 20, source: 'close' })
    expect(inst.style).toEqual({ color: '#2196f3', width: 2 })
    expect(inst.hidden).toBe(false)
  })

  it('stacks multiple instances of the same overlay indicator', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('sma'))
    act(() => result.current.addIndicator('sma'))
    act(() => result.current.addIndicator('sma'))
    expect(result.current.activeIndicators).toHaveLength(3)
    const ids = result.current.activeIndicators.map(a => a.instanceId)
    expect(new Set(ids).size).toBe(3) // all unique
  })

  it('updateInputs mutates the instance in place, keeping its instanceId', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    const id = result.current.activeIndicators[0].instanceId
    act(() => result.current.updateInputs(id, { period: 50, source: 'hl2' }))
    expect(result.current.activeIndicators[0].instanceId).toBe(id)
    expect(result.current.activeIndicators[0].inputs).toEqual({ period: 50, source: 'hl2' })
  })

  it('two instances edited to the same inputs stay distinct', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))
    act(() => result.current.addIndicator('ema'))
    const [a, b] = result.current.activeIndicators
    act(() => result.current.updateInputs(a.instanceId, { period: 50, source: 'close' }))
    act(() => result.current.updateInputs(b.instanceId, { period: 50, source: 'close' }))
    expect(result.current.activeIndicators).toHaveLength(2)
    expect(result.current.activeIndicators[0].instanceId).not.toBe(result.current.activeIndicators[1].instanceId)
  })

  it('toggleHidden flips the flag', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('vwap'))
    act(() => result.current.toggleHidden(result.current.activeIndicators[0].instanceId))
    expect(result.current.activeIndicators[0].hidden).toBe(true)
  })

  it('updateStyle merges partial style without wiping other keys', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('ema'))   // style { color:'#2196f3', width:2 }
    const id = result.current.activeIndicators[0].instanceId
    act(() => result.current.updateStyle(id, { color: '#00ff00' }))
    expect(result.current.activeIndicators[0].style).toEqual({ color: '#00ff00', width: 2 })
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

  it('persists and hydrates multiple instances of one indicator', () => {
    const first = renderHook(() => useIndicators())
    act(() => first.result.current.addIndicator('sma'))
    act(() => first.result.current.addIndicator('sma'))
    first.unmount()
    const second = renderHook(() => useIndicators())
    expect(second.result.current.activeIndicators).toHaveLength(2)
    expect(second.result.current.activeIndicators.every(a => a.indicatorId === 'sma')).toBe(true)
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

  it('caps panels when adding interactively', () => {
    const { result } = renderHook(() => useIndicators())
    act(() => result.current.addIndicator('rsi'))
    act(() => result.current.addIndicator('macd'))
    act(() => result.current.addIndicator('adx')) // 3rd panel rejected
    expect(result.current.panelIndicators).toHaveLength(2)
  })
})
