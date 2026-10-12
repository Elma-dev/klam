export function formatTime(seconds: number, withMillis = false): string {
  const s = Math.max(0, seconds)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const base = `${h > 0 ? `${String(h).padStart(2, '0')}:` : ''}${String(m).padStart(2, '0')}:${String(Math.floor(sec)).padStart(2, '0')}`
  if (!withMillis) return base
  const millis = Math.round((sec - Math.floor(sec)) * 1000)
  return `${base}.${String(millis).padStart(3, '0')}`
}

export function newId(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4)
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}
