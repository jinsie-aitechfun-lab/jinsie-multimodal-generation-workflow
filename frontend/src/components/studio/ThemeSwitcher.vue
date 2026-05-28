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
          v-for="(c, i) in themeMeta.swatches"
          :key="i"
          class="ts-trigger-dot"
          :style="{ background: c }"
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
              v-for="(c, i) in themes[key].swatches"
              :key="i"
              class="ts-swatch"
              :style="{ background: c }"
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
.ts-root {
  position: relative;
  display: inline-block;
}

/* ── Trigger pill ── */
.ts-trigger {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 56px;
  padding: 8px 4px;
  border-radius: 12px;
  border: 1px solid var(--sidebar-border, rgba(245,158,11,0.14));
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
}

.ts-trigger:hover {
  background: var(--item-hover-bg, rgba(245,158,11,0.08));
  border-color: var(--item-active-border, rgba(245,158,11,0.30));
}

.ts-trigger[aria-expanded='true'] {
  background: var(--item-active-bg, rgba(245,158,11,0.14));
  border-color: var(--item-active-border, rgba(245,158,11,0.42));
  box-shadow: 0 0 14px var(--item-glow, rgba(245,158,11,0.18));
}

/* Three mini swatches in trigger */
.ts-trigger-swatches {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.ts-trigger-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 4px currentColor;
}

.ts-trigger-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--text-muted, rgba(255,255,255,0.40));
}

/* ── Popover panel ── */
.ts-panel {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  width: 240px;
  padding: 8px;
  border-radius: 14px;
  background: var(--glass-bg-light, rgba(20,16,8,0.92));
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid var(--glass-border, rgba(245,158,11,0.16));
  box-shadow:
    0 14px 40px rgba(0,0,0,0.50),
    0 0 0 1px var(--glass-border, rgba(245,158,11,0.08)),
    inset 0 1px 0 rgba(255,255,255,0.10);
  z-index: 80;
}

/* Arrow tip pointing down */
.ts-panel::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 7px solid transparent;
  border-right: 7px solid transparent;
  border-top: 7px solid var(--glass-bg-light, rgba(20,16,8,0.92));
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

.ts-swatches {
  display: inline-flex;
  flex-shrink: 0;
  gap: 3px;
  padding: 3px 5px;
  border-radius: 6px;
  background: rgba(0,0,0,0.25);
  border: 1px solid rgba(255,255,255,0.08);
}

.ts-swatch {
  display: block;
  width: 10px;
  height: 16px;
  border-radius: 2px;
  box-shadow: 0 0 4px currentColor;
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

/* ── Fade animation ── */
.ts-fade-enter-active,
.ts-fade-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.ts-fade-enter-from,
.ts-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(4px);
}
</style>
