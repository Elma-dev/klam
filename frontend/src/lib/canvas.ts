// Mirrors the backend's export frame math (backend/src/vox_darija/export/video.py)
// so the preview canvas is the same frame ffmpeg produces. Keep the two in step:
// if `target_size` or `build_vf` change there, change them here.

export type Aspect = 'source' | '16:9' | '1:1' | '9:16'
export type FitMode = 'fit' | 'fill'

const ASPECTS: Record<'16:9' | '1:1' | '9:16', [number, number]> = {
  '16:9': [1920, 1080],
  '1:1': [1080, 1080],
  '9:16': [1080, 1920],
}

/** Encoders need even dimensions; the backend rounds down, so we do too. */
const even = (n: number) => n - (n % 2)

/** Output canvas for a target aspect. `source` keeps the media's own size. */
export function targetSize(
  mediaWidth: number,
  mediaHeight: number,
  aspect: Aspect,
): [number, number] {
  const [w, h] =
    aspect === 'source'
      ? [mediaWidth || 1920, mediaHeight || 1080]
      : ASPECTS[aspect]
  return [even(w), even(h)]
}

/**
 * How the source is fitted into the canvas. `cover` reproduces ffmpeg's
 * `scale=…:force_original_aspect_ratio=increase,crop=W:H` (a centred crop) and
 * `contain` reproduces `…=decrease,pad=…:color=black` over a black canvas.
 */
export function objectFitFor(
  aspect: Aspect,
  mode: FitMode,
): 'fill' | 'cover' | 'contain' {
  // `source` never crops or pads, and its canvas already equals the media's
  // aspect — so `contain` is a no-op there, and unlike `fill` it won't distort
  // the picture during the moment before the video reports its real dimensions.
  if (aspect === 'source') return 'contain'
  return mode === 'fill' ? 'cover' : 'contain'
}

function gcd(a: number, b: number): number {
  return b === 0 ? a : gcd(b, a % b)
}

/** Human label for a canvas, e.g. "9:16" or "4:5". */
export function ratioLabel(width: number, height: number): string {
  if (!width || !height) return ''
  const d = gcd(width, height) || 1
  return `${width / d}:${height / d}`
}

/**
 * True when `fill` actually discards part of the source — the canvas ratio
 * differs enough from the media's that creators should be told.
 */
export function cropsContent(
  mediaWidth: number,
  mediaHeight: number,
  canvasWidth: number,
  canvasHeight: number,
  mode: FitMode,
): boolean {
  if (mode !== 'fill' || !mediaWidth || !mediaHeight) return false
  return Math.abs(mediaWidth / mediaHeight - canvasWidth / canvasHeight) > 0.01
}
