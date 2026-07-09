<template>
  <div v-if="visible" class="studio-progress" :class="{ 'studio-progress--complete': percent >= 100 }">
    <div class="studio-progress__bar">
      <div class="progress-track" style="flex:1;">
        <div class="progress-fill" :style="{ width: `${Math.min(100, percent)}%` }" />
      </div>
      <span class="studio-progress__pct">{{ Math.round(percent) }}%</span>
      <!-- Global cancel entry — visible on every tab whenever a workflow
           run is in flight. Reuses cancelWorkflow via @cancel emit; pure
           UI, no new state. -->
      <button
        v-if="cancellable"
        type="button"
        class="studio-progress__cancel"
        :disabled="cancelRequested"
        @click="$emit('cancel')"
      >
        {{ cancelRequested ? '正在取消…' : '取消' }}
      </button>
    </div>
    <InlineStatusPulse
      v-if="label"
      class="studio-progress__label"
      :variant="cancelRequested ? 'cancelling' : 'running'"
      :text="label"
    />
  </div>
</template>

<script setup lang="ts">
import InlineStatusPulse from './InlineStatusPulse.vue'

defineProps<{
  percent: number
  label?: string
  visible?: boolean
  cancellable?: boolean
  cancelRequested?: boolean
}>()

defineEmits<{
  (e: 'cancel'): void
}>()
</script>

<style scoped>
.studio-progress {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  /* Glass strip styling (was on parent .s-progress wrapper, moved here
     so it only renders when v-if="visible" is true) */
  padding: 0.45rem 1.5rem 0.35rem 1.25rem;
  background: var(--sidebar-bg, rgba(9,7,3,0.82));
  backdrop-filter: blur(24px) saturate(150%);
  -webkit-backdrop-filter: blur(24px) saturate(150%);
  border-bottom: 1px solid var(--sidebar-border, rgba(245,158,11,0.10));
  animation: fadeIn 0.25s ease-out;
}

/* Pearl override — soft white-blue glass */
:global(:root[data-theme="pearl"]) .studio-progress {
  background: linear-gradient(90deg, rgba(255,255,255,0.42), rgba(238,247,255,0.30));
  border-bottom-color: rgba(214, 179, 90, 0.10);
  box-shadow: 0 8px 22px rgba(90, 110, 130, 0.025);
  padding-left: 0.5rem;
}
.studio-progress__bar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.studio-progress__pct {
  font-size: 0.6875rem;
  font-weight: 700;
  color: var(--arc-300);
  min-width: 2.5rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.studio-progress__label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  letter-spacing: 0.03em;
}

/* Lightweight cancel link on the right of the global progress bar. */
.studio-progress__cancel {
  flex-shrink: 0;
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--text-muted) 55%, transparent);
  background: transparent;
  color: var(--text-secondary);
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-family: inherit;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.studio-progress__cancel:hover:not(:disabled) {
  border-color: rgba(248, 113, 133, 0.55);
  color: #fca5a5;
  background: rgba(248, 113, 133, 0.06);
}
.studio-progress__cancel:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}
.studio-progress--complete .progress-fill {
  background: linear-gradient(90deg, #34d399 0%, var(--arc-400) 100%);
  box-shadow: 0 0 8px rgba(52,211,153,0.60);
}

:global(:root[data-theme="pearl"]) .studio-progress__pct {
  color: rgba(138, 112, 64, 0.72);
}

:global(:root[data-theme="pearl"]) .studio-progress__label {
  color: rgba(111, 106, 95, 0.68);
}

:global(:root[data-theme="pearl"]) .studio-progress--complete .progress-fill {
  background: linear-gradient(
    90deg,
    rgba(196, 216, 228, 0.58) 0%,
    rgba(218, 188, 124, 0.54) 100%
  );
  box-shadow: 0 0 6px rgba(188, 215, 232, 0.14);
}

@media (max-width: 768px) {
  .studio-progress {
    padding: 8px 12px 9px;
  }

  .studio-progress__bar {
    flex-wrap: wrap;
    gap: 8px;
  }

  .studio-progress__pct {
    font-size: 0.6875rem;
  }

  .studio-progress__cancel {
    min-height: 30px;
    padding: 4px 10px;
  }

  .studio-progress__label {
    font-size: 0.75rem;
    line-height: 1.45;
  }
}
</style>
