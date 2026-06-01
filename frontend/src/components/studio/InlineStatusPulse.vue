<template>
  <span class="inline-status" :class="`inline-status--${variant}`">
    <span
      v-if="variant !== 'idle'"
      class="inline-status__dot"
      aria-hidden="true"
    ></span>
    <span v-if="text" class="inline-status__text">{{ text }}</span>
    <span
      v-if="showDots && variant !== 'idle'"
      class="inline-status__dots"
      aria-hidden="true"
    >
      <span></span><span></span><span></span>
    </span>
  </span>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'running' | 'cancelling' | 'idle'
    text?: string
    showDots?: boolean
  }>(),
  {
    variant: 'running',
    text: '',
    showDots: true,
  },
)
</script>

<style scoped>
.inline-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font: inherit;
  min-width: 0;
}

.inline-status__dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: currentColor;
  animation: inline-status-pulse 1.6s ease-in-out infinite;
  box-shadow: 0 0 6px color-mix(in srgb, currentColor 45%, transparent);
}

.inline-status__text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text-secondary);
  letter-spacing: 0.01em;
}

.inline-status__dots {
  flex-shrink: 0;
  display: inline-flex;
  gap: 2px;
  align-items: center;
}
.inline-status__dots span {
  display: inline-block;
  width: 3px;
  height: 3px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.22;
  animation: inline-status-dots 1.6s ease-in-out infinite;
}
.inline-status__dots span:nth-child(1) { animation-delay: 0s;    }
.inline-status__dots span:nth-child(2) { animation-delay: 0.3s;  }
.inline-status__dots span:nth-child(3) { animation-delay: 0.6s;  }

/* ── Variants ────────────────────────────────────────────────
   currentColor drives both the leading dot and the trailing
   ellipsis, so changing the wrapper's color is enough to retint
   the entire badge. ─────────────────────────────────────────── */
.inline-status--running   { color: var(--arc-300); }
.inline-status--cancelling { color: rgba(252, 165, 165, 0.82); }
.inline-status--idle       { color: var(--text-muted); }

.inline-status--cancelling .inline-status__text {
  color: rgba(252, 165, 165, 0.92);
}
.inline-status--running .inline-status__text {
  /* Stay readable on dark glass — text stays in the secondary copy
     palette, while only the dot + ellipsis carry the accent hue. */
  color: var(--text-secondary);
}

@keyframes inline-status-pulse {
  0%, 100% { opacity: 0.50; transform: scale(0.85); }
  50%      { opacity: 1;    transform: scale(1.15); }
}
@keyframes inline-status-dots {
  0%, 60%, 100% { opacity: 0.22; }
  20%, 40%      { opacity: 1;    }
}

@media (prefers-reduced-motion: reduce) {
  .inline-status__dot,
  .inline-status__dots span {
    animation: none;
  }
}
</style>
