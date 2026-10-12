import { describe, expect, it } from 'vitest'

import { hexToRgba } from '../src/lib/color'
import { clamp, formatTime, newId } from '../src/lib/format'
import { STRINGS, translate } from '../src/i18n'
import { splitTextAtFraction } from '../src/store'
import { DEFAULT_STYLE, Project } from '../src/schema'

describe('i18n', () => {
  it('defines every English key in Arabic too', () => {
    // TranslationKey is derived from the English table, so a key added there
    // and forgotten in Arabic type-checks and then renders as `undefined`.
    const missing = Object.keys(STRINGS.en).filter(
      (key) => !(key in STRINGS.ar),
    )
    expect(missing).toEqual([])
  })

  it('renders every key in both languages', () => {
    for (const key of Object.keys(STRINGS.en) as (keyof typeof STRINGS.en)[]) {
      expect(translate('en', key)).toBeTruthy()
      expect(translate('ar', key)).toBeTruthy()
    }
  })
})

describe('formatTime', () => {
  it('formats with and without millis', () => {
    expect(formatTime(65.5)).toBe('01:05')
    expect(formatTime(65.5, true)).toBe('01:05.500')
    expect(formatTime(3661.25, true)).toBe('01:01:01.250')
  })
})

describe('hexToRgba', () => {
  it('converts hex to rgba', () => {
    expect(hexToRgba('#000000', 0.6)).toBe('rgba(0, 0, 0, 0.6)')
    expect(hexToRgba('#FFFFFF', 1)).toBe('rgba(255, 255, 255, 1)')
    expect(hexToRgba('#0a0b0c', 0.5)).toBe('rgba(10, 11, 12, 0.5)')
  })
})

describe('splitTextAtFraction', () => {
  it('splits at the word boundary nearest the fraction', () => {
    const [left, right] = splitTextAtFraction('one two three four', 0.5)
    expect(left).toBe('one two')
    expect(right).toBe('three four')
  })

  it('splits near the end for a high fraction', () => {
    const [left, right] = splitTextAtFraction('one two three four', 0.99)
    expect(left).toBe('one two three')
    expect(right).toBe('four')
  })

  it('returns the whole text for a single word', () => {
    const [left, right] = splitTextAtFraction('مرحبا', 0.5)
    expect(left).toBe('مرحبا')
    expect(right).toBe('')
  })
})

describe('schema', () => {
  it('validates a minimal project', () => {
    const project = Project.parse({
      version: '1.0.0',
      media: { filename: 'a.mp4', duration: 10, width: 1920, height: 1080 },
      language: 'ar',
      segments: [{ id: 'a', start: 0, end: 2, text: 'مرحبا' }],
      style: DEFAULT_STYLE,
      presets: [],
    })
    expect(project.segments[0].text).toBe('مرحبا')
  })

  it('rejects an invalid language', () => {
    expect(() =>
      Project.parse({
        version: '1.0.0',
        media: { filename: 'a.mp4', duration: 10, width: 1920, height: 1080 },
        language: 'de',
        segments: [],
        style: DEFAULT_STYLE,
        presets: [],
      }),
    ).toThrow()
  })
})

describe('misc', () => {
  it('clamp and newId behave', () => {
    expect(clamp(5, 0, 3)).toBe(3)
    expect(clamp(-1, 0, 3)).toBe(0)
    expect(newId()).toBeTruthy()
  })
})

describe('DEFAULT_STYLE', () => {
  it('starts with one word at a time and no background box', () => {
    expect(DEFAULT_STYLE.active_word.mode).toBe('single')
    expect(DEFAULT_STYLE.background.opacity).toBe(0)
  })
})
