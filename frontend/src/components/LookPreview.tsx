// A miniature of a caption style, rendered with the same rules as the real
// overlay (fonts, box, outline, shadow, word effect) but scaled so the text
// stays legible in a thumbnail. Creators pick a look by seeing it, not by
// reading numbers.

import { memo } from 'react'

import { detectDirection } from '../direction'
import { hexToRgba } from '../lib/color'
import type { CaptionStyle } from '../schema'

const SAMPLE = ['بزاف', 'مزيان']

/** Thumbnail type size: keeps size differences visible without shrinking to nothing. */
function previewFontSize(fontSize: number): number {
  return Math.min(22, Math.max(12, fontSize * 0.34))
}

function LookPreview({
  style,
  activeIndex = 0,
  className = '',
}: {
  style: CaptionStyle
  activeIndex?: number
  className?: string
}) {
  const k = previewFontSize(style.font_size) / Math.max(1, style.font_size)
  const { position, background } = style
  const free = position.x != null || position.y != null

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
    // Heavy strokes turn to mud at thumbnail size, so cap what the swatch shows.
    WebkitTextStroke: style.outline.width
      ? `${Math.min(style.outline.width * k, 1.6)}px ${style.outline.color}`
      : undefined,
    textShadow: `${style.shadow.offset_x * k}px ${style.shadow.offset_y * k}px ${style.shadow.blur * k}px ${hexToRgba(style.shadow.color, style.shadow.opacity)}`,
    textAlign: style.align,
  }

  return (
    <div
      aria-hidden
      className={`relative overflow-hidden rounded-lg border border-line ${className}`}
      style={{
        background:
          'radial-gradient(120% 90% at 50% 0%, #232330 0%, #14141a 55%, #0d0d12 100%)',
      }}
    >
      <div
        className="flex h-full w-full"
        style={{
          padding: `${style.margin_v * k}px ${style.margin_h * k}px`,
          alignItems:
            position.vertical === 'top'
              ? 'flex-start'
              : position.vertical === 'middle'
                ? 'center'
                : 'flex-end',
          justifyContent: 'center',
        }}
      >
        <div
          dir={detectDirection(SAMPLE.join(' '))}
          className="caption-text"
          style={{
            ...boxStyle,
            ...(free
              ? {
                  position: 'absolute',
                  left: `${(position.x ?? 0.5) * 100}%`,
                  top: `${(position.y ?? 0.5) * 100}%`,
                  transform: 'translate(-50%, -50%)',
                  maxWidth: '88%',
                }
              : { maxWidth: '88%' }),
          }}
        >
          {SAMPLE.map((word, i) => {
            const active = i === activeIndex
            const mode = style.active_word.mode ?? 'single'
            if (mode === 'single') {
              if (!active) return null
              return (
                <span
                  key={i}
                  className="inline-block"
                  style={{ color: style.active_word.color, transform: `scale(${style.active_word.scale})` }}
                >
                  {word}
                </span>
              )
            }
            return (
              <span key={i}>
                <span
                  className="inline-block"
                  style={
                    active
                      ? {
                          color: style.active_word.color,
                          transform: `scale(${style.active_word.scale})`,
                          ...(mode === 'reveal' ? { opacity: 1 } : {}),
                        }
                      : mode === 'reveal'
                        ? { opacity: 0.12 }
                        : undefined
                  }
                >
                  {word}
                </span>
                {i < SAMPLE.length - 1 ? ' ' : ''}
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// Swatches are pure and their style props are stable, so they should not
// re-render every time an unrelated style control changes.
export default memo(LookPreview)
