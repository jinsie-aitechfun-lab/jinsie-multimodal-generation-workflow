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
  padding: 0.375rem 0 0.125rem;
  animation: fadeIn 0.25s ease-out;
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
</style>
