// Loads open-licensed fonts (from the public manifest) and injects @font-face
// rules so the preview and the export use the same fonts.

export interface FontEntry {
  family: string
  file: string
  weight: string
  style: string
  variable: boolean
  license: string
}

export interface FontManifest {
  fonts: FontEntry[]
}

export const FALLBACK_FAMILIES = [
  'Cairo',
  'Noto Naskh Arabic',
  'Amiri',
  'Tajawal',
  'IBM Plex Sans Arabic',
  'Inter',
]

let injected = false

function injectStyle(css: string): void {
  const id = 'vox-font-faces'
  let el = document.getElementById(id) as HTMLStyleElement | null
  if (!el) {
    el = document.createElement('style')
    el.id = id
    document.head.appendChild(el)
  }
  el.textContent = css
}

export async function loadFonts(): Promise<string[]> {
  try {
    const res = await fetch('/fonts/manifest.json')
    if (!res.ok) throw new Error('no manifest')
    const manifest = (await res.json()) as FontManifest
    if (!injected) {
      const css = manifest.fonts
        .map(
          (f) =>
            `@font-face{font-family:'${f.family}';src:url('/fonts/${f.file}') format('truetype');` +
            `font-weight:${f.weight};font-style:${f.style};font-display:swap;}`,
        )
        .join('\n')
      injectStyle(css)
      injected = true
    }
    return [...new Set(manifest.fonts.map((f) => f.family))]
  } catch {
    return FALLBACK_FAMILIES
  }
}

export async function registerCustomFont(family: string, file: File): Promise<void> {
  const url = URL.createObjectURL(file)
  const face = new FontFace(family, `url(${url})`)
  await face.load()
  document.fonts.add(face)
}
