<script setup lang="ts">
import { computed, ref } from 'vue'

type StepResult = {
  name?: string
  status?: string
  output?: Record<string, unknown>
}

type WorkflowRunResponse = {
  workflow_id?: string
  run_id?: string
  status?: string
  steps?: StepResult[]
  outputs?: Record<string, unknown>
  timestamp?: string
  [key: string]: unknown
}

const loading = ref(false)
const errorMessage = ref('')
const resultText = ref('')
const storyText = ref('')
const topic = ref('写一个关于小猫冒险的故事')

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

const canSubmit = computed(() => topic.value.trim().length > 0 && !loading.value)

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

async function runWorkflow() {
  loading.value = true
  errorMessage.value = ''
  resultText.value = ''
  storyText.value = ''

  const payload = {
    workflow_id: 'storybook-demo',
    input: {
      topic: topic.value.trim(),
    },
    steps: [{ name: 'story' }],
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
    storyText.value = extractStoryText(data)
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
        //前端调用项目四后端 workflow 接口并展示结果。
      </p>

      <label class="label" for="topic">Topic</label>
      <textarea
        id="topic"
        v-model="topic"
        class="textarea"
        rows="5"
        placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      />

      <button class="btn" :disabled="!canSubmit" @click="runWorkflow">
        {{ loading ? '请求中...' : 'Run Workflow' }}
      </button>

      <p v-if="errorMessage" class="error">
        请求失败：{{ errorMessage }}
      </p>

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
  max-width: 720px;
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