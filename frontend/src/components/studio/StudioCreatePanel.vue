<template>
  <div class="create-panel glass-card animate-fade-in">
    <div class="create-panel__header">
      <span class="create-panel__icon" aria-hidden="true">✦</span>
      <span class="create-panel__title">创作故事</span>
      <span
        v-if="loading"
        class="badge badge-arc"
        style="font-size:0.6rem;"
      >{{ cancelRequested ? '取消中' : '生成中' }}</span>
    </div>
    <div class="create-panel__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  loading?: boolean
  cancelRequested?: boolean
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
  border-bottom: 1px solid rgba(245,158,11,0.10);
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

@media (max-width: 768px) {
  .create-panel {
    height: auto;
    min-height: 0;
  }

  .create-panel__header {
    padding: 0.75rem 1rem 0.625rem;
  }

  .create-panel__body {
    padding: 1rem;
    overflow: visible;
  }
}

@media (max-width: 420px) {
  .create-panel__body {
    padding: 0.875rem;
  }
}
</style>

<style>
:root[data-theme="pearl"] .create-panel__header {
  border-bottom-color: rgba(214,179,90,0.14);
  background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0));
}

:root[data-theme="pearl"] .create-panel__icon {
  color: #c89a55;
  filter: drop-shadow(0 0 8px rgba(214,179,90,0.18));
}

@media (max-width: 768px) {
  :root[data-theme="pearl"] .create-panel {
    background:
      linear-gradient(145deg, rgba(255,255,255,0.76), rgba(250,247,238,0.58));
    border-color: rgba(200,154,85,0.18);
    box-shadow:
      0 14px 34px rgba(100,90,60,0.07),
      inset 0 1px 0 rgba(255,255,255,0.78);
  }
}
</style>
