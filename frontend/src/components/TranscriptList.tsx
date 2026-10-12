import { useT } from '../lib/useT'
import { useStore } from '../store'
import SegmentRow from './SegmentRow'
import { Button, IconPlus } from './ui'

export default function TranscriptList({ onSeek }: { onSeek: (t: number) => void }) {
  const t = useT()
  const segments = useStore((s) => s.segments)
  const addSegment = useStore((s) => s.addSegment)
  const selectedId = useStore((s) => s.selectedId)

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-2 pb-3">
        <p className="min-w-0 truncate text-[11px] text-muted/80">{t('timelineHint')}</p>
        <Button onClick={() => addSegment(selectedId ?? undefined)} className="shrink-0">
          <IconPlus className="h-4 w-4" />
          {t('addSegment')}
        </Button>
      </div>

      {segments.length === 0 ? (
        <p className="text-sm text-muted">{t('empty')}</p>
      ) : (
        <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1">
          {segments.map((seg, i) => (
            <SegmentRow
              key={seg.id}
              segment={seg}
              onSeek={onSeek}
              canMerge={i < segments.length - 1}
            />
          ))}
        </div>
      )}
    </div>
  )
}
