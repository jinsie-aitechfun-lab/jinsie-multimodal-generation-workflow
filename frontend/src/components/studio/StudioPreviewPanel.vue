<template>
  <div class="preview-panel glass-card animate-fade-in">
    <!-- ── Header ── -->
    <div class="pp-header">
      <span class="pp-header-icon" aria-hidden="true">▶</span>
      <span class="pp-header-title">视频预览</span>
      <span v-if="renderInFlight"   class="badge badge-arc" style="font-size:0.6rem;">渲染中</span>
      <span v-else-if="displayUrl" class="badge badge-ok"  style="font-size:0.6rem;">已完成</span>
    </div>

    <!-- ── Main player area ── -->
    <div class="pp-body">

      <!-- Current video -->
      <div v-if="displayUrl" class="pp-main">
        <div class="pp-player-wrap">
          <video
            :src="displayUrl"
            class="pp-video"
            controls
            playsinline
            :key="displayUrl"
          />
        </div>
        <!-- Label under the player -->
        <div class="pp-current-label">
          <span v-if="displayUrl === props.finalVideoUrl" class="pp-current-tag">当前生成</span>
          <span v-else class="pp-current-tag pp-current-tag--hist">历史回放</span>
          <span class="pp-current-url">{{ shortUrl(displayUrl) }}</span>
        </div>
      </div>

      <!-- Render in flight -->
      <div v-else-if="renderInFlight" class="pp-state pp-state--render">
        <div class="pp-state-icon">
          <svg class="pp-state-svg pp-spin" viewBox="0 0 60 60" fill="none">
            <circle cx="30" cy="30" r="24" stroke="currentColor" stroke-opacity="0.15" stroke-width="4"/>
            <path d="M30 6 A24 24 0 0 1 54 30" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="pp-state-title">视频合成中…</div>
        <div class="pp-state-desc">画面、音频与字幕正在拼接渲染</div>
      </div>

      <!-- Workflow processing -->
      <div v-else-if="isProcessing" class="pp-state pp-state--proc">
        <div class="pp-steps">
          <div
            v-for="step in progressSteps"
            :key="step.id"
            :class="['pp-step', `pp-step--${step.state}`]"
          >
            <span class="pp-step-dot"/>
            <span class="pp-step-label">{{ step.label }}</span>
            <span v-if="step.state === 'active'" class="pp-step-pulse"/>
          </div>
        </div>
        <div v-if="statusLabel" class="pp-status-label">{{ statusLabel }}</div>
      </div>

      <!-- Has history but nothing selected — prompt user to click a thumbnail -->
      <div v-else-if="allVideoUrls.length > 0" class="pp-select-hint">
        <div class="pp-hint-icon">
          <svg viewBox="0 0 52 52" fill="none" width="44" height="44">
            <rect x="4" y="10" width="44" height="32" rx="6" stroke="currentColor" stroke-width="1.8" stroke-opacity="0.40"/>
            <path d="M20 20 L34 26 L20 32 Z" fill="currentColor" fill-opacity="0.35"/>
          </svg>
        </div>
        <div class="pp-hint-title">点击下方缩略图播放</div>
        <div class="pp-hint-desc">共 {{ allVideoUrls.length }} 个历史视频可查看</div>
      </div>

      <!-- Fully empty — no videos at all -->
      <div v-else class="pp-empty">
        <div class="pp-empty-inner">
          <div class="pp-empty-icon" aria-hidden="true">
            <svg viewBox="0 0 64 64" fill="none" width="56" height="56">
              <rect x="6" y="14" width="52" height="36" rx="7" stroke="currentColor" stroke-width="1.8" stroke-opacity="0.28"/>
              <path d="M26 24 L42 32 L26 40 Z" fill="currentColor" fill-opacity="0.20"/>
              <circle cx="16" cy="44" r="2" fill="currentColor" fill-opacity="0.14"/>
              <circle cx="48" cy="20" r="1.5" fill="currentColor" fill-opacity="0.14"/>
            </svg>
          </div>
          <div class="pp-empty-title">视频将在这里播放</div>
          <div class="pp-empty-desc">创作完成后自动渲染并展示</div>
          <div v-if="(exampleTopics?.length ?? 0) > 0" class="pp-empty-topics">
            <div class="pp-empty-topics-label">快速开始：</div>
            <div class="pp-empty-topics-row">
              <button
                v-for="topic in (exampleTopics ?? [])"
                :key="topic"
                class="pp-topic-btn"
                @click="$emit('set-topic', topic)"
              >{{ topic }}</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ── History strip (always shown if there are videos) ── -->
      <div v-if="allVideoUrls.length > 0" class="pp-history">
        <div class="pp-history-header">
          <span class="pp-history-title">历史视频</span>
          <span class="pp-history-count">{{ allVideoUrls.length }} 个</span>
        </div>
        <div class="pp-history-list" ref="historyListRef">
          <button
            v-for="(url, idx) in allVideoUrls"
            :key="url"
            :class="['pp-thumb', { 'pp-thumb--active': url === displayUrl }]"
            @click="selectVideo(url)"
            :title="`视频 ${idx + 1}`"
          >
            <video
              class="pp-thumb-video"
              :src="url"
              preload="metadata"
              :muted="true"
            />
            <div class="pp-thumb-overlay">
              <span class="pp-thumb-play">▶</span>
            </div>
            <div class="pp-thumb-index">{{ idx + 1 }}</div>
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

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

// ── All unique video URLs (current first, then history) ──
const allVideoUrls = computed(() => {
  const seen = new Set<string>()
  const result: string[] = []
  const push = (u?: string) => {
    if (u && !seen.has(u)) { seen.add(u); result.push(u) }
  }
  push(props.finalVideoUrl)
  for (const u of props.recentVideoUrls ?? []) push(u)
  return result
})

// ── Selected video for main player ──
// Only auto-selects when a new finalVideoUrl arrives (user-triggered generation).
// History videos are NEVER auto-played — user must explicitly click a thumbnail.
const selectedUrl = ref<string | null>(null)

watch(() => props.finalVideoUrl, (url) => {
  if (url) selectedUrl.value = url
}, { immediate: true })

const displayUrl = computed(() => {
  if (selectedUrl.value && allVideoUrls.value.includes(selectedUrl.value)) {
    return selectedUrl.value
  }
  // Only auto-show the current generation result, not historical ones
  return props.finalVideoUrl ?? null
})

function selectVideo(url: string) {
  selectedUrl.value = url
}

function shortUrl(url: string): string {
  try {
    const u = new URL(url)
    const parts = u.pathname.split('/')
    return parts[parts.length - 1] || url
  } catch {
    return url.split('/').pop() || url
  }
}

// ── Processing steps ──
const STEP_DEFS = [
  { id: 'story',      label: '故事生成' },
  { id: 'storyboard', label: '分镜设计' },
  { id: 'images',     label: '画面生成' },
  { id: 'voice',      label: '配音生成' },
  { id: 'subtitles',  label: '字幕生成' },
  { id: 'video',      label: '视频合成' },
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

const historyListRef = ref<HTMLElement | null>(null)
</script>

<style scoped>
/* ── Panel shell ── */
.preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* ── Header ── */
.pp-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem 0.75rem;
  border-bottom: 1px solid rgba(245,158,11,0.10);
  flex-shrink: 0;
}
.pp-header-icon  { color: var(--arc-400); font-size: 0.75rem; }
.pp-header-title { font-size: 0.875rem; font-weight: 700; color: var(--text-primary); flex: 1; }

/* ── Body ── */
.pp-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
}

/* ── Main player ── */
.pp-main {
  flex-shrink: 0;
}

.pp-player-wrap {
  width: 100%;
  background: #000;
}

.pp-video {
  width: 100%;
  display: block;
  max-height: 360px;
  object-fit: contain;
  background: #000;
}

.pp-current-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1.25rem;
  border-bottom: 1px solid rgba(245,158,11,0.07);
}

.pp-current-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.05em;
  background: rgba(245,158,11,0.14);
  color: var(--arc-300);
  border: 1px solid rgba(245,158,11,0.25);
  white-space: nowrap;
}

.pp-current-tag--hist {
  background: rgba(255,255,255,0.05);
  color: var(--text-muted);
  border-color: rgba(255,255,255,0.10);
}

.pp-current-url {
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── State placeholders ── */
.pp-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 2rem 1.5rem;
  text-align: center;
  min-height: 220px;
}

.pp-state--render {
  background: rgba(245,158,11,0.03);
  border-bottom: 1px solid rgba(245,158,11,0.07);
}

.pp-state-icon { line-height: 0; }

.pp-state-svg {
  width: 48px; height: 48px;
  color: var(--arc-300);
  filter: drop-shadow(0 0 10px rgba(245,158,11,0.45));
}

.pp-spin {
  animation: ppSpin 1.8s linear infinite;
  transform-origin: 50% 50%;
}

@keyframes ppSpin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.pp-state-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
}

.pp-state-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
  line-height: 1.6;
}

/* Processing steps */
.pp-state--proc {
  align-items: flex-start;
  background: rgba(245,158,11,0.03);
}

.pp-steps {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.pp-step {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  font-size: 0.8125rem;
}

.pp-step-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: rgba(255,255,255,0.15);
}

.pp-step--done .pp-step-dot {
  background: var(--arc-400);
  box-shadow: 0 0 6px rgba(245,158,11,0.60);
}

.pp-step--active .pp-step-dot {
  background: var(--arc-300);
  box-shadow: 0 0 8px rgba(245,158,11,0.70);
  animation: pulseGlow 1s ease-in-out infinite;
}

.pp-step--done   .pp-step-label { color: var(--text-secondary); }
.pp-step--active .pp-step-label { color: var(--arc-300); font-weight: 600; }
.pp-step--pending .pp-step-label { color: var(--text-muted); }

.pp-step-pulse {
  display: inline-block;
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--arc-400);
  animation: pulseGlow 1s ease-in-out infinite;
  margin-left: auto;
}

.pp-status-label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-align: center;
  line-height: 1.5;
  margin-top: 0.5rem;
  width: 100%;
}

/* ── "Select from history" hint ── */
.pp-select-hint {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.625rem;
  padding: 2rem 1.5rem;
  text-align: center;
  min-height: 180px;
}

.pp-hint-icon {
  color: var(--arc-300);
  opacity: 0.45;
  margin-bottom: 0.25rem;
}

.pp-hint-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.pp-hint-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

/* ── Fully empty state ── */
.pp-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.25rem;
  min-height: 240px;
}

.pp-empty-inner {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.625rem;
  max-width: 320px;
}

.pp-empty-icon {
  color: var(--arc-300);
  opacity: 0.25;
  margin-bottom: 0.375rem;
}

.pp-empty-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-secondary);
}

.pp-empty-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.pp-empty-topics {
  margin-top: 1.25rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
}

.pp-empty-topics-label {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.pp-empty-topics-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.pp-topic-btn {
  cursor: pointer;
  border: 1px solid rgba(245,158,11,0.20);
  background: rgba(245,158,11,0.06);
  color: var(--arc-300);
  font-family: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s;
  width: 100%;
}

.pp-topic-btn:hover {
  border-color: rgba(245,158,11,0.45);
  background: rgba(245,158,11,0.12);
  color: var(--arc-200);
}

/* ── History strip ── */
.pp-history {
  flex-shrink: 0;
  padding: 0.875rem 1.25rem 1rem;
  border-top: 1px solid rgba(245,158,11,0.08);
  background: rgba(0,0,0,0.15);
}

.pp-history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.625rem;
}

.pp-history-title {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.pp-history-count {
  font-size: 0.6875rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.pp-history-list {
  display: flex;
  gap: 0.625rem;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(245,158,11,0.20) transparent;
}

.pp-history-list::-webkit-scrollbar        { height: 3px; }
.pp-history-list::-webkit-scrollbar-track  { background: transparent; }
.pp-history-list::-webkit-scrollbar-thumb  { background: rgba(245,158,11,0.25); border-radius: 2px; }

/* Thumbnail button */
.pp-thumb {
  position: relative;
  flex-shrink: 0;
  width: 140px;
  height: 79px; /* 16:9 */
  border-radius: 8px;
  overflow: hidden;
  border: 1.5px solid rgba(255,255,255,0.08);
  background: #000;
  cursor: pointer;
  padding: 0;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
}

.pp-thumb:hover {
  border-color: rgba(245,158,11,0.40);
  box-shadow: 0 0 12px rgba(245,158,11,0.20);
  transform: translateY(-2px);
}

.pp-thumb--active {
  border-color: var(--arc-400) !important;
  box-shadow: 0 0 16px rgba(245,158,11,0.35) !important;
}

.pp-thumb-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.pp-thumb-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.30);
  opacity: 0;
  transition: opacity 0.18s;
}

.pp-thumb:hover .pp-thumb-overlay { opacity: 1; }
.pp-thumb--active .pp-thumb-overlay {
  opacity: 1;
  background: rgba(245,158,11,0.10);
}

.pp-thumb-play {
  font-size: 18px;
  color: #fff;
  filter: drop-shadow(0 1px 4px rgba(0,0,0,0.6));
}

.pp-thumb--active .pp-thumb-play { color: var(--arc-300); }

.pp-thumb-index {
  position: absolute;
  bottom: 4px;
  right: 6px;
  font-size: 9px;
  font-weight: 700;
  color: rgba(255,255,255,0.60);
  font-variant-numeric: tabular-nums;
}
</style>
