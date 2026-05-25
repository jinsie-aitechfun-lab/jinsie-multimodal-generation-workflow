<template>
  <section class="final-hero">
    <h3 class="final-title">Final Video</h3>

    <div class="final-shell" :class="{ ready: Boolean(finalVideoUrl) }">
      <video
        v-if="finalVideoUrl"
        :src="finalVideoUrl"
        controls
        playsinline
        class="final-video"
      />

      <div v-else class="final-placeholder">
        <div class="ph-title">{{ placeholderTitle }}</div>
        <div class="ph-desc">{{ placeholderDesc }}</div>

        <div class="ph-progress">
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
      </div>
    </div>

    <pre v-if="finalVideoText" class="final-json">{{ finalVideoText }}</pre>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type UnknownRecord = Record<string, unknown>

const props = defineProps<{
  finalVideoUrl: string
  finalVideoText: string
  workflowResponse: UnknownRecord | null
  renderInFlight: boolean
  loading: boolean
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
  if (hasBlockingError.value) return '候选图生成失败'
  if (workflowInFlight.value) return '正在生成分镜'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '正在生成视频'
  if (!sceneCount.value) return '等待分镜'
  if (!assetsReady.value) return '等待候选图生成'
  return '等待渲染'
})

const placeholderDesc = computed(() => {
  if (hasBlockingError.value) {
    return `${blockingErrorMessage.value}。请在 Review 中重新生成失败场景，全部候选图生成后才能渲染视频。`
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
}

.final-shell {
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
  border-radius: 18px;
  background: linear-gradient(180deg, #0b1220 0%, #0b152b 100%);
  overflow: hidden;
  border: 1px solid rgba(17, 24, 39, 0.12);
}

.final-video {
  width: 100%;
  display: block;
  background: transparent;
  object-fit: contain;
  max-height: 72vh;
}

.final-placeholder {
  padding: 28px 16px 22px;
  text-align: center;
  color: rgba(255, 255, 255, 0.92);
}

.ph-title {
  font-size: 22px;
  font-weight: 800;
  margin-bottom: 6px;
}

.ph-desc {
  font-size: 14px;
  opacity: 0.85;
  margin-bottom: 18px;
}

.ph-progress {
  max-width: 720px;
  margin: 0 auto;
}

.ph-bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.14);
  border-radius: 999px;
  overflow: hidden;
}

.ph-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #6ea8fe 0%, #9f7aea 60%, #a78bfa 100%);
  border-radius: 999px;
  transition: width 180ms ease-out;
}

.ph-bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  overflow: hidden;
  position: relative;
}

/* ✅ 企业风格：全宽的 indeterminate 背景 shimmer */
.ph-bar.indeterminate::before {
  content: '';
  position: absolute;
  inset: 0;
  /* 低对比度、低饱和：不抢真实进度 */
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.06) 0%,
    rgba(255, 255, 255, 0.14) 20%,
    rgba(255, 255, 255, 0.06) 40%,
    rgba(255, 255, 255, 0.06) 100%
  );
  background-size: 240px 100%;
  animation: ph-indeterminate 1.1s linear infinite;
}

/* ✅ 真实进度条仍然用 fill（你原来的渐变） */
.ph-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #6ea8fe 0%, #9f7aea 60%, #a78bfa 100%);
  border-radius: 999px;
  transition: width 180ms ease-out;
  position: relative;
  z-index: 1;
}

/* ✅ indeterminate 时，不显示 fill（避免“假进度”） */
.ph-bar.indeterminate .ph-bar-fill {
  width: 0 !important;
}

@keyframes ph-indeterminate {
  from {
    background-position: -240px 0;
  }
  to {
    background-position: 240px 0;
  }
}

.ph-meta {
  margin-top: 10px;
  font-size: 13px;
  opacity: 0.9;
  display: flex;
  justify-content: center;
  gap: 8px;
}

.ph-dot {
  opacity: 0.6;
}

.render-button {
  margin-top: 18px;
  min-width: 220px;
  height: 42px;
  padding: 0 18px;
  border: none;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  background: #ffffff;
  color: #111827;
}

.render-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.final-json {
  max-width: 1100px;
  margin: 10px auto 0;
  background: #f7f7f9;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 12px;
  padding: 10px 12px;
  font-size: 12px;
  overflow: auto;
}
</style>
