// Golden-image tests for Arabic rendering, using Skia (@napi-rs/canvas), which
// shapes text with HarfBuzz the same way the browser and libass do.
//
// Run `UPDATE_GOLDEN=1 pnpm test` to (re)generate the reference images.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import { GlobalFonts, createCanvas, loadImage } from '@napi-rs/canvas'
import { describe, expect, it } from 'vitest'

const HERE = dirname(fileURLToPath(import.meta.url))
const FONTS = join(HERE, '..', 'public', 'fonts')
const GOLDEN = join(HERE, 'golden')
const FONT = join(FONTS, 'Cairo-Variable.ttf')

const hasFont = existsSync(FONT)
const registered = hasFont ? GlobalFonts.registerFromPath(FONT, 'Cairo') : undefined

const W = 640
const H = 180
const DIFF_THRESHOLD = 0.02

function render(lines: string[], dir: 'rtl' | 'ltr'): Buffer {
  const canvas = createCanvas(W, H)
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#0b1220'
  ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = '#ffffff'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = '36px Cairo'
  ctx.direction = dir
  const lineH = 48
  const startY = H / 2 - ((lines.length - 1) * lineH) / 2
  lines.forEach((line, i) => ctx.fillText(line, W / 2, startY + i * lineH))
  return canvas.toBuffer('image/png')
}

async function pixels(png: Buffer): Promise<Uint8ClampedArray> {
  const img = await loadImage(png)
  const canvas = createCanvas(W, H)
  const ctx = canvas.getContext('2d')
  ctx.drawImage(img, 0, 0, W, H)
  return ctx.getImageData(0, 0, W, H).data
}

function inkRatio(data: Uint8ClampedArray): number {
  let ink = 0
  for (let i = 0; i < data.length; i += 4) {
    if (data[i] > 100) ink += 1
  }
  return ink / (W * H)
}

async function expectGolden(png: Buffer, name: string): Promise<void> {
  mkdirSync(GOLDEN, { recursive: true })
  const path = join(GOLDEN, `${name}.png`)
  if (process.env.UPDATE_GOLDEN || !existsSync(path)) {
    writeFileSync(path, png)
    return
  }
  const actual = await pixels(png)
  const expected = await pixels(readFileSync(path))
  let diff = 0
  for (let i = 0; i < actual.length; i += 4) {
    if (
      Math.abs(actual[i] - expected[i]) > 24 ||
      Math.abs(actual[i + 1] - expected[i + 1]) > 24 ||
      Math.abs(actual[i + 2] - expected[i + 2]) > 24
    ) {
      diff += 1
    }
  }
  const ratio = diff / (W * H)
  expect(ratio).toBeLessThan(DIFF_THRESHOLD)
}

describe.skipIf(!registered)('arabic golden images', () => {
  it('renders RTL Arabic captions', async () => {
    const png = render(['الدارجة المغربية', 'مرحبا بكم في الدارجة'], 'rtl')
    expect(inkRatio(await pixels(png))).toBeGreaterThan(0.01)
    await expectGolden(png, 'arabic-rtl')
  })

  it('renders mixed Darija + Latin + digits', async () => {
    const png = render(['code switching والدارجة', 'Français 100%'], 'rtl')
    expect(inkRatio(await pixels(png))).toBeGreaterThan(0.01)
    await expectGolden(png, 'mixed-darija')
  })
})
