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
  /** Three swatch colors for the preview chip (CSS color strings) */
  swatches: [string, string, string]
}

export const THEMES: Record<ThemeKey, ThemeMeta> = {
  gold: {
    key: 'gold',
    label: '沉金暗调',
    short: '金',
    tagline: '黑金科技 · 专业工作台',
    mode: 'dark',
    swatches: ['#f59e0b', '#fb923c', '#fbbf24'],
  },
  blue: {
    key: 'blue',
    label: '极夜蓝调',
    short: '蓝',
    tagline: '深空冷光 · 科技未来感',
    mode: 'dark',
    swatches: ['#0ea5e9', '#6366f1', '#38bdf8'],
  },
  purple: {
    key: 'purple',
    label: '暗紫星芒',
    short: '紫',
    tagline: '神秘星芒 · 极致创作',
    mode: 'dark',
    swatches: ['#a855f7', '#f43f5e', '#c084fc'],
  },
  pearl: {
    key: 'pearl',
    label: '珍珠晨光',
    short: '珠',
    tagline: '香槟金 · 浅色高级',
    mode: 'light',
    swatches: ['#c2914a', '#4f8fc0', '#e9cb83'],
  },
}

export const THEME_ORDER: ThemeKey[] = ['gold', 'blue', 'purple', 'pearl']

const STORAGE_KEY = 'studio_theme'
const DEFAULT_THEME: ThemeKey = 'gold'

function readInitial(): ThemeKey {
  if (typeof window === 'undefined') return DEFAULT_THEME
  const stored = window.localStorage.getItem(STORAGE_KEY) as ThemeKey | null
  return stored && stored in THEMES ? stored : DEFAULT_THEME
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
    setTheme,
    cycleTheme,
  }
}
