// Unicode bidi first-strong heuristic, mirroring the backend direction.py.

function isRtlCode(code: number): boolean {
  return (
    (code >= 0x0590 && code <= 0x05ff) || // Hebrew
    (code >= 0x0600 && code <= 0x06ff) || // Arabic
    (code >= 0x0700 && code <= 0x074f) || // Syriac
    (code >= 0x0750 && code <= 0x077f) || // Arabic Supplement
    (code >= 0x08a0 && code <= 0x08ff) || // Arabic Extended-A
    (code >= 0xfb1d && code <= 0xfb4f) || // Hebrew presentation forms
    (code >= 0xfb50 && code <= 0xfdff) || // Arabic presentation forms A
    (code >= 0xfe70 && code <= 0xfeff) // Arabic presentation forms B
  )
}

function isLtrCode(code: number): boolean {
  return (
    (code >= 0x0041 && code <= 0x005a) ||
    (code >= 0x0061 && code <= 0x007a) ||
    (code >= 0x00c0 && code <= 0x024f) || // Latin-1 + Latin Extended
    (code >= 0x0370 && code <= 0x03ff) || // Greek
    (code >= 0x0400 && code <= 0x04ff) // Cyrillic
  )
}

export function detectDirection(text: string): 'rtl' | 'ltr' {
  for (const ch of text) {
    const code = ch.codePointAt(0)
    if (code === undefined) continue
    if (isRtlCode(code)) return 'rtl'
    if (isLtrCode(code)) return 'ltr'
  }
  return 'ltr'
}

export function hasRtl(text: string): boolean {
  for (const ch of text) {
    const code = ch.codePointAt(0)
    if (code !== undefined && isRtlCode(code)) return true
  }
  return false
}

export function resolveDirection(
  dir: 'auto' | 'ltr' | 'rtl' | null | undefined,
  text: string,
): 'ltr' | 'rtl' {
  if (dir === 'ltr' || dir === 'rtl') return dir
  return detectDirection(text)
}
