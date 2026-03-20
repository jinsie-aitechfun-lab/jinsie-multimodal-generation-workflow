<script setup lang="ts">
import { computed, ref } from 'vue'

type StepName = 'story' | 'image' | 'audio' | 'video'

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
  { label: 'Image', value: 'image' },
  { label: 'Audio', value: 'audio' },
  { label: 'Video', value: 'video' },
]

const loading = ref(false)
const errorMessage = ref('')
const resultText = ref('')
const storyText = ref('')
const topic = ref('写一个关于小猫冒险的故事')
const sessionId = ref('demo-session-001')
const selectedSteps = ref<StepName[]>(['story', 'image', 'audio', 'video'])
const stepSummaries = ref<Array<{ name: string; status: string; preview: string }>>([])

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

const canSubmit = computed(() => {
  return (
    topic.value.trim().length > 0 &&
    selectedSteps.value.length > 0 &&
    !loading.value
  )
})

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

  const storyStep = data.steps?.find((step) => step.name === 'story')
  const stepOutputText = storyStep?.output?.text
  if (typeof stepOutputText === 'string') {
    return stepOutputText
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

  if (typeof output.image_prompt === 'string') {
    return output.image_prompt
  }

  if (typeof output.tts_text === 'string') {
    return output.tts_text
  }

  if (output.video_plan && typeof output.video_plan === 'object') {
    return JSON.stringify(output.video_plan, null, 2)
  }

  return JSON.stringify(output, null, 2)
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
  stepSummaries.value = []

  const payload = {
    workflow_id: 'storybook-demo',
    session_id: sessionId.value.trim() || 'demo-session-001',
    input: {
      topic: topic.value.trim(),
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
    stepSummaries.value = buildStepSummaries(data)
    resultText.value = JSON.stringify(data, null, 2)
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'Request failed'
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
        前端调用项目四后端 workflow 接口并展示多 step 结果。
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
        rows="5"
        placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      />

      <section class="steps-panel">
        <h2 class="section-title">Steps</h2>
        <div class="steps-grid">
          <label
            v-for="step in STEP_OPTIONS"
            :key="step.value"
            class="step-option"
          >
            <input v-model="selectedSteps" type="checkbox" :value="step.value" />
            <span>{{ step.label }}</span>
          </label>
        </div>
        <p v-if="selectedSteps.length === 0" class="hint">
          请至少选择一个 step。
        </p>
      </section>

      <button class="btn" :disabled="!canSubmit" @click="runWorkflow">
        {{ loading ? '请求中...' : 'Run Workflow' }}
      </button>

      <p v-if="errorMessage" class="error">
        请求失败：{{ errorMessage }}
      </p>

      <section v-if="stepSummaries.length > 0" class="summary-panel">
        <h2 class="section-title">Steps Summary</h2>

        <article
          v-for="item in stepSummaries"
          :key="item.name"
          class="summary-item"
        >
          <div class="summary-head">
            <strong>{{ item.name }}</strong>
            <span class="summary-status">{{ item.status }}</span>
          </div>
          <pre class="summary-preview">{{ item.preview }}</pre>
        </article>
      </section>

      <section v-if="storyText" class="story-panel">
        <h2 class="section-title">Story Result</h2>
        <p class="story-text">{{ storyText }}</p>
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
  align-items: center;
  justify-content: center;
  background: #f7f8fa;
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 820px;
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

.textarea:focus {
  outline: none;
  border-color: #111827;
}

.steps-panel {
  margin-top: 20px;
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
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

.summary-panel {
  margin-top: 24px;
}

.summary-item {
  margin-top: 12px;
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
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

.summary-preview {
  margin: 12px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2937;
}

.story-panel {
  margin-top: 24px;
  padding: 20px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.debug-panel {
  margin-top: 20px;
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