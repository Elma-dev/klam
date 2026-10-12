import { useRef, useState } from 'react'

import { useT } from '../lib/useT'
import { useStore } from '../store'
import CaptionDemo from './CaptionDemo'
import { IconAlert, IconUpload } from './ui'

const LANGUAGES = [
  { value: 'auto', label: null },
  { value: 'ar', label: 'العربية' },
  { value: 'fr', label: 'Français' },
  { value: 'en', label: 'English' },
]

export default function UploadPanel() {
  const t = useT()
  const startUpload = useStore((s) => s.startUpload)
  const jobStatus = useStore((s) => s.jobStatus)
  const error = useStore((s) => s.error)

  const [language, setLanguage] = useState('auto')
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement | null>(null)

  const busy = jobStatus === 'uploading'

  const handleFile = (file: File | undefined) => {
    if (file && !busy) void startUpload(file, language)
  }

  return (
    <div className="flex w-full max-w-lg flex-col items-center py-6">
      <h1 className="text-balance text-center font-display text-3xl leading-snug text-paper md:text-4xl">
        {t('uploadHeadline')}
      </h1>
      <p className="mt-3 max-w-[44ch] text-center text-[15px] leading-relaxed text-muted">
        {t('uploadLead')}
      </p>

      <label className="mt-7 flex items-center gap-2.5 text-sm text-muted">
        {t('language')}
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="h-10 cursor-pointer rounded-lg border border-line bg-surface-2 px-3 text-paper"
        >
          {LANGUAGES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label ?? t('auto')}
            </option>
          ))}
        </select>
      </label>

      {/* The drop zone is the primary action: pick a file and it starts. */}
      <div
        role="button"
        tabIndex={0}
        aria-busy={busy}
        className={`relative mt-4 flex aspect-video w-full cursor-pointer flex-col items-center justify-center overflow-hidden rounded-card border-2 border-dashed bg-surface transition-colors duration-150 ${
          dragging ? 'border-accent bg-accent/5' : 'border-line hover:border-muted/60'
        } ${busy ? 'pointer-events-none opacity-60' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFile(e.dataTransfer.files[0])
        }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
      >
        <div className="absolute inset-x-6 top-6 text-center text-[13px] text-muted">
          {busy ? t('uploading') : t('dropHint')}
        </div>

        <div className="absolute inset-x-6 bottom-6 flex justify-center">
          <CaptionDemo />
        </div>

        {!busy && (
          <span className="inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2.5 text-sm font-semibold text-ink shadow-pop">
            <IconUpload className="h-4 w-4" />
            {t('browse')}
          </span>
        )}
      </div>

      <p className="mt-3 text-xs text-muted/80">{t('dropFormats')}</p>
      <p className="mt-1 text-center text-xs text-muted/80">{t('localNote')}</p>

      {error && (
        <p className="mt-4 flex items-start gap-2 text-sm text-danger">
          <IconAlert className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </p>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="video/*,audio/*"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  )
}
