<script setup lang="ts">
defineProps<{
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
</script>

<template>
  <section
    v-if="
      storyText ||
      storyboardText ||
      imagePromptsText ||
      imageAssetsText ||
      imageReviewText ||
      videoPromptsText ||
      narrationText ||
      subtitlesText ||
      renderPlanText ||
      characterCandidatesText ||
      characterManifestText
    "
    class="result-panel developer-results-panel"
  >
    <details>
      <summary>生成细节</summary>

      <section v-if="storyText" class="developer-result-block">
        <h2 class="section-title">故事结果</h2>
        <p class="story-text">{{ storyText }}</p>
      </section>

      <section v-if="storyboardText" class="developer-result-block">
        <h2 class="section-title">分镜结构</h2>
        <pre class="light-result">{{ storyboardText }}</pre>
      </section>

      <section v-if="imagePromptsText" class="developer-result-block">
        <h2 class="section-title">图片提示词</h2>
        <pre class="light-result">{{ imagePromptsText }}</pre>
      </section>

      <section v-if="imageAssetsText" class="developer-result-block">
        <h2 class="section-title">图片素材</h2>
        <pre class="light-result">{{ imageAssetsText }}</pre>
      </section>

      <section v-if="imageReviewText" class="developer-result-block">
        <h2 class="section-title">画面审核 / 素材选择</h2>
        <pre class="light-result">{{ imageReviewText }}</pre>
      </section>

      <section v-if="videoPromptsText" class="developer-result-block">
        <h2 class="section-title">视频提示词</h2>
        <pre class="light-result">{{ videoPromptsText }}</pre>
      </section>

      <section v-if="narrationText" class="developer-result-block">
        <h2 class="section-title">旁白</h2>
        <pre class="light-result">{{ narrationText }}</pre>
      </section>

      <section v-if="subtitlesText" class="developer-result-block">
        <h2 class="section-title">字幕预览</h2>
        <pre class="light-result">{{ subtitlesText }}</pre>
      </section>

      <section v-if="renderPlanText" class="developer-result-block">
        <h2 class="section-title">渲染计划</h2>
        <pre class="light-result">{{ renderPlanText }}</pre>
      </section>

      <section v-if="characterCandidatesText" class="developer-result-block">
        <h2 class="section-title">角色候选</h2>
        <pre class="light-result">{{ characterCandidatesText }}</pre>
      </section>

      <section v-if="characterManifestText" class="developer-result-block">
        <h2 class="section-title">角色设定清单</h2>
        <pre class="light-result">{{ characterManifestText }}</pre>
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
