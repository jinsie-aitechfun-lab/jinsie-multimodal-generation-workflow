import type { ThemeKey } from '../composables/useTheme'

export type LandingHeroTheme = 'gold' | 'pearl'
export type LandingHeroPriority = 'high' | 'low'

export interface LandingHeroAsset {
  theme: LandingHeroTheme
  src: string
  width: number
  height: number
}

const HERO_ASSETS: Record<LandingHeroTheme, LandingHeroAsset> = {
  gold: {
    theme: 'gold',
    src: '/hero/storybook-hero-transparent.webp',
    width: 2178,
    height: 1531,
  },
  pearl: {
    theme: 'pearl',
    src: '/hero/storybook-hero-transparent-white.webp',
    width: 2212,
    height: 1896,
  },
}

type HeroCacheEntry = {
  image: HTMLImageElement | null
  promise: Promise<LandingHeroAsset> | null
  ready: boolean
}

const heroCache: Record<LandingHeroTheme, HeroCacheEntry> = {
  gold: { image: null, promise: null, ready: false },
  pearl: { image: null, promise: null, ready: false },
}

let alternatePreloadScheduled = false

function toHeroTheme(theme: ThemeKey): LandingHeroTheme {
  return theme === 'pearl' ? 'pearl' : 'gold'
}

export function getHeroAsset(theme: ThemeKey): LandingHeroAsset {
  return HERO_ASSETS[toHeroTheme(theme)]
}

export function isHeroReady(theme: ThemeKey): boolean {
  return heroCache[toHeroTheme(theme)].ready
}

function waitForImageLoad(image: HTMLImageElement): Promise<void> {
  return new Promise((resolve, reject) => {
    if (image.complete && image.naturalWidth > 0) {
      resolve()
      return
    }
    if (image.complete && image.hasAttribute('src')) {
      reject(new Error('Hero image failed to load'))
      return
    }

    image.addEventListener('load', () => resolve(), { once: true })
    image.addEventListener('error', () => reject(new Error('Hero image failed to load')), {
      once: true,
    })
  })
}

export function loadAndDecodeHero(
  theme: ThemeKey,
  priority: LandingHeroPriority = 'high',
): Promise<LandingHeroAsset> {
  const heroTheme = toHeroTheme(theme)
  const asset = HERO_ASSETS[heroTheme]
  const entry = heroCache[heroTheme]

  if (entry.ready) return Promise.resolve(asset)

  if (entry.promise) {
    if (priority === 'high' && entry.image) entry.image.fetchPriority = 'high'
    return entry.promise
  }

  const image = new Image()
  image.decoding = 'async'
  image.fetchPriority = priority
  entry.image = image

  const loadPromise = waitForImageLoad(image)
  image.src = asset.src

  entry.promise = (async () => {
    await loadPromise

    if (typeof image.decode === 'function') {
      try {
        await image.decode()
      } catch (error) {
        // A completed image is still safe to display when decode() is
        // unsupported in practice or rejects after a successful load.
        if (!image.complete || image.naturalWidth === 0) throw error
      }
    }

    entry.ready = true
    return asset
  })().catch((error: unknown) => {
    entry.image = null
    entry.promise = null
    entry.ready = false
    throw error
  })

  return entry.promise
}

export function preloadAlternateHero(currentTheme: ThemeKey): void {
  if (alternatePreloadScheduled || typeof window === 'undefined') return
  alternatePreloadScheduled = true

  const alternateTheme: LandingHeroTheme = toHeroTheme(currentTheme) === 'pearl' ? 'gold' : 'pearl'
  const loadAlternate = () => {
    void loadAndDecodeHero(alternateTheme, 'low').catch((error: unknown) => {
      console.warn('[Landing Hero] Alternate theme image preload failed.', error)
    })
  }

  const idleWindow = window as Window & {
    requestIdleCallback?: (callback: () => void) => number
  }

  if (typeof idleWindow.requestIdleCallback === 'function') {
    idleWindow.requestIdleCallback(loadAlternate)
    return
  }

  if (document.readyState === 'complete') {
    queueMicrotask(loadAlternate)
  } else {
    window.addEventListener('load', loadAlternate, { once: true })
  }
}
