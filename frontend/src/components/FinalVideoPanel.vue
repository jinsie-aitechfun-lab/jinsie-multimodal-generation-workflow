<template>
  <section class="final-hero">
    <h3 class="final-title">最终视频</h3>

    <div class="final-shell" :class="{ ready: Boolean(finalVideoUrl) }">
      <video
        v-if="finalVideoUrl"
        :src="finalVideoUrl"
        controls
        playsinline
        class="final-video"
      />

      <div v-else class="final-placeholder">
        <!-- Illustration icon: idle clapperboard when nothing's running,
             AI-workflow loading animation during any active phase
             (initial workflow run · candidate image refresh · render). -->
        <div class="ph-illus">
          <svg v-if="!isAnyLoading" class="ph-svg" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
            <!-- Film frame outer -->
            <rect x="8" y="18" width="64" height="44" rx="8" stroke="currentColor" stroke-width="1.8" stroke-opacity="0.6"/>
            <!-- Clapperboard top stripe -->
            <rect x="8" y="18" width="64" height="14" rx="8" fill="currentColor" fill-opacity="0.08" stroke="currentColor" stroke-width="1.8" stroke-opacity="0.6"/>
            <!-- Film sprocket holes top -->
            <circle cx="20" cy="25" r="3" fill="currentColor" fill-opacity="0.45"/>
            <circle cx="32" cy="25" r="3" fill="currentColor" fill-opacity="0.45"/>
            <circle cx="44" cy="25" r="3" fill="currentColor" fill-opacity="0.45"/>
            <circle cx="56" cy="25" r="3" fill="currentColor" fill-opacity="0.45"/>
            <!-- Play triangle -->
            <path d="M34 42 L50 50 L34 58 Z" fill="currentColor" fill-opacity="0.55" stroke="currentColor" stroke-width="1.2" stroke-opacity="0.7" stroke-linejoin="round"/>
          </svg>
          <GenerationLoadingAnimation v-else />
        </div>
        <div class="ph-title">{{ placeholderTitle }}</div>
        <div class="ph-desc">{{ placeholderDesc }}</div>

        <!-- Internal bar: only when global sticky bar is NOT covering the same progress -->
        <div v-if="showInternalProgress" class="ph-progress">
          <div class="ph-bar" :class="{ indeterminate }">
            <div
              class="ph-bar-fill"
              :style="indeterminate ? {} : { width: progressPct + '%' }"
            ></div>
          </div>
          <div class="ph-meta">
            <template v-if="!indeterminate">
              <span>{{ progressPct }}%</span>
              <span class="ph-dot">·</span>
            </template>
            <span>{{ progressLabel }}</span>
          </div>
        </div>
        <!-- Global bar is active → just a pulsing status chip -->
        <div v-else class="ph-status-chip">
          <span class="ph-status-dot"/>
          {{ progressLabel }}
        </div>
      </div>
    </div>

    <!-- JSON only shown in dev/debug context, hidden in main view -->
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import GenerationLoadingAnimation from './studio/GenerationLoadingAnimation.vue'

type UnknownRecord = Record<string, unknown>

const props = defineProps<{
  finalVideoUrl: string
  finalVideoText: string
  workflowResponse: UnknownRecord | null
  renderInFlight: boolean
  loading: boolean
  refreshingImages?: boolean   // true when image review refresh is running (top bar already covers it)
  cancelRequested?: boolean    // user has clicked "取消生成"; overrides running titles
  errorMessage?: string
  workflowStatusMessage?: string
  workflowStatusProgress?: number | null
}>()

function asObj(v: unknown): UnknownRecord | null {
  return v && typeof v === 'object' ? (v as UnknownRecord) : null
}

function asStr(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function asNum(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

const outputs = computed(() => asObj(props.workflowResponse?.outputs))
const storyboard = computed(() => asObj(outputs.value?.storyboard))
const imageAssets = computed(() => asObj(outputs.value?.image_assets))
const audioSegments = computed(() => asObj(outputs.value?.audio_segments))
const finalVideo = computed(() => asObj(outputs.value?.final_video))

const indeterminate = computed(() => {
  if (props.finalVideoUrl) return false
  if (props.renderInFlight || finalStatus.value === 'rendering') return false
  if (workflowInFlight.value && props.workflowStatusProgress != null) {
    return props.workflowStatusProgress <= 0
  }
  // runWorkflow 请求中，或 refresh 正在跑，但还没有任何 image_assets
  return props.loading && imageAssetCount.value === 0
})

const sceneCount = computed(() => {
  const n = asNum(storyboard.value?.scene_count)
  return n && n > 0 ? Math.floor(n) : 0
})

const imageAssetCount = computed(() => {
  const assets = imageAssets.value?.assets
  return Array.isArray(assets) ? assets.length : 0
})

const audioItemCount = computed(() => {
  const items = audioSegments.value?.items
  return Array.isArray(items) ? items.length : 0
})

const finalStatus = computed(() => asStr(finalVideo.value?.status).toLowerCase())
const workflowInFlight = computed(() => props.loading && !outputs.value)

// Any active phase that should swap the static clapperboard for the
// AI-workflow loading animation: initial workflow, image refresh, render.
const isAnyLoading = computed(() => {
  return Boolean(
    props.loading ||
    props.renderInFlight ||
    props.refreshingImages ||
    finalStatus.value === 'rendering' ||
    workflowInFlight.value,
  )
})

// Internal bar only shows when global sticky bar is NOT already covering the progress.
// Global bar is active during: initial workflow run (workflowInFlight) OR image refresh.
const showInternalProgress = computed(() => {
  if (props.refreshingImages) return false
  if (workflowInFlight.value) return false
  return true
})
const blockingErrorMessage = computed(() => asStr(props.errorMessage).trim())
const hasBlockingError = computed(() => {
  return Boolean(blockingErrorMessage.value && !props.loading && !props.finalVideoUrl)
})

const assetsReady = computed(() => {
  return sceneCount.value > 0 && imageAssetCount.value >= sceneCount.value
})

const progressPct = computed(() => {
  if (props.finalVideoUrl) return 100
  if (props.renderInFlight || finalStatus.value === 'rendering') return 90
  if (workflowInFlight.value && props.workflowStatusProgress != null) {
    return Math.max(0, Math.min(100, Math.round(props.workflowStatusProgress)))
  }
  if (!sceneCount.value) return 0

  const ratio = Math.min(1, Math.max(0, imageAssetCount.value / sceneCount.value))
  return Math.floor(ratio * 85)
})

const progressLabel = computed(() => {
  // Cancel state wins over every "running" label so the user doesn't see
  // contradictory progress copy while the runner walks to its next
  // checkpoint.
  if (props.cancelRequested) return '正在取消生成…'
  if (hasBlockingError.value) return `候选图生成失败（${imageAssetCount.value}/${sceneCount.value || '?'}）`
  if (workflowInFlight.value) return '处理中…'
  if (indeterminate.value) return '准备中…'
  if (props.finalVideoUrl) return '已生成'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '视频渲染中'
  if (!sceneCount.value) return '等待 Storyboard'
  if (!assetsReady.value) return `候选图生成中（${imageAssetCount.value}/${sceneCount.value}）`
  return '等待用户触发渲染'
})

const placeholderTitle = computed(() => {
  if (props.cancelRequested) return '正在取消生成'
  if (hasBlockingError.value) return '候选图生成失败'
  if (workflowInFlight.value) return '正在生成分镜'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '正在生成视频'
  if (!sceneCount.value) return '等待分镜'
  if (!assetsReady.value) return '等待候选图生成'
  return '等待渲染'
})

const placeholderDesc = computed(() => {
  if (props.cancelRequested) {
    return '已发送取消请求，等待当前步骤结束后会停止后续生成。'
  }
  if (hasBlockingError.value) {
    return blockingErrorMessage.value
  }
  if (workflowInFlight.value) {
    return props.workflowStatusMessage || 'Workflow 已提交，后端正在生成故事与分镜。完成后会自动进入候选图与视频准备阶段。'
  }
  if (props.renderInFlight || finalStatus.value === 'rendering') {
    return '视频正在合成中，请稍候（音频/字幕/画面正在拼接）。'
  }
  if (!sceneCount.value) {
    return '还没有可用的 storyboard。请在 Run 页签执行一次 workflow。'
  }
  if (!assetsReady.value) {
    return '系统正在准备每个场景的候选图，默认图生成后即可直接渲染，也可以手动改选。'
  }
  if (audioItemCount.value === 0) {
    return '当前缺少音频片段，请先完成音频生成。'
  }
  return '候选图已就绪。你可以直接使用默认图，也可以手动改选，然后点击按钮开始渲染。'
})
</script>

<style scoped>
.final-hero {
  margin: 16px 0 20px;
}

.final-title {
  text-align: center;
  font-weight: 700;
  margin: 8px 0 12px;
  font-size: 0.875rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.final-shell {
  position: relative;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto 30px;
  border-radius: 18px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  overflow: hidden;
  border: 1px solid var(--border-glass);
  box-shadow: var(--shadow-glass);
}
/* Bottom gradient that softens the contrast between dark gold studio and
   the white native progress bar. Only shown when a video is actually
   loaded (.ready) so it never tints the placeholder illustration.
   pointer-events:none → controls remain fully clickable. */
.final-shell.ready::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 64px;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(8, 5, 2, 0) 0%,
    rgba(8, 5, 2, 0.30) 55%,
    rgba(8, 5, 2, 0.46) 100%
  );
  border-bottom-left-radius: 18px;
  border-bottom-right-radius: 18px;
}
:global(:root[data-theme="pearl"]) .final-shell.ready::after {
  height: 52px;
  background: linear-gradient(
    180deg,
    rgba(46, 42, 34, 0) 0%,
    rgba(46, 42, 34, 0.10) 60%,
    rgba(46, 42, 34, 0.18) 100%
  );
}

.final-video {
  width: 100%;
  display: block;
  background: #000;
  object-fit: contain;
  max-height: 72vh;
  accent-color: var(--arc-300, #fbbf24);
}
:global(:root[data-theme="pearl"]) .final-video {
  accent-color: #b8843e;
}

.final-placeholder {
  padding: 32px 20px 45px;
  text-align: center;
  color: var(--text-primary);
}

.ph-illus {
  margin: 0 auto 20px;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.ph-svg {
  width: 80px;
  height: 80px;
  color: var(--arc-300);
  filter: drop-shadow(0 0 12px rgba(245,158,11,0.40));
}

.ph-svg-spin {
  animation: phSpin 2s linear infinite;
  transform-origin: 50% 50%;
}

@keyframes phSpin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.ph-title {
  font-size: 1.375rem;
  font-weight: 800;
  margin-bottom: 8px;
  background: linear-gradient(120deg, var(--arc-200) 0%, var(--arc-300) 50%, var(--prism-400) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.ph-desc {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 22px;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
}

.ph-progress {
  max-width: 680px;
  margin: 0 auto;
}

.ph-bar {
  height: 6px;
  background: rgba(255,255,255,0.08);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

/* Gold indeterminate shimmer */
.ph-bar.indeterminate::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    rgba(245,158,11,0.04) 0%,
    rgba(245,158,11,0.18) 35%,
    rgba(251,191,36,0.22) 50%,
    rgba(245,158,11,0.18) 65%,
    rgba(245,158,11,0.04) 100%
  );
  background-size: 240px 100%;
  animation: ph-indeterminate 1.4s linear infinite;
}

/* Gold progress fill */
.ph-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--arc-400) 0%, var(--prism-400) 100%);
  box-shadow: 0 0 8px rgba(245,158,11,0.55);
  border-radius: 999px;
  transition: width 220ms ease-out;
  position: relative;
  z-index: 1;
}

.ph-bar.indeterminate .ph-bar-fill {
  width: 0 !important;
}

@keyframes ph-indeterminate {
  from { background-position: -240px 0; }
  to   { background-position:  240px 0; }
}

.ph-meta {
  margin-top: 10px;
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  justify-content: center;
  gap: 8px;
}

.ph-dot { opacity: 0.5; }

/* Minimal status chip shown when global bar is covering the progress */
.ph-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(245,158,11,0.20);
  background: rgba(245,158,11,0.07);
  font-size: 12px;
  color: var(--text-muted);
  margin: 0 auto;
}

.ph-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--arc-400);
  box-shadow: 0 0 6px rgba(245,158,11,0.70);
  animation: dotPulse 1.4s ease-in-out infinite;
}

@keyframes dotPulse {
  0%,100% { opacity: 1; transform: scale(1); }
  50%      { opacity: 0.5; transform: scale(0.75); }
}

.render-button {
  margin-top: 18px;
  min-width: 220px;
  height: 42px;
  padding: 0 18px;
  border: 1px solid rgba(245,158,11,0.45);
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, rgba(245,158,11,0.22) 0%, rgba(249,115,22,0.16) 100%);
  color: #fff;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.render-button:hover:not(:disabled) {
  border-color: rgba(245,158,11,0.75);
  box-shadow: 0 0 20px rgba(245,158,11,0.40);
}
.render-button:disabled { cursor: not-allowed; opacity: 0.40; }

.final-json {
  max-width: 1100px;
  margin: 10px auto 0;
  background: var(--surface-overlay-strong);
  border: 1px solid rgba(245,158,11,0.10);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  overflow: auto;
}
</style>
