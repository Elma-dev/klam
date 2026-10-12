import { useEffect, useRef, useState } from 'react'

import ExportPanel from './components/ExportPanel'
import PreviewAspectBar from './components/PreviewAspectBar'
import StylePanel from './components/StylePanel'
import Timeline from './components/Timeline'
import TranscriptList from './components/TranscriptList'
import TranscribingOverlay from './components/TranscribingOverlay'
import UploadPanel from './components/UploadPanel'
import VideoPlayer from './components/VideoPlayer'
import Wordmark from './components/Wordmark'
import {
  Button,
  IconDownload,
  IconList,
  IconMoon,
  IconPalette,
  IconPlus,
  IconRedo,
  IconButton,
  IconSun,
  IconUndo,
} from './components/ui'
import { loadFonts } from './fonts'
import type { TranslationKey } from './i18n'
import { useT } from './lib/useT'
import { applyTheme, storedTheme, type Theme } from './lib/theme'
import { useStore } from './store'

type Tab = 'transcript' | 'style' | 'export'

const TABS: { id: Tab; key: TranslationKey; Icon: typeof IconList }[] = [
  { id: 'transcript', key: 'transcript', Icon: IconList },
  { id: 'style', key: 'styleTab', Icon: IconPalette },
  { id: 'export', key: 'exportTab', Icon: IconDownload },
]

const PANEL =
  'flex min-h-0 flex-1 flex-col overflow-hidden border-t border-line bg-surface/40 lg:flex-none lg:rounded-card lg:border lg:border-line lg:bg-surface/60 lg:shadow-panel'

export default function App() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const mediaUrl = useStore((s) => s.mediaUrl)
  const jobStatus = useStore((s) => s.jobStatus)
  const uiLang = useStore((s) => s.uiLang)
  const setUiLang = useStore((s) => s.setUiLang)
  // Light unless this visitor has chosen dark. index.html has already applied
  // the stored value to <html data-theme> before first paint.
  const [theme, setTheme] = useState<Theme>(storedTheme)
  const toggleTheme = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    applyTheme(next)
  }
  const undo = useStore((s) => s.undo)
  const redo = useStore((s) => s.redo)
  const reset = useStore((s) => s.reset)
  const canUndo = useStore((s) => s.past.length > 0)
  const canRedo = useStore((s) => s.future.length > 0)
  const [families, setFamilies] = useState<string[]>([])
  const [tab, setTab] = useState<Tab>('transcript')

  const t = useT()
  const ready = jobStatus === 'done'

  useEffect(() => {
    void loadFonts().then(setFamilies)
  }, [])

  // Playback and history shortcuts. Skipped while typing so the caption editor
  // keeps normal text behaviour.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null
      if (
        el &&
        (el.tagName === 'INPUT' ||
          el.tagName === 'TEXTAREA' ||
          el.tagName === 'SELECT' ||
          el.isContentEditable)
      ) {
        return
      }
      if (!ready) return
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault()
        if (e.shiftKey) redo()
        else undo()
        return
      }
      if (e.code === 'Space') {
        const video = videoRef.current
        if (!video) return
        e.preventDefault()
        if (video.paused) void video.play()
        else video.pause()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [ready, undo, redo])

  const seek = (time: number) => {
    const video = videoRef.current
    if (video) video.currentTime = time
  }

  const panelBody =
    tab === 'transcript' ? (
      <TranscriptList onSeek={seek} />
    ) : tab === 'style' ? (
      <StylePanel families={families} />
    ) : (
      <ExportPanel />
    )

  return (
    <div className="flex h-full flex-col bg-ink text-paper">
      <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line px-4 lg:px-5">
        <Wordmark />
        <div className="flex items-center gap-0.5">
          <IconButton label={t('undo')} onClick={undo} disabled={!canUndo || !ready}>
            <IconUndo />
          </IconButton>
          <IconButton label={t('redo')} onClick={redo} disabled={!canRedo || !ready}>
            <IconRedo />
          </IconButton>
          {mediaUrl && (
            <Button
              variant="ghost"
              className="ms-1"
              aria-label={t('newProject')}
              title={t('newProject')}
              onClick={() => {
                if (window.confirm(t('discardConfirm'))) reset()
              }}
            >
              <IconPlus className="h-4 w-4" />
              <span className="hidden sm:inline">{t('newProject')}</span>
            </Button>
          )}
          <span className="mx-1.5 h-5 w-px bg-line" />
          <button
            onClick={() => setUiLang(uiLang === 'ar' ? 'en' : 'ar')}
            aria-label={uiLang === 'ar' ? 'English' : 'العربية'}
            className="h-10 cursor-pointer rounded-lg border border-line px-2.5 text-[13px] text-muted transition-colors hover:border-accent hover:text-paper max-sm:h-11"
          >
            {uiLang === 'ar' ? 'EN' : 'ع'}
          </button>
          <button
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? t('switchToLight') : t('switchToDark')}
            title={theme === 'dark' ? t('switchToLight') : t('switchToDark')}
            className="grid h-10 w-10 cursor-pointer place-items-center rounded-lg border border-line text-muted transition-colors hover:border-accent hover:text-paper max-sm:h-11 max-sm:w-11"
          >
            {theme === 'dark' ? <IconSun /> : <IconMoon />}
          </button>
        </div>
      </header>

      <main className="flex min-h-0 flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-5 lg:p-5">
        {!mediaUrl ? (
          <div className="flex min-h-0 flex-1 items-start justify-center overflow-y-auto p-4 lg:col-span-2 lg:items-center">
            <UploadPanel />
          </div>
        ) : !ready ? (
          <div className="relative flex min-h-0 flex-1 flex-col p-4 lg:col-span-2">
            <VideoPlayer videoRef={videoRef} />
            <TranscribingOverlay />
          </div>
        ) : (
          <>
            <section className="flex h-[50vh] shrink-0 flex-col gap-3 p-4 pb-3 lg:h-auto lg:min-h-0 lg:flex-1 lg:p-0">
              <PreviewAspectBar />
              <VideoPlayer videoRef={videoRef} />
              <Timeline />
            </section>

            <aside className={PANEL}>
              <nav className="hidden shrink-0 gap-1 border-b border-line p-2 lg:flex">
                {TABS.map(({ id, key }) => (
                  <button
                    key={id}
                    onClick={() => setTab(id)}
                    aria-selected={tab === id}
                    role="tab"
                    className={`h-9 flex-1 cursor-pointer rounded-lg text-[13px] transition-colors duration-150 ${
                      tab === id
                        ? 'bg-accent font-semibold text-on-accent'
                        : 'text-muted hover:bg-surface-2 hover:text-paper'
                    }`}
                  >
                    {t(key)}
                  </button>
                ))}
              </nav>
              <div className="min-h-0 flex-1 overflow-hidden p-4">{panelBody}</div>
            </aside>
          </>
        )}
      </main>

      {mediaUrl && ready && (
        <nav className="flex shrink-0 border-t border-line bg-surface/60 lg:hidden">
          {TABS.map(({ id, key, Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              aria-selected={tab === id}
              role="tab"
              className={`flex flex-1 cursor-pointer flex-col items-center gap-1 py-2.5 text-[11px] transition-colors ${
                tab === id ? 'text-accent' : 'text-muted'
              }`}
            >
              <Icon className="h-5 w-5" />
              {t(key)}
            </button>
          ))}
        </nav>
      )}
    </div>
  )
}
