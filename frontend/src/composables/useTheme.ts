import { computed, readonly, ref } from 'vue'

export type ThemeKey = 'gold' | 'blue' | 'purple' | 'pearl'

export interface ThemeMeta {
  /** Stable key persisted to localStorage and written to data-theme */
  key: ThemeKey
  /** Display label shown in the switcher */
  label: string
  /** Short 1-char tag for compact UIs */
  short: string
  /** Short tagline shown below the label in the switcher */
  tagline: string
  /** Whether the theme is dark-on-light or light-on-dark */
  mode: 'dark' | 'light'
  /** Three solid swatch colors — used as fallback for tinted UI accents */
  swatches: [string, string, string]
  /** Three CSS gradient strings — preview chips render with these for premium feel */
  gradients: [string, string, string]
}

export const THEMES: Record<ThemeKey, ThemeMeta> = {
  gold: {
    key: 'gold',
    label: '沉金暗调',
    short: '金',
    tagline: '黑金科技 · 专业工作台',
    mode: 'dark',
    swatches: ['#f59e0b', '#fb923c', '#fbbf24'],
    gradients: [
      'linear-gradient(135deg, #8A5A14, #F0B23A)',
      'linear-gradient(135deg, #FF8A3D, #FFCF5A)',
      'linear-gradient(135deg, #D6B35A, #FFE7A3)',
    ],
  },
  blue: {
    key: 'blue',
    label: '极夜蓝调',
    short: '蓝',
    tagline: '深空冷光 · 科技未来感',
    mode: 'dark',
    swatches: ['#0ea5e9', '#6366f1', '#38bdf8'],
    gradients: [
      'linear-gradient(135deg, #0EA5E9, #67E8F9)',
      'linear-gradient(135deg, #6366F1, #A5B4FC)',
      'linear-gradient(135deg, #22D3EE, #BAE6FD)',
    ],
  },
  purple: {
    key: 'purple',
    label: '暗紫星芒',
    short: '紫',
    tagline: '神秘星芒 · 极致创作',
    mode: 'dark',
    swatches: ['#a855f7', '#f43f5e', '#c084fc'],
    gradients: [
      'linear-gradient(135deg, #A855F7, #D8B4FE)',
      'linear-gradient(135deg, #F43F5E, #FDA4AF)',
      'linear-gradient(135deg, #C084FC, #F0ABFC)',
    ],
  },
  pearl: {
    key: 'pearl',
    label: '珍珠晨光',
    short: '珠',
    tagline: '香槟金 · 浅色高级',
    mode: 'light',
    swatches: ['#c2914a', '#4f8fc0', '#e9cb83'],
    gradients: [
      'linear-gradient(135deg, #D6B35A, #F7E3A1)',
      'linear-gradient(135deg, #8EC5FF, #DDEBFF)',
      'linear-gradient(135deg, #F3DF9D, #FFF7D6)',
    ],
  },
}

/* Full ordered list of theme keys — keeps CSS / type compatibility for any
   consumer that still references blue/purple. DO NOT delete entries here:
   theme definitions in style.css and per-theme overrides still target
   them. To control which themes are SELECTABLE in the UI, use the
   VISIBLE_THEME_ORDER list below instead. */
export const THEME_ORDER: ThemeKey[] = ['gold', 'blue', 'purple', 'pearl']

/* Themes currently surfaced in the landing/studio theme switcher. The
   blue + purple variants are temporarily hidden until their per-theme
   illustration assets are ready — the underlying CSS for those themes
   remains intact and can be re-enabled by listing them here. */
export const VISIBLE_THEME_ORDER: ThemeKey[] = ['gold', 'pearl']

const STORAGE_KEY = 'studio_theme'
const DEFAULT_THEME: ThemeKey = 'gold'

function readInitial(): ThemeKey {
  if (typeof window === 'undefined') return DEFAULT_THEME
  const stored = window.localStorage.getItem(STORAGE_KEY) as ThemeKey | null
  if (!stored || !(stored in THEMES)) return DEFAULT_THEME
  // If a user previously selected a now-hidden theme (blue / purple),
  // gracefully fall back to the default so the page renders well.
  if (!VISIBLE_THEME_ORDER.includes(stored)) return DEFAULT_THEME
  return stored
}

// Shared singleton state (module-level ref → all components see the same value)
const currentTheme = ref<ThemeKey>(readInitial())

function applyToDocument(key: ThemeKey) {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', key)
  document.documentElement.style.colorScheme = THEMES[key].mode
}

let transitionTimer: ReturnType<typeof setTimeout> | null = null

function withCrossfade(key: ThemeKey) {
  if (typeof document === 'undefined') {
    applyToDocument(key)
    return
  }
  const root = document.documentElement
  root.classList.add('theme-transitioning')
  applyToDocument(key)
  if (transitionTimer) clearTimeout(transitionTimer)
  transitionTimer = setTimeout(() => {
    root.classList.remove('theme-transitioning')
    transitionTimer = null
  }, 500)
}

// Apply once at module load so theme is correct before first paint
applyToDocument(currentTheme.value)

export function useTheme() {
  function setTheme(key: ThemeKey) {
    if (!(key in THEMES) || currentTheme.value === key) return
    currentTheme.value = key
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, key)
    }
    withCrossfade(key)
  }

  function cycleTheme() {
    const idx = THEME_ORDER.indexOf(currentTheme.value)
    setTheme(THEME_ORDER[(idx + 1) % THEME_ORDER.length])
  }

  const themeMeta = computed(() => THEMES[currentTheme.value])

  return {
    theme: readonly(currentTheme),
    themeMeta,
    themes: THEMES,
    themeOrder: THEME_ORDER,
    visibleThemeOrder: VISIBLE_THEME_ORDER,
    setTheme,
    cycleTheme,
  }
}
