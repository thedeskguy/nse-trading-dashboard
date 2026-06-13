'use client'
import { Eye, EyeOff, Settings2, X } from 'lucide-react'

export interface LegendRowData {
  instanceId: string
  title: string
  lines: Array<{ lineKey: string; color: string }>
  hidden: boolean
}

interface Props {
  rows: LegendRowData[]
  volumeVisible: boolean
  registerValueEl: (id: string, el: HTMLElement | null) => void
  onToggleHidden: (instanceId: string) => void
  onOpenSettings: (instanceId: string) => void
  onRemove: (instanceId: string) => void
  onToggleVolume: () => void
}

const BTN = 'p-0.5 rounded text-[#787b86] hover:text-white opacity-0 group-hover:opacity-100 transition-opacity'

export function ChartLegend({
  rows, volumeVisible, registerValueEl,
  onToggleHidden, onOpenSettings, onRemove, onToggleVolume,
}: Props) {
  return (
    <div className="absolute top-2 left-2 z-10 flex flex-col gap-0.5 text-[11px] font-mono pointer-events-none max-w-[75%]">
      {/* OHLC row — innerHTML managed imperatively by ChartCore */}
      <div ref={el => registerValueEl('ohlc', el)} className="flex flex-wrap items-center leading-tight" />

      {/* Volume row */}
      <div className={`group flex items-center gap-1.5 pointer-events-auto w-fit ${volumeVisible ? '' : 'opacity-40'}`}>
        <span className="text-[#b2b5be]">Vol</span>
        {volumeVisible && <span ref={el => registerValueEl('volume', el)} className="text-[#26a69a]" />}
        <button aria-label="Toggle volume" title="Toggle volume" className={BTN} onClick={onToggleVolume}>
          {volumeVisible ? <Eye className="h-3 w-3" /> : <EyeOff className="h-3 w-3" />}
        </button>
      </div>

      {/* Indicator rows */}
      {rows.map(row => (
        <div
          key={row.instanceId}
          className={`group flex items-center gap-1.5 pointer-events-auto w-fit ${row.hidden ? 'opacity-40' : ''}`}
        >
          <span className="text-[#b2b5be]">{row.title}</span>
          {!row.hidden && row.lines.map(l => (
            <span
              key={l.lineKey}
              ref={el => registerValueEl(`${row.instanceId}:${l.lineKey}`, el)}
              style={{ color: l.color }}
            />
          ))}
          <span className="flex items-center gap-0.5">
            <button
              aria-label={`${row.hidden ? 'Show' : 'Hide'} ${row.title}`}
              title={row.hidden ? 'Show' : 'Hide'}
              className={BTN}
              onClick={() => onToggleHidden(row.instanceId)}
            >
              {row.hidden ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </button>
            <button aria-label={`Settings ${row.title}`} title="Settings" className={BTN}
                    onClick={() => onOpenSettings(row.instanceId)}>
              <Settings2 className="h-3 w-3" />
            </button>
            <button aria-label={`Remove ${row.title}`} title="Remove" className={BTN}
                    onClick={() => onRemove(row.instanceId)}>
              <X className="h-3 w-3" />
            </button>
          </span>
        </div>
      ))}
    </div>
  )
}
