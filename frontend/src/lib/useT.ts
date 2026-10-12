import { translate, type TranslationKey, type UI_LANG } from '../i18n'
import { useStore } from '../store'

/** Translator bound to the current UI language. */
export function useT(): (key: TranslationKey) => string {
  const uiLang = useStore((s) => s.uiLang)
  return (key: TranslationKey) => translate(uiLang as UI_LANG, key)
}

/** True when the UI chrome should read right-to-left. */
export function useIsRtl(): boolean {
  return useStore((s) => s.uiLang) === 'ar'
}
