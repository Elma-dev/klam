import { useEffect, useRef } from 'react'

import { formatTime } from '../lib/format'
import { useT } from '../lib/useT'
import type { Segment } from '../schema'
import { useStore } from '../store'
import { IconButton, IconTrash } from './ui'

export default function SegmentRow({
  segment,
  onSeek,
  canMerge,
}: {
  segment: Segment
  onSeek: (t: number) => void
  canMerge: boolean
}) {
  const t = useT()
  const selectedId = useStore((s) => s.selectedId)
  const currentTime = useStore((s) => s.currentTime)
  const select = useStore((s) => s.select)
  const updateSegmentText = useStore((s) => s.updateSegmentText)
  const deleteSegment = useStore((s) => s.deleteSegment)
  const splitSegment = useStore((s) => s.splitSegment)
  const mergeWithNext = useStore((s) => s.mergeWithNext)
  const setSegmentDir = useStore((s) => s.setSegmentDir)

  const textRef = useRef<HTMLTextAreaElement | null>(null)
  const selected = segment.id === selectedId
  const active = currentTime >= segment.start && currentTime < segment.end

  // Keep the box sized to its content, including after undo/redo or a merge.
  useEffect(() => {
    const el = textRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [segment.text])

  const handleSplit = () => {
    const at =
      currentTime > segment.start && currentTime < segment.end
        ? currentTime
        : (segment.start + segment.end) / 2
    splitSegment(segment.id, at)
  }

  return (
    <div
      onClick={() => select(segment.id)}
      className={`relative grid cursor-pointer grid-cols-[64px_1fr] gap-2 border-b border-line/60 px-2 py-3 transition-colors ${
        selected ? 'bg-accent/5' : active ? 'bg-signal/5' : 'hover:bg-surface-2/50'
      }`}
    >
      <span
        aria-hidden
        className={`absolute inset-y-0 start-0 w-0.5 ${
          selected ? 'bg-accent' : active ? 'bg-signal' : 'bg-transparent'
        }`}
      />

      <div className="flex flex-col items-end gap-1 pt-0.5">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onSeek(segment.start)
          }}
          title={t('seekStart')}
          className="tnum cursor-pointer text-[11px] leading-tight text-paper/80 transition-colors hover:text-accent"
        >
          {formatTime(segment.start, true)}
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onSeek(segment.end)
          }}
          title={t('seekEnd')}
          className="tnum cursor-pointer text-[11px] leading-tight text-muted transition-colors hover:text-accent"
        >
          {formatTime(segment.end, true)}
        </button>
      </div>

      <div className="min-w-0">
        <textarea
          ref={textRef}
          dir="auto"
          rows={1}
          aria-label={t('captionText')}
          className="w-full resize-none rounded-lg bg-transparent text-sm leading-relaxed text-paper outline-none transition-colors focus:bg-surface-2/60"
          value={segment.text}
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => updateSegmentText(segment.id, e.target.value)}
        />

        <div className="mt-1.5 flex flex-wrap items-center gap-1">
          <select
            value={segment.dir ?? 'auto'}
            aria-label={t('direction')}
            title={t('direction')}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) =>
              setSegmentDir(
                segment.id,
                e.target.value === 'auto' ? null : (e.target.value as 'rtl' | 'ltr'),
              )
            }
            className="h-8 cursor-pointer rounded-lg border border-line bg-surface px-1.5 text-[11px] text-muted"
          >
            <option value="auto">{t('dirAuto')}</option>
            <option value="rtl">RTL</option>
            <option value="ltr">LTR</option>
          </select>

          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              handleSplit()
            }}
            className="h-8 cursor-pointer rounded-lg px-2 text-[11px] text-muted transition-colors hover:bg-surface-2 hover:text-paper"
          >
            {t('split')}
          </button>

          {canMerge && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                mergeWithNext(segment.id)
              }}
              className="h-8 cursor-pointer rounded-lg px-2 text-[11px] text-muted transition-colors hover:bg-surface-2 hover:text-paper"
            >
              {t('merge')}
            </button>
          )}

          <IconButton
            label={t('delete')}
            variant="danger"
            className="ms-auto h-8 w-8"
            onClick={(e) => {
              e.stopPropagation()
              deleteSegment(segment.id)
            }}
          >
            <IconTrash className="h-4 w-4" />
          </IconButton>
        </div>
      </div>
    </div>
  )
}
