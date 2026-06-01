<template>
  <div class="ts-select" v-click-outside="close">
    <button
      ref="triggerRef"
      type="button"
      class="ts-trigger"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="toggle"
    >
      <span class="ts-current">{{ currentLabel }}</span>
      <svg class="ts-chev" :class="{ 'is-open': open }" width="12" height="8" viewBox="0 0 12 8" fill="none">
        <path d="M1 1 L6 6 L11 1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <Teleport to="body">
      <transition name="ts-fade">
        <ul
          v-if="open"
          ref="panelRef"
          class="ts-panel"
          role="listbox"
          :style="panelStyle"
        >
          <li
            v-for="opt in options"
            :key="opt.value"
            role="option"
            :aria-selected="opt.value === modelValue"
            :class="['ts-option', { 'is-active': opt.value === modelValue }]"
            @click="select(opt.value)"
          >
            <span class="ts-option-label">{{ opt.label }}</span>
            <svg
              v-if="opt.value === modelValue"
              class="ts-option-check"
              width="12" height="12" viewBox="0 0 12 12" fill="none"
            >
              <path d="M2 6 L5 9 L10 3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </li>
        </ul>
      </transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, type Directive } from 'vue'

type Option = { value: string; label: string }

const props = defineProps<{
  modelValue: string
  options: Option[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', v: string): void
}>()

const open = ref(false)
const triggerRef = ref<HTMLButtonElement | null>(null)
const panelRef = ref<HTMLUListElement | null>(null)
const panelStyle = ref<Record<string, string>>({})

const currentLabel = computed(() => {
  const match = props.options.find((o) => o.value === props.modelValue)
  return match ? match.label : props.modelValue
})

function recalcPosition() {
  if (!triggerRef.value) return
  const rect = triggerRef.value.getBoundingClientRect()
  panelStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 6}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
  }
}

async function toggle() {
  if (open.value) {
    close()
    return
  }
  recalcPosition()
  open.value = true
  await nextTick()
  // Re-measure after panel rendered (in case fonts/scrollbar shift sizes)
  recalcPosition()
}

function close() {
  open.value = false
}

function select(v: string) {
  if (v !== props.modelValue) emit('update:modelValue', v)
  close()
}

// Close on scroll / resize — fixed position panel wouldn't follow trigger
function onScrollOrResize() {
  if (open.value) close()
}
window.addEventListener('scroll', onScrollOrResize, true)
window.addEventListener('resize', onScrollOrResize)

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScrollOrResize, true)
  window.removeEventListener('resize', onScrollOrResize)
})

// Click-outside directive
const vClickOutside: Directive<HTMLElement, () => void> = {
  mounted(el, binding) {
    const handler = (e: MouseEvent) => {
      const target = e.target as Node
      if (el.contains(target)) return
      // panel lives in body via Teleport; treat clicks inside it as inside
      if (panelRef.value && panelRef.value.contains(target)) return
      binding.value()
    }
    ;(el as HTMLElement & { __co?: (e: MouseEvent) => void }).__co = handler
    document.addEventListener('mousedown', handler)
  },
  unmounted(el) {
    const handler = (el as HTMLElement & { __co?: (e: MouseEvent) => void }).__co
    if (handler) document.removeEventListener('mousedown', handler)
  },
}
</script>

<style scoped>
.ts-select {
  position: relative;
  width: 100%;
}

/* ── Trigger (looks like .input) ── */
.ts-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--input-border, rgba(255,255,255,0.08));
  background: var(--input-bg, rgba(4,8,22,0.55));
  color: var(--text-primary, rgba(255,255,255,0.95));
  font-family: inherit;
  font-size: 0.875rem;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, background 0.2s, box-shadow 0.15s;
}

.ts-trigger:hover {
  border-color: var(--input-focus-border, rgba(245,158,11,0.50));
}

.ts-trigger[aria-expanded='true'] {
  border-color: var(--input-focus-border, rgba(245,158,11,0.50));
  box-shadow: var(--input-focus-shadow, 0 0 0 3px rgba(245,158,11,0.10));
}

.ts-current {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ts-chev {
  flex-shrink: 0;
  color: var(--arc-300, #fbbf24);
  transition: transform 0.22s ease;
}
.ts-chev.is-open {
  transform: rotate(180deg);
}
</style>

<style>
/* ───────── Global (un-scoped) for teleported panel ───────── */
.ts-panel {
  margin: 0;
  padding: 6px;
  list-style: none;
  border-radius: 12px;
  background: var(--glass-bg-light, rgba(20,16,8,0.94));
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid var(--border-glass, rgba(245,158,11,0.18));
  box-shadow:
    0 16px 44px rgba(0,0,0,0.55),
    inset 0 1px 0 rgba(255,255,255,0.08);
  z-index: 9999;
  max-height: 280px;
  overflow-y: auto;
  font-family: Inter, 'SF Pro Display', system-ui, sans-serif;
  font-size: 0.875rem;
}

.ts-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  color: var(--text-secondary, rgba(255,255,255,0.72));
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.ts-option:hover {
  background: rgba(245, 158, 11, 0.08);
  color: var(--text-primary, rgba(255,255,255,0.95));
}

.ts-option.is-active {
  background: rgba(245, 158, 11, 0.14);
  color: var(--arc-300, #fbbf24);
  font-weight: 600;
}

.ts-option-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ts-option-check {
  flex-shrink: 0;
  color: var(--arc-300, #fbbf24);
}

/* Pearl theme — light glass panel */
:root[data-theme="pearl"] .ts-panel {
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(214, 179, 90, 0.30);
  box-shadow:
    0 18px 48px rgba(120, 90, 50, 0.16),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

:root[data-theme="pearl"] .ts-option {
  color: rgba(50, 44, 34, 0.78);
}

:root[data-theme="pearl"] .ts-option:hover {
  background: rgba(214, 179, 90, 0.10);
  color: #2E2A22;
}

:root[data-theme="pearl"] .ts-option.is-active {
  background: rgba(214, 179, 90, 0.18);
  color: #8b6722;
}

:root[data-theme="pearl"] .ts-option-check {
  color: #b8843e;
}

/* Fade animation */
.ts-fade-enter-active,
.ts-fade-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.ts-fade-enter-from,
.ts-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

<style scoped>
/* Pearl theme — scoped overrides for trigger */
:global(:root[data-theme="pearl"]) .ts-trigger {
  background: rgba(255, 255, 255, 0.92);
  border-color: rgba(214, 179, 90, 0.26);
  color: #2E2A22;
}

:global(:root[data-theme="pearl"]) .ts-chev {
  color: #b8843e;
}
</style>
