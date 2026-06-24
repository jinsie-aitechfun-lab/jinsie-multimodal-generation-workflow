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
        <!-- Current work card — workflow chain visualisation.
             Always shown when a video is loaded so the user keeps the
             timeline summary even after multiple generations. -->
        <div class="pp-work">
          <div class="pp-work-head">
            <div class="pp-work-head-left">
              <div class="pp-work-eyebrow">当前作品</div>
              <div class="pp-work-filename">{{ shortUrl(displayUrl!) }}</div>
            </div>
            <span :class="['pp-work-badge', { 'pp-work-badge--live': workInProgress }]">
              <span class="pp-work-badge-dot" aria-hidden="true"></span>
              {{
                cancelRequested
                  ? '取消中 · 工作流'
                  : workInProgress
                    ? '生成中 · 工作流'
                    : '已完成 · 完整视频'
              }}
            </span>
          </div>

          <ol class="pp-work-flow" aria-label="生成链路">
            <template v-for="(step, idx) in workflowChain" :key="step.id">
              <li :class="['pp-flow-node', `pp-flow-node--${step.state}`]">
                <span class="pp-flow-dot" aria-hidden="true"></span>
                <span class="pp-flow-label">{{ step.label }}</span>
              </li>
              <li
                v-if="idx < workflowChain.length - 1"
                :class="['pp-flow-link', { 'pp-flow-link--done': step.state === 'done' }]"
                aria-hidden="true"
              ></li>
            </template>
          </ol>

          <div class="pp-work-foot">
            <span class="pp-work-foot-check" aria-hidden="true">✓</span>
            <span class="pp-work-foot-text">
              已完成 {{ doneCount }} / {{ workflowChain.length }} 步骤
            </span>
            <button
              v-if="cancellable"
              type="button"
              class="pp-cancel-link"
              :disabled="cancelRequested"
              @click="$emit('cancel')"
            >
              {{ cancelRequested ? '正在取消…' : '取消生成' }}
            </button>
          </div>
        </div>

        <!-- History strip — independent of the work card so the user keeps
             both the timeline summary AND a quick switcher for prior takes.
             Hidden when only the current video exists (length === 1). -->
        <div v-if="allVideoUrls.length > 1" class="pp-history">
          <div class="pp-history-header">
            <span class="pp-history-title">历史视频</span>
            <span class="pp-history-count">{{ allVideoUrls.length }} 个</span>
          </div>
          <div class="pp-history-list">
            <div
              v-for="(url, idx) in allVideoUrls"
              :key="url"
              :class="['pp-thumb', { 'pp-thumb--active': url === displayUrl }]"
            >
              <button
                type="button"
                class="pp-thumb-main"
                :title="historyVideoTooltip(url, idx)"
                @click="selectVideo(url)"
              >
                <video class="pp-thumb-video" :src="url" preload="metadata" :muted="true"/>
                <div class="pp-thumb-overlay"><span class="pp-thumb-play">▶</span></div>
                <div class="pp-thumb-index">{{ idx + 1 }}</div>
                <div class="pp-thumb-caption">{{ historyVideoLabel(url, idx) }}</div>
              </button>
              <button
                type="button"
                class="pp-thumb-delete"
                aria-label="从历史记录中删除"
                title="从历史记录中删除"
                @click.stop="requestDeleteVideo(url)"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ════ A2: Workflow running but no current video on screen.
           Without this branch, B (history grid) wins and the user loses
           any visual of the active workflow progress. ════ -->
      <template v-else-if="workInProgress">
        <div class="pp-work">
          <div class="pp-work-head">
            <div class="pp-work-head-left">
              <div class="pp-work-eyebrow">本轮生成</div>
              <div class="pp-work-filename">{{ statusLabel || '正在运行 Workflow' }}</div>
            </div>
            <span class="pp-work-badge pp-work-badge--live">
              <span class="pp-work-badge-dot" aria-hidden="true"></span>
              生成中 · 工作流
            </span>
          </div>

          <ol class="pp-work-flow" aria-label="生成链路">
            <template v-for="(step, idx) in workflowChain" :key="step.id">
              <li :class="['pp-flow-node', `pp-flow-node--${step.state}`]">
                <span class="pp-flow-dot" aria-hidden="true"></span>
                <span class="pp-flow-label">{{ step.label }}</span>
              </li>
              <li
                v-if="idx < workflowChain.length - 1"
                :class="['pp-flow-link', { 'pp-flow-link--done': step.state === 'done' }]"
                aria-hidden="true"
              ></li>
            </template>
          </ol>

          <div class="pp-work-foot">
            <span class="pp-work-foot-check" aria-hidden="true">✓</span>
            <span class="pp-work-foot-text">
              已完成 {{ doneCount }} / {{ workflowChain.length }} 步骤
            </span>
            <button
              v-if="cancellable"
              type="button"
              class="pp-cancel-link"
              :disabled="cancelRequested"
              @click="$emit('cancel')"
            >
              {{ cancelRequested ? '正在取消…' : '取消生成' }}
            </button>
          </div>
        </div>

        <!-- Keep the history grid below so users can still click a prior take. -->
        <div v-if="allVideoUrls.length > 0" class="pp-hist-main">
          <div class="pp-hist-main-header">
            <span class="pp-hist-main-title">历史视频</span>
            <span class="pp-hist-main-count">{{ allVideoUrls.length }} 个</span>
          </div>
          <div class="pp-hist-main-grid">
            <div
              v-for="(url, idx) in allVideoUrls"
              :key="url"
              class="pp-hist-card"
            >
              <button
                type="button"
                class="pp-hist-card-main"
                :title="historyVideoTooltip(url, idx)"
                @click="selectVideo(url)"
              >
                <div class="pp-hist-card-frame">
                  <video class="pp-hist-card-video" :src="url" preload="metadata" :muted="true"/>
                  <div class="pp-hist-card-overlay">
                    <span class="pp-hist-card-play">▶</span>
                  </div>
                </div>
                <div class="pp-hist-card-label">{{ historyVideoLabel(url, idx) }}</div>
              </button>
              <button
                type="button"
                class="pp-hist-card-delete"
                aria-label="从历史记录中删除"
                title="从历史记录中删除"
                @click.stop="requestDeleteVideo(url)"
              >
                ×
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ════ A3: Workflow halted by image failures.
           Sits above B / E so failures dominate the right column even
           when history exists or the workflow has settled. Without
           this, a partially-failed run with no video shows either the
           history grid or an empty illustration on the main tab — the
           failure is only visible on the 画面审核 tab, which doesn't
           match how the user navigates. ════ -->
      <template v-else-if="hasImageFailures">
        <div class="pp-work">
          <div class="pp-work-head">
            <div class="pp-work-head-left">
              <div class="pp-work-eyebrow">本轮生成</div>
              <div class="pp-work-filename">部分场景候选图失败，请前往「画面审核」重试</div>
            </div>
            <span class="pp-work-badge pp-work-badge--failed">
              <span class="pp-work-badge-dot" aria-hidden="true"></span>
              生成失败 · 工作流
            </span>
          </div>

          <ol class="pp-work-flow" aria-label="生成链路">
            <template v-for="(step, idx) in workflowChain" :key="step.id">
              <li :class="['pp-flow-node', `pp-flow-node--${step.state}`]">
                <span class="pp-flow-dot" aria-hidden="true"></span>
                <span class="pp-flow-label">{{ step.label }}</span>
              </li>
              <li
                v-if="idx < workflowChain.length - 1"
                :class="['pp-flow-link', { 'pp-flow-link--done': step.state === 'done' }]"
                aria-hidden="true"
              ></li>
            </template>
          </ol>

          <div class="pp-work-foot">
            <span class="pp-work-foot-text">
              已完成 {{ doneCount }} / {{ workflowChain.length }} 步骤
            </span>
          </div>
        </div>
      </template>

      <!-- ════ B: Has history but no current — history as main content ════ -->
      <div v-else-if="allVideoUrls.length > 0" class="pp-hist-main">
        <div class="pp-hist-main-header">
          <span class="pp-hist-main-title">历史视频</span>
          <span class="pp-hist-main-count">{{ allVideoUrls.length }} 个</span>
        </div>
        <div class="pp-hist-main-grid">
          <div
            v-for="(url, idx) in allVideoUrls"
            :key="url"
            class="pp-hist-card"
          >
            <button
              type="button"
              class="pp-hist-card-main"
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
            <button
              type="button"
              class="pp-hist-card-delete"
              aria-label="从历史记录中删除"
              title="从历史记录中删除"
              @click.stop="requestDeleteVideo(url)"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <!-- ════ C: Render in flight ════ -->
      <div v-else-if="renderInFlight" class="pp-state">
        <svg class="pp-state-svg pp-spin" viewBox="0 0 60 60" fill="none">
          <circle cx="30" cy="30" r="24" stroke="currentColor" stroke-opacity="0.15" stroke-width="4"/>
          <path d="M30 6 A24 24 0 0 1 54 30" stroke="currentColor" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <div class="pp-state-title">视频合成中…</div>
        <div class="pp-state-desc">画面、音频与字幕正在拼接渲染</div>
      </div>

      <!-- ════ D: Workflow processing ════ -->
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

interface RecentVideoMeta {
  title?: string
  topic?: string
  createdAt?: string
}

const props = defineProps<{
  finalVideoUrl?: string
  recentVideoUrls?: string[]
  /** url → { title, topic, createdAt } map. Optional; missing entries
   *  fall back to "视频 N" / "视频 N (N=index+1)" tooltip. */
  recentVideoMetadata?: Record<string, RecentVideoMeta>
  renderInFlight?: boolean
  isProcessing?: boolean
  refreshingImages?: boolean
  // Manual-mode wait state: assets are ready but the user hasn't clicked
  // the "生成视频" button yet. Backend isn't running anything; we still
  // want the workflow chain to STAY visible (video step active) so the
  // page doesn't look frozen during the wait.
  awaitingManualRender?: boolean
  // True when image_assets has persisted failed-scene placeholders.
  // Drives the workflow chain into a halted state: images step shows
  // as 'failed' (red), and the audio/subtitle/video steps stay
  // pending. Without this, the chain advances past the image step
  // (since the backend reports image_assets as a completed step in
  // step_summaries) and visually claims everything is done — directly
  // contradicting the FinalVideoPanel showing "场景图片生成失败".
  hasImageFailures?: boolean
  statusLabel?: string
  completedSteps?: number
  totalSteps?: number
  exampleTopics?: string[]
  // Cancel affordance for the in-flight workflow (driven by App.vue).
  cancellable?: boolean
  cancelRequested?: boolean
}>()

const emit = defineEmits<{
  (e: 'set-topic', topic: string): void
  (e: 'cancel'): void
  (e: 'delete-video', url: string): void
}>()

/* Local-only history delete. Bubbles the URL up to the parent — the
   parent shows a themed confirm dialog (matching the rest of the app)
   and owns the localStorage persistence. stopPropagation is on the
   button itself in the template so the parent thumbnail click (which
   selects/plays the video) doesn't fire. */
function requestDeleteVideo(url: string) {
  if (!url) return
  emit('delete-video', url)
}

/* History card label — the human-readable subtitle shown beneath the
   thumbnail. Prefers the LLM-generated story title; falls back to the
   user's input topic (truncated) ; then to the generic ordinal "视频 N"
   so cards without any metadata don't go blank. */
function historyVideoLabel(url: string, fallbackIndex: number): string {
  const meta = props.recentVideoMetadata?.[url]
  const title = (meta?.title || '').trim()
  if (title) return title
  const topic = (meta?.topic || '').trim()
  if (topic) {
    return topic.length > 14 ? `${topic.slice(0, 14)}…` : topic
  }
  return `视频 ${fallbackIndex + 1}`
}

/* History card tooltip — fuller info for hover. Shows title + topic +
   generation date when available so a user can disambiguate two cards
   with similar thumbnails. */
function historyVideoTooltip(url: string, fallbackIndex: number): string {
  const meta = props.recentVideoMetadata?.[url]
  const title = (meta?.title || '').trim()
  const topic = (meta?.topic || '').trim()
  const createdAt = (meta?.createdAt || '').trim()
  const parts: string[] = []
  if (title) parts.push(title)
  if (topic && topic !== title) parts.push(`主题：${topic}`)
  if (createdAt) {
    const dt = new Date(createdAt)
    if (!Number.isNaN(dt.getTime())) {
      parts.push(
        `生成于 ${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')} ${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`,
      )
    }
  }
  if (parts.length === 0) return `视频 ${fallbackIndex + 1}`
  return parts.join(' · ')
}

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
// `label` is the Chinese label used by the in-progress state panel.
// `flowLabel` is the short English caption used by the timeline rail in
// the current-work card (a lighter, more "workflow product" feel).
const STEP_DEFS = [
  { id: 'story',      label: '故事生成', flowLabel: 'Story'      },
  { id: 'storyboard', label: '分镜设计', flowLabel: 'Storyboard' },
  { id: 'images',     label: '画面生成', flowLabel: 'Image'      },
  { id: 'voice',      label: '配音生成', flowLabel: 'Voice'      },
  { id: 'subtitles',  label: '字幕生成', flowLabel: 'Subtitle'   },
  { id: 'video',      label: '视频合成', flowLabel: 'Video'      },
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

// Workflow chain for the current-work card — stage-aware:
//   • renderInFlight     → all earlier steps done, video step active
//   • refreshingImages   → story+storyboard done, image step active
//   • isProcessing       → initial workflow run; CAPPED at image step.
//     See INITIAL_PHASE_MAX_IDX below for the no-regress contract.
//   • finalVideoUrl set  → fully done
//   • otherwise          → derive from completedSteps / totalSteps
// Stage indices into STEP_DEFS:
//   0 story · 1 storyboard · 2 images · 3 voice · 4 subtitles · 5 video
type FlowState = 'done' | 'active' | 'pending' | 'failed'

// During the initial workflow run, the backend's `completed_steps` walks
// through ~11 internal stages including audio/subtitle/video — but those
// stages run against PLACEHOLDER images, not real ones. Real image
// generation only happens in the deferred-refresh phase that follows
// (props.refreshingImages = true). So if we let the visualization advance
// to "video done" during the initial run, the user sees "6/6 已完成"
// momentarily — then refresh starts and the chain visually REGRESSES
// back to "画面生成". That regression reads as a UI bug.
//
// Cap initial-phase advance at index 2 (image step). Story/storyboard
// can show as "done"; image step stays "active" through the rest of the
// initial run; audio/subtitle/video stay "pending" until the deferred
// refresh actually completes and (eventually) the final-video re-render
// fires. This keeps the chain MONOTONICALLY non-regressing across the
// phase 1 → phase 2 boundary.
const INITIAL_PHASE_MAX_IDX = 2  // image step

function buildChainWithActive(activeIdx: number) {
  return STEP_DEFS.map((step, idx) => ({
    ...step,
    state: (idx < activeIdx ? 'done' : idx === activeIdx ? 'active' : 'pending') as FlowState,
  }))
}

const workflowChain = computed<{ id: string; label: string; flowLabel: string; state: FlowState }[]>(() => {
  // Image failures halt the pipeline. Story / storyboard are done by
  // definition (image generation can't have failed without those
  // running first), images shows 'failed', downstream stays pending.
  // Sits above renderInFlight so a stale prior-render in-flight flag
  // can't overrule a fresh failure state — but in practice render
  // wouldn't be in flight when failures are persisted (B2 gate).
  if (props.hasImageFailures) {
    return STEP_DEFS.map((step, idx) => ({
      ...step,
      state: (
        idx <= 1 ? 'done'           // story / storyboard
        : idx === 2 ? 'failed'      // images — halted
        : 'pending'                 // voice / subtitle / video
      ) as FlowState,
    }))
  }

  // Final-video render — every prior step is finished, only "视频合成" is live.
  if (props.renderInFlight) return buildChainWithActive(5)

  // Manual-mode wait: candidate images are ready, video step is waiting
  // for the user's click. Even though backend's phase-1 already produced
  // placeholder audio/subtitles, the user hasn't seen that progress (the
  // chain was capped at image step throughout phase 1). To match the
  // user's mental model — "I've only seen images get generated, the
  // video step is what's next" — show image step as DONE, video step as
  // ACTIVE, and the intermediate audio/subtitle steps as PENDING. They
  // will visually advance into "done" together when the user clicks
  // render and `renderInFlight` takes over.
  if (props.awaitingManualRender) {
    return STEP_DEFS.map((step, idx) => ({
      ...step,
      state: (
        idx <= 2 ? 'done'              // story / storyboard / image done
        : idx === 5 ? 'active'         // video step waiting on user
        : 'pending'                    // audio / subtitle held until render
      ) as FlowState,
    }))
  }

  // Candidate image generation — Story + Storyboard are prerequisites and
  // therefore already done; the image step is the live one.
  if (props.refreshingImages) return buildChainWithActive(2)

  // Initial workflow run — completedSteps drives the active index, but
  // never advance past the image step (see INITIAL_PHASE_MAX_IDX above).
  if (props.isProcessing) {
    const completed = props.completedSteps ?? 0
    const total = props.totalSteps ?? STEP_DEFS.length
    const ratio = total > 0 ? completed / total : 0
    const naiveIdx = Math.min(
      Math.floor(ratio * STEP_DEFS.length),
      STEP_DEFS.length - 1,
    )
    const cappedIdx = Math.min(naiveIdx, INITIAL_PHASE_MAX_IDX)
    return buildChainWithActive(cappedIdx)
  }

  // Settled state with a finished video → mark everything done.
  if (props.finalVideoUrl) {
    return STEP_DEFS.map((step) => ({ ...step, state: 'done' as FlowState }))
  }

  // Idle / partial state — best-effort fallback.
  const completed = props.completedSteps ?? 0
  const total = props.totalSteps ?? STEP_DEFS.length
  const ratio = total > 0 ? completed / total : 0
  const activeIdx = Math.min(
    Math.floor(ratio * STEP_DEFS.length),
    STEP_DEFS.length - 1,
  )
  return buildChainWithActive(activeIdx)
})

// True whenever any workflow phase is in flight — drives badge wording,
// dot pulse, and the A2 template branch in the right panel. Includes the
// manual-render wait so the "generating" affordance keeps showing while
// the user hasn't clicked the render CTA yet.
const workInProgress = computed(
  () => Boolean(
    props.isProcessing ||
    props.renderInFlight ||
    props.refreshingImages ||
    props.awaitingManualRender,
  ),
)
const doneCount = computed(
  () => workflowChain.value.filter((s) => s.state === 'done').length,
)

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
  position: relative;
  width: 100%;
  background: #000;
}
/* Soft bottom gradient — frames native controls so the white progress bar
   feels less jarring against the dark gold studio. pointer-events:none so
   the player's hit-target is untouched. Height limited to ~52px so subtitles
   above the controls aren't washed out. */
.pp-player-wrap::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 52px;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(8, 5, 2, 0) 0%,
    rgba(8, 5, 2, 0.28) 55%,
    rgba(8, 5, 2, 0.42) 100%
  );
  border-bottom-left-radius: inherit;
  border-bottom-right-radius: inherit;
}

.pp-video {
  width: 100%;
  display: block;
  max-height: 360px;
  object-fit: contain;
  background: #000;
  accent-color: var(--arc-300, #fbbf24);
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
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0;
  background: transparent;
  text-align: left;
  transition: transform 0.18s;
}
.pp-hist-card:hover { transform: translateY(-2px); }
.pp-hist-card-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
}
.pp-hist-card-delete {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 1px solid rgba(245,158,11,0.24);
  border-radius: 999px;
  background: rgba(8,6,3,0.78);
  color: rgba(255,245,220,0.82);
  font-size: 15px;
  line-height: 1;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.16s ease, background 0.16s, border-color 0.16s, color 0.16s;
  z-index: 2;
}
.pp-hist-card:hover .pp-hist-card-delete,
.pp-hist-card:focus-within .pp-hist-card-delete {
  opacity: 1;
}
.pp-hist-card-delete:hover {
  background: rgba(180,60,40,0.74);
  border-color: rgba(245,158,11,0.50);
  color: #fff;
}

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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Allow the label to occupy the full card width then truncate so
     long story titles don't push the card layout. */
  max-width: 100%;
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
  background: var(--surface-overlay-soft);
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

/* ── Current work info + workflow summary
   Theme-aware: all accent colours come from --arc-*, --border-glass,
   --border-arc, --text-muted/secondary, --surface-overlay-soft. ── */
.pp-work {
  margin: 0.875rem 1.25rem 1.125rem;
  padding: 0.875rem 1rem;
  border-radius: 14px;
  border: 1px solid var(--border-glass);
  background:
    linear-gradient(135deg, rgba(255,255,255,0.04), transparent),
    var(--surface-overlay-soft);
  min-height: 160px;
  max-height: 220px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.pp-work-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.pp-work-head-left { min-width: 0; flex: 1; }

.pp-work-eyebrow {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--arc-300);
  opacity: 0.85;
}

.pp-work-filename {
  margin-top: 2px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pp-work-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 10%, transparent);
  color: var(--arc-300);
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  line-height: 1.4;
}

.pp-work-badge-dot {
  display: inline-block;
  width: 6px; height: 6px;
  margin-right: 6px;
  border-radius: 999px;
  background: var(--arc-300);
  box-shadow: 0 0 6px color-mix(in srgb, var(--arc-400) 55%, transparent);
}

.pp-work-badge--live .pp-work-badge-dot {
  animation: ppFlowPulse 1.6s ease-in-out infinite;
}

.pp-work-badge--failed {
  border-color: color-mix(in srgb, #f87171 50%, transparent);
  background: color-mix(in srgb, #f87171 12%, transparent);
  color: #fca5a5;
}
.pp-work-badge--failed .pp-work-badge-dot {
  background: #f87171;
  box-shadow: 0 0 6px color-mix(in srgb, #f87171 60%, transparent);
}

/* ═══════════════════════════════════════════════
   Workflow Timeline — minimalist horizontal rail
   • 6 stops along a continuous 1px gold rail
   • Filled gold on the completed segment, faded after
   • Short English caption below each stop
═══════════════════════════════════════════════ */
.pp-work-flow {
  margin: 0;
  padding: 8px 6px 22px;   /* bottom padding = room for absolute labels */
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0;
}

.pp-flow-node {
  position: relative;
  flex-shrink: 0;
  width: 12px;
  height: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pp-flow-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  /* Hollow pending dot — interior uses theme glass, border uses theme accent */
  background: var(--glass-bg);
  border: 1.5px solid var(--border-arc);
  box-sizing: border-box;
  transition: background 0.2s ease, border-color 0.2s ease,
              box-shadow 0.2s ease;
}

.pp-flow-node--done .pp-flow-dot {
  background: var(--arc-300);
  border-color: var(--arc-300);
}

.pp-flow-node--active .pp-flow-dot {
  background: var(--arc-300);
  border-color: var(--arc-300);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--arc-300) 20%, transparent),
    0 0 10px color-mix(in srgb, var(--arc-300) 45%, transparent);
  animation: ppFlowPulse 1.8s ease-in-out infinite;
}

.pp-flow-node--failed .pp-flow-dot {
  background: #f87171;
  border-color: #f87171;
  box-shadow:
    0 0 0 3px color-mix(in srgb, #f87171 22%, transparent),
    0 0 10px color-mix(in srgb, #f87171 45%, transparent);
}

.pp-flow-label {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  font-size: 0.625rem;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  white-space: nowrap;
  transition: color 0.2s ease;
  font-feature-settings: "ss01" on;
}

.pp-flow-node--done .pp-flow-label {
  color: color-mix(in srgb, var(--arc-300) 70%, transparent);
}

.pp-flow-node--active .pp-flow-label {
  color: var(--arc-200);
  font-weight: 600;
}

.pp-flow-node--failed .pp-flow-label {
  color: #f87171;
  font-weight: 600;
}

.pp-flow-link {
  flex: 1;
  min-width: 14px;
  height: 1px;
  background: var(--border-glass);
  transition: background 0.25s ease;
}

.pp-flow-link--done {
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--arc-300) 50%, transparent) 0%,
    color-mix(in srgb, var(--arc-300) 50%, transparent) 80%,
    color-mix(in srgb, var(--arc-300) 22%, transparent) 100%
  );
}

@keyframes ppFlowPulse {
  0%, 100% {
    box-shadow:
      0 0 0 3px color-mix(in srgb, var(--arc-300) 18%, transparent),
      0 0 8px  color-mix(in srgb, var(--arc-300) 32%, transparent);
  }
  50% {
    box-shadow:
      0 0 0 4px color-mix(in srgb, var(--arc-300) 28%, transparent),
      0 0 14px color-mix(in srgb, var(--arc-300) 55%, transparent);
  }
}

/* ── Footer summary ── */
.pp-work-foot {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Trailing "取消生成" link inside the work card foot — sits at the
   far right (margin-left: auto) and only shows when a run is in flight. */
.pp-cancel-link {
  margin-left: auto;
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
.pp-cancel-link:hover:not(:disabled) {
  border-color: rgba(248, 113, 113, 0.55);
  color: #f87171;
  background: rgba(248, 113, 113, 0.06);
}
.pp-cancel-link:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.pp-work-foot-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 8%, transparent);
  color: var(--arc-300);
  font-size: 0.625rem;
  font-weight: 700;
}

.pp-work-foot-text {
  letter-spacing: 0.04em;
}

/* Pearl Dawn: refined acrylic preview surface */
:global(:root[data-theme="pearl"]) .preview-panel {
  border-color: rgba(214, 179, 90, 0.20);
  box-shadow:
    0 26px 72px rgba(46,42,34,0.085),
    0 10px 26px rgba(142,197,255,0.075),
    inset 0 1px 0 rgba(255,255,255,0.92);
}

:global(:root[data-theme="pearl"]) .pp-header {
  border-bottom-color: rgba(214, 179, 90, 0.14);
  background: linear-gradient(180deg, rgba(255,255,255,0.42), rgba(255,255,255,0));
}

:global(:root[data-theme="pearl"]) .pp-player-wrap {
  border: 1px solid rgba(214,179,90,0.18);
  box-shadow:
    0 24px 64px rgba(46,42,34,0.10),
    0 8px 28px rgba(142,197,255,0.08),
    inset 0 1px 0 rgba(255,255,255,0.82);
}
/* Pearl theme — overlay is much lighter so the bright canvas stays bright. */
:global(:root[data-theme="pearl"]) .pp-player-wrap::after {
  height: 44px;
  background: linear-gradient(
    180deg,
    rgba(46, 42, 34, 0) 0%,
    rgba(46, 42, 34, 0.10) 60%,
    rgba(46, 42, 34, 0.16) 100%
  );
}

:global(:root[data-theme="pearl"]) .pp-current-label {
  background:
    linear-gradient(90deg, rgba(255,255,255,0.66), rgba(238,247,255,0.50));
  border-bottom-color: rgba(214,179,90,0.12);
  backdrop-filter: blur(14px) saturate(1.08);
  -webkit-backdrop-filter: blur(14px) saturate(1.08);
}

:global(:root[data-theme="pearl"]) .pp-current-tag {
  background: linear-gradient(135deg, rgba(248,232,198,0.78), rgba(229,242,255,0.56));
  border-color: rgba(214,179,90,0.28);
  color: #8b6722;
  box-shadow:
    0 0 14px rgba(214,179,90,0.12),
    inset 0 1px 0 rgba(255,255,255,0.78);
}

:global(:root[data-theme="pearl"]) .pp-work,
:global(:root[data-theme="pearl"]) .pp-empty {
  background:
    radial-gradient(circle at 12% 18%, rgba(246, 222, 166, 0.20), transparent 28%),
    radial-gradient(circle at 86% 78%, rgba(142, 197, 255, 0.16), transparent 36%),
    linear-gradient(145deg, rgba(255,255,255,0.72), rgba(247,250,252,0.54));
  border: 1px solid rgba(214,179,90,0.18);
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.86),
    0 18px 46px rgba(46,42,34,0.06);
  backdrop-filter: blur(18px) saturate(1.08);
  -webkit-backdrop-filter: blur(18px) saturate(1.08);
}

:global(:root[data-theme="pearl"]) .pp-empty {
  border-radius: 18px;
}

/* Pearl-only refinement — filename gets darker on the white surface to
   keep text contrast (other states now flow from --arc-* tokens directly). */
:global(:root[data-theme="pearl"]) .pp-work-filename {
  color: rgba(46,42,34,0.92);
}
:global(:root[data-theme="pearl"]) .pp-current-url {
  color: rgba(111,106,95,0.76);
}

/* Thumbnail tile (was a button — now a div wrapping a main button +
   delete button so the × doesn't trigger the play click). */
.pp-thumb {
  position: relative;
  flex-shrink: 0;
  width: 140px;
  height: 79px; /* 16:9 */
  border-radius: 8px;
  overflow: hidden;
  border: 1.5px solid rgba(255,255,255,0.08);
  background: #000;
  transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
}
.pp-thumb-main {
  position: absolute;
  inset: 0;
  display: block;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
}
.pp-thumb-delete {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 1px solid rgba(245,158,11,0.22);
  border-radius: 999px;
  background: rgba(8,6,3,0.72);
  color: rgba(255,245,220,0.78);
  font-size: 14px;
  line-height: 1;
  font-family: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.16s ease, background 0.16s, border-color 0.16s, color 0.16s;
  z-index: 2;
}
.pp-thumb:hover .pp-thumb-delete,
.pp-thumb:focus-within .pp-thumb-delete {
  opacity: 1;
}
.pp-thumb-delete:hover {
  background: rgba(180,60,40,0.72);
  border-color: rgba(245,158,11,0.46);
  color: #fff;
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
  background: var(--surface-overlay-strong);
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

/* History thumb caption — story title as a 1-line subtitle pinned to
   the bottom of the thumbnail, on top of a soft gradient scrim so
   readability survives any cover frame. Falls back to "视频 N" when
   no metadata is attached, so older entries still look intentional. */
.pp-thumb-caption {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 14px 8px 6px;
  font-size: 10px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.92);
  text-align: left;
  letter-spacing: 0.01em;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(0, 0, 0, 0.62) 70%
  );
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  pointer-events: none;
}
</style>
