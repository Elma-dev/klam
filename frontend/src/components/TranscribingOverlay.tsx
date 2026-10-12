import { useEffect, useState } from 'react'

import type { TranslationKey } from '../i18n'
import { useT } from '../lib/useT'
import { useStore } from '../store'
import { Button, IconAlert } from './ui'

// How long progress may sit still before we say so. Long enough that ordinary
// chunking never trips it, short enough to arrive while the user is still
// waiting rather than after they have given up.
const STALL_SECONDS = 20

const STAGE_KEY: Record<string, TranslationKey> = {
  extract: 'extracting',
  vad: 'detecting',
  transcribe: 'transcribing',
  segment: 'formatting',
  done: 'done',
}

export default function TranscribingOverlay() {
  const t = useT()
  const jobStatus = useStore((s) => s.jobStatus)
  const jobStage = useStore((s) => s.jobStage)
  const jobProgress = useStore((s) => s.jobProgress)
  const error = useStore((s) => s.error)
  const reset = useStore((s) => s.reset)

  const failed = jobStatus === 'failed'
  const pct = Math.round((jobProgress || 0) * 100)
  const label = failed ? t('failed') : t(STAGE_KEY[jobStage] ?? 'transcribing')

  // Progress advances only when the backend reports a new value, so a long
  // still stretch means the request is waiting on the model, not that the
  // browser has frozen. On the hosted build the usual cause is the GPU scaling
  // from zero, which is worth naming because it looks exactly like a hang.
  //
  // The stall is keyed by the progress value it was observed at, so any update
  // clears it during render — no state to reset when progress moves again.
  const progressKey = `${jobStage}:${jobProgress}`
  const [stalledAt, setStalledAt] = useState<string | null>(null)
  useEffect(() => {
    if (failed || jobStage !== 'transcribe') return
    const timer = setTimeout(() => setStalledAt(progressKey), STALL_SECONDS * 1000)
    return () => clearTimeout(timer)
  }, [progressKey, jobStage, failed])
  const stalled = stalledAt === progressKey && !failed

  return (
    <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 rounded-card bg-ink/85 p-6 backdrop-blur-sm">
      {failed ? (
        <IconAlert className="h-8 w-8 text-danger" />
      ) : (
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-line border-t-accent" />
      )}

      <p className="text-sm font-medium text-paper">
        {label}
        {!failed && <span className="tnum text-muted"> — {pct}%</span>}
      </p>

      {!failed && (
        <div className="h-1.5 w-full max-w-xs overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full rounded-full bg-accent transition-all duration-300"
            style={{ width: `${Math.max(3, pct)}%` }}
          />
        </div>
      )}

      {jobStatus === 'queued' && <p className="text-xs text-muted">{t('queued')}</p>}

      {!failed && stalled && (
        <p className="max-w-md text-center text-xs leading-relaxed text-muted">
          {t('wakingUp')}
        </p>
      )}

      {failed && error && (
        <p className="max-w-md text-center text-xs leading-relaxed text-danger">{error}</p>
      )}

      <Button
        variant={failed ? 'primary' : 'outline'}
        onClick={reset}
        className="mt-1"
      >
        {failed ? t('startOver') : t('cancel')}
      </Button>
    </div>
  )
}
