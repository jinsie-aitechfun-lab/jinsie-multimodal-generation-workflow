<script setup lang="ts">
import { computed, ref } from 'vue'

type StepName =
  | 'story'
  | 'storyboard'
  | 'image_prompts'
  | 'video_prompts'
  | 'narration'
  | 'subtitles'
  | 'render_plan'

type StepResult = {
  name?: string
  status?: string
  output?: Record<string, unknown>
}

type WorkflowRunResponse = {
  workflow_id?: string
  session_id?: string
  run_id?: string
  status?: string
  steps?: StepResult[]
  outputs?: Record<string, unknown>
  timestamp?: string
  [key: string]: unknown
}

const STEP_OPTIONS: Array<{ label: string; value: StepName }> = [
  { label: 'Story', value: 'story' },
  { label: 'Storyboard', value: 'storyboard' },
  { label: 'Image Prompts', value: 'image_prompts' },
  { label: 'Video Prompts', value: 'video_prompts' },
  { label: 'Narration', value: 'narration' },
  { label: 'Subtitles', value: 'subtitles' },
  { label: 'Render Plan', value: 'render_plan' },
]

const DEFAULT_STEPS: StepName[] = [
  'story',
  'storyboard',
  'image_prompts',
  'video_prompts',
  'narration',
  'subtitles',
  'render_plan',
]

const loading = ref(false)
const errorMessage = ref('')
const resultText = ref('')
const storyText = ref('')
const storyboardText = ref('')
const narrationText = ref('')
const subtitlesText = ref('')
const renderPlanText = ref('')

const topic = ref('写一个关于小猫冒险的故事')
const sessionId = ref('demo-session-001')
const audience = ref('children')
const tone = ref('warm')
const visualStyle = ref('storybook')
const characterStyle = ref('animal')
const voiceStyle = ref('warm_female')
const durationSec = ref(60)
const language = ref('zh-CN')
const subtitleEnabled = ref(true)
const videoProvider = ref('mock')
const outputMode = ref('full_video')

const selectedSteps = ref<StepName[]>([...DEFAULT_STEPS])
const stepSummaries = ref<Array<{ name: string; status: string; preview: string }>>(
  []
)

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

const canSubmit = computed(() => {
  return topic.value.trim().length > 0 && selectedSteps.value.length > 0 && !loading.value
})

function stringifyPretty(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function extractStoryText(data: WorkflowRunResponse): string {
  const outputsStory = data.outputs?.story
  if (
    outputsStory &&
    typeof outputsStory === 'object' &&
    'text' in outputsStory &&
    typeof outputsStory.text === 'string'
  ) {
    return outputsStory.text
  }
  return ''
}

function extractStoryboardText(data: WorkflowRunResponse): string {
  const storyboard = data.outputs?.storyboard
  if (
    storyboard &&
    typeof storyboard === 'object' &&
    'scenes' in storyboard &&
    Array.isArray(storyboard.scenes)
  ) {
    return stringifyPretty(storyboard.scenes)
  }
  return ''
}

function extractNarrationText(data: WorkflowRunResponse): string {
  const narration = data.outputs?.narration
  if (
    narration &&
    typeof narration === 'object' &&
    'full_text' in narration &&
    typeof narration.full_text === 'string'
  ) {
    return narration.full_text
  }
  return ''
}

function extractSubtitlesText(data: WorkflowRunResponse): string {
  const subtitles = data.outputs?.subtitles
  if (
    subtitles &&
    typeof subtitles === 'object' &&
    'srt_preview' in subtitles &&
    typeof subtitles.srt_preview === 'string'
  ) {
    return subtitles.srt_preview
  }
  return ''
}

function extractRenderPlanText(data: WorkflowRunResponse): string {
  const renderPlan = data.outputs?.render_plan
  if (renderPlan && typeof renderPlan === 'object') {
    return stringifyPretty(renderPlan)
  }
  return ''
}

function formatPreview(output?: Record<string, unknown>): string {
  if (!output) {
    return ''
  }

  if (typeof output.text === 'string') {
    return output.text
  }

  if ('scenes' in output && Array.isArray(output.scenes)) {
    return stringifyPretty(output.scenes)
  }

  if ('prompts' in output && Array.isArray(output.prompts)) {
    return stringifyPretty(output.prompts)
  }

  if (typeof output.full_text === 'string') {
    return output.full_text
  }

  if (typeof output.srt_preview === 'string') {
    return output.srt_preview
  }

  if ('edit_plan' in output && output.edit_plan) {
    return stringifyPretty(output)
  }

  return stringifyPretty(output)
}

function buildStepSummaries(data: WorkflowRunResponse): Array<{
  name: string
  status: string
  preview: string
}> {
  return (data.steps || []).map((step) => ({
    name: step.name || 'unknown',
    status: step.status || 'UNKNOWN',
    preview: formatPreview(step.output),
  }))
}

async function runWorkflow() {
  loading.value = true
  errorMessage.value = ''
  resultText.value = ''
  storyText.value = ''
  storyboardText.value = ''
  narrationText.value = ''
  subtitlesText.value = ''
  renderPlanText.value = ''
  stepSummaries.value = []

  const payload = {
    workflow_id: 'storybook-demo',
    session_id: sessionId.value.trim() || 'demo-session-001',
    input: {
      topic: topic.value.trim(),
      audience: audience.value,
      tone: tone.value,
      visual_style: visualStyle.value,
      character_style: characterStyle.value,
      voice_style: voiceStyle.value,
      duration_sec: durationSec.value,
      language: language.value,
      subtitle_enabled: subtitleEnabled.value,
      video_provider: videoProvider.value,
      output_mode: outputMode.value,
    },
    steps: selectedSteps.value.map((name) => ({ name })),
  }

  try {
    const response = await fetch(`${apiBaseUrl}/v1/workflow/run`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data: WorkflowRunResponse = await response.json()
    if (typeof data.session_id === 'string' && data.session_id.trim()) {
      sessionId.value = data.session_id
    }

    storyText.value = extractStoryText(data)
    storyboardText.value = extractStoryboardText(data)
    narrationText.value = extractNarrationText(data)
    subtitlesText.value = extractSubtitlesText(data)
    renderPlanText.value = extractRenderPlanText(data)
    stepSummaries.value = buildStepSummaries(data)
    resultText.value = stringifyPretty(data)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="page">
    <section class="card">
      <h1>Jinsie Multimodal Frontend</h1>
      <p class="desc">
        输入一个主题，系统按默认参数或可选配置生成故事、分镜、旁白、字幕与视频渲染计划。
      </p>

      <label class="label" for="session-id">Session ID</label>
      <input
        id="session-id"
        v-model="sessionId"
        class="input"
        type="text"
        placeholder="请输入会话标识，例如 demo-session-001"
      />

      <label class="label" for="topic">Topic</label>
      <textarea
        id="topic"
        v-model="topic"
        class="textarea"
        rows="4"
        placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      />

      <section class="config-panel">
        <h2 class="section-title">Generation Config</h2>

        <div class="config-grid">
          <label class="field">
            <span>Audience</span>
            <input v-model="audience" class="input" type="text" />
          </label>

          <label class="field">
            <span>Tone</span>
            <input v-model="tone" class="input" type="text" />
          </label>

          <label class="field">
            <span>Visual Style</span>
            <input v-model="visualStyle" class="input" type="text" />
          </label>

          <label class="field">
            <span>Character Style</span>
            <input v-model="characterStyle" class="input" type="text" />
          </label>

          <label class="field">
            <span>Voice Style</span>
            <input v-model="voiceStyle" class="input" type="text" />
          </label>

          <label class="field">
            <span>Duration (sec)</span>
            <input v-model.number="durationSec" class="input" type="number" min="15" max="300" />
          </label>

          <label class="field">
            <span>Language</span>
            <input v-model="language" class="input" type="text" />
          </label>

          <label class="field">
            <span>Video Provider</span>
            <input v-model="videoProvider" class="input" type="text" />
          </label>

          <label class="field">
            <span>Output Mode</span>
            <input v-model="outputMode" class="input" type="text" />
          </label>

          <label class="checkbox-field">
            <input v-model="subtitleEnabled" type="checkbox" />
            <span>Enable Subtitles</span>
          </label>
        </div>
      </section>

      <section class="steps-panel">
        <h2 class="section-title">Workflow Steps</h2>
        <div class="steps-grid">
          <label v-for="step in STEP_OPTIONS" :key="step.value" class="step-option">
            <input v-model="selectedSteps" type="checkbox" :value="step.value" />
            <span>{{ step.label }}</span>
          </label>
        </div>
        <p v-if="selectedSteps.length === 0" class="hint">请至少选择一个 step。</p>
      </section>

      <button class="btn" :disabled="!canSubmit" @click="runWorkflow">
        {{ loading ? '请求中...' : 'Run Workflow' }}
      </button>

      <p v-if="errorMessage" class="error">请求失败：{{ errorMessage }}</p>

      <section v-if="storyText" class="story-panel">
        <h2 class="section-title">Story Result</h2>
        <p class="story-text">{{ storyText }}</p>
      </section>

      <section v-if="storyboardText" class="result-panel">
        <h2 class="section-title">Storyboard</h2>
        <pre class="light-result">{{ storyboardText }}</pre>
      </section>

      <section v-if="narrationText" class="result-panel">
        <h2 class="section-title">Narration</h2>
        <pre class="light-result">{{ narrationText }}</pre>
      </section>

      <section v-if="subtitlesText" class="result-panel">
        <h2 class="section-title">Subtitles Preview</h2>
        <pre class="light-result">{{ subtitlesText }}</pre>
      </section>

      <section v-if="renderPlanText" class="result-panel">
        <h2 class="section-title">Render Plan</h2>
        <pre class="light-result">{{ renderPlanText }}</pre>
      </section>

      <section v-if="stepSummaries.length > 0" class="summary-panel">
        <h2 class="section-title">Steps Summary</h2>

        <article v-for="item in stepSummaries" :key="item.name" class="summary-item">
          <div class="summary-head">
            <strong>{{ item.name }}</strong>
            <span class="summary-status">{{ item.status }}</span>
          </div>
          <pre class="summary-preview">{{ item.preview }}</pre>
        </article>
      </section>

      <section v-if="resultText" class="debug-panel">
        <h2 class="section-title">Raw JSON</h2>
        <pre class="result">{{ resultText }}</pre>
      </section>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: #f7f8fa;
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 960px;
  background: #ffffff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
}

h1 {
  margin: 0 0 12px;
  font-size: 32px;
  line-height: 1.2;
  color: #111827;
}

.desc {
  margin: 0 0 24px;
  color: #4b5563;
  font-size: 15px;
}

.label {
  display: block;
  margin-bottom: 8px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
}

.textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 15px;
  line-height: 1.5;
  resize: vertical;
  background: #ffffff;
  color: #111827;
}

.textarea:focus,
.input:focus {
  outline: none;
  border-color: #111827;
}

.config-panel,
.steps-panel,
.story-panel,
.result-panel,
.summary-item {
  margin-top: 20px;
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: block;
}

.field span,
.checkbox-field span {
  display: block;
  margin-bottom: 8px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 28px;
}

.checkbox-field span {
  margin-bottom: 0;
  font-weight: 500;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.step-option {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-size: 14px;
}

.hint {
  margin: 12px 0 0;
  color: #dc2626;
  font-size: 13px;
}

.btn {
  margin-top: 16px;
  border: none;
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 15px;
  cursor: pointer;
  background: #111827;
  color: #ffffff;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.error {
  margin-top: 16px;
  color: #dc2626;
  font-size: 14px;
}

.summary-panel,
.debug-panel {
  margin-top: 24px;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.summary-status {
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
}

.summary-preview,
.light-result {
  margin: 12px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2937;
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  line-height: 1.4;
  color: #111827;
}

.story-text {
  margin: 0;
  color: #1f2937;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.result {
  margin: 0;
  padding: 16px;
  border-radius: 12px;
  background: #0f172a;
  color: #e5e7eb;
  overflow: auto;
  font-size: 14px;
  line-height: 1.5;
}
</style>