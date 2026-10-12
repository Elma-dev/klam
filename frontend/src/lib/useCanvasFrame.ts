import { useStore } from '../store'
import { targetSize } from './canvas'
import { platformFor, type Platform } from './platforms'

export interface CanvasFrame {
  chosen: Platform
  width: number
  height: number
  aspect: number
  mediaWidth: number
  mediaHeight: number
}

/**
 * The export canvas the preview is currently showing. Derived here once so the
 * video stage and the "Preview as" readout can never disagree.
 */
export function useCanvasFrame(): CanvasFrame {
  const platform = useStore((s) => s.platform)
  const mediaWidth = useStore((s) => s.mediaWidth)
  const mediaHeight = useStore((s) => s.mediaHeight)

  const chosen = platformFor(platform)
  const [width, height] = targetSize(mediaWidth, mediaHeight, chosen.aspect)

  return {
    chosen,
    width,
    height,
    aspect: height > 0 ? width / height : 16 / 9,
    mediaWidth,
    mediaHeight,
  }
}
