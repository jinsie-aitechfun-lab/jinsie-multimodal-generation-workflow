<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  storyText: string
  storyboardText: string
  imagePromptsText: string
  imageAssetsText: string
  imageReviewText: string
  videoPromptsText: string
  narrationText: string
  subtitlesText: string
  renderPlanText: string
  characterCandidatesText: string
  characterManifestText: string
}>()

type SceneSummary = {
  id: string
  title: string
  description: string
}

type PromptSummary = {
  id: string
  prompt: string
}

function parseJson(text: string): unknown {
  if (!text.trim()) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

const hasDeveloperContent = computed(() => Boolean(
  props.storyboardText ||
  props.imagePromptsText ||
  props.imageAssetsText ||
  props.imageReviewText ||
  props.videoPromptsText ||
  props.narrationText ||
  props.subtitlesText ||
  props.renderPlanText ||
  props.characterCandidatesText ||
  props.characterManifestText
))

const storyboardScenes = computed<SceneSummary[]>(() => {
  const parsed = parseJson(props.storyboardText)
  const record = parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : {}
  const scenesValue: unknown[] = Array.isArray(record.scenes)
    ? record.scenes
    : record.storyboard && typeof record.storyboard === 'object' && Array.isArray((record.storyboard as Record<string, unknown>).scenes)
      ? (record.storyboard as Record<string, unknown>).scenes as unknown[]
      : []

  return scenesValue.map((scene, index) => {
    const item = scene && typeof scene === 'object' ? scene as Record<string, unknown> : {}
    const fallbackId = `场景 ${String(index + 1).padStart(2, '0')}`
    const id = String(item.scene_id || item.id || fallbackId)
    const title = String(item.title || item.scene_title || item.stage || fallbackId)
    const description = String(
      item.narration ||
      item.voiceover ||
      item.description ||
      item.visual_description ||
      item.action ||
      ''
    )
    return { id, title, description }
  })
})

const imagePromptEntries = computed<PromptSummary[]>(() => {
  const parsed = parseJson(props.imagePromptsText)
  if (!parsed) return []

  const source = parsed && typeof parsed === 'object' && Array.isArray((parsed as Record<string, unknown>).prompts)
    ? (parsed as Record<string, unknown>).prompts
    : parsed

  if (Array.isArray(source)) {
    return source.map((entry, index) => {
      const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
      return {
        id: String(item.scene_id || item.id || `场景 ${String(index + 1).padStart(2, '0')}`),
        prompt: stringifyValue(item.prompt || item.image_prompt || entry),
      }
    })
  }

  if (source && typeof source === 'object') {
    return Object.entries(source as Record<string, unknown>).map(([key, value]) => ({
      id: key,
      prompt: stringifyValue(
        value && typeof value === 'object'
          ? (value as Record<string, unknown>).prompt || (value as Record<string, unknown>).image_prompt || value
          : value
      ),
    }))
  }

  return []
})
</script>

<template>
  <section
    v-if="hasDeveloperContent"
    class="result-panel developer-results-panel"
  >
    <details>
      <summary>生成细节</summary>

      <section v-if="storyboardText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">分镜结构</summary>
          <div v-if="storyboardScenes.length" class="scene-summary-list">
            <article
              v-for="scene in storyboardScenes"
              :key="scene.id"
              class="scene-summary-card"
            >
              <strong>{{ scene.title }}</strong>
              <span>{{ scene.id }}</span>
              <p v-if="scene.description">{{ scene.description }}</p>
            </article>
          </div>
          <p v-else class="developer-empty-copy">
            分镜结构已生成，可在开发者原始数据中查看完整 JSON。
          </p>
        </details>
      </section>

      <section v-if="imagePromptsText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">图片提示词</summary>
          <div v-if="imagePromptEntries.length" class="prompt-summary-list">
            <details
              v-for="entry in imagePromptEntries"
              :key="entry.id"
              class="prompt-summary-item"
            >
              <summary>{{ entry.id }}</summary>
              <p>{{ entry.prompt }}</p>
            </details>
          </div>
          <p v-else class="developer-empty-copy">
            图片提示词已生成，可在开发者原始数据中查看完整 JSON。
          </p>
        </details>
      </section>

      <section class="developer-result-block">
        <details>
          <summary class="developer-subsummary">开发者原始数据</summary>

          <div v-if="storyboardText" class="raw-data-block">
            <h2 class="section-title">完整 Storyboard JSON</h2>
            <pre class="light-result">{{ storyboardText }}</pre>
          </div>

          <div v-if="imagePromptsText" class="raw-data-block">
            <h2 class="section-title">Image Prompts JSON</h2>
            <pre class="light-result">{{ imagePromptsText }}</pre>
          </div>

          <div v-if="imageAssetsText" class="raw-data-block">
            <h2 class="section-title">图片素材原始数据</h2>
            <pre class="light-result">{{ imageAssetsText }}</pre>
          </div>

          <div v-if="imageReviewText" class="raw-data-block">
            <h2 class="section-title">画面审核 / 素材选择原始数据</h2>
            <pre class="light-result">{{ imageReviewText }}</pre>
          </div>

          <div v-if="videoPromptsText" class="raw-data-block">
            <h2 class="section-title">视频提示词原始数据</h2>
            <pre class="light-result">{{ videoPromptsText }}</pre>
          </div>

          <div v-if="narrationText" class="raw-data-block">
            <h2 class="section-title">旁白原始数据</h2>
            <pre class="light-result">{{ narrationText }}</pre>
          </div>

          <div v-if="subtitlesText" class="raw-data-block">
            <h2 class="section-title">字幕原始数据</h2>
            <pre class="light-result">{{ subtitlesText }}</pre>
          </div>

          <div v-if="renderPlanText" class="raw-data-block">
            <h2 class="section-title">渲染计划原始数据</h2>
            <pre class="light-result">{{ renderPlanText }}</pre>
          </div>

          <div v-if="characterCandidatesText" class="raw-data-block">
            <h2 class="section-title">角色候选原始数据</h2>
            <pre class="light-result">{{ characterCandidatesText }}</pre>
          </div>

          <div v-if="characterManifestText" class="raw-data-block">
            <h2 class="section-title">角色设定清单原始数据</h2>
            <pre class="light-result">{{ characterManifestText }}</pre>
          </div>
        </details>
      </section>
    </details>
  </section>
</template>

<style scoped>
.story-panel,
.result-panel {
  margin-top: 16px;
  padding: 18px 20px;
  border-radius: 14px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(245,158,11,0.12);
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(251,191,36,0.06);
}

.developer-results-panel summary {
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.developer-results-panel summary:hover {
  color: var(--arc-300);
}

.developer-result-block {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(245,158,11,0.08);
}

.developer-subsummary {
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}

.developer-subsummary:hover {
  color: var(--arc-300);
}

.scene-summary-list,
.prompt-summary-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.scene-summary-card,
.prompt-summary-item {
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--surface-overlay-strong);
  border: 1px solid rgba(245,158,11,0.08);
}

.scene-summary-card strong {
  display: block;
  color: var(--arc-300);
  font-size: 0.875rem;
  margin-bottom: 4px;
}

.scene-summary-card span {
  display: block;
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-bottom: 6px;
}

.scene-summary-card p,
.prompt-summary-item p,
.developer-empty-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.7;
  white-space: pre-wrap;
}

.prompt-summary-item summary {
  color: var(--arc-300);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}

.prompt-summary-item p {
  margin-top: 8px;
}

.raw-data-block {
  margin-top: 14px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.story-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.light-result {
  margin: 8px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}
</style>
