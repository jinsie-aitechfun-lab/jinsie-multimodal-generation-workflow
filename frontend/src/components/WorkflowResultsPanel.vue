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
  <section v-if="storyText" class="story-panel">
    <h2 class="section-title">Story Result</h2>
    <p class="story-text">{{ storyText }}</p>
  </section>

  <section v-if="storyboardText" class="result-panel">
    <h2 class="section-title">Storyboard</h2>
    <pre class="light-result">{{ storyboardText }}</pre>
  </section>

  <section v-if="imagePromptsText" class="result-panel">
    <h2 class="section-title">Image Prompts</h2>
    <pre class="light-result">{{ imagePromptsText }}</pre>
  </section>

  <section v-if="imageAssetsText" class="result-panel">
    <h2 class="section-title">Image Assets</h2>
    <pre class="light-result">{{ imageAssetsText }}</pre>
  </section>

  <section v-if="imageReviewText" class="result-panel">
    <h2 class="section-title">Image Review / Asset Selection</h2>
    <pre class="light-result">{{ imageReviewText }}</pre>
  </section>

  <section v-if="videoPromptsText" class="result-panel">
    <h2 class="section-title">Video Prompts</h2>
    <pre class="light-result">{{ videoPromptsText }}</pre>
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

  <section v-if="characterCandidatesText" class="result-panel">
    <h2 class="section-title">Character Candidates</h2>
    <pre class="light-result">{{ characterCandidatesText }}</pre>
  </section>

  <section v-if="characterManifestText" class="result-panel">
    <h2 class="section-title">Character Manifest</h2>
    <pre class="light-result">{{ characterManifestText }}</pre>
  </section>
</template>

<style scoped>
.story-panel,
.result-panel {
  margin-top: 16px;
  padding: 18px 20px;
  border-radius: 14px;
  background: rgba(14,11,5,0.65);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(245,158,11,0.12);
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(251,191,36,0.06);
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