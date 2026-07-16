<template>
  <section class="final-hero">
    <h3 class="final-title">最终视频</h3>

    <div class="final-shell" :class="{ ready: videoLoadState === 'ready' }">
      <video
        v-if="finalVideoUrl"
        :key="videoPlayerKey"
        :src="videoPreviewUrl"
        controls
        playsinline
        preload="metadata"
        class="final-video"
        @loadedmetadata="$emit('video-ready')"
        @canplay="$emit('video-ready')"
        @error="$emit('video-error')"
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
            <!-- During any in-flight phase, use InlineStatusPulse so the
                 label gets the same left-pulse + trailing 3-dot ellipsis
                 animation as the top global progress bar. Outside in-flight
                 (e.g. settled-failure, 等待用户触发渲染), render the plain
                 label so we don't imply ongoing work. -->
            <InlineStatusPulse
              v-if="isAnyLoading"
              :text="progressLabel"
              variant="running"
            />
            <span v-else>{{ progressLabel }}</span>
          </div>
        </div>
        <!-- Global bar is active → pulsing status chip. Uses the same
             InlineStatusPulse component the top bar uses, so the chip
             carries the same left pulse dot + trailing 3-dot ellipsis
             animation. -->
        <div v-else class="ph-status-chip">
          <InlineStatusPulse :text="progressLabel" variant="running" />
        </div>

        <!-- Manual-mode render CTA. Shows in the BODY of the placeholder
             (the same area the user is already looking at) so it's
             impossible to miss. Visible only when:
               • renderMode === 'manual' (auto mode self-renders via watcher)
               • assets are ready (candidates done + audio present)
               • no render currently in flight
               • no final video URL yet
             The header also has a smaller version of this button for
             alignment with the section title; keeping both is harmless,
             body version is the user's primary affordance.
        -->
        <button
          v-if="
            renderMode === 'manual' &&
            assetsReady &&
            !hasFailedAssets &&
            !hasBlockingError &&
            !renderInFlight &&
            !finalVideoUrl &&
            audioItemCount > 0 &&
            !sceneRefreshingId
          "
          type="button"
          class="ph-render-cta"
          @click="emit('render')"
        >
          生成视频
        </button>
        <button
          v-if="hasBlockingError"
          type="button"
          class="ph-discard-cta"
          @click="emit('discard')"
        >
          放弃当前生成
        </button>
      </div>
    </div>

    <div v-if="finalVideoUrl" class="ph-meta">
      <span>{{ videoStatusText }}</span>
      <template v-if="videoLoadState === 'failed'">
        <button type="button" class="ph-render-cta" @click="$emit('reload-video')">
          重新加载
        </button>
        <a class="ph-render-cta" :href="finalVideoUrl" target="_blank" rel="noopener noreferrer">
          打开原视频
        </a>
      </template>
    </div>

    <!-- JSON only shown in dev/debug context, hidden in main view -->
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import GenerationLoadingAnimation from './studio/GenerationLoadingAnimation.vue'
import InlineStatusPulse from './studio/InlineStatusPulse.vue'
import type { ImageGenerationSummary, WorkflowProgressSummary } from '../lib/workflowState'

type UnknownRecord = Record<string, unknown>

const props = defineProps<{
  finalVideoUrl: string
  videoPreviewUrl: string
  videoPlayerKey: string
  videoLoadState: 'idle' | 'loading' | 'ready' | 'retrying' | 'failed'
  videoStatusText: string
  finalVideoText: string
  workflowResponse: UnknownRecord | null
  renderInFlight: boolean
  loading: boolean
  refreshingImages?: boolean   // true when image review refresh is running (top bar already covers it)
  cancelRequested?: boolean    // user has clicked "取消生成"; overrides running titles
  pausedByUser?: boolean       // user explicitly cancelled image refresh — render as "已暂停", not "失败"
  errorMessage?: string
  workflowStatusMessage?: string
  workflowStatusProgress?: number | null
  imageGenerationSummary?: ImageGenerationSummary
  workflowProgressSummary?: WorkflowProgressSummary
  // Render mode drives both the banner copy and an in-body prominent
  // render button. In 'manual' mode the user is responsible for clicking
  // through (or swapping a candidate first); in 'auto' mode the system
  // auto-triggers the render watcher and the button stays hidden.
  renderMode?: 'auto' | 'manual'
  // Scene_id currently being regenerated via the per-scene "重新生成"
  // button. Different from `refreshingImages` (which is the bulk refresh
  // covering all scenes). When set, the placeholder copy swaps to
  // "正在重新生成 …" so the user sees activity while waiting.
  sceneRefreshingId?: string
}>()

const emit = defineEmits<{
  (e: 'render'): void
  (e: 'discard'): void
  (e: 'video-ready'): void
  (e: 'video-error'): void
  (e: 'reload-video'): void
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
  if (props.workflowProgressSummary) return props.workflowProgressSummary.indeterminate
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

// Scenes whose image generation failed and were persisted as
// status='failed' placeholders by the backend (B1 in PR #154). When
// any exist, the panel must short-circuit into a "图片生成失败" state
// — rendering is blocked until the user clicks per-scene 重试. Without
// this, length(image_assets.assets) reaches scene_count and assetsReady
// flips to true, and the panel falsely shows "等待渲染 / 生成视频".
const failedAssetCount = computed(() => {
  if (props.imageGenerationSummary) return props.imageGenerationSummary.failedCount
  const n = asNum(imageAssets.value?.failed_count)
  const ids = imageAssets.value?.failed_scene_ids
  const assets = imageAssets.value?.assets
  const failedFromStatus = Array.isArray(assets)
    ? assets.filter((a) => {
        const status = asStr((a as UnknownRecord | null)?.status).toLowerCase()
        return status === 'failed'
      }).length
    : 0
  return Math.max(
    n != null && n >= 0 ? n : 0,
    Array.isArray(ids) ? ids.length : 0,
    failedFromStatus,
  )
})
const hasFailedAssets = computed(() => failedAssetCount.value > 0)
const generatedAssetCount = computed(() => {
  if (props.imageGenerationSummary) return props.imageGenerationSummary.readyCount
  const n = asNum(imageAssets.value?.generated_count)
  if (n != null && n >= 0) return n
  return Math.max(0, imageAssetCount.value - failedAssetCount.value)
})

// Title of the scene currently being refreshed — appended to the
// inline progress pill so it matches the top progress bar's
// "候选图生成中：11/12 · 美好的下午" copy. Without this, the user
// could see "11/12 · 美好的下午" up top and just "11/12" in the pill
// for the same in-flight run — confusing state mismatch.
const currentRefreshingSceneTitle = computed(() => {
  const id = props.sceneRefreshingId
  if (!id) return ''
  const scenes = storyboard.value?.scenes
  if (!Array.isArray(scenes)) return ''
  const scene = (scenes as Array<Record<string, unknown>>).find(
    (s) => asStr(s?.scene_id) === id,
  )
  return scene ? asStr(scene.scene_title) : ''
})

const audioItemCount = computed(() => {
  const items = audioSegments.value?.items
  return Array.isArray(items) ? items.length : 0
})

const finalStatus = computed(() => asStr(finalVideo.value?.status).toLowerCase())
const workflowInFlight = computed(() => props.loading && !outputs.value)

// Any active phase that should swap the static clapperboard for the
// AI-workflow loading animation: initial workflow, image refresh,
// render, OR per-scene retry (sceneRefreshingId set). Without the
// per-scene case the placeholder icon stays static during "重新生成"
// even though we're showing "正在重新生成候选图" text — looks broken.
const isAnyLoading = computed(() => {
  return Boolean(
    props.loading ||
    props.renderInFlight ||
    props.refreshingImages ||
    props.sceneRefreshingId ||
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

const assetsReady = computed(() => {
  if (props.imageGenerationSummary) {
    return props.imageGenerationSummary.overallState === 'ready'
  }
  return (
    sceneCount.value > 0 &&
    generatedAssetCount.value >= sceneCount.value &&
    !hasFailedAssets.value
  )
})

const blockingErrorMessage = computed(() => asStr(props.errorMessage).trim())
const isFinalVideoRenderError = computed(() =>
  blockingErrorMessage.value.startsWith('最终视频生成失败：'),
)
const isStaleGenericNetworkError = computed(() => {
  if (!assetsReady.value || hasFailedAssets.value) return false
  return [
    'Failed to fetch',
    'Load failed',
    'NetworkError when attempting to fetch resource.',
  ].includes(blockingErrorMessage.value)
})
const hasBlockingError = computed(() => {
  const state = props.imageGenerationSummary?.overallState
  if (state && state !== 'idle') {
    if (isFinalVideoRenderError.value) return !props.renderInFlight
    if (blockingErrorMessage.value.includes('workflow 输入参数')) return true
    return false
  }
  return Boolean(
    blockingErrorMessage.value &&
    !isStaleGenericNetworkError.value &&
    !props.loading &&
    !props.finalVideoUrl,
  )
})

const blockingErrorTitle = computed(() => {
  if (isFinalVideoRenderError.value) {
    return '最终视频生成失败'
  }
  if (blockingErrorMessage.value.includes('workflow 输入参数')) {
    return '无法继续当前草稿'
  }
  return '候选图生成失败'
})

const progressPct = computed(() => {
  if (props.workflowProgressSummary?.overallPercent != null) {
    return props.workflowProgressSummary.overallPercent
  }
  if (props.finalVideoUrl) return 100
  if (props.renderInFlight || finalStatus.value === 'rendering') return 0
  if (workflowInFlight.value && props.workflowStatusProgress != null) {
    return Math.max(0, Math.min(100, Math.round(props.workflowStatusProgress)))
  }
  if (!sceneCount.value) return 0

  // Failed scenes count against progress — show only the generated
  // ratio so the bar visibly stays below the "ready" threshold.
  if (hasFailedAssets.value) {
    const ratio = Math.min(1, Math.max(0, generatedAssetCount.value / sceneCount.value))
    return Math.floor(ratio * 85)
  }

  const ratio = Math.min(1, Math.max(0, imageAssetCount.value / sceneCount.value))
  return Math.floor(ratio * 85)
})

const progressLabel = computed(() => {
  // Cancel state wins over every "running" label so the user doesn't see
  // contradictory progress copy while the runner walks to its next
  // checkpoint. pausedByUser is checked BEFORE hasBlockingError because
  // cancelImageReviewRefresh sets errorMessage="已取消..." which would
  // otherwise trip the "失败" branch — but a user-initiated pause is not
  // a failure, and the copy should reflect that.
  if (props.cancelRequested) return '正在取消生成…'
  if (props.pausedByUser) return `候选图已暂停（${generatedAssetCount.value}/${sceneCount.value || '?'}）`
  if (props.workflowProgressSummary?.stageLabel) {
    return props.workflowProgressSummary.stageLabel
  }
  if (hasBlockingError.value) {
    return isFinalVideoRenderError.value
      ? '最终视频生成失败'
      : '候选图生成未完成'
  }
  // Persisted per-scene failures (B1). Must come BEFORE any check that
  // counts asset length, since failed placeholders inflate the length
  // and would otherwise let the state machine cross into "等待渲染".
  if (hasFailedAssets.value && !props.refreshingImages && !props.sceneRefreshingId) {
    return `候选图生成完成，${failedAssetCount.value} 个场景待处理`
  }
  if (workflowInFlight.value) return '处理中…'
  if (indeterminate.value) return '准备中…'
  if (props.finalVideoUrl) return '已生成'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '视频渲染中'
  if (!sceneCount.value) return '等待 Storyboard'
  // Per-scene retry — applies whether or not assetsReady is true:
  //   - assetsReady=false (重试该场景 on a failed scene): retry to repair
  //   - assetsReady=true  (重新生成 on a done scene): retry to swap a
  //     candidate while the workflow is otherwise settled
  // Both want the label to reflect the active retry, not the surrounding
  // settled state. Counts are dropped because they don't move during a
  // single-scene retry (stays e.g. 5/6 throughout) and would just add
  // noise — the scene title alone tells the user what's in flight.
  if (props.sceneRefreshingId && !props.refreshingImages) {
    const sceneSuffix = currentRefreshingSceneTitle.value
      ? ` · ${currentRefreshingSceneTitle.value}`
      : ''
    return `正在重新生成${sceneSuffix}`
  }
  if (!assetsReady.value) {
    if (props.refreshingImages) {
      const sceneSuffix = currentRefreshingSceneTitle.value
        ? ` · ${currentRefreshingSceneTitle.value}`
        : ''
      // Exclude failed placeholders from the count — a partial bulk
      // refresh after a prior failure would otherwise show e.g. 12/12.
      return `候选图生成中（${generatedAssetCount.value}/${sceneCount.value}${sceneSuffix}）`
    }
    if (generatedAssetCount.value > 0) return `候选图已暂停（${generatedAssetCount.value}/${sceneCount.value}）`
    return `候选图待生成（0/${sceneCount.value}）`
  }
  return '等待用户触发渲染'
})

const placeholderTitle = computed(() => {
  if (props.cancelRequested) return '正在取消生成'
  if (props.pausedByUser) return '候选图已暂停'
  if (hasBlockingError.value) return blockingErrorTitle.value
  if (hasFailedAssets.value && !props.refreshingImages && !props.sceneRefreshingId) {
    return `候选图生成完成，${failedAssetCount.value} 个场景待处理`
  }
  if (workflowInFlight.value) return '正在生成分镜'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '正在生成视频'
  if (!sceneCount.value) return '等待分镜'
  // Single-scene retry (manual-mode "重新生成" button on a done scene)
  // — show activity even though the OVERALL render isn't in flight.
  // Gated on !refreshingImages so the initial bulk refresh (which
  // ALSO sets sceneRefreshingId as it walks scenes) falls through to
  // its own "正在生成候选图" copy below.
  if (props.sceneRefreshingId && !props.refreshingImages) return '正在重新生成候选图'
  if (!assetsReady.value) {
    if (props.refreshingImages) return '正在生成候选图'
    if (imageAssetCount.value > 0) return '候选图已暂停'
    return '候选图待生成'
  }
  return '等待渲染'
})

const placeholderDesc = computed(() => {
  if (props.cancelRequested) {
    return '已发送取消请求，等待当前步骤结束后会停止后续生成。'
  }
  if (props.pausedByUser) {
    return '已取消剩余候选图生成。可点击下方「继续生成候选图」恢复，或「放弃当前生成」清空草稿。'
  }
  if (hasBlockingError.value) {
    return blockingErrorMessage.value
  }
  if (hasFailedAssets.value && !props.refreshingImages && !props.sceneRefreshingId) {
    return `${generatedAssetCount.value} 个场景已就绪，${failedAssetCount.value} 个场景生成失败。请点击对应场景的「重试该场景」按钮。`
  }
  if (workflowInFlight.value) {
    return props.workflowStatusMessage || 'Workflow 已提交，后端正在生成故事与分镜。完成后会自动进入候选图与视频准备阶段。'
  }
  if (props.renderInFlight || finalStatus.value === 'rendering') {
    return '视频正在合成中，请稍候（音频/字幕/画面正在拼接）。'
  }
  if (!sceneCount.value) {
    return '还没有可用的分镜。请先在「创作故事」页签输入故事主题，并点击「开始创作」生成内容。'
  }
  // Match the title above — single-scene retry has its own description.
  // Gated on !refreshingImages so the initial bulk refresh's own copy
  // takes priority (it sets sceneRefreshingId per-scene as it walks
  // through, but the user wants to see "1/6 候选图生成中", not
  // "正在为 scene_01 重新生成").
  if (props.sceneRefreshingId && !props.refreshingImages) {
    return `正在为 ${props.sceneRefreshingId} 重新生成候选图，请稍候。`
  }
  if (!assetsReady.value) {
    if (props.refreshingImages) {
      return props.renderMode === 'manual'
        ? '系统正在为每个场景生成候选图，生成完成后请审核并点击「生成视频」。'
        : '系统正在为每个场景自动挑选最佳候选图，生成完成后即可直接渲染。'
    }
    if (imageAssetCount.value > 0) return '剩余候选图尚未生成。点击下方「继续生成候选图」可恢复。'
    return '候选图尚未生成。点击下方「立即生成候选图」开始。'
  }
  if (audioItemCount.value === 0) {
    return '当前缺少音频片段，请先完成音频生成。'
  }
  if (props.renderMode === 'manual') {
    return '候选图已就绪，你可以在下方审核每个场景的画面、必要时切换备选，确认后点击「生成视频」开始合成。'
  }
  return '候选图已就绪，系统已自动为每个场景挑选最佳画面。'
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
.final-video {
  width: 100%;
  display: block;
  background: #000;
  object-fit: contain;
  max-height: 72vh;
  accent-color: var(--arc-300, #fbbf24);
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

/* Manual-mode "生成视频" CTA. Placed inside the placeholder body so the
   user looking at "等待用户触发渲染" can't miss the action. Sized to
   anchor visual attention without dominating the placeholder card. */
.ph-render-cta {
  margin: 16px auto 0;
  padding: 10px 28px;
  border: 1px solid var(--primary-action-border, rgba(224, 180, 82, 0.32));
  border-radius: 10px;
  background: var(--primary-action-bg, linear-gradient(135deg, rgba(10, 8, 4, 0.96), rgba(164, 116, 34, 0.50)));
  color: var(--primary-action-text, rgba(255, 238, 190, 0.96));
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  box-shadow: var(--primary-action-shadow, 0 12px 28px rgba(0, 0, 0, 0.30));
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ph-render-cta:hover {
  transform: translateY(-1px);
  filter: brightness(1.06);
  border-color: var(--primary-action-border-hover, rgba(232, 192, 96, 0.48));
  box-shadow: var(--primary-action-shadow-hover, 0 14px 32px rgba(0, 0, 0, 0.36));
}
.ph-render-cta:active { transform: translateY(0); }

.ph-discard-cta {
  margin: 16px auto 0;
  padding: 9px 24px;
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 10px;
  background: rgba(245, 158, 11, 0.08);
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 650;
  letter-spacing: 0.03em;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
  transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.ph-discard-cta:hover {
  transform: translateY(-1px);
  border-color: rgba(245, 158, 11, 0.48);
  background: rgba(245, 158, 11, 0.14);
}
.ph-discard-cta:active { transform: translateY(0); }

/* Status chip shown when global bar is covering the progress. The
   left pulse dot + trailing 3-dot ellipsis come from the embedded
   InlineStatusPulse component, so the chip only owns the pill
   container styling here. */
.ph-status-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid rgba(245,158,11,0.20);
  background: rgba(245,158,11,0.07);
  font-size: 12px;
  margin: 0 auto;
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

@media (max-width: 768px) {
  .final-hero {
    margin: 10px 0 14px;
  }

  .final-title {
    margin-bottom: 10px;
    font-size: 0.8125rem;
  }

  .final-shell {
    margin-bottom: 18px;
    border-radius: 14px;
  }

  .final-video {
    max-height: min(54vh, 320px);
  }

  .final-placeholder {
    padding: 24px 14px 30px;
  }

  .ph-illus {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
  }

  .ph-svg {
    width: 64px;
    height: 64px;
  }

  .ph-title {
    font-size: 1.15rem;
  }

  .ph-desc {
    margin-bottom: 18px;
    font-size: 12px;
  }

  .ph-meta {
    flex-wrap: wrap;
    line-height: 1.5;
  }

  .ph-render-cta {
    width: 100%;
    max-width: 240px;
    min-height: 44px;
  }
}
</style>

<style>
:root[data-theme="pearl"] .final-hero .final-shell.ready::after {
  height: 52px;
  background: linear-gradient(
    180deg,
    rgba(46, 42, 34, 0) 0%,
    rgba(46, 42, 34, 0.10) 60%,
    rgba(46, 42, 34, 0.18) 100%
  );
}

:root[data-theme="pearl"] .final-hero .final-video {
  accent-color: #b8843e;
}
</style>
