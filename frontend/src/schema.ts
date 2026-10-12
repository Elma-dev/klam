// Zod mirror of the backend Pydantic schema (backend/src/vox_darija/schema.py).
// This is the single source of truth for the frontend; keep it in sync.

import { z } from 'zod'

export const Language = z.enum(['auto', 'ar', 'fr', 'en'])
export type Language = z.infer<typeof Language>

export const Direction = z.enum(['auto', 'ltr', 'rtl'])
export type Direction = z.infer<typeof Direction>

export const Alignment = z.enum(['left', 'center', 'right'])
export type Alignment = z.infer<typeof Alignment>

export const VerticalPosition = z.enum(['top', 'middle', 'bottom'])
export type VerticalPosition = z.infer<typeof VerticalPosition>

export const AnimationType = z.enum(['none', 'fade', 'pop', 'slide'])
export type AnimationType = z.infer<typeof AnimationType>

export const Word = z.object({
  word: z.string(),
  start: z.number(),
  end: z.number(),
})
export type Word = z.infer<typeof Word>

export const Segment = z.object({
  id: z.string(),
  start: z.number(),
  end: z.number(),
  text: z.string(),
  words: z.array(Word).nullable().optional(),
  speaker: z.string().nullable().optional(),
  dir: Direction.nullable().optional(),
})
export type Segment = z.infer<typeof Segment>

export const Outline = z.object({
  color: z.string(),
  width: z.number(),
})
export type Outline = z.infer<typeof Outline>

export const Shadow = z.object({
  color: z.string(),
  offset_x: z.number(),
  offset_y: z.number(),
  blur: z.number(),
  opacity: z.number(),
})
export type Shadow = z.infer<typeof Shadow>

export const Background = z.object({
  color: z.string(),
  opacity: z.number(),
  padding: z.number(),
  radius: z.number(),
})
export type Background = z.infer<typeof Background>

export const Position = z.object({
  vertical: VerticalPosition,
  x: z.number().nullable().optional(),
  y: z.number().nullable().optional(),
})
export type Position = z.infer<typeof Position>

export const WordMode = z.enum(['highlight', 'reveal', 'single'])
export type WordMode = z.infer<typeof WordMode>

export const ActiveWord = z.object({
  color: z.string(),
  scale: z.number(),
  mode: WordMode.optional().default('single'),
})
export type ActiveWord = z.infer<typeof ActiveWord>

export const Animation = z.object({
  type: AnimationType,
  duration: z.number(),
})
export type Animation = z.infer<typeof Animation>

export const CaptionStyle = z.object({
  font_family: z.string(),
  font_size: z.number(),
  font_weight: z.number(),
  italic: z.boolean(),
  color: z.string(),
  outline: Outline,
  shadow: Shadow,
  background: Background,
  position: Position,
  align: Alignment,
  line_spacing: z.number(),
  margin_h: z.number(),
  margin_v: z.number(),
  direction: Direction,
  active_word: ActiveWord,
  animation: Animation,
})
export type CaptionStyle = z.infer<typeof CaptionStyle>

export const StylePreset = z.object({
  id: z.string(),
  name: z.string(),
  style: CaptionStyle,
})
export type StylePreset = z.infer<typeof StylePreset>

export const MediaInfo = z.object({
  filename: z.string(),
  duration: z.number(),
  width: z.number(),
  height: z.number(),
})
export type MediaInfo = z.infer<typeof MediaInfo>

export const Project = z.object({
  version: z.string(),
  media: MediaInfo,
  language: Language,
  segments: z.array(Segment),
  style: CaptionStyle,
  presets: z.array(StylePreset),
})
export type Project = z.infer<typeof Project>

export const DEFAULT_STYLE: CaptionStyle = {
  font_family: 'Cairo',
  font_size: 48,
  font_weight: 600,
  italic: false,
  color: '#FFFFFF',
  outline: { color: '#000000', width: 0 },
  shadow: { color: '#000000', offset_x: 0, offset_y: 2, blur: 0, opacity: 0.5 },
  background: { color: '#000000', opacity: 0, padding: 20, radius: 8 },
  position: { vertical: 'bottom' },
  align: 'center',
  line_spacing: 1.2,
  margin_h: 40,
  margin_v: 40,
  direction: 'auto',
  active_word: { color: '#FFE900', scale: 1.15, mode: 'single' },
  animation: { type: 'none', duration: 0.25 },
}

// CaptionStyle lengths are expressed in px at this reference height; the
// preview scales them by the displayed video height, and the ASS export by the
// output height, so preview and export match.
export const REFERENCE_HEIGHT = 1080
