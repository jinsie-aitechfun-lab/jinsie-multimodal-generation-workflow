<template>
  <div class="create-panel glass-card animate-fade-in">
    <div class="create-panel__header">
      <span class="create-panel__icon" aria-hidden="true">✦</span>
      <span class="create-panel__title">创作故事</span>
      <span v-if="loading" class="badge badge-arc" style="font-size:0.6rem;">生成中</span>
    </div>
    <div class="create-panel__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean
}>()
</script>

<style scoped>
.create-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.create-panel__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem 0.75rem;
  border-bottom: 1px solid rgba(0,181,240,0.10);
  flex-shrink: 0;
}
.create-panel__icon {
  color: var(--arc-400);
  font-size: 0.8rem;
  line-height: 1;
}
.create-panel__title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
  letter-spacing: 0.01em;
}
.create-panel__body {
  padding: 1.25rem;
  flex: 1;
  overflow-y: auto;
}
</style>
