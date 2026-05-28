<template>
  <div class="diagnostics-panel glass-card animate-fade-in">
    <div class="diagnostics-panel__header">
      <span class="diagnostics-panel__icon" aria-hidden="true">⚠</span>
      <span class="diagnostics-panel__title">Developer Diagnostics</span>
      <span class="badge badge-warn">DEV ONLY</span>
    </div>

    <div class="diagnostics-panel__body">
      <!-- Workflow meta -->
      <div v-if="workflowId || runId || sessionId" class="diag-section">
        <p class="diag-section__label">Workflow IDs</p>
        <div class="diag-fields">
          <div v-if="workflowId" class="diag-field">
            <span class="diag-field__key">workflow_id</span>
            <code class="diag-field__val">{{ workflowId }}</code>
          </div>
          <div v-if="runId" class="diag-field">
            <span class="diag-field__key">run_id</span>
            <code class="diag-field__val">{{ runId }}</code>
          </div>
          <div v-if="sessionId" class="diag-field">
            <span class="diag-field__key">session_id</span>
            <code class="diag-field__val">{{ sessionId }}</code>
          </div>
        </div>
      </div>

      <!-- Generation source -->
      <div v-if="generationSource" class="diag-section">
        <p class="diag-section__label">Story Generation</p>
        <div class="diag-fields">
          <div class="diag-field">
            <span class="diag-field__key">generation_source</span>
            <span :class="['badge', generationSourceBadge]">{{ generationSource }}</span>
          </div>
          <div v-if="fallbackReason" class="diag-field">
            <span class="diag-field__key">fallback_reason</span>
            <code class="diag-field__val diag-field__val--warn">{{ fallbackReason }}</code>
          </div>
        </div>
      </div>

      <!-- Raw JSON slot -->
      <div v-if="$slots.json" class="diag-section">
        <p class="diag-section__label">Raw Outputs</p>
        <div class="diag-json">
          <slot name="json" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  workflowId?: string
  runId?: string
  sessionId?: string
  generationSource?: string
  fallbackReason?: string
}>()

const generationSourceBadge = computed(() => {
  const s = props.generationSource || ''
  if (s === 'llm' || s === 'llm_sanitized') return 'badge-ok'
  if (s.startsWith('llm_retried') || s === 'llm_repaired') return 'badge-arc'
  if (s === 'llm_degraded') return 'badge-warn'
  if (s === 'template_fallback') return 'badge-err'
  return 'badge-prism'
})
</script>

<style scoped>
.diagnostics-panel {
  border-color: rgba(251,191,36,0.20) !important;
  background: rgba(6,4,0,0.72) !important;
}
.diagnostics-panel__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid rgba(251,191,36,0.12);
}
.diagnostics-panel__icon { color: #fbbf24; font-size: 0.875rem; }
.diagnostics-panel__title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: #fbbf24;
  flex: 1;
}
.diagnostics-panel__body { padding: 0.75rem; display: flex; flex-direction: column; gap: 0.75rem; }

.diag-section__label {
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin: 0 0 0.375rem;
}
.diag-fields { display: flex; flex-direction: column; gap: 0.25rem; }
.diag-field {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
}
.diag-field__key {
  color: var(--text-muted);
  min-width: 8rem;
  font-family: var(--font-mono, monospace);
}
.diag-field__val {
  font-family: var(--font-mono, monospace);
  color: var(--text-secondary);
  background: rgba(0,0,0,0.30);
  padding: 0.1rem 0.4rem;
  border-radius: 0.25rem;
  font-size: 0.7rem;
  word-break: break-all;
}
.diag-field__val--warn { color: #fbbf24; }

.diag-json {
  background: rgba(0,0,0,0.40);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 0.5rem;
  padding: 0.625rem;
  font-family: monospace;
  font-size: 0.6875rem;
  color: var(--text-secondary);
  max-height: 300px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}

.animate-fade-in { animation: fadeIn 0.25s ease-out; }
</style>
