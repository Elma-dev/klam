// Pure placement maths for dragging a caption around the output canvas.
//
// Everything is in canvas fractions (0..1), because that is also the unit the
// exporter uses: `position.x/y` become `\an5\pos(x*W, y*H)` in the ASS file. The
// caption is anchored by its CENTRE, so each snap has two numbers — where the
// anchor goes, and which canvas line to draw a guide on.

export interface Anchor {
  x: number
  y: number
}

export interface SnapResult extends Anchor {
  /** Canvas line to draw a vertical guide at, or null when not snapped. */
  guideX: number | null
  /** Canvas line to draw a horizontal guide at, or null when not snapped. */
  guideY: number | null
}

interface Target {
  anchor: number
  guide: number
}

function nearest(value: number, targets: Target[], threshold: number): Target | null {
  let match: Target | null = null
  let best = Infinity
  for (const target of targets) {
    const distance = Math.abs(value - target.anchor)
    if (distance <= threshold && distance < best) {
      best = distance
      match = target
    }
  }
  return match
}

/**
 * Keep the whole box inside the safe margin. Falls back to the centre when the
 * box is wider or taller than the space available, so the range can't invert.
 */
export function clampAnchor(
  x: number,
  y: number,
  halfW: number,
  halfH: number,
  marginX: number,
  marginY: number,
): Anchor {
  const minX = Math.min(marginX + halfW, 0.5)
  const maxX = Math.max(1 - marginX - halfW, 0.5)
  const minY = Math.min(marginY + halfH, 0.5)
  const maxY = Math.max(1 - marginY - halfH, 0.5)
  return {
    x: Math.min(maxX, Math.max(minX, x)),
    y: Math.min(maxY, Math.max(minY, y)),
  }
}

/**
 * Snap the anchor to the canvas centre or to the safe-margin edges. `threshold`
 * is in canvas fractions — callers convert from screen pixels so the stickiness
 * feels the same whatever size the preview is drawn at.
 */
export function snapAnchor(
  x: number,
  y: number,
  halfW: number,
  halfH: number,
  marginX: number,
  marginY: number,
  threshold: number,
): SnapResult {
  const xTargets: Target[] = [
    { anchor: 0.5, guide: 0.5 },
    { anchor: marginX + halfW, guide: marginX },
    { anchor: 1 - marginX - halfW, guide: 1 - marginX },
  ]
  const yTargets: Target[] = [
    { anchor: 0.5, guide: 0.5 },
    { anchor: marginY + halfH, guide: marginY },
    { anchor: 1 - marginY - halfH, guide: 1 - marginY },
  ]

  const sx = nearest(x, xTargets, threshold)
  const sy = nearest(y, yTargets, threshold)

  return {
    x: sx ? sx.anchor : x,
    y: sy ? sy.anchor : y,
    guideX: sx ? sx.guide : null,
    guideY: sy ? sy.guide : null,
  }
}
