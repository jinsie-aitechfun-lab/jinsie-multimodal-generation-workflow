<template>
  <div v-if="visible" class="studio-progress" :class="{ 'studio-progress--complete': percent >= 100 }">
    <div class="studio-progress__bar">
      <div class="progress-track" style="flex:1;">
        <div class="progress-fill" :style="{ width: `${Math.min(100, percent)}%` }" />
      </div>
      <span class="studio-progress__pct">{{ Math.round(percent) }}%</span>
    </div>
    <span v-if="label" class="studio-progress__label">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  percent: number
  label?: string
  visible?: boolean
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
</style>
