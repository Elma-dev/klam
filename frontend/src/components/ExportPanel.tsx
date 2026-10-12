import { useState } from 'react'

import {
  createExport,
  exportDownloadUrl,
  exportSubtitle,
  getJob,
  type ExportOptions,
} from '../api'
import { useT } from '../lib/useT'
import { PLATFORMS, platformFor } from '../lib/platforms'
import type { Project } from '../schema'
import { useStore } from '../store'
import {
  Button,
  IconAlert,
  IconCheck,
  IconChevron,
  IconDownload,
  Segmented,
  SelectRow,
} from './ui'

type Format = 'mp4' | 'srt' | 'vtt' | 'ass' | 'json'

const SUBTITLE_FORMATS: { value: Format; label: string }[] = [
  { value: 'srt', label: 'SRT' },
  { value: 'vtt', label: 'VTT' },
  { value: 'ass', label: 'ASS' },
  { value: 'json', label: 'JSON' },
]

function downloadBlob(text: string, filename: string): void {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadUrl(url: string): void {
  const a = document.createElement('a')
  a.href = url
  a.download = 'klam.mp4'
  a.click()
}

export default function ExportPanel() {
  const t = useT()
  const assetId = useStore((s) => s.assetId)
  const project = useStore((s) => s.project)
  const segments = useStore((s) => s.segments)
  const style = useStore((s) => s.style)
  const mediaDuration = useStore((s) => s.mediaDuration)
  const mediaWidth = useStore((s) => s.mediaWidth)
  const mediaHeight = useStore((s) => s.mediaHeight)
  // Shared with the stage's "Preview as" selector, so the preview you are
  // looking at is always the frame this panel is about to export.
  const platform = useStore((s) => s.platform)
  const setPlatform = useStore((s) => s.setPlatform)

  const [format, setFormat] = useState<Format>('mp4')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [crf, setCrf] = useState('23')
  const [preset, setPreset] = useState('medium')
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  const isVideo = format === 'mp4'
  const chosen = platformFor(platform)

  const buildProject = (): Project => ({
    version: '1.0.0',
    media: project?.media ?? {
      filename: 'video.mp4',
      duration: mediaDuration,
      // Real dimensions, not 0x0: a zero size would make the backend fall back
      // to 1920x1080 for the "source" canvas and diverge from the preview.
      width: mediaWidth,
      height: mediaHeight,
    },
    language: project?.language ?? 'auto',
    segments,
    style,
    presets: [],
  })

  const runExport = async () => {
    setBusy(true)
    setError(null)
    setDone(false)
    setProgress(0)
    try {
      if (!isVideo) {
        const text = await exportSubtitle(buildProject(), format)
        downloadBlob(text, `captions.${format}`)
        setDone(true)
        return
      }
      if (!assetId) throw new Error(t('needVideo'))
      const options: ExportOptions = {
        format: 'mp4',
        aspect: chosen.aspect,
        mode: chosen.mode,
        crf: Number(crf),
        preset,
      }
      const { job_id, export_id } = await createExport(assetId, buildProject(), options)
      for (;;) {
        const job = await getJob(job_id)
        setProgress(job.progress)
        if (job.status === 'done') {
          downloadUrl(exportDownloadUrl(export_id))
          setDone(true)
          break
        }
        if (job.status === 'failed') throw new Error(job.error ?? t('failed'))
        await new Promise((r) => setTimeout(r, 500))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const empty = segments.length === 0

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto pe-1">
      <div className="space-y-2.5">
        <h3 className="text-[13px] font-semibold text-paper">{t('format')}</h3>
        <Segmented
          value={isVideo ? 'mp4' : format}
          ariaLabel={t('format')}
          onChange={(v) => setFormat(v as Format)}
          options={[
            { value: 'mp4' as Format, label: t('video') },
            { value: 'srt' as Format, label: t('subtitles') },
          ]}
        />
        {!isVideo && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {SUBTITLE_FORMATS.map((f) => (
              <button
                key={f.value}
                onClick={() => setFormat(f.value)}
                className={`h-9 cursor-pointer rounded-lg border px-3 text-[13px] transition-colors ${
                  format === f.value
                    ? 'border-accent bg-accent/10 text-paper'
                    : 'border-line text-muted hover:border-muted/60 hover:text-paper'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {isVideo && (
        <div className="space-y-2.5">
          <h3 className="text-[13px] font-semibold text-paper">{t('whereToPost')}</h3>
          <div className="grid grid-cols-2 gap-1.5">
            {PLATFORMS.map((p) => {
              const active = p.id === platform
              return (
                <button
                  key={p.id}
                  onClick={() => setPlatform(p.id)}
                  aria-pressed={active}
                  className={`cursor-pointer rounded-xl border px-3 py-2.5 text-start text-[12px] transition-colors duration-150 ${
                    active
                      ? 'border-accent bg-accent/5 text-paper'
                      : 'border-line text-muted hover:border-muted/60 hover:text-paper'
                  }`}
                >
                  {t(p.key)}
                </button>
              )
            })}
          </div>
          <p className="text-[11px] leading-relaxed text-muted/80">{t('burnInHint')}</p>
        </div>
      )}

      {isVideo && (
        <div>
          <button
            onClick={() => setShowAdvanced((v) => !v)}
            aria-expanded={showAdvanced}
            className="flex cursor-pointer items-center gap-1.5 text-[12px] text-muted transition-colors hover:text-paper"
          >
            <IconChevron className={`h-3.5 w-3.5 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
            {showAdvanced ? t('lessSettings') : t('moreSettings')}
          </button>
          {showAdvanced && (
            <div className="mt-3 space-y-2.5 rounded-xl border border-line/60 bg-surface/40 p-3">
              <SelectRow
                label={t('quality')}
                value={crf}
                options={[
                  { value: '18', label: t('qualityHigh') },
                  { value: '23', label: t('qualityMedium') },
                  { value: '28', label: t('qualityDraft') },
                ]}
                onChange={setCrf}
              />
              <SelectRow
                label={t('speed')}
                value={preset}
                options={[
                  { value: 'veryfast', label: t('speedVeryFast') },
                  { value: 'fast', label: t('speedFast') },
                  { value: 'medium', label: t('speedMedium') },
                  { value: 'slow', label: t('speedSlow') },
                ]}
                onChange={setPreset}
              />
            </div>
          )}
        </div>
      )}

      <div className="space-y-3">
        <Button
          variant="primary"
          size="md"
          className="w-full"
          onClick={runExport}
          disabled={busy || empty}
        >
          {busy ? (
            t('exporting')
          ) : isVideo ? (
            <>
              <IconDownload className="h-4 w-4" />
              {t('exportVideo')}
            </>
          ) : (
            <>
              <IconDownload className="h-4 w-4" />
              {t('download')} .{format}
            </>
          )}
        </Button>

        {busy && (
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-accent transition-all"
              style={{ width: `${Math.max(4, progress * 100)}%` }}
            />
          </div>
        )}
        {done && (
          <p className="flex items-center gap-2 text-sm text-signal">
            <IconCheck className="h-4 w-4" />
            {t('exportDone')}
          </p>
        )}
        {error && (
          <p className="flex items-start gap-2 text-sm text-danger">
            <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
            {error}
          </p>
        )}
      </div>
    </div>
  )
}
