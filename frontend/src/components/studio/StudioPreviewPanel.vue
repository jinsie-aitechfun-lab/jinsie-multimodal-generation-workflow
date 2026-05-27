<template>
  <div class="preview-panel glass-card animate-fade-in">
    <div class="preview-panel__header">
      <span class="preview-panel__icon" aria-hidden="true">▶</span>
      <span class="preview-panel__title">视频预览</span>
      <span v-if="renderInFlight" class="badge badge-arc" style="font-size:0.6rem;">渲染中</span>
      <span v-else-if="finalVideoUrl" class="badge badge-ok" style="font-size:0.6rem;">已完成</span>
    </div>

    <div class="preview-panel__body">
      <!-- Current video -->
      <div v-if="finalVideoUrl" class="preview-video-wrap">
        <video
          :src="finalVideoUrl"
          class="preview-video"
          controls
          playsinline
          :key="finalVideoUrl"
        />
      </div>

      <!-- Render-in-flight shimmer placeholder -->
      <div v-else-if="renderInFlight" class="preview-render-state">
        <div class="preview-video-shell preview-video-shell--loading">
          <div class="preview-render-icon">🎬</div>
          <div class="preview-render-label">视频合成中…</div>
          <div class="progress-track" style="width:200px;margin-top:12px;">
            <div class="progress-fill preview-render-bar" />
          </div>
        </div>
      </div>

      <!-- Workflow processing -->
      <div v-else-if="isProcessing" class="preview-processing-state">
        <div class="preview-video-shell preview-video-shell--processing">
          <div class="preview-processing-steps">
            <div
              v-for="step in progressSteps"
              :key="step.id"
              :class="['preview-step', `preview-step--${step.state}`]"
            >
              <span class="preview-step__dot" />
              <span class="preview-step__label">{{ step.label }}</span>
              <span v-if="step.state === 'active'" class="preview-step__pulse" />
            </div>
          </div>
          <div v-if="statusLabel" class="preview-status-label">{{ statusLabel }}</div>
        </div>
      </div>

      <!-- Recent history list -->
      <div v-else-if="(recentVideoUrls?.length ?? 0) > 0" class="preview-recent">
        <div class="preview-recent__heading">最近生成</div>
        <div class="preview-recent__list">
          <video
            v-for="(url, idx) in (recentVideoUrls ?? [])"
            :key="`${url}-${idx}`"
            class="preview-recent__item"
            :src="url"
            controls
            playsinline
          />
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="preview-empty">
        <div class="preview-empty__shell">
          <div class="preview-empty__icon">▶</div>
          <div class="preview-empty__title">视频将在这里播放</div>
          <div class="preview-empty__desc">创作完成后自动渲染并展示</div>
          <div v-if="(exampleTopics?.length ?? 0) > 0" class="preview-empty__topics">
            <span class="preview-empty__topics-label">快速开始：</span>
            <button
              v-for="topic in (exampleTopics ?? [])"
              :key="topic"
              class="badge badge-arc preview-empty__topic-btn"
              @click="$emit('set-topic', topic)"
            >{{ topic }}</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  finalVideoUrl?: string
  recentVideoUrls?: string[]
  renderInFlight?: boolean
  isProcessing?: boolean
  statusLabel?: string
  completedSteps?: number
  totalSteps?: number
  exampleTopics?: string[]
}>()

defineEmits<{
  (e: 'set-topic', topic: string): void
}>()

const STEP_DEFS = [
  { id: 'story', label: '故事生成' },
  { id: 'storyboard', label: '分镜设计' },
  { id: 'images', label: '画面生成' },
  { id: 'voice', label: '配音生成' },
  { id: 'subtitles', label: '字幕生成' },
  { id: 'video', label: '视频合成' },
]

const progressSteps = computed(() => {
  const completed = props.completedSteps ?? 0
  const total = props.totalSteps ?? STEP_DEFS.length
  const ratio = total > 0 ? completed / total : 0
  const activeIdx = Math.min(Math.floor(ratio * STEP_DEFS.length), STEP_DEFS.length - 1)
  return STEP_DEFS.map((step, idx) => ({
    ...step,
    state: idx < activeIdx ? 'done' : idx === activeIdx ? 'active' : 'pending',
  }))
})
</script>

<style scoped>
.preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.preview-panel__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem 0.75rem;
  border-bottom: 1px solid rgba(0,181,240,0.10);
  flex-shrink: 0;
}
.preview-panel__icon {
  color: var(--arc-400);
  font-size: 0.75rem;
  line-height: 1;
}
.preview-panel__title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
  letter-spacing: 0.01em;
}

.preview-panel__body {
  flex: 1;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
}

/* Video player */
.preview-video-wrap {
  width: 100%;
  border-radius: 0.75rem;
  overflow: hidden;
  background: #000;
  box-shadow: 0 0 24px rgba(0,181,240,0.15);
}
.preview-video {
  width: 100%;
  display: block;
  max-height: 400px;
  object-fit: contain;
  background: #000;
}

/* Placeholder shell */
.preview-video-shell {
  aspect-ratio: 16 / 9;
  border-radius: 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  border: 1px dashed rgba(0,181,240,0.25);
  background: rgba(0,181,240,0.03);
}

.preview-video-shell--loading {
  border-color: rgba(139,92,246,0.30);
  background: rgba(139,92,246,0.05);
}

.preview-video-shell--processing {
  border-color: rgba(0,181,240,0.20);
  background: rgba(0,181,240,0.04);
  padding: 1.5rem;
  aspect-ratio: unset;
  min-height: 220px;
}

/* Render in flight */
.preview-render-icon {
  font-size: 2rem;
  filter: drop-shadow(0 0 8px rgba(139,92,246,0.6));
}
.preview-render-label {
  font-size: 0.875rem;
  color: var(--prism-400);
  font-weight: 600;
}
.preview-render-bar {
  width: 40% !important;
  animation: shimmer 1.4s ease-in-out infinite;
}

/* Processing steps */
.preview-processing-steps {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}
.preview-step {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.8125rem;
}
.preview-step__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: rgba(255,255,255,0.15);
}
.preview-step--done .preview-step__dot {
  background: #34d399;
  box-shadow: 0 0 6px rgba(52,211,153,0.6);
}
.preview-step--active .preview-step__dot {
  background: var(--arc-400);
  box-shadow: 0 0 8px rgba(0,181,240,0.7);
}
.preview-step--done .preview-step__label { color: var(--text-secondary); }
.preview-step--active .preview-step__label { color: var(--arc-300); font-weight: 600; }
.preview-step--pending .preview-step__label { color: var(--text-muted); }
.preview-step__pulse {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--arc-400);
  animation: pulseGlow 1s ease-in-out infinite;
  margin-left: auto;
}
.preview-status-label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  margin-top: 0.75rem;
  text-align: center;
  line-height: 1.5;
}

/* Recent videos */
.preview-recent__heading {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 0.75rem;
}
.preview-recent__list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.preview-recent__item {
  width: 100%;
  border-radius: 0.75rem;
  background: #000;
  display: block;
}

/* Empty state */
.preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-empty__shell {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.625rem;
  padding: 2rem 1rem;
}
.preview-empty__icon {
  font-size: 2.5rem;
  opacity: 0.2;
  margin-bottom: 0.25rem;
}
.preview-empty__title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-secondary);
}
.preview-empty__desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
.preview-empty__topics {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  margin-top: 0.5rem;
}
.preview-empty__topics-label {
  font-size: 0.75rem;
  color: var(--text-muted);
}
.preview-empty__topic-btn {
  cursor: pointer;
  border: none;
  background: none;
  font-family: inherit;
}
.preview-empty__topic-btn:hover {
  filter: brightness(1.2);
}
</style>
