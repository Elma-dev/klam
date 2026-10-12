// The export preview is only honest if its frame math matches the exporter's.
// These tests pin the frontend table to the backend source, which is the one
// place exact agreement is achievable.

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import { cropsContent, objectFitFor, ratioLabel, targetSize } from '../src/lib/canvas'

const HERE = dirname(fileURLToPath(import.meta.url))
const VIDEO_PY = join(HERE, '..', '..', 'backend', 'src', 'vox_darija', 'export', 'video.py')

describe('targetSize', () => {
  it('uses the fixed canvas for a target aspect', () => {
    expect(targetSize(1080, 1920, '16:9')).toEqual([1920, 1080])
    expect(targetSize(1080, 1920, '1:1')).toEqual([1080, 1080])
    expect(targetSize(1080, 1920, '9:16')).toEqual([1080, 1920])
  })

  it('keeps the media size for "source"', () => {
    expect(targetSize(1080, 1920, 'source')).toEqual([1080, 1920])
    expect(targetSize(720, 1280, 'source')).toEqual([720, 1280])
  })

  it('falls back to 1920x1080 when dimensions are unknown', () => {
    // Mirrors the backend's `or 1920` / `or 1080`, which treat 0 as falsy.
    expect(targetSize(0, 0, 'source')).toEqual([1920, 1080])
    expect(targetSize(0, 1920, 'source')).toEqual([1920, 1920])
  })

  it('rounds odd dimensions down to even', () => {
    // Mirrors the backend's `_even(n) = n - (n % 2)`.
    expect(targetSize(1921, 1081, 'source')).toEqual([1920, 1080])
    expect(targetSize(1079, 1919, 'source')).toEqual([1078, 1918])
  })
})

describe('objectFitFor', () => {
  it('maps fill to a centred crop and fit to a letterbox', () => {
    expect(objectFitFor('9:16', 'fill')).toBe('cover')
    expect(objectFitFor('16:9', 'fit')).toBe('contain')
  })

  it('never crops for "source", whatever the mode says', () => {
    // The backend returns only the ass= filter when aspect is "source".
    expect(objectFitFor('source', 'fill')).toBe('contain')
    expect(objectFitFor('source', 'fit')).toBe('contain')
  })
})

describe('ratioLabel', () => {
  it('reduces to the familiar tokens', () => {
    expect(ratioLabel(1080, 1920)).toBe('9:16')
    expect(ratioLabel(1920, 1080)).toBe('16:9')
    expect(ratioLabel(1080, 1080)).toBe('1:1')
  })
})

describe('cropsContent', () => {
  it('is silent when fill keeps everything', () => {
    // A 1080x1920 clip exported as 9:16 loses nothing.
    expect(cropsContent(1080, 1920, 1080, 1920, 'fill')).toBe(false)
  })

  it('reports a real crop', () => {
    expect(cropsContent(1080, 1920, 1080, 1080, 'fill')).toBe(true)
  })

  it('never reports a crop for fit', () => {
    expect(cropsContent(1080, 1920, 1080, 1080, 'fit')).toBe(false)
  })
})

describe('backend parity', () => {
  it('mirrors _ASPECTS from export/video.py', () => {
    const source = readFileSync(VIDEO_PY, 'utf8')
    const match = source.match(/_ASPECTS\s*=\s*\{([^}]*)\}/)
    expect(match, 'could not find _ASPECTS in export/video.py').not.toBeNull()

    const parsed: Record<string, [number, number]> = {}
    const pairs = /"([^"]+)"\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)/g
    for (const entry of (match?.[1] ?? '').matchAll(pairs)) {
      parsed[entry[1]] = [Number(entry[2]), Number(entry[3])]
    }

    expect(parsed).toEqual({
      '16:9': [1920, 1080],
      '1:1': [1080, 1080],
      '9:16': [1080, 1920],
    })
    for (const [aspect, [w, h]] of Object.entries(parsed)) {
      expect(targetSize(1, 1, aspect as '16:9')).toEqual([w, h])
    }
  })

  it('mirrors the even-rounding rule', () => {
    const source = readFileSync(VIDEO_PY, 'utf8')
    expect(source).toContain('def _even(n: int) -> int:')
    expect(source).toContain('return n - (n % 2)')
  })
})
