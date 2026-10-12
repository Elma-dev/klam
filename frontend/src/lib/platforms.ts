// Where the creator is posting decides the export frame. Shared by the stage's
// "Preview as" selector and the Export tab so the two can never drift apart.

import type { TranslationKey } from '../i18n'
import type { Aspect, FitMode } from './canvas'

export const PLATFORM_IDS = ['original', 'reels', 'feed', 'youtube'] as const
export type PlatformId = (typeof PLATFORM_IDS)[number]

export interface Platform {
  id: PlatformId
  /** Translation key for the platform's full name. */
  key: TranslationKey
  aspect: Aspect
  /** Ignored by the backend whenever `aspect` is "source". */
  mode: FitMode
}

export const PLATFORMS: Platform[] = [
  { id: 'original', key: 'platformOriginal', aspect: 'source', mode: 'fit' },
  { id: 'reels', key: 'platformReels', aspect: '9:16', mode: 'fill' },
  { id: 'feed', key: 'platformFeed', aspect: '1:1', mode: 'fill' },
  { id: 'youtube', key: 'platformYoutube', aspect: '16:9', mode: 'fit' },
]

export const DEFAULT_PLATFORM: PlatformId = 'original'

export function platformFor(id: string): Platform {
  return PLATFORMS.find((p) => p.id === id) ?? PLATFORMS[0]
}
