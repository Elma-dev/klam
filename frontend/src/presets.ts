// Style presets: a few built-in looks plus user presets saved to localStorage
// and importable/exportable as JSON. Built-in names are translated by id in the
// gallery; user preset names are whatever the creator typed.

import { DEFAULT_STYLE, type CaptionStyle, type StylePreset } from './schema'
import { newId } from './lib/format'

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] }

function preset(id: string, name: string, partial: DeepPartial<CaptionStyle>): StylePreset {
  return {
    id,
    name,
    style: {
      ...DEFAULT_STYLE,
      ...partial,
      outline: { ...DEFAULT_STYLE.outline, ...partial.outline },
      shadow: { ...DEFAULT_STYLE.shadow, ...partial.shadow },
      background: { ...DEFAULT_STYLE.background, ...partial.background },
      position: { ...DEFAULT_STYLE.position, ...partial.position },
      active_word: { ...DEFAULT_STYLE.active_word, ...partial.active_word },
      animation: { ...DEFAULT_STYLE.animation, ...partial.animation },
    },
  }
}

export const BUILTIN_PRESETS: StylePreset[] = [
  // These looks pin their word effect rather than inheriting the default, so the
  // gallery keeps its variety when the default changes.
  preset('clean', 'Clean', {
    color: '#FFFFFF',
    font_weight: 700,
    active_word: { mode: 'highlight' },
    outline: { color: '#000000', width: 0 },
    shadow: { color: '#000000', offset_x: 0, offset_y: 2, blur: 6, opacity: 0.6 },
    background: { color: '#000000', opacity: 0, padding: 0, radius: 0 },
  }),
  preset('outline', 'Outline', {
    color: '#FFFFFF',
    font_weight: 800,
    font_size: 52,
    active_word: { mode: 'highlight' },
    outline: { color: '#000000', width: 6 },
    shadow: { color: '#000000', offset_x: 0, offset_y: 0, blur: 0, opacity: 0 },
    background: { color: '#000000', opacity: 0, padding: 0, radius: 0 },
  }),
  preset('boxed', 'Boxed', {
    color: '#FFFFFF',
    font_weight: 600,
    active_word: { mode: 'highlight' },
    background: { color: '#111827', opacity: 0.75, padding: 12, radius: 8 },
  }),
  preset('karaoke', 'Karaoke', {
    color: '#FFFFFF',
    font_weight: 800,
    active_word: { color: '#FFE900', scale: 1.2, mode: 'highlight' },
    background: { color: '#000000', opacity: 0.35, padding: 10, radius: 8 },
  }),
  preset('shorts', 'Shorts / Reels', {
    color: '#FFFFFF',
    font_weight: 900,
    font_size: 54,
    active_word: { color: '#38EF7D', scale: 1.25, mode: 'reveal' },
    background: { color: '#000000', opacity: 0.5, padding: 12, radius: 10 },
  }),
  preset('amiri', 'Amiri Classic', {
    font_family: 'Amiri',
    font_weight: 700,
    color: '#FDE68A',
    active_word: { mode: 'highlight' },
    background: { color: '#1C1917', opacity: 1, padding: 20, radius: 8 },
  }),
  preset('neon', 'Neon Glow', {
    color: '#7DF9FF',
    font_weight: 800,
    font_size: 52,
    active_word: { color: '#FFFFFF', scale: 1.15, mode: 'highlight' },
    shadow: { color: '#00E5FF', offset_x: 0, offset_y: 0, blur: 18, opacity: 0.9 },
    background: { color: '#000000', opacity: 0, padding: 0, radius: 0 },
  }),
]

/** Translation key for a built-in preset's display name, keyed by preset id. */
export const PRESET_NAME_KEY: Record<string, string> = {
  clean: 'lookClean',
  outline: 'lookOutline',
  boxed: 'lookBoxed',
  karaoke: 'lookKaraoke',
  shorts: 'lookShorts',
  amiri: 'lookAmiri',
  neon: 'lookNeon',
}

const STORAGE_KEY = 'vox.userPresets'

export function listUserPresets(): StylePreset[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as StylePreset[]) : []
  } catch {
    return []
  }
}

function writeUserPresets(presets: StylePreset[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(presets))
}

export function saveUserPreset(name: string, style: CaptionStyle): StylePreset[] {
  const presets = listUserPresets()
  const next = [...presets, { id: newId(), name, style }]
  writeUserPresets(next)
  return next
}

export function deleteUserPreset(id: string): StylePreset[] {
  const next = listUserPresets().filter((p) => p.id !== id)
  writeUserPresets(next)
  return next
}

export function exportPresetsJson(style: CaptionStyle): string {
  return JSON.stringify({ version: '1.0.0', style }, null, 2)
}

export function parsePresetsJson(raw: string): CaptionStyle {
  const data = JSON.parse(raw) as { style?: CaptionStyle }
  if (!data.style) throw new Error('missing "style" key')
  return data.style
}
