import { useEffect, useRef, useState, type RefObject } from 'react'

import { objectFitFor } from '../lib/canvas'
import { useCanvasFrame } from '../lib/useCanvasFrame'
import { useStore } from '../store'
import CaptionOverlay from './CaptionOverlay'

/** Largest box with `aspect` that fits inside w×h. */
function fit(w: number, h: number, aspect: number): { w: number; h: number } {
  if (!w || !h) return { w: 0, h: 0 }
  return w / h > aspect ? { w: h * aspect, h } : { w, h: w / aspect }
}

export default function VideoPlayer({
  videoRef,
}: {
  videoRef: RefObject<HTMLVideoElement | null>
}) {
  const mediaUrl = useStore((s) => s.mediaUrl)
  const setDuration = useStore((s) => s.setDuration)
  const setCurrentTime = useStore((s) => s.setCurrentTime)
  const setMediaSize = useStore((s) => s.setMediaSize)

  // The stage shows the EXPORT canvas, not the media's own shape, so what you
  // see framed here is the frame ffmpeg will produce.
  const { chosen, aspect } = useCanvasFrame()

  const stageRef = useRef<HTMLDivElement | null>(null)
  const [stage, setStage] = useState({ w: 0, h: 0 })

  useEffect(() => {
    const el = stageRef.current
    if (!el) return
    const measure = () => setStage({ w: el.clientWidth, h: el.clientHeight })
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    measure()
    return () => ro.disconnect()
  }, [])

  const frame = fit(stage.w, stage.h, aspect)

  return (
    <div ref={stageRef} className="grid min-h-0 flex-1 place-items-center">
      {mediaUrl && (
        <div
          className="relative overflow-hidden rounded-xl border border-line bg-black shadow-[0_20px_60px_-24px_rgba(0,0,0,0.9)]"
          style={{ width: frame.w || undefined, height: frame.h || undefined }}
        >
          {/* `cover` reproduces ffmpeg's increase-scale + centred crop; `contain`
              reproduces its decrease-scale + centred black pad. */}
          <video
            ref={videoRef}
            src={mediaUrl}
            playsInline
            controls
            className="absolute inset-0 h-full w-full"
            style={{ objectFit: objectFitFor(chosen.aspect, chosen.mode) }}
            onLoadedMetadata={(e) => {
              const v = e.currentTarget
              setDuration(v.duration || 0)
              setMediaSize(v.videoWidth, v.videoHeight)
            }}
            onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
          />
          {/* Must stay a sibling of the video inside this box: it measures its
              own height to scale captions, and the box — bars included — is the
              canvas libass positions captions in. */}
          <CaptionOverlay />
        </div>
      )}
    </div>
  )
}
