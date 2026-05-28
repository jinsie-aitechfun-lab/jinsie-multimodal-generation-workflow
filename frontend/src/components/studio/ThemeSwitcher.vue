<template>
  <div class="ts-root" v-click-outside="closePanel">
    <!-- Trigger button -->
    <button
      class="ts-trigger"
      :aria-expanded="open"
      aria-haspopup="listbox"
      :title="`当前主题：${themeMeta.label}`"
      @click="open = !open"
    >
      <span class="ts-trigger-swatches" aria-hidden="true">
        <span
          v-for="(g, i) in themeMeta.gradients"
          :key="i"
          class="ts-trigger-dot"
          :style="{ background: g }"
        />
      </span>
      <span class="ts-trigger-label">{{ themeMeta.short }}</span>
    </button>

    <!-- Popover panel -->
    <transition name="ts-fade">
      <div v-if="open" class="ts-panel" role="listbox" :aria-label="'主题切换'">
        <div class="ts-panel-header">
          <span class="ts-panel-title">主题</span>
          <span class="ts-panel-hint">选择你喜欢的风格</span>
        </div>

        <button
          v-for="key in themeOrder"
          :key="key"
          role="option"
          :aria-selected="theme === key"
          :class="['ts-option', { 'is-active': theme === key }]"
          @click="onPick(key)"
        >
          <!-- Color swatches -->
          <span class="ts-swatches" aria-hidden="true">
            <span
              v-for="(g, i) in themes[key].gradients"
              :key="i"
              class="ts-swatch"
              :style="{ background: g }"
            />
          </span>

          <!-- Label + tagline -->
          <span class="ts-text">
            <span class="ts-label">{{ themes[key].label }}</span>
            <span class="ts-tagline">{{ themes[key].tagline }}</span>
          </span>

          <!-- Active check -->
          <span class="ts-check" aria-hidden="true">
            <svg v-if="theme === key" width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M3 7.5 L6 10.5 L11.5 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </span>
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, type Directive } from 'vue'
import { useTheme, type ThemeKey } from '../../composables/useTheme'

const { theme, themeMeta, themes, themeOrder, setTheme } = useTheme()

const open = ref(false)

function closePanel() {
  open.value = false
}

function onPick(key: ThemeKey) {
  setTheme(key)
  // brief delay so user sees the check appear before panel closes
  setTimeout(closePanel, 140)
}

// Simple click-outside directive — closes panel when clicking elsewhere
const vClickOutside: Directive<HTMLElement, () => void> = {
  mounted(el, binding) {
    const handler = (e: MouseEvent) => {
      if (!el.contains(e.target as Node)) binding.value()
    }
    ;(el as HTMLElement & { __cob?: (e: MouseEvent) => void }).__cob = handler
    document.addEventListener('mousedown', handler)
  },
  unmounted(el) {
    const handler = (el as HTMLElement & { __cob?: (e: MouseEvent) => void }).__cob
    if (handler) document.removeEventListener('mousedown', handler)
  },
}
</script>

<style scoped>
/* Fixed bottom-right floating switcher — never affects layout flow */
.ts-root {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: inline-block;
}

/* ── Trigger pill (horizontal capsule) ── */
.ts-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 12px 0 10px;
  border-radius: 999px;
  border: 1px solid var(--sidebar-border, rgba(245,158,11,0.18));
  background: var(--glass-bg-light, rgba(20,16,8,0.78));
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 14px rgba(0,0,0,0.22);
}

.ts-trigger:hover {
  background: var(--item-hover-bg, rgba(245,158,11,0.10));
  border-color: var(--item-active-border, rgba(245,158,11,0.36));
}

.ts-trigger[aria-expanded='true'] {
  background: var(--item-active-bg, rgba(245,158,11,0.16));
  border-color: var(--item-active-border, rgba(245,158,11,0.50));
  box-shadow: 0 0 18px var(--item-glow, rgba(245,158,11,0.22)),
              0 4px 14px rgba(0,0,0,0.20);
}

/* Three mini gradient chips in trigger — bare, no tray */
.ts-trigger-swatches {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

.ts-trigger-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.08);
}

.ts-trigger-label {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-secondary, rgba(255,255,255,0.70));
}

/* ── Popover panel — opens upward, right-aligned ── */
.ts-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 12px);
  width: 248px;
  max-height: min(420px, calc(100vh - 96px));
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 10px;
  border-radius: 14px;
  background: var(--glass-bg-light, rgba(20,16,8,0.94));
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  border: 1px solid var(--glass-border, rgba(245,158,11,0.18));
  box-shadow:
    0 18px 48px rgba(0,0,0,0.55),
    0 0 0 1px var(--glass-border, rgba(245,158,11,0.10)),
    inset 0 1px 0 rgba(255,255,255,0.10);
  z-index: 10000;
}

/* Arrow tip pointing down (panel above the button) */
.ts-panel::after {
  content: '';
  position: absolute;
  top: 100%;
  right: 22px;
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-top: 7px solid var(--glass-bg-light, rgba(20,16,8,0.94));
  filter: drop-shadow(0 1px 1px rgba(0,0,0,0.30));
}

.ts-panel-header {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 8px 8px;
  border-bottom: 1px solid var(--border-subtle, rgba(245,158,11,0.08));
  margin-bottom: 4px;
}

.ts-panel-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-muted, rgba(255,255,255,0.45));
}

.ts-panel-hint {
  font-size: 10px;
  color: var(--text-muted, rgba(255,255,255,0.35));
  letter-spacing: 0.02em;
}

/* ── Option row ── */
.ts-option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 8px;
  border-radius: 9px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: background 0.18s, border-color 0.18s, transform 0.18s;
}

.ts-option:hover {
  background: var(--item-hover-bg, rgba(245,158,11,0.06));
  border-color: var(--item-hover-border, rgba(245,158,11,0.20));
}

.ts-option.is-active {
  background: var(--item-active-bg, rgba(245,158,11,0.14));
  border-color: var(--item-active-border, rgba(245,158,11,0.38));
}

/* Palette tray (option row) — glass card, NOT grey plastic */
.ts-swatches {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 4px;
  padding: 4px 6px;
  border-radius: 6px;
  background: transparent;
  border: none;
  box-shadow: none;
  transition: opacity 0.18s;
}

/* No special hover/active for swatch tray — keeps focus on dots themselves */

/* Individual chip — tiny flat circle */
.ts-swatch {
  display: block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(0,0,0,0.06);
}

.ts-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.ts-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary, rgba(255,255,255,0.92));
}

.ts-option.is-active .ts-label {
  color: var(--arc-300, #fbbf24);
}

.ts-tagline {
  font-size: 10px;
  color: var(--text-muted, rgba(255,255,255,0.42));
  line-height: 1.3;
}

.ts-check {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--arc-300, #fbbf24);
}

/* ── Fade animation (drop-down) ── */
.ts-fade-enter-active,
.ts-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.ts-fade-enter-from,
.ts-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

/* Pearl Dawn: lighter acrylic switcher, no grey capsule feel */
:global(:root[data-theme="pearl"]) .ts-trigger {
  background:
    linear-gradient(145deg, rgba(255,255,255,0.86), rgba(255,255,255,0.62));
  border-color: rgba(214,179,90,0.24);
  box-shadow:
    0 12px 34px rgba(46,42,34,0.08),
    0 4px 14px rgba(142,197,255,0.08),
    inset 0 1px 0 rgba(255,255,255,0.88);
}

:global(:root[data-theme="pearl"]) .ts-trigger:hover,
:global(:root[data-theme="pearl"]) .ts-trigger[aria-expanded='true'] {
  background:
    linear-gradient(145deg, rgba(255,255,255,0.92), rgba(240,248,255,0.68));
  border-color: rgba(214,179,90,0.34);
  box-shadow:
    0 16px 40px rgba(46,42,34,0.09),
    0 0 22px rgba(142,197,255,0.10),
    inset 0 1px 0 rgba(255,255,255,0.92);
}

:global(:root[data-theme="pearl"]) .ts-trigger-dot,
:global(:root[data-theme="pearl"]) .ts-swatch {
  box-shadow:
    0 0 0 1px rgba(214,179,90,0.18),
    0 2px 6px rgba(46,42,34,0.10);
}

:global(:root[data-theme="pearl"]) .ts-panel {
  background:
    linear-gradient(145deg, rgba(255,255,255,0.90), rgba(255,255,255,0.70));
  border-color: rgba(214,179,90,0.22);
  box-shadow:
    0 24px 60px rgba(46,42,34,0.12),
    0 8px 24px rgba(142,197,255,0.08),
    inset 0 1px 0 rgba(255,255,255,0.88);
}

:global(:root[data-theme="pearl"]) .ts-panel::after {
  border-top-color: rgba(255,255,255,0.82);
  filter: drop-shadow(0 1px 1px rgba(214,179,90,0.12));
}

@media (max-width: 768px) {
  .ts-root {
    bottom: 18px;
    right: 14px;
  }

  .ts-panel {
    width: min(248px, calc(100vw - 28px));
    max-height: min(420px, calc(100vh - 78px));
  }
}
</style>
