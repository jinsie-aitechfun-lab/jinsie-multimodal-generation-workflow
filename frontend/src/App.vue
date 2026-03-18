<script setup lang="ts">
import { ref } from 'vue'

type HealthResponse = {
  status?: string
  [key: string]: unknown
}

const loading = ref(false)
const errorMessage = ref('')
const resultText = ref('')

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

async function pingBackend() {
  loading.value = true
  errorMessage.value = ''
  resultText.value = ''

  try {
    const response = await fetch(`${apiBaseUrl}/health`)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data: HealthResponse = await response.json()
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
      <p class="desc">Day57 最小闭环：前端调用项目四后端 health 接口。</p>

      <button class="btn" :disabled="loading" @click="pingBackend">
        {{ loading ? '请求中...' : 'Ping Backend /health' }}
      </button>

      <p v-if="errorMessage" class="error">
        请求失败：{{ errorMessage }}
      </p>

      <pre v-if="resultText" class="result">{{ resultText }}</pre>
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

.btn {
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

.result {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
  background: #0f172a;
  color: #e5e7eb;
  overflow: auto;
  font-size: 14px;
  line-height: 1.5;
}
</style>