import { describe, expect, it } from 'vitest'

import {
  BUILTIN_PRESETS,
  exportPresetsJson,
  parsePresetsJson,
} from '../src/presets'
import { CaptionStyle, DEFAULT_STYLE } from '../src/schema'

describe('builtin presets', () => {
  it('are all valid CaptionStyle objects', () => {
    for (const preset of BUILTIN_PRESETS) {
      expect(() => CaptionStyle.parse(preset.style)).not.toThrow()
    }
  })

  it('include the expected looks', () => {
    const names = BUILTIN_PRESETS.map((p) => p.id)
    expect(names).toContain('clean')
    expect(names).toContain('boxed')
    expect(names).toContain('karaoke')
  })
})

describe('preset json', () => {
  it('round-trips a style', () => {
    const json = exportPresetsJson(DEFAULT_STYLE)
    const parsed = parsePresetsJson(json)
    expect(parsed).toEqual(DEFAULT_STYLE)
  })

  it('rejects malformed json', () => {
    expect(() => parsePresetsJson('{"nope":true}')).toThrow()
  })
})
