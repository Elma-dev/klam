import { useEffect, useRef, useState } from 'react'

import { useStore } from '../store'
import { hexToRgba } from '../lib/color'
import { clampAnchor, snapAnchor } from '../lib/snap'
import { detectDirection } from '../direction'
import { alignWordsProportionally } from '../store'
import { REFERENCE_HEIGHT, type Word, type WordMode } from '../schema'

/** Snap stickiness, in screen pixels so it feels the same at any preview size. */
const SNAP_PX = 8
/** Ignore sub-pixel jitter: below this the gesture is a click, not a drag. */
const DRAG_SLOP_PX = 3

/**
 * `width: max-content` matters: an absolutely positioned box with `width: auto`
 * shrink-to-fits against the space left of `left`, so the caption would re-wrap
 * and change size as it is dragged sideways. The exporter wraps at a constant
 * width regardless of \pos, so a fixed box is also the more faithful preview.
 */
const BOX_SIZING: React.CSSProperties = { width: 'max-content', maxWidth: '90%' }

interface DragVisual {
  /** Anchor the box had when the gesture started, in canvas fractions. */
  startX: number
  startY: number
  /** Live offset from that anchor, in screen pixels. */
  dx: number
  dy: number
  guideX: number | null
  guideY: number | null
}

const ANIM_CLASS: Record<string, string> = {
  fade: 'vox-anim-fade',
  pop: 'vox-anim-pop',
  slide: 'vox-anim-slide',
}

function useElementHeight(ref: React.RefObject<HTMLElement | null>): number {
  const [height, setHeight] = useState(0)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const observer = new ResizeObserver(() => setHeight(el.clientHeight))
    observer.observe(el)
    setHeight(el.clientHeight)
    return () => observer.disconnect()
  }, [ref])
  return height
}

export default function CaptionOverlay() {
  const segments = useStore((s) => s.segments)
  const currentTime = useStore((s) => s.currentTime)
  const style = useStore((s) => s.style)
  const updateStyle = useStore((s) => s.updateStyle)
  const editingSegmentId = useStore((s) => s.editingSegmentId)
  const setEditingSegmentId = useStore((s) => s.setEditingSegmentId)
  const updateSegmentText = useStore((s) => s.updateSegmentText)
  const select = useStore((s) => s.select)

  const containerRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  const [drag, setDrag] = useState<DragVisual | null>(null)
  const dragRef = useRef<{
    rect: DOMRect
    halfW: number
    halfH: number
    marginX: number
    marginY: number
    startX: number
    startY: number
    originX: number
    originY: number
    moved: boolean
    latest: { x: number; y: number; guideX: number | null; guideY: number | null }
  } | null>(null)
  const rafRef = useRef<number | null>(null)
  const pendingRef = useRef<{ clientX: number; clientY: number } | null>(null)
  const height = useElementHeight(containerRef)
  const k = height > 0 ? height / REFERENCE_HEIGHT : 0

  const active = segments.find((s) => currentTime >= s.start && currentTime < s.end)
  const isEditing = active != null && editingSegmentId === active.id

  // Auto-focus and auto-size textarea when entering edit mode
  useEffect(() => {
    if (isEditing && textareaRef.current) {
      const ta = textareaRef.current
      ta.focus()
      ta.selectionStart = ta.value.length
      ta.style.height = 'auto'
      ta.style.height = `${ta.scrollHeight}px`
    }
  }, [isEditing])

  // Exit edit mode when the active segment changes
  useEffect(() => {
    if (editingSegmentId && (!active || active.id !== editingSegmentId)) {
      setEditingSegmentId(null)
    }
  }, [active, editingSegmentId, setEditingSegmentId])

  /**
   * Drag is transient: the store is written ONCE on release. Committing per
   * pointer event re-rendered the whole style panel (and every look swatch)
   * dozens of times a second, which is what made this feel stuck.
   */
  const startDrag = (e: React.PointerEvent) => {
    if (isEditing || !containerRef.current) return
    e.preventDefault()
    e.stopPropagation()

    const rect = containerRef.current.getBoundingClientRect()
    const box = e.currentTarget.getBoundingClientRect()
    if (!rect.width || !rect.height) return

    const startX = (box.left + box.width / 2 - rect.left) / rect.width
    const startY = (box.top + box.height / 2 - rect.top) / rect.height
    // Safe margins come from the style's own margins, so the edge snaps land
    // exactly where the top/middle/bottom layout would place the caption.
    const marginX = (style.margin_h * k) / rect.width
    const marginY = (style.margin_v * k) / rect.height

    dragRef.current = {
      rect,
      halfW: box.width / 2 / rect.width,
      halfH: box.height / 2 / rect.height,
      marginX,
      marginY,
      startX,
      startY,
      originX: e.clientX,
      originY: e.clientY,
      moved: false,
      latest: { x: startX, y: startY, guideX: null, guideY: null },
    }
    setDrag({ startX, startY, dx: 0, dy: 0, guideX: null, guideY: null })

    const compute = (clientX: number, clientY: number) => {
      const st = dragRef.current
      if (!st) return
      const clamped = clampAnchor(
        (clientX - st.rect.left) / st.rect.width,
        (clientY - st.rect.top) / st.rect.height,
        st.halfW,
        st.halfH,
        st.marginX,
        st.marginY,
      )
      const snapped = snapAnchor(
        clamped.x,
        clamped.y,
        st.halfW,
        st.halfH,
        st.marginX,
        st.marginY,
        SNAP_PX / st.rect.width,
      )
      st.latest = snapped
      if (Math.hypot(clientX - st.originX, clientY - st.originY) > DRAG_SLOP_PX) {
        st.moved = true
      }
    }

    const paint = () => {
      const st = dragRef.current
      if (!st) return
      const { latest } = st
      setDrag({
        startX: st.startX,
        startY: st.startY,
        dx: (latest.x - st.startX) * st.rect.width,
        dy: (latest.y - st.startY) * st.rect.height,
        guideX: latest.guideX,
        guideY: latest.guideY,
      })
    }

    const move = (ev: PointerEvent) => {
      pendingRef.current = { clientX: ev.clientX, clientY: ev.clientY }
      if (rafRef.current != null) return
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null
        const p = pendingRef.current
        if (!p) return
        compute(p.clientX, p.clientY)
        paint()
      })
    }

    const finish = (commit: boolean) => {
      if (rafRef.current != null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      // Flush a coalesced move so a fast flick still lands under the pointer.
      const p = pendingRef.current
      if (p) compute(p.clientX, p.clientY)
      pendingRef.current = null

      const st = dragRef.current
      dragRef.current = null
      setDrag(null)
      window.removeEventListener('pointermove', move)
      window.removeEventListener('pointerup', up)
      window.removeEventListener('pointercancel', cancel)

      // A click that never moved must not turn an anchored caption into a
      // free-placed one — that would break double-click-to-edit.
      if (commit && st?.moved) {
        updateStyle({
          position: {
            x: Number(st.latest.x.toFixed(3)),
            y: Number(st.latest.y.toFixed(3)),
          },
        })
      }
    }

    const up = () => finish(true)
    const cancel = () => finish(false)

    window.addEventListener('pointermove', move)
    window.addEventListener('pointerup', up)
    window.addEventListener('pointercancel', cancel)
  }

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (active) {
      select(active.id)
      setEditingSegmentId(active.id)
    }
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setEditingSegmentId(null)
    }
    // Prevent keyboard shortcuts (like undo) from bubbling while editing
    e.stopPropagation()
  }

  const dir = active
    ? active.dir && active.dir !== 'auto'
      ? active.dir
      : style.direction !== 'auto'
        ? style.direction
        : detectDirection(active.text)
    : 'auto'

  const { position, background } = style
  // With a box the export switches to BorderStyle 3, which draws the box from
  // `background.padding` and drops BOTH the text outline and the shadow
  // (ass.py: `border_style = 3; outline = padding * k; shadow = 0.0`).
  const boxed = background.opacity > 0.001
  const boxStyle: React.CSSProperties = {
    fontFamily: style.font_family,
    fontSize: `${style.font_size * k}px`,
    fontWeight: style.font_weight,
    fontStyle: style.italic ? 'italic' : 'normal',
    color: style.color,
    lineHeight: style.line_spacing,
    background: hexToRgba(background.color, background.opacity),
    padding: `${background.padding * k}px`,
    borderRadius: `${background.radius * k}px`,
    WebkitTextStroke:
      !boxed && style.outline.width
        ? `${style.outline.width * k}px ${style.outline.color}`
        : undefined,
    textShadow: boxed
      ? 'none'
      : `${style.shadow.offset_x * k}px ${style.shadow.offset_y * k}px ${style.shadow.blur * k}px ${hexToRgba(style.shadow.color, style.shadow.opacity)}`,
    textAlign: style.align,
  }

  const animClass =
    style.animation.type !== 'none' ? (ANIM_CLASS[style.animation.type] ?? '') : ''
  const animStyle: React.CSSProperties = animClass
    ? { animationDuration: `${style.animation.duration}s` }
    : {}
  // Grabbing the caption takes over its placement, so a caption anchored by
  // top/middle/bottom becomes free-positioned from the moment it is picked up.
  const freePosition = drag != null || position.x != null || position.y != null
  const anchorX = drag ? drag.startX : (position.x ?? 0.5)
  const anchorY = drag ? drag.startY : (position.y ?? 0.5)

  return (
    <div
      ref={containerRef}
      className="pointer-events-none absolute inset-0"
      style={{ padding: `${style.margin_v * k}px ${style.margin_h * k}px` }}
    >
      {/* Snap guides, drawn in canvas fractions (the padding box is the canvas). */}
      {drag?.guideX != null && (
        <span
          aria-hidden
          className="absolute inset-y-0 w-px bg-accent/80"
          style={{ left: `${drag.guideX * 100}%` }}
        />
      )}
      {drag?.guideY != null && (
        <span
          aria-hidden
          className="absolute inset-x-0 h-px bg-accent/80"
          style={{ top: `${drag.guideY * 100}%` }}
        />
      )}

      {/* The export pins the whole block with \an1/2/3 — physical left, centre
          or right — so the flex axis is pinned LTR and the caption keeps its own
          bidi direction on the element below. */}
      <div
        dir="ltr"
        className="flex h-full w-full"
        style={{
          alignItems:
            position.vertical === 'top'
              ? 'flex-start'
              : position.vertical === 'middle'
                ? 'center'
                : 'flex-end',
          justifyContent:
            style.align === 'left'
              ? 'flex-start'
              : style.align === 'right'
                ? 'flex-end'
                : 'center',
        }}
      >
        {active && k > 0 && (
          <div
            dir={dir}
            onPointerDown={startDrag}
            onDoubleClick={handleDoubleClick}
            className={`caption-text pointer-events-auto ${
              isEditing
                ? 'cursor-text ring-2 ring-accent/60'
                : drag
                  ? 'touch-none cursor-grabbing'
                  : 'touch-none cursor-grab hover:ring-1 hover:ring-paper/20'
            }`}
            style={{
              ...boxStyle,
              ...BOX_SIZING,
              ...(freePosition
                ? {
                    position: 'absolute',
                    left: `${anchorX * 100}%`,
                    top: `${anchorY * 100}%`,
                    // During a drag only the transform changes, which the
                    // compositor can handle without laying the page out again.
                    transform: drag
                      ? `translate(-50%, -50%) translate3d(${drag.dx}px, ${drag.dy}px, 0)`
                      : 'translate(-50%, -50%)',
                    ...(drag ? { willChange: 'transform' } : {}),
                  }
                : null),
            }}
          >
            {isEditing ? (
              <textarea
                ref={textareaRef}
                dir="auto"
                value={active.text}
                onChange={(e) => {
                  updateSegmentText(active.id, e.target.value)
                  // Auto-resize
                  const ta = e.currentTarget
                  ta.style.height = 'auto'
                  ta.style.height = `${ta.scrollHeight}px`
                }}
                onBlur={() => setEditingSegmentId(null)}
                onKeyDown={handleEditKeyDown}
                className="w-full resize-none border-none bg-transparent text-inherit outline-none"
                style={{
                  font: 'inherit',
                  fontWeight: 'inherit',
                  fontStyle: 'inherit',
                  color: 'inherit',
                  lineHeight: 'inherit',
                  textAlign: 'inherit',
                  WebkitTextStroke: 'inherit',
                  textShadow: 'inherit',
                  minWidth: '120px',
                }}
              />
            ) : (
              <div key={active.id} className={animClass} style={animStyle}>
                <CaptionText
                  text={active.text}
                  words={
                    active.words && active.words.length > 0
                      ? active.words
                      : alignWordsProportionally(active.text, active.start, active.end)
                  }
                  currentTime={currentTime}
                  color={style.active_word.color}
                  scale={style.active_word.scale}
                  mode={style.active_word.mode ?? 'single'}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface CaptionTextProps {
  text: string
  words: Word[] | null
  currentTime: number
  color: string
  scale: number
  mode: WordMode
}

function CaptionText({ text, words, currentTime, color, scale, mode }: CaptionTextProps) {
  const lines = text.split('\n')
  const lineWordCounts = lines.map((l) => l.split(/\s+/).filter(Boolean).length)
  const totalWords = lineWordCounts.reduce((a, b) => a + b, 0)

  if (!words || words.length !== totalWords) {
    return <>{text}</>
  }

  // Find index of currently active word across all words
  const activeIndex = words.findIndex((w) => currentTime >= w.start && currentTime < w.end)
  // Find index of latest word that has started (for reveal mode even in gaps between words)
  let latestStartedIndex = -1
  for (let i = 0; i < words.length; i++) {
    if (currentTime >= words[i].start) {
      latestStartedIndex = i
    }
  }

  const slices: Word[][] = []
  let cursor = 0
  for (const count of lineWordCounts) {
    slices.push(words.slice(cursor, cursor + count))
    cursor += count
  }

  let globalWordIndex = 0

  return (
    <>
      {slices.map((slice, li) => (
        <div key={li}>
          {slice.map((w, wi) => {
            const currentIdx = globalWordIndex++
            const isActive = activeIndex === currentIdx || (activeIndex === -1 && latestStartedIndex === currentIdx)
            const hasAppeared = currentIdx <= latestStartedIndex

            // "single" mode: show only the current spoken word (popular on TikTok/Reels Shorts)
            if (mode === 'single') {
              if (!isActive) return null
              return (
                <span
                  key={wi}
                  className="inline-block transition-transform duration-75"
                  style={{
                    color,
                    transform: `scale(${scale})`,
                  }}
                >
                  {w.word}
                </span>
              )
            }

            // "reveal" mode: words pop in one-by-one as spoken (Instagram Shorts style)
            if (mode === 'reveal') {
              return (
                <span key={wi}>
                  <span
                    className="inline-block transition-all duration-100"
                    style={{
                      opacity: hasAppeared ? 1 : 0.12,
                      transform: isActive ? `scale(${scale})` : 'scale(1)',
                      color: isActive ? color : 'inherit',
                      filter: hasAppeared ? 'none' : 'blur(0.5px)',
                    }}
                  >
                    {w.word}
                  </span>
                  {wi < slice.length - 1 ? ' ' : ''}
                </span>
              )
            }

            // Default "highlight" (Karaoke) mode
            return (
              <span key={wi}>
                <span
                  className="inline-block transition-transform duration-75"
                  style={
                    isActive
                      ? { color, transform: `scale(${scale})` }
                      : undefined
                  }
                >
                  {w.word}
                </span>
                {wi < slice.length - 1 ? ' ' : ''}
              </span>
            )
          })}
        </div>
      ))}
    </>
  )
}
