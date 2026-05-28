<template>
  <div class="preview-panel glass-card animate-fade-in">
    <!-- ── Header ── -->
    <div class="pp-header">
      <span class="pp-header-icon" aria-hidden="true">▶</span>
      <span class="pp-header-title">视频预览</span>
      <span v-if="renderInFlight"   class="badge badge-arc" style="font-size:0.6rem;">渲染中</span>
      <span v-else-if="displayUrl" class="badge badge-ok"  style="font-size:0.6rem;">已完成</span>
    </div>

    <!-- ── Body ── -->
    <div class="pp-body">

      <!-- ════ A: Current video + history strip below ════ -->
      <template v-if="displayUrl">
        <div class="pp-player-wrap">
          <video
            :src="displayUrl"
            class="pp-video"
            controls
            playsinline
            :key="displayUrl"
          />
        </div>
        <div class="pp-current-label">
          <span v-if="displayUrl === props.finalVideoUrl" class="pp-current-tag">当前生成</span>
          <span v-else class="pp-current-tag pp-current-tag--hist">历史回放</span>
          <span class="pp-current-url">{{ shortUrl(displayUrl) }}</span>
        </div>
        <div v-if="allVideoUrls.length > 1" class="pp-history">
          <div class="pp-history-header">
            <span class="pp-history-title">历史视频</span>
            <span class="pp-history-count">{{ allVideoUrls.length }} 个</span>
          </div>
          <div class="pp-history-list">
            <button
              v-for="(url, idx) in allVideoUrls"
              :key="url"
              :class="['pp-thumb', { 'pp-thumb--active': url === displayUrl }]"
              @click="selectVideo(url)"
              :title="`视频 ${idx + 1}`"
            >
              <video class="pp-thumb-video" :src="url" preload="metadata" :muted="true"/>
              <div class="pp-thumb-overlay"><span class="pp-thumb-play">▶</span></div>
              <div class="pp-thumb-index">{{ idx + 1 }}</div>
            </button>
          </div>
        </div>
      </template>

      <!-- ════ B: Render in flight ════ -->
      <div v-else-if="renderInFlight" class="pp-state">
        <svg class="pp-state-svg pp-spin" viewBox="0 0 60 60" fill="none">
          <circle cx="30" cy="30" r="24" stroke="currentColor" stroke-opacity="0.15" stroke-width="4"/>
          <path d="M30 6 A24 24 0 0 1 54 30" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <div class="pp-state-title">视频合成中…</div>
        <div class="pp-state-desc">画面、音频与字幕正在拼接渲染</div>
      </div>

      <!-- ════ C: Workflow processing ════ -->
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

      <!-- ════ D: Has history but no current — history as main content ════ -->
      <div v-else-if="allVideoUrls.length > 0" class="pp-hist-main">
        <div class="pp-hist-main-header">
          <span class="pp-hist-main-title">历史视频</span>
          <span class="pp-hist-main-count">{{ allVideoUrls.length }} 个</span>
        </div>
        <div class="pp-hist-main-grid">
          <button
            v-for="(url, idx) in allVideoUrls"
            :key="url"
            class="pp-hist-card"
            @click="selectVideo(url)"
          >
            <div class="pp-hist-card-frame">
              <video class="pp-hist-card-video" :src="url" preload="metadata" :muted="true"/>
              <div class="pp-hist-card-overlay">
                <span class="pp-hist-card-play">▶</span>
              </div>
            </div>
            <div class="pp-hist-card-label">视频 {{ idx + 1 }}</div>
          </button>
        </div>
      </div>

      <!-- ════ E: Completely empty — illustrated empty state ════ -->
      <div v-else class="pp-empty">
        <!-- Decorative illustration -->
        <div class="pp-empty-illus" aria-hidden="true">
          <svg viewBox="0 0 240 180" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="ppGrad1" x1="0" y1="0" x2="240" y2="180" gradientUnits="userSpaceOnUse">
                <stop offset="0%"  stop-color="#fbbf24" stop-opacity="0.55"/>
                <stop offset="100%" stop-color="#f97316" stop-opacity="0.30"/>
              </linearGradient>
              <linearGradient id="ppGrad2" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"   stop-color="#fbbf24" stop-opacity="0.30"/>
                <stop offset="100%" stop-color="#f59e0b" stop-opacity="0.10"/>
              </linearGradient>
              <radialGradient id="ppGlow" cx="50%" cy="50%" r="50%">
                <stop offset="0%"   stop-color="#fbbf24" stop-opacity="0.35"/>
                <stop offset="100%" stop-color="#fbbf24" stop-opacity="0"/>
              </radialGradient>
            </defs>

            <!-- Background glow -->
            <ellipse cx="120" cy="90" rx="100" ry="60" fill="url(#ppGlow)"/>

            <!-- Background mountains (story landscape) -->
            <path d="M0 130 L40 92 L66 110 L92 78 L122 105 L156 70 L190 100 L240 75 L240 180 L0 180 Z"
                  fill="url(#ppGrad2)" opacity="0.7"/>
            <path d="M0 130 L40 92 L66 110 L92 78 L122 105 L156 70 L190 100 L240 75"
                  stroke="#fbbf24" stroke-width="1.2" stroke-opacity="0.45" stroke-linecap="round" stroke-linejoin="round" fill="none"/>

            <!-- Film clapperboard centre -->
            <g transform="translate(72, 38)">
              <!-- Top stripe -->
              <rect x="0" y="0" width="96" height="14" rx="2" fill="#1a1409" stroke="url(#ppGrad1)" stroke-width="1.4"/>
              <!-- Diagonal stripes -->
              <path d="M4 0 L14 14 M22 0 L32 14 M40 0 L50 14 M58 0 L68 14 M76 0 L86 14"
                    stroke="#fbbf24" stroke-width="1.4" stroke-opacity="0.55"/>
              <!-- Main board -->
              <rect x="0" y="16" width="96" height="58" rx="3" fill="#0f0c06" stroke="url(#ppGrad1)" stroke-width="1.4"/>
              <!-- Play triangle -->
              <path d="M36 32 L60 45 L36 58 Z" fill="url(#ppGrad1)" opacity="0.85"/>
              <circle cx="48" cy="45" r="22" stroke="#fbbf24" stroke-width="1.2" stroke-opacity="0.40" stroke-dasharray="3 3" fill="none"/>
            </g>

            <!-- Sparkle stars -->
            <g fill="#fbbf24">
              <path d="M28 36 L30 41 L35 42 L30 43 L28 48 L26 43 L21 42 L26 41 Z" opacity="0.70"/>
              <path d="M208 50 L210 55 L215 56 L210 57 L208 62 L206 57 L201 56 L206 55 Z" opacity="0.55"/>
              <path d="M195 28 L197 32 L201 33 L197 34 L195 38 L193 34 L189 33 L193 32 Z" opacity="0.45"/>
              <path d="M40 110 L42 114 L46 115 L42 116 L40 120 L38 116 L34 115 L38 114 Z" opacity="0.40"/>
              <circle cx="18"  cy="68"  r="1.5" opacity="0.50"/>
              <circle cx="222" cy="118" r="1.5" opacity="0.50"/>
              <circle cx="58"  cy="22"  r="1.2" opacity="0.40"/>
              <circle cx="180" cy="142" r="1.2" opacity="0.40"/>
            </g>

            <!-- Floating particles around centre -->
            <g fill="#fde68a">
              <circle cx="62"  cy="60"  r="1.2" opacity="0.65"/>
              <circle cx="178" cy="78"  r="1.5" opacity="0.55"/>
              <circle cx="158" cy="118" r="1.0" opacity="0.40"/>
              <circle cx="90"  cy="128" r="1.3" opacity="0.50"/>
            </g>
          </svg>
        </div>

        <div class="pp-empty-title">还没有视频，先讲一个故事吧</div>
        <div class="pp-empty-desc">在左侧填写故事主题，配置生成参数<br/>点击「开始创作」即可生成专属视频</div>

        <div v-if="(exampleTopics?.length ?? 0) > 0" class="pp-empty-topics">
          <div class="pp-empty-topics-label">
            <span class="pp-empty-topics-icon">✦</span>
            试试这些主题
          </div>
          <div class="pp-empty-topics-row">
            <button
              v-for="topic in (exampleTopics ?? [])"
              :key="topic"
              class="pp-topic-btn"
              @click="$emit('set-topic', topic)"
            >
              <span class="pp-topic-icon">→</span>
              <span class="pp-topic-text">{{ topic }}</span>
            </button>
          </div>
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

</script>

<style scoped>
/* ── Panel shell ── */
.preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
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
  min-height: 0;
  overflow-y: auto;
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

/* ══════════════════════════════════════════════════
   History as MAIN content (when no current video)
══════════════════════════════════════════════════ */
.pp-hist-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 1.25rem 1.25rem 1.5rem;
  overflow-y: auto;
}

.pp-hist-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.pp-hist-main-title {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.pp-hist-main-count {
  font-size: 0.6875rem;
  color: var(--text-muted);
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(245,158,11,0.10);
  border: 1px solid rgba(245,158,11,0.18);
}

.pp-hist-main-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.pp-hist-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  transition: transform 0.18s;
}
.pp-hist-card:hover { transform: translateY(-2px); }

.pp-hist-card-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 10px;
  overflow: hidden;
  border: 1.5px solid rgba(255,255,255,0.08);
  background: #000;
  transition: border-color 0.18s, box-shadow 0.18s;
}

.pp-hist-card:hover .pp-hist-card-frame {
  border-color: rgba(245,158,11,0.45);
  box-shadow: 0 4px 20px rgba(245,158,11,0.18);
}

.pp-hist-card-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  pointer-events: none;
}

.pp-hist-card-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.35);
  opacity: 0;
  transition: opacity 0.18s;
}
.pp-hist-card:hover .pp-hist-card-overlay { opacity: 1; }

.pp-hist-card-play {
  font-size: 26px;
  color: var(--arc-200);
  filter: drop-shadow(0 2px 6px rgba(0,0,0,0.7));
}

.pp-hist-card-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  padding: 0 2px;
}

.pp-hist-card:hover .pp-hist-card-label { color: var(--arc-300); }

/* ══════════════════════════════════════════════════
   Illustrated empty state — invites user to create
══════════════════════════════════════════════════ */
.pp-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1.75rem 2rem;
  text-align: center;
  gap: 0.5rem;
}

/* SVG illustration — floats gently */
.pp-empty-illus {
  width: 240px;
  max-width: 80%;
  line-height: 0;
  margin-bottom: 0.5rem;
  animation: ppEmptyFloat 5s ease-in-out infinite;
}

.pp-empty-illus svg { width: 100%; height: auto; }

@keyframes ppEmptyFloat {
  0%,100% { transform: translateY(0); }
  50%      { transform: translateY(-8px); }
}

.pp-empty-title {
  font-size: 1.125rem;
  font-weight: 700;
  background: linear-gradient(120deg, var(--arc-200) 0%, var(--arc-300) 50%, var(--prism-400) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 0.01em;
}

.pp-empty-desc {
  font-size: 0.8125rem;
  color: var(--text-muted);
  line-height: 1.7;
  max-width: 280px;
}

.pp-empty-topics {
  margin-top: 1.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  max-width: 360px;
}

.pp-empty-topics-label {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.pp-empty-topics-icon {
  color: var(--arc-300);
  font-size: 0.75rem;
  text-shadow: 0 0 8px rgba(245,158,11,0.55);
  animation: ppEmptySpark 2.4s ease-in-out infinite;
}

@keyframes ppEmptySpark {
  0%,100% { opacity: 0.6; transform: scale(1); }
  50%      { opacity: 1.0; transform: scale(1.2); }
}

.pp-empty-topics-row {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
}

.pp-topic-btn {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  cursor: pointer;
  border: 1px solid rgba(245,158,11,0.22);
  background: linear-gradient(135deg, rgba(245,158,11,0.06) 0%, rgba(249,115,22,0.04) 100%);
  color: var(--arc-300);
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 0.625rem 0.875rem;
  border-radius: 10px;
  text-align: left;
  transition: border-color 0.18s, background 0.18s, transform 0.18s, box-shadow 0.18s;
  width: 100%;
}

.pp-topic-btn:hover {
  border-color: rgba(245,158,11,0.55);
  background: linear-gradient(135deg, rgba(245,158,11,0.14) 0%, rgba(249,115,22,0.10) 100%);
  color: var(--arc-200);
  transform: translateX(2px);
  box-shadow: 0 4px 16px rgba(245,158,11,0.18);
}

.pp-topic-icon {
  color: var(--arc-400);
  font-weight: 800;
  font-size: 0.875rem;
  flex-shrink: 0;
  transition: transform 0.18s;
}

.pp-topic-btn:hover .pp-topic-icon { transform: translateX(2px); }

.pp-topic-text { flex: 1; min-width: 0; }

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
