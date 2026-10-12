import { describe, expect, it } from 'vitest'

import { clampAnchor, snapAnchor } from '../src/lib/snap'

// A caption box 40% wide, 20% tall on a canvas with a 5%/4% safe margin.
const HALF_W = 0.2
const HALF_H = 0.1
const MARGIN_X = 0.05
const MARGIN_Y = 0.04
const THRESHOLD = 0.03

const snap = (x: number, y: number) =>
  snapAnchor(x, y, HALF_W, HALF_H, MARGIN_X, MARGIN_Y, THRESHOLD)

describe('clampAnchor', () => {
  it('keeps the whole box inside the safe margin', () => {
    // Left edge of the box may not cross marginX, right edge may not cross 1-marginX.
    expect(clampAnchor(0.95, 0.99, HALF_W, HALF_H, MARGIN_X, MARGIN_Y)).toEqual({
      x: 0.75,
      y: 0.86,
    })
    expect(clampAnchor(0.01, 0.0, HALF_W, HALF_H, MARGIN_X, MARGIN_Y)).toEqual({
      x: 0.25,
      y: 0.14,
    })
  })

  it('leaves an already-valid anchor alone', () => {
    expect(clampAnchor(0.5, 0.5, HALF_W, HALF_H, MARGIN_X, MARGIN_Y)).toEqual({
      x: 0.5,
      y: 0.5,
    })
  })

  it('centres a box bigger than the available space instead of inverting', () => {
    expect(clampAnchor(0.1, 0.1, 0.6, 0.6, MARGIN_X, MARGIN_Y)).toEqual({ x: 0.5, y: 0.5 })
  })
})

describe('snapAnchor', () => {
  it('snaps to the canvas centre and asks for the centre guides', () => {
    expect(snap(0.51, 0.49)).toEqual({ x: 0.5, y: 0.5, guideX: 0.5, guideY: 0.5 })
  })

  it('snaps to the safe-margin edges, guided by the margin line', () => {
    // anchor = margin + half extent, guide = the margin itself
    expect(snap(0.26, 0.15)).toEqual({ x: 0.25, y: 0.14, guideX: MARGIN_X, guideY: MARGIN_Y })
    expect(snap(0.74, 0.85)).toEqual({
      x: 0.75,
      y: 0.86,
      guideX: 1 - MARGIN_X,
      guideY: 1 - MARGIN_Y,
    })
  })

  it('leaves a position alone when nothing is close, with no guides', () => {
    expect(snap(0.6, 0.4)).toEqual({ x: 0.6, y: 0.4, guideX: null, guideY: null })
  })

  it('picks the nearest target when two are in range', () => {
    // 0.52 is 0.02 from the centre and 0.23 from the top margin.
    expect(snap(0.52, 0.52).x).toBe(0.5)
  })

  it('snaps each axis independently', () => {
    const result = snap(0.51, 0.4)
    expect(result.x).toBe(0.5)
    expect(result.guideX).toBe(0.5)
    expect(result.y).toBe(0.4)
    expect(result.guideY).toBeNull()
  })
})
