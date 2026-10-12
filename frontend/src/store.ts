import { create } from 'zustand'

import { getJob, streamJob, uploadMedia, type JobStatus } from './api'
import { clamp, newId } from './lib/format'
import { deleteUserPreset, listUserPresets, saveUserPreset } from './presets'
import {
  DEFAULT_STYLE,
  type CaptionStyle,
  type Direction,
  type Project,
  type Segment,
  type StylePreset,
  type Word,
} from './schema'

const MAX_HISTORY = 50

type DeepPartial<T> = { [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K] }

function mergeStyle(base: CaptionStyle, patch: DeepPartial<CaptionStyle>): CaptionStyle {
  return {
    ...base,
    ...patch,
    outline: patch.outline ? { ...base.outline, ...patch.outline } : base.outline,
    shadow: patch.shadow ? { ...base.shadow, ...patch.shadow } : base.shadow,
    background: patch.background ? { ...base.background, ...patch.background } : base.background,
    position: patch.position ? { ...base.position, ...patch.position } : base.position,
    active_word: patch.active_word ? { ...base.active_word, ...patch.active_word } : base.active_word,
    animation: patch.animation ? { ...base.animation, ...patch.animation } : base.animation,
  }
}

type JobState = JobStatus['status'] | 'idle' | 'uploading'

interface AppState {
  mediaUrl: string | null
  assetId: string | null
  mediaDuration: number
  mediaWidth: number
  mediaHeight: number
  /** Target frame for the export preview; see lib/platforms.ts. */
  platform: string
  project: Project | null
  segments: Segment[]
  style: CaptionStyle
  selectedId: string | null
  editingSegmentId: string | null
  currentTime: number
  jobId: string | null
  jobStatus: JobState
  jobStage: string
  jobProgress: number
  error: string | null
  uiLang: 'ar' | 'en'
  past: Segment[][]
  future: Segment[][]
  userPresets: StylePreset[]
  customFonts: string[]

  setUiLang: (lang: 'ar' | 'en') => void
  setMedia: (url: string) => void
  setDuration: (duration: number) => void
  setMediaSize: (width: number, height: number) => void
  setPlatform: (id: string) => void
  setCurrentTime: (t: number) => void
  select: (id: string | null) => void
  setEditingSegmentId: (id: string | null) => void
  setStyle: (style: CaptionStyle) => void
  updateStyle: (patch: DeepPartial<CaptionStyle>) => void
  setSegmentDir: (id: string, dir: Direction | null) => void
  savePreset: (name: string) => void
  deletePreset: (id: string) => void
  addCustomFont: (family: string) => void
  updateSegmentText: (id: string, text: string) => void
  updateSegmentTimes: (id: string, start: number, end: number) => void
  addSegment: (afterId?: string) => void
  deleteSegment: (id: string) => void
  splitSegment: (id: string, at: number) => void
  mergeWithNext: (id: string) => void
  undo: () => void
  redo: () => void
  startUpload: (file: File, language: string) => Promise<void>
  reset: () => void
}

function withHistory(state: AppState, segments: Segment[]) {
  return {
    segments,
    past: [...state.past.slice(-(MAX_HISTORY - 1)), state.segments],
    future: [],
  }
}

export function splitTextAtFraction(text: string, fraction: number): [string, string] {
  const words = text.split(/\s+/).filter(Boolean)
  if (words.length < 2) return [text, '']
  const totalChars = words.reduce((sum, w) => sum + w.length, 0)
  const target = fraction * totalChars
  let acc = 0
  let best = 1
  let bestDist = Number.POSITIVE_INFINITY
  for (let i = 1; i < words.length; i += 1) {
    acc += words[i - 1].length
    const dist = Math.abs(acc - target)
    if (dist < bestDist) {
      bestDist = dist
      best = i
    }
  }
  const left = words.slice(0, best).join(' ')
  const right = words.slice(best).join(' ')
  return [left || text, right]
}

export function alignWordsProportionally(text: string, start: number, end: number): Word[] {
  const words = text.split(/\s+/).filter(Boolean)
  if (words.length === 0) return []
  const totalChars = words.reduce((sum, w) => sum + w.length, 0) || 1
  const span = Math.max(0.05, end - start)
  let cursor = start
  const result: Word[] = []
  for (let i = 0; i < words.length; i++) {
    const w = words[i]
    const wEnd = i === words.length - 1 ? end : cursor + span * (w.length / totalChars)
    result.push({
      word: w,
      start: Number(cursor.toFixed(3)),
      end: Number(wEnd.toFixed(3)),
    })
    cursor = wEnd
  }
  return result
}

export const useStore = create<AppState>()((set, get) => ({
  mediaUrl: null,
  assetId: null,
  mediaDuration: 0,
  mediaWidth: 0,
  mediaHeight: 0,
  platform: 'original',
  project: null,
  segments: [],
  style: DEFAULT_STYLE,
  selectedId: null,
  editingSegmentId: null,
  currentTime: 0,
  jobId: null,
  jobStatus: 'idle',
  jobStage: '',
  jobProgress: 0,
  error: null,
  uiLang: 'en',
  past: [],
  future: [],
  userPresets: listUserPresets(),
  customFonts: [],

  setUiLang: (lang) => {
    document.documentElement.lang = lang
    document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr'
    set({ uiLang: lang })
  },

  setMedia: (url) => set({ mediaUrl: url }),
  setDuration: (duration) => set({ mediaDuration: duration }),
  setMediaSize: (width, height) =>
    set((state) =>
      state.mediaWidth && state.mediaHeight ? {} : { mediaWidth: width, mediaHeight: height },
    ),
  setPlatform: (id) => set({ platform: id }),
  setCurrentTime: (t) => set({ currentTime: t }),
  select: (id) => set({ selectedId: id }),
  setEditingSegmentId: (id) => set({ editingSegmentId: id }),
  setStyle: (style) => set({ style }),
  updateStyle: (patch) => set((state) => ({ style: mergeStyle(state.style, patch) })),

  setSegmentDir: (id, dir) =>
    set((state) => ({
      ...withHistory(
        state,
        state.segments.map((s) => (s.id === id ? { ...s, dir } : s)),
      ),
    })),

  savePreset: (name) => set({ userPresets: saveUserPreset(name, get().style) }),
  deletePreset: (id) => set({ userPresets: deleteUserPreset(id) }),
  addCustomFont: (family) =>
    set((state) =>
      state.customFonts.includes(family)
        ? {}
        : { customFonts: [...state.customFonts, family] },
    ),

  updateSegmentText: (id, text) =>
    set((state) =>
      withHistory(
        state,
        state.segments.map((s) => {
          if (s.id !== id) return s
          const words = alignWordsProportionally(text, s.start, s.end)
          return { ...s, text, words }
        }),
      ),
    ),

  updateSegmentTimes: (id, start, end) =>
    set((state) => {
      const s = state.segments.find((seg) => seg.id === id)
      if (!s) return {}
      const nextStart = clamp(start, 0, Math.max(0, end - 0.05))
      const nextEnd = clamp(end, nextStart + 0.05, state.mediaDuration || end)
      const next = state.segments.map((seg) => {
        if (seg.id !== id) return seg
        const words = alignWordsProportionally(seg.text, nextStart, nextEnd)
        return { ...seg, start: nextStart, end: nextEnd, words }
      })
      return withHistory(state, next)
    }),

  addSegment: (afterId) =>
    set((state) => {
      const base = afterId
        ? state.segments.find((s) => s.id === afterId)
        : state.segments[state.segments.length - 1]
      const start = base ? base.end : 0
      const end = clamp(start + 2, start, state.mediaDuration || start + 2)
      const seg: Segment = { id: newId(), start, end, text: '' }
      const index = base ? state.segments.findIndex((s) => s.id === base.id) + 1 : state.segments.length
      const next = [...state.segments]
      next.splice(index, 0, seg)
      return withHistory(state, next)
    }),

  deleteSegment: (id) =>
    set((state) => ({
      ...withHistory(state, state.segments.filter((s) => s.id !== id)),
      selectedId: state.selectedId === id ? null : state.selectedId,
    })),

  splitSegment: (id, at) =>
    set((state) => {
      const seg = state.segments.find((s) => s.id === id)
      if (!seg || at <= seg.start || at >= seg.end) return {}
      const fraction = (at - seg.start) / (seg.end - seg.start)
      const [left, right] = splitTextAtFraction(seg.text, fraction)
      const first: Segment = { ...seg, end: at, text: left }
      const second: Segment = { id: newId(), start: at, end: seg.end, text: right }
      const index = state.segments.findIndex((s) => s.id === id)
      const next = [...state.segments]
      next.splice(index, 1, first, second)
      return withHistory(state, next)
    }),

  mergeWithNext: (id) =>
    set((state) => {
      const index = state.segments.findIndex((s) => s.id === id)
      if (index < 0 || index >= state.segments.length - 1) return {}
      const current = state.segments[index]
      const nextSeg = state.segments[index + 1]
      const merged: Segment = {
        ...current,
        end: nextSeg.end,
        text: `${current.text} ${nextSeg.text}`.trim(),
      }
      const next = [...state.segments]
      next.splice(index, 2, merged)
      return withHistory(state, next)
    }),

  undo: () =>
    set((state) => {
      const past = state.past
      if (past.length === 0) return {}
      const previous = past[past.length - 1]
      return {
        segments: previous,
        past: past.slice(0, -1),
        future: [state.segments, ...state.future],
      }
    }),

  redo: () =>
    set((state) => {
      if (state.future.length === 0) return {}
      const [nextSegments, ...rest] = state.future
      return {
        segments: nextSegments,
        past: [...state.past, state.segments],
        future: rest,
      }
    }),

  startUpload: async (file, language) => {
    set({
      jobStatus: 'uploading',
      jobStage: '',
      jobProgress: 0,
      error: null,
      segments: [],
      selectedId: null,
    })
    try {
      const { job_id, asset_id } = await uploadMedia(file, language)
      set({
        jobId: job_id,
        assetId: asset_id,
        mediaUrl: `/api/assets/${asset_id}`,
        jobStatus: 'queued',
      })
      for await (const status of streamJob(job_id)) {
        if (status.status === 'done' && status.result) {
          const project = status.result
          const segmentsWithWords = project.segments.map((seg) => ({
            ...seg,
            words:
              seg.words && seg.words.length > 0
                ? seg.words
                : alignWordsProportionally(seg.text, seg.start, seg.end),
          }))
          set({
            jobStatus: 'done',
            jobStage: 'done',
            jobProgress: 1,
            project,
            segments: segmentsWithWords,
            style: project.style ?? DEFAULT_STYLE,
            mediaDuration: project.media.duration || get().mediaDuration,
            mediaWidth: project.media.width || get().mediaWidth,
            mediaHeight: project.media.height || get().mediaHeight,
            past: [],
            future: [],
          })
          return
        }
        set({
          jobStatus: status.status === 'failed' ? 'failed' : 'running',
          jobStage: status.stage ?? '',
          jobProgress: status.progress ?? 0,
          error: status.error,
        })
        if (status.status === 'failed') return
      }
    } catch (err) {
      set({ error: err instanceof Error ? err.message : String(err), jobStatus: 'failed' })
    }
  },

  reset: () =>
    set({
      mediaUrl: null,
      assetId: null,
      mediaDuration: 0,
      mediaWidth: 0,
      mediaHeight: 0,
      project: null,
      segments: [],
      selectedId: null,
      editingSegmentId: null,
      currentTime: 0,
      jobId: null,
      jobStatus: 'idle',
      jobStage: '',
      jobProgress: 0,
      error: null,
      past: [],
      future: [],
    }),
}))

export async function refreshJob(jobId: string): Promise<void> {
  const status = await getJob(jobId)
  useStore.setState({
    jobStatus: status.status,
    jobStage: status.stage ?? '',
    jobProgress: status.progress ?? 0,
    error: status.error,
  })
  if (status.status === 'done' && status.result) {
    useStore.setState({
      project: status.result,
      segments: status.result.segments,
      style: status.result.style ?? DEFAULT_STYLE,
      mediaWidth: status.result.media.width || 0,
      mediaHeight: status.result.media.height || 0,
    })
  }
}
