import { memo, useRef, useState } from 'react'

import { registerCustomFont } from '../fonts'
import type { TranslationKey } from '../i18n'
import { useT } from '../lib/useT'
import {
  BUILTIN_PRESETS,
  PRESET_NAME_KEY,
  exportPresetsJson,
  parsePresetsJson,
} from '../presets'
import type { CaptionStyle, StylePreset } from '../schema'
import { useStore } from '../store'
import LookPreview from './LookPreview'
import {
  Button,
  ColorRow,
  IconBookmark,
  IconClose,
  IconUpload,
  Segmented,
  SelectRow,
  SliderRow,
  ToggleRow,
} from './ui'

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true
  if (typeof a !== 'object' || typeof b !== 'object' || a === null || b === null) return false
  const ka = Object.keys(a as object)
  const kb = Object.keys(b as object)
  if (ka.length !== kb.length) return false
  return ka.every((key) =>
    deepEqual((a as Record<string, unknown>)[key], (b as Record<string, unknown>)[key]),
  )
}

/** One-tap anchors. Free-placed captions (x/y set) override all of them. */
const ANCHORS = ['top', 'middle', 'bottom'] as const

// Memoized with stable callbacks so the gallery does not re-render while an
// unrelated control (a slider, a colour) is being changed.
const LookTile = memo(function LookTile({
  preset,
  name,
  active,
  onApply,
  onDelete,
}: {
  preset: StylePreset
  name: string
  active: boolean
  onApply: (style: CaptionStyle) => void
  onDelete?: (id: string) => void
}) {
  return (
    <div className="group relative">
      <button
        type="button"
        onClick={() => onApply(preset.style)}
        aria-pressed={active}
        className={`w-full cursor-pointer rounded-xl border p-1.5 text-start transition-colors duration-150 ${
          active
            ? 'border-accent bg-accent/5'
            : 'border-line hover:border-muted/60 hover:bg-surface-2/60'
        }`}
      >
        <LookPreview style={preset.style} className="aspect-video w-full" />
        <span
          className={`mt-1.5 block truncate px-0.5 text-[11px] ${
            active ? 'text-accent' : 'text-muted'
          }`}
        >
          {name}
        </span>
      </button>
      {onDelete && (
        <button
          type="button"
          aria-label="delete"
          onClick={() => onDelete(preset.id)}
          className="absolute end-1 top-1 grid h-7 w-7 cursor-pointer place-items-center rounded-md bg-ink/80 text-muted opacity-100 transition-opacity hover:text-danger focus-visible:opacity-100 sm:opacity-0 sm:group-hover:opacity-100"
        >
          <IconClose className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  )
})

export default function StylePanel({ families }: { families: string[] }) {
  const t = useT()
  const style = useStore((s) => s.style)
  const updateStyle = useStore((s) => s.updateStyle)
  const setStyle = useStore((s) => s.setStyle)
  const userPresets = useStore((s) => s.userPresets)
  const customFonts = useStore((s) => s.customFonts)
  const savePreset = useStore((s) => s.savePreset)
  const deletePreset = useStore((s) => s.deletePreset)
  const addCustomFont = useStore((s) => s.addCustomFont)

  const importRef = useRef<HTMLInputElement | null>(null)
  const fontRef = useRef<HTMLInputElement | null>(null)
  const [mode, setMode] = useState<'simple' | 'advanced'>('simple')
  const [naming, setNaming] = useState(false)
  const [draftName, setDraftName] = useState('')

  const s = style
  const allFamilies = [...new Set([...families, ...customFonts])]
  const advanced = mode === 'advanced'
  // A dragged caption overrides the anchor, so the anchor chips must stop
  // claiming to be the position once x/y are set.
  const freePlaced = s.position.x != null || s.position.y != null

  const presetName = (p: StylePreset) => {
    const key = PRESET_NAME_KEY[p.id]
    return key ? t(key as TranslationKey) : p.name
  }

  const commitSave = () => {
    const name = draftName.trim()
    if (name) savePreset(name)
    setDraftName('')
    setNaming(false)
  }

  const download = () => {
    const blob = new Blob([exportPresetsJson(s)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'vox-preset.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const onImport = async (file: File | undefined) => {
    if (!file) return
    try {
      setStyle(parsePresetsJson(await file.text()))
    } catch {
      /* ignore malformed */
    }
  }

  const onFontUpload = async (file: File | undefined) => {
    if (!file) return
    const family = file.name.replace(/\.[^.]+$/, '')
    await registerCustomFont(family, file)
    addCustomFont(family)
    updateStyle({ font_family: family })
  }

  const fontOptions = allFamilies.map((f) => ({ value: f, label: f }))

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto pe-1">
      <Segmented
        value={mode}
        onChange={setMode}
        ariaLabel={t('styleTab')}
        options={[
          { value: 'simple', label: t('simple') },
          { value: 'advanced', label: t('advanced') },
        ]}
      />

      {/* ---------------------------------------------------------- looks */}
      <section className="space-y-2.5">
        <h3 className="text-[13px] font-semibold text-paper">{t('lookGallery')}</h3>
        <div className="grid grid-cols-2 gap-2">
          {BUILTIN_PRESETS.map((p) => (
            <LookTile
              key={p.id}
              preset={p}
              name={presetName(p)}
              active={deepEqual(s, p.style)}
              onApply={setStyle}
            />
          ))}
        </div>

        {userPresets.length > 0 && (
          <div className="space-y-2.5 pt-1">
            <h4 className="text-[11px] uppercase tracking-wide text-muted">{t('savedLooks')}</h4>
            <div className="grid grid-cols-2 gap-2">
              {userPresets.map((p) => (
                <LookTile
                  key={p.id}
                  preset={p}
                  name={p.name}
                  active={deepEqual(s, p.style)}
                  onApply={setStyle}
                  onDelete={deletePreset}
                />
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-1.5">
          {naming ? (
            <>
              <input
                autoFocus
                value={draftName}
                onChange={(e) => setDraftName(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') commitSave()
                  if (e.key === 'Escape') setNaming(false)
                }}
                placeholder={t('lookName')}
                aria-label={t('lookName')}
                className="h-9 min-w-0 flex-1 rounded-lg border border-line bg-surface-2 px-2.5 text-sm text-paper"
              />
              <Button variant="primary" onClick={commitSave} disabled={!draftName.trim()}>
                {t('save')}
              </Button>
            </>
          ) : (
            <Button onClick={() => setNaming(true)}>
              <IconBookmark className="h-4 w-4" />
              {t('saveLook')}
            </Button>
          )}
          <Button onClick={download}>{t('exportJson')}</Button>
          <Button onClick={() => importRef.current?.click()}>{t('importJson')}</Button>
          <input
            ref={importRef}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(e) => onImport(e.target.files?.[0])}
          />
        </div>
      </section>

      {/* ------------------------------------------------- caption text */}
      <section className="space-y-2.5 border-t border-line/60 pt-4">
        <h3 className="text-[13px] font-semibold text-paper">{t('captionText')}</h3>
        <SelectRow
          label={t('font')}
          value={s.font_family}
          options={fontOptions}
          onChange={(v) => updateStyle({ font_family: v })}
        />
        <button
          type="button"
          onClick={() => fontRef.current?.click()}
          className="flex cursor-pointer items-center gap-1.5 text-[11px] text-muted transition-colors hover:text-paper"
        >
          <IconUpload className="h-3.5 w-3.5" />
          {t('uploadFont')}
        </button>
        <input
          ref={fontRef}
          type="file"
          accept=".ttf,.otf,.woff,.woff2"
          className="hidden"
          onChange={(e) => onFontUpload(e.target.files?.[0])}
        />
        <SliderRow
          label={t('size')}
          value={s.font_size}
          min={12}
          max={96}
          onChange={(v) => updateStyle({ font_size: v })}
        />
        <ColorRow label={t('textColor')} value={s.color} onChange={(v) => updateStyle({ color: v })} />
        <ColorRow
          label={t('highlightColor')}
          value={s.active_word.color}
          onChange={(v) => updateStyle({ active_word: { color: v } })}
        />
        <SelectRow
          label={t('effectStyle')}
          value={s.active_word.mode ?? 'single'}
          options={[
            { value: 'reveal', label: t('effectReveal') },
            { value: 'single', label: t('effectSingle') },
            { value: 'highlight', label: t('effectHighlight') },
          ]}
          onChange={(v) => updateStyle({ active_word: { mode: v } })}
        />
        <div className="flex items-center gap-3 text-sm">
          <span className="w-24 shrink-0 truncate text-muted">{t('position')}</span>
          <div className="flex flex-1 gap-1">
            {ANCHORS.map((anchor) => {
              const active = !freePlaced && s.position.vertical === anchor
              return (
                <button
                  key={anchor}
                  type="button"
                  aria-pressed={active}
                  onClick={() => updateStyle({ position: { vertical: anchor, x: null, y: null } })}
                  className={`h-9 flex-1 cursor-pointer rounded-lg border text-[12px] transition-colors duration-150 ${
                    active
                      ? 'border-accent bg-accent/10 text-paper'
                      : 'border-line text-muted hover:border-muted/60 hover:text-paper'
                  }`}
                >
                  {t(anchor)}
                </button>
              )
            })}
          </div>
        </div>
        {freePlaced && (
          <div className="flex items-center gap-3 text-sm">
            <span className="w-24 shrink-0" />
            <span className="min-w-0 flex-1 truncate text-[11px] text-muted">
              {t('customPosition')}
            </span>
            <Button onClick={() => updateStyle({ position: { x: null, y: null } })}>
              {t('resetPosition')}
            </Button>
          </div>
        )}
        <ToggleRow
          label={t('boxOn')}
          value={s.background.opacity > 0}
          onChange={(v) =>
            updateStyle({
              background: v
                ? { opacity: 0.5, padding: Math.max(10, s.background.padding), radius: Math.max(8, s.background.radius) }
                : { opacity: 0 },
            })
          }
        />
      </section>

      {/* ------------------------------------------------------ advanced */}
      {!advanced && (
        <p className="pb-2 text-[11px] leading-relaxed text-muted/80">{t('effectsHint')}</p>
      )}

      {advanced && (
        <>
          <section className="space-y-2.5 border-t border-line/60 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('typography')}</h3>
            <SliderRow
              label={t('weight')}
              value={s.font_weight}
              min={100}
              max={900}
              step={100}
              onChange={(v) => updateStyle({ font_weight: v })}
            />
            <ToggleRow
              label={t('italic')}
              value={s.italic}
              onChange={(v) => updateStyle({ italic: v })}
            />
            <SliderRow
              label={t('lineSpacing')}
              value={s.line_spacing}
              min={0.8}
              max={2.5}
              step={0.05}
              onChange={(v) => updateStyle({ line_spacing: v })}
            />
          </section>

          <section className="space-y-2.5 border-t border-line/60 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('outline')}</h3>
            <ColorRow
              label={t('outlineColor')}
              value={s.outline.color}
              onChange={(v) => updateStyle({ outline: { color: v } })}
            />
            <SliderRow
              label={t('outlineWidth')}
              value={s.outline.width}
              min={0}
              max={12}
              step={0.5}
              onChange={(v) => updateStyle({ outline: { width: v } })}
            />
          </section>

          <section className="space-y-2.5 border-t border-line/60 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('shadow')}</h3>
            <ColorRow
              label={t('shadowColor')}
              value={s.shadow.color}
              onChange={(v) => updateStyle({ shadow: { color: v } })}
            />
            <SliderRow
              label={t('offsetX')}
              value={s.shadow.offset_x}
              min={-20}
              max={20}
              onChange={(v) => updateStyle({ shadow: { offset_x: v } })}
            />
            <SliderRow
              label={t('offsetY')}
              value={s.shadow.offset_y}
              min={-20}
              max={20}
              onChange={(v) => updateStyle({ shadow: { offset_y: v } })}
            />
            <SliderRow
              label={t('blur')}
              value={s.shadow.blur}
              min={0}
              max={30}
              onChange={(v) => updateStyle({ shadow: { blur: v } })}
            />
            <SliderRow
              label={t('opacity')}
              value={s.shadow.opacity}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => updateStyle({ shadow: { opacity: v } })}
            />
          </section>

          <section className="space-y-2.5 border-t border-line/60 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('box')}</h3>
            <ColorRow
              label={t('bgColor')}
              value={s.background.color}
              onChange={(v) => updateStyle({ background: { color: v } })}
            />
            <SliderRow
              label={t('bgOpacity')}
              value={s.background.opacity}
              min={0}
              max={1}
              step={0.05}
              onChange={(v) => updateStyle({ background: { opacity: v } })}
            />
            <SliderRow
              label={t('padding')}
              value={s.background.padding}
              min={0}
              max={40}
              onChange={(v) => updateStyle({ background: { padding: v } })}
            />
            <SliderRow
              label={t('radius')}
              value={s.background.radius}
              min={0}
              max={30}
              onChange={(v) => updateStyle({ background: { radius: v } })}
            />
          </section>

          <section className="space-y-2.5 border-t border-line/60 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('layout')}</h3>
            <SelectRow
              label={t('align')}
              value={s.align}
              options={[
                { value: 'left', label: t('alignLeft') },
                { value: 'center', label: t('alignCenter') },
                { value: 'right', label: t('alignRight') },
              ]}
              onChange={(v) => updateStyle({ align: v })}
            />
            <SelectRow
              label={t('direction')}
              value={s.direction}
              options={[
                { value: 'auto', label: t('dirAuto') },
                { value: 'rtl', label: 'RTL' },
                { value: 'ltr', label: 'LTR' },
              ]}
              onChange={(v) => updateStyle({ direction: v })}
            />
            <SliderRow
              label={t('marginH')}
              value={s.margin_h}
              min={0}
              max={200}
              onChange={(v) => updateStyle({ margin_h: v })}
            />
            <SliderRow
              label={t('marginV')}
              value={s.margin_v}
              min={0}
              max={200}
              onChange={(v) => updateStyle({ margin_v: v })}
            />
            <SliderRow
              label={t('activeScale')}
              value={s.active_word.scale}
              min={1}
              max={2}
              step={0.05}
              onChange={(v) => updateStyle({ active_word: { scale: v } })}
            />
            <p className="text-[11px] leading-relaxed text-muted/80">{t('dragHint')}</p>
            <Button onClick={() => updateStyle({ position: { x: null, y: null } })}>
              {t('resetPosition')}
            </Button>
          </section>

          <section className="space-y-2.5 border-t border-line/60 pb-2 pt-4">
            <h3 className="text-[13px] font-semibold text-paper">{t('animation')}</h3>
            <SelectRow
              label={t('effectStyle')}
              value={s.animation.type}
              options={[
                { value: 'none', label: t('animNone') },
                { value: 'fade', label: t('animFade') },
                { value: 'pop', label: t('animPop') },
                { value: 'slide', label: t('animSlide') },
              ]}
              onChange={(v) => updateStyle({ animation: { type: v } })}
            />
            <SliderRow
              label={t('duration')}
              value={s.animation.duration}
              min={0.05}
              max={1}
              step={0.05}
              suffix="s"
              onChange={(v) => updateStyle({ animation: { duration: v } })}
            />
          </section>
        </>
      )}
    </div>
  )
}
