import { cropsContent, ratioLabel } from '../lib/canvas'
import { PLATFORMS } from '../lib/platforms'
import { useCanvasFrame } from '../lib/useCanvasFrame'
import { useT } from '../lib/useT'
import { useStore } from '../store'

/**
 * Switches the stage between the media's own frame and the export frames a
 * creator actually posts to. Chips are labelled with the aspect token because
 * that is the thing being chosen; the full platform name is the accessible label.
 */
export default function PreviewAspectBar() {
  const t = useT()
  const platform = useStore((s) => s.platform)
  const setPlatform = useStore((s) => s.setPlatform)
  const { chosen, width, height, mediaWidth, mediaHeight } = useCanvasFrame()

  const cropping = cropsContent(mediaWidth, mediaHeight, width, height, chosen.mode)

  return (
    <div className="flex shrink-0 items-center gap-2">
      <span className="hidden shrink-0 text-[11px] text-muted sm:inline">{t('previewAs')}</span>

      <div
        role="group"
        aria-label={t('previewAs')}
        className="flex min-w-0 flex-1 gap-1 overflow-x-auto pb-0.5"
      >
        {PLATFORMS.map((p) => {
          const active = p.id === platform
          return (
            <button
              key={p.id}
              type="button"
              aria-pressed={active}
              aria-label={t(p.key)}
              title={t(p.key)}
              onClick={() => setPlatform(p.id)}
              className={`h-8 shrink-0 cursor-pointer rounded-lg border px-2.5 text-[12px] whitespace-nowrap transition-colors duration-150 max-sm:h-9 ${
                active
                  ? 'border-accent bg-accent/10 text-paper'
                  : 'border-line text-muted hover:border-muted/60 hover:text-paper'
              }`}
            >
              {p.aspect === 'source' ? t('platformOriginal') : p.aspect}
            </button>
          )
        })}
      </div>

      <span
        dir="ltr"
        title={t('outputSize')}
        className="tnum hidden shrink-0 text-[11px] text-muted sm:inline"
      >
        {ratioLabel(width, height)} · {width}×{height}
        {cropping ? ` · ${t('cropped')}` : ''}
      </span>
    </div>
  )
}
