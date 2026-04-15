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
          <div class="ph-bar">
            <div class="ph-bar-fill" :style="{ width: progressPct + '%' }"></div>
          </div>
          <div class="ph-meta">
            <span>{{ progressPct }}%</span>
            <span class="ph-dot">·</span>
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
const imageReview = computed(() => asObj(outputs.value?.image_review))
const finalVideo = computed(() => asObj(outputs.value?.final_video))

const sceneCount = computed(() => {
  const n = asNum(storyboard.value?.scene_count)
  return n && n > 0 ? Math.floor(n) : 0
})

const selectedCount = computed(() => {
  const arr = imageReview.value?.selected_assets
  return Array.isArray(arr) ? arr.length : 0
})

const finalStatus = computed(() => asStr(finalVideo.value?.status).toLowerCase())
const finalEnabled = computed(() => Boolean(finalVideo.value?.enabled))

const progressPct = computed(() => {
  if (props.finalVideoUrl) return 100

  // render 请求已发出：先给一个真实但保守的“渲染中”区间（不做假计时，只反映状态）
  if (props.renderInFlight || finalStatus.value === 'rendering') {
    // 选图完成度决定渲染前置进度（最多到 85%），渲染中固定显示 90%
    return 90
  }

  // 没开始渲染：用“选图完成度”作为真实进度
  const total = sceneCount.value
  if (total <= 0) return 0
  const ratio = Math.min(1, Math.max(0, selectedCount.value / total))
  // 选图阶段最多显示到 85%，避免误导 “快好了但其实还没渲染”
  return Math.floor(ratio * 85)
})

const progressLabel = computed(() => {
  if (props.finalVideoUrl) return '已生成'
  if (props.renderInFlight || finalStatus.value === 'rendering') return '视频渲染中'
  if (!sceneCount.value) return '等待 Storyboard'
  if (selectedCount.value < sceneCount.value) {
    return `选图中（${selectedCount.value}/${sceneCount.value}）`
  }
  // 选图完成但还没渲染
  if (finalEnabled.value && finalStatus.value === 'skipped') return '等待渲染触发'
  return '等待渲染触发'
})

const placeholderTitle = computed(() => {
  if (props.renderInFlight || finalStatus.value === 'rendering') return '正在生成视频'
  if (!sceneCount.value) return '等待分镜'
  if (selectedCount.value < sceneCount.value) return '等待选图完成'
  return '等待渲染'
})

const placeholderDesc = computed(() => {
  if (props.renderInFlight || finalStatus.value === 'rendering')
    return '视频正在合成中，请稍候（音频/字幕/画面正在拼接）。'
  if (!sceneCount.value) return '请先在 Run 执行一次，生成 storyboard。'
  if (selectedCount.value < sceneCount.value)
    return '请先完成每个场景的候选图生成与选择。'
  return '选图已完成，等待触发 Final Video 渲染。'
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
  /* 关键：9:16 在网页端“居中留边”，不怪异 */
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