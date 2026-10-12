import { useCallback, useEffect, useRef, useState } from 'react'

import { clamp, formatTime } from '../lib/format'
import { useT } from '../lib/useT'
import type { Segment } from '../schema'
import { useStore } from '../store'

type Mode =
  | null
  | { kind: 'scrub' }
  | {
      kind: 'resize'
      id: string
      edge: 'start' | 'end'
      originX: number
      originStart: number
      originEnd: number
    }

interface Times {
  id: string
  start: number
  end: number
}

/** Same limits the store applies, so the live preview can't promise more. */
function clampTimes(start: number, end: number, duration: number): Omit<Times, 'id'> {
  const s = clamp(start, 0, Math.max(0, end - 0.05))
  const e = clamp(end, s + 0.05, duration || end)
  return { start: s, end: e }
}

export default function Timeline() {
  const t = useT()
  const segments = useStore((s) => s.segments)
  const duration = useStore((s) => s.mediaDuration)
  const currentTime = useStore((s) => s.currentTime)
  const selectedId = useStore((s) => s.selectedId)
  const select = useStore((s) => s.select)
  const setCurrentTime = useStore((s) => s.setCurrentTime)
  const updateSegmentTimes = useStore((s) => s.updateSegmentTimes)

  const barRef = useRef<HTMLDivElement | null>(null)
  const [mode, setMode] = useState<Mode>(null)
  // Resize is transient too: the block follows the pointer locally and the
  // store is written once on release, so a drag is a single undo step.
  const [preview, setPreview] = useState<Times | null>(null)
  const previewRef = useRef<Times | null>(null)

  const timeAt = useCallback(
    (clientX: number): number => {
      const el = barRef.current
      if (!el || !duration) return 0
      const rect = el.getBoundingClientRect()
      const fraction = (clientX - rect.left) / rect.width
      return Math.min(duration, Math.max(0, fraction * duration))
    },
    [duration],
  )

  useEffect(() => {
    if (!mode) return
    const move = (e: PointerEvent) => {
      if (mode.kind === 'scrub') {
        setCurrentTime(timeAt(e.clientX))
        return
      }
      const width = barRef.current?.getBoundingClientRect().width ?? 0
      if (!width || !duration) return
      const delta = ((e.clientX - mode.originX) / width) * duration
      const next: Times = {
        id: mode.id,
        ...clampTimes(
          mode.edge === 'start' ? mode.originStart + delta : mode.originStart,
          mode.edge === 'end' ? mode.originEnd + delta : mode.originEnd,
          duration,
        ),
      }
      previewRef.current = next
      setPreview(next)
    }
    const up = () => {
      const pending = previewRef.current
      previewRef.current = null
      setPreview(null)
      if (pending) updateSegmentTimes(pending.id, pending.start, pending.end)
      setMode(null)
    }
    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    window.addEventListener('pointercancel', up)
    return () => {
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      window.removeEventListener('pointercancel', up)
    }
  }, [mode, duration, timeAt, setCurrentTime, updateSegmentTimes])

  if (!duration) return null

  const startResize = (
    e: React.PointerEvent,
    seg: Segment,
    edge: 'start' | 'end',
  ) => {
    e.stopPropagation()
    e.preventDefault()
    select(seg.id)
    setMode({
      kind: 'resize',
      id: seg.id,
      edge,
      originX: e.clientX,
      originStart: seg.start,
      originEnd: seg.end,
    })
  }

  return (
    <div className="w-full select-none">
      {/* Time always runs left→right, as in every video editor, even in an RTL UI. */}
      <div
        ref={barRef}
        dir="ltr"
        role="slider"
        aria-label={t('timeline')}
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        aria-valuenow={Math.round(currentTime)}
        tabIndex={0}
        title={t('timelineHint')}
        className="relative h-16 cursor-pointer touch-none overflow-hidden rounded-xl border border-line bg-ink/60"
        onPointerDown={(e) => {
          e.preventDefault()
          setMode({ kind: 'scrub' })
          setCurrentTime(timeAt(e.clientX))
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') setCurrentTime(Math.max(0, currentTime - 1))
          if (e.key === 'ArrowRight') setCurrentTime(Math.min(duration, currentTime + 1))
        }}
      >
        {segments.map((seg) => {
          const shown = preview?.id === seg.id ? preview : seg
          const left = (shown.start / duration) * 100
          const width = Math.max(0.4, ((shown.end - shown.start) / duration) * 100)
          const selected = seg.id === selectedId
          const active = currentTime >= seg.start && currentTime < seg.end
          const fill = selected
            ? 'bg-accent/25 border-accent/50'
            : active
              ? 'bg-signal/25 border-signal/40'
              : 'bg-surface-2/80 border-line'
          const spine = selected ? 'bg-accent' : active ? 'bg-signal' : 'bg-muted/40'
          return (
            <div
              key={seg.id}
              title={seg.text.replace(/\n/g, ' ')}
              onPointerDown={(e) => {
                e.stopPropagation()
                select(seg.id)
                setCurrentTime(seg.start)
              }}
              className={`absolute inset-y-2 overflow-hidden rounded-md border ${fill} ${
                selected ? 'cursor-ew-resize' : 'cursor-pointer'
              }`}
              style={{ left: `${left}%`, width: `${width}%` }}
            >
              <span className={`absolute inset-y-0 left-0 w-0.5 ${spine}`} />
              <span
                dir="auto"
                className="pointer-events-none block truncate px-2 py-1.5 text-[10px] leading-tight text-paper/70"
              >
                {seg.text.replace(/\n/g, ' ')}
              </span>

              {selected && (
                <>
                  <span
                    role="button"
                    aria-label={t('seekStart')}
                    onPointerDown={(e) => startResize(e, seg, 'start')}
                    className="absolute inset-y-0 left-0 w-2.5 cursor-ew-resize bg-accent/70 hover:bg-accent"
                  />
                  <span
                    role="button"
                    aria-label={t('seekEnd')}
                    onPointerDown={(e) => startResize(e, seg, 'end')}
                    className="absolute inset-y-0 right-0 w-2.5 cursor-ew-resize bg-accent/70 hover:bg-accent"
                  />
                </>
              )}
            </div>
          )
        })}

        {/* Playhead */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 w-px bg-accent"
          style={{ left: `${(currentTime / duration) * 100}%` }}
        >
          <span className="absolute -left-1.5 top-0 h-3 w-3 rounded-b-full bg-accent" />
        </div>
      </div>

      {/* Matches the bar: elapsed on the left, total on the right, in any UI language. */}
      <div dir="ltr" className="tnum mt-2 flex justify-between text-[11px] text-muted">
        <span className="text-paper/80">{formatTime(currentTime, true)}</span>
        <span>{formatTime(duration, true)}</span>
      </div>
    </div>
  )
}
