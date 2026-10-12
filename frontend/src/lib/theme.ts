/**
 * Theme selection.
 *
 * Light is the default; dark is opt-in and remembered. The choice lives on
 * `<html data-theme>`, which the tokens in `index.css` key off, so no component
 * needs to know which theme is active.
 *
 * The same value is read by a small inline script in `index.html` before first
 * paint, so a dark-mode visitor never sees a flash of light. The storage key is
 * duplicated there on purpose: that script has to run before any module loads.
 */
export type Theme = 'light' | 'dark'

export const THEME_KEY = 'klam-theme'

export function storedTheme(): Theme {
  try {
    return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light'
  } catch {
    // Storage can be blocked (private windows, hardened settings). Light is
    // still a perfectly good answer.
    return 'light'
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch {
    // A theme preference is not worth failing over.
  }
}
