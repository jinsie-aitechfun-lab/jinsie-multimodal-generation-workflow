<script setup lang="ts">
import { computed } from 'vue'

type ImageAssetRef = {
  scene_id?: string
  file_name?: string
  relative_path?: string
  public_url?: string
  mime_type?: string
  provider?: string
}

type ImageReviewSelectedAsset = {
  scene_id?: string
  scene_title?: string
  review_status?: string
  selection_mode?: string
  selection_source?: string
  selection_reason?: string
  selected_asset_ref?: ImageAssetRef
  candidate_asset_refs?: ImageAssetRef[]
  characters?: Array<Record<string, unknown>>
  character_ids?: string[]
  prompt?: string
}

type ReviewPlaceholderItem = {
  scene_id: string
  scene_title: string
  state: 'waiting' | 'refreshing' | 'done'
}

type ReviewWaitingState =
  | 'idle'
  | 'deferred_pending'
  | 'refreshing'
  | 'rate_limited_retrying'
  | 'ready'

type ReviewRenderEntry =
  | {
      kind: 'item'
      sceneId: string
      sceneTitle: string
      state: 'done'
      item: ImageReviewSelectedAsset
    }
  | {
      kind: 'placeholder'
      sceneId: string
      sceneTitle: string
      state: 'waiting' | 'refreshing' | 'done'
    }

const props = defineProps<{
  items: ImageReviewSelectedAsset[]
  placeholders?: ReviewPlaceholderItem[]
  apiBaseUrl: string
  loading: boolean
  selectingSceneId: string
  waitingState?: ReviewWaitingState
  waitingTitle?: string
  waitingMessage?: string
  showWaitingCard?: boolean
  refreshing?: boolean
  canRefresh?: boolean
}>()

const emit = defineEmits<{
  (
    e: 'select-asset',
    payload: {
      sceneId: string
      assetRef: ImageAssetRef
    }
  ): void
  (e: 'refresh-review'): void
}>()

function toAssetHref(path?: string): string {
  if (!path) {
    return ''
  }

  const trimmed = path.trim()
  if (!trimmed) {
    return ''
  }

  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed
  }

  const normalizedBase = props.apiBaseUrl.replace(/\/+$/, '')
  const normalizedPath = trimmed.startsWith('/') ? trimmed : `/${trimmed}`

  return `${normalizedBase}${normalizedPath}`
}

function assetRefPath(assetRef?: ImageAssetRef): string {
  if (!assetRef) {
    return ''
  }
  return assetRef.public_url || assetRef.relative_path || ''
}

function isImageAsset(path?: string): boolean {
  if (!path) {
    return false
  }

  const value = path.toLowerCase()
  return (
    value.endsWith('.png') ||
    value.endsWith('.jpg') ||
    value.endsWith('.jpeg') ||
    value.endsWith('.webp') ||
    value.endsWith('.gif')
  )
}

function isSameAssetRef(a?: ImageAssetRef, b?: ImageAssetRef): boolean {
  if (!a || !b) {
    return false
  }

  const aRelativePath = (a.relative_path || '').trim()
  const bRelativePath = (b.relative_path || '').trim()
  const aFileName = (a.file_name || '').trim()
  const bFileName = (b.file_name || '').trim()

  return aRelativePath === bRelativePath && aFileName === bFileName
}

function onSelect(sceneId: string, assetRef: ImageAssetRef) {
  emit('select-asset', {
    sceneId,
    assetRef,
  })
}

function onRefreshReview() {
  emit('refresh-review')
}

function placeholderStatusText(state: 'waiting' | 'refreshing' | 'done'): string {
  if (state === 'refreshing') {
    return 'refreshing'
  }
  if (state === 'done') {
    return 'ready'
  }
  return 'waiting'
}

const renderEntries = computed<ReviewRenderEntry[]>(() => {
  const itemMap = new Map<string, ImageReviewSelectedAsset>()

  for (const item of props.items || []) {
    const sceneId = String(item.scene_id || '').trim()
    if (sceneId) {
      itemMap.set(sceneId, item)
    }
  }

  const entries: ReviewRenderEntry[] = []

  for (const placeholder of props.placeholders || []) {
    const sceneId = String(placeholder.scene_id || '').trim()
    const sceneTitle = String(placeholder.scene_title || sceneId || 'unknown-scene').trim()

    if (!sceneId) {
      continue
    }

    const matchedItem = itemMap.get(sceneId)
    if (matchedItem) {
      entries.push({
        kind: 'item',
        sceneId,
        sceneTitle,
        state: 'done',
        item: matchedItem,
      })
      itemMap.delete(sceneId)
    } else {
      entries.push({
        kind: 'placeholder',
        sceneId,
        sceneTitle,
        state: placeholder.state,
      })
    }
  }

  for (const item of props.items || []) {
    const sceneId = String(item.scene_id || '').trim()
    if (!sceneId || !itemMap.has(sceneId)) {
      continue
    }

    entries.push({
      kind: 'item',
      sceneId,
      sceneTitle: String(item.scene_title || sceneId || 'unknown-scene').trim(),
      state: 'done',
      item,
    })
  }

  return entries
})
</script>

<template>
  <section
    v-if="renderEntries.length > 0 || showWaitingCard"
    class="result-panel"
  >
    <h2 class="section-title">Interactive Image Review</h2>

    <article v-if="showWaitingCard && renderEntries.length === 0" class="review-waiting-card">
      <div class="waiting-preview-frame">
        <div class="waiting-preview-inner">
          <div class="waiting-image-icon">🖼️</div>
          <div class="waiting-shimmer"></div>
        </div>
      </div>

      <div class="waiting-copy">
        <h3 class="waiting-title">{{ waitingTitle || '候选图准备中' }}</h3>
        <p class="waiting-message">
          {{ waitingMessage || '候选图尚未生成，请稍后刷新。' }}
        </p>

        <div class="waiting-actions">
          <button
            type="button"
            class="refresh-button"
            :disabled="loading || refreshing || !canRefresh"
            @click="onRefreshReview"
          >
            {{
              refreshing
                ? '正在刷新...'
                : waitingState === 'rate_limited_retrying'
                  ? '立即重试'
                  : '立即刷新结果'
            }}
          </button>
        </div>
      </div>
    </article>

    <div v-if="renderEntries.length > 0" class="review-scene-grid">
      <article
        v-for="entry in renderEntries"
        :key="entry.sceneId"
        class="review-scene-card"
        :class="{
          'review-scene-card-placeholder': entry.kind === 'placeholder',
          'review-scene-card-refreshing': entry.kind === 'placeholder' && entry.state === 'refreshing',
        }"
      >
        <div class="review-scene-head">
          <div class="scene-meta-block">
            <strong class="scene-title-text">
              {{ entry.sceneTitle }}
            </strong>

            <p v-if="entry.kind === 'item'" class="detail-text scene-subtext">
              {{ entry.item.selection_source || '-' }} / {{ entry.item.selection_mode || '-' }}
            </p>

            <p v-else class="detail-text scene-subtext">
              progressive_scene_refresh / {{ entry.state }}
            </p>
          </div>

          <span class="summary-status">
            {{
              entry.kind === 'item'
                ? (selectingSceneId === entry.sceneId ? 'Switching...' : entry.item.review_status || '-')
                : placeholderStatusText(entry.state)
            }}
          </span>
        </div>

        <template v-if="entry.kind === 'item'">
          <div class="detail-block">
            <span class="detail-label detail-label-centered">Current Selected</span>

            <div class="asset-code-wrap">
              <code class="asset-code-text">
                {{ assetRefPath(entry.item.selected_asset_ref) || '-' }}
              </code>
            </div>

            <a
              v-if="isImageAsset(assetRefPath(entry.item.selected_asset_ref))"
              class="selected-image-link"
              :href="toAssetHref(assetRefPath(entry.item.selected_asset_ref))"
              target="_blank"
              rel="noreferrer"
            >
              <div class="selected-preview-frame">
                <img
                  class="selected-preview-image"
                  :src="toAssetHref(assetRefPath(entry.item.selected_asset_ref))"
                  :alt="entry.sceneTitle || 'selected-image'"
                />
              </div>
            </a>

            <div v-else class="selected-preview-frame selected-preview-placeholder">
              <div class="preview-placeholder-inner">
                <span class="preview-placeholder-icon">🖼️</span>
                <span class="preview-placeholder-text">Waiting for selected image</span>
              </div>
            </div>
          </div>

          <div class="detail-block">
            <span class="detail-label detail-label-centered">Candidate Assets</span>

            <div class="review-candidate-grid">
              <button
                v-for="candidate in entry.item.candidate_asset_refs || []"
                :key="candidate.relative_path || candidate.file_name || candidate.public_url"
                type="button"
                class="asset-select-card"
                :class="{
                  active: isSameAssetRef(candidate, entry.item.selected_asset_ref),
                }"
                :disabled="loading || selectingSceneId === entry.sceneId"
                @click="onSelect(entry.sceneId, candidate)"
              >
                <div class="candidate-card-head">
                  <span class="candidate-status-text">
                    {{
                      isSameAssetRef(candidate, entry.item.selected_asset_ref)
                        ? 'Selected'
                        : 'Click to Select'
                    }}
                  </span>

                  <code class="candidate-file-chip">{{ candidate.file_name || '-' }}</code>
                </div>

                <div class="candidate-preview-frame">
                  <img
                    v-if="isImageAsset(assetRefPath(candidate))"
                    class="candidate-preview-image"
                    :src="toAssetHref(assetRefPath(candidate))"
                    :alt="candidate.file_name || 'candidate-image'"
                  />

                  <div v-else class="candidate-preview-placeholder">
                    <div class="preview-placeholder-inner">
                      <span class="preview-placeholder-icon">🖼️</span>
                      <span class="preview-placeholder-text">Waiting for candidate</span>
                    </div>
                  </div>
                </div>
              </button>

              <div
                v-if="(entry.item.candidate_asset_refs || []).length === 0"
                class="asset-select-card asset-select-card-static"
              >
                <div class="candidate-card-head">
                  <span class="candidate-status-text">Waiting</span>
                  <code class="candidate-file-chip">candidate-a</code>
                </div>

                <div class="candidate-preview-frame candidate-preview-placeholder">
                  <div class="preview-placeholder-inner">
                    <span class="preview-placeholder-icon">🖼️</span>
                    <span class="preview-placeholder-text">Waiting for candidate</span>
                  </div>
                </div>
              </div>

              <div
                v-if="(entry.item.candidate_asset_refs || []).length === 0"
                class="asset-select-card asset-select-card-static"
              >
                <div class="candidate-card-head">
                  <span class="candidate-status-text">Waiting</span>
                  <code class="candidate-file-chip">candidate-b</code>
                </div>

                <div class="candidate-preview-frame candidate-preview-placeholder">
                  <div class="preview-placeholder-inner">
                    <span class="preview-placeholder-icon">🖼️</span>
                    <span class="preview-placeholder-text">Waiting for candidate</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="detail-block">
            <span class="detail-label detail-label-centered">Current Selected</span>

            <div class="asset-code-wrap">
              <code class="asset-code-text">pending://{{ entry.sceneId }}/selected</code>
            </div>

            <div class="selected-preview-frame selected-preview-placeholder">
              <div class="preview-placeholder-inner">
                <span class="preview-placeholder-icon">🖼️</span>
                <span class="preview-placeholder-text">
                  {{
                    entry.state === 'refreshing'
                      ? 'Generating selected image...'
                      : 'Waiting for selected image'
                  }}
                </span>
              </div>
            </div>
          </div>

          <div class="detail-block">
            <span class="detail-label detail-label-centered">Candidate Assets</span>

            <div class="review-candidate-grid">
              <div class="asset-select-card asset-select-card-static">
                <div class="candidate-card-head">
                  <span class="candidate-status-text">
                    {{ entry.state === 'refreshing' ? 'Refreshing' : 'Waiting' }}
                  </span>
                  <code class="candidate-file-chip">{{ entry.sceneId }}__candidate_a.png</code>
                </div>

                <div class="candidate-preview-frame candidate-preview-placeholder">
                  <div class="preview-placeholder-inner">
                    <span class="preview-placeholder-icon">🖼️</span>
                    <span class="preview-placeholder-text">
                      {{
                        entry.state === 'refreshing'
                          ? 'Generating candidate A...'
                          : 'Waiting for candidate'
                      }}
                    </span>
                  </div>
                </div>
              </div>

              <div class="asset-select-card asset-select-card-static">
                <div class="candidate-card-head">
                  <span class="candidate-status-text">
                    {{ entry.state === 'refreshing' ? 'Refreshing' : 'Waiting' }}
                  </span>
                  <code class="candidate-file-chip">{{ entry.sceneId }}__candidate_b.png</code>
                </div>

                <div class="candidate-preview-frame candidate-preview-placeholder">
                  <div class="preview-placeholder-inner">
                    <span class="preview-placeholder-icon">🖼️</span>
                    <span class="preview-placeholder-text">
                      {{
                        entry.state === 'refreshing'
                          ? 'Generating candidate B...'
                          : 'Waiting for candidate'
                      }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>
      </article>
    </div>
  </section>
</template>

<style scoped>
.result-panel {
  margin-top: 20px;
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  line-height: 1.4;
  color: #111827;
  text-align: center;
}

.summary-status {
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.detail-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-label {
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
}

.detail-label-centered {
  text-align: center;
}

.detail-text {
  color: #111827;
  line-height: 1.6;
}

.scene-subtext {
  margin: 8px 0 0;
  font-size: 16px;
}

.asset-code-wrap {
  padding: 10px 12px;
  border-radius: 6px;
  background: #f3f1eb;
}

.asset-code-text {
  display: block;
  color: #111827;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: anywhere;
}

.review-scene-grid {
  display: grid;
  gap: 16px;
}

.review-scene-card {
  padding: 16px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.review-scene-card-placeholder {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.review-scene-card-refreshing {
  border-color: #cbd5e1;
}

.review-scene-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.scene-meta-block {
  min-width: 0;
}

.scene-title-text {
  display: block;
  color: #111827;
  font-size: 18px;
  line-height: 1.4;
  word-break: break-word;
}

.selected-image-link {
  display: inline-block;
  width: fit-content;
  text-decoration: none;
}

.selected-preview-frame {
  width: 176px;
  height: 280px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid #d7dee8;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.selected-preview-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.review-candidate-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

.asset-select-card {
  appearance: none;
  border: 1px solid #d1d5db;
  background: #ffffff;
  border-radius: 12px;
  padding: 12px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.asset-select-card:hover:not(:disabled) {
  border-color: #94a3b8;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.asset-select-card.active {
  border-color: #0f172a;
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.08);
}

.asset-select-card:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.asset-select-card-static {
  cursor: default;
}

.candidate-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.candidate-status-text {
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.candidate-file-chip {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f3f1eb;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.4;
  word-break: break-all;
}

.candidate-preview-frame {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.candidate-preview-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.selected-preview-placeholder,
.candidate-preview-placeholder {
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
}

.preview-placeholder-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #94a3b8;
  text-align: center;
  padding: 16px;
}

.preview-placeholder-icon {
  font-size: 24px;
  line-height: 1;
}

.preview-placeholder-text {
  font-size: 12px;
  font-weight: 600;
}

.review-waiting-card {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
  align-items: center;
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.waiting-preview-frame {
  width: 220px;
  aspect-ratio: 9 / 16;
  border-radius: 18px;
  border: 1px solid #dbe3ee;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  padding: 12px;
  box-sizing: border-box;
}

.waiting-preview-inner {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: linear-gradient(180deg, #f1f5f9 0%, #e5edf6 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.waiting-image-icon {
  position: relative;
  z-index: 2;
  font-size: 28px;
  opacity: 0.7;
}

.waiting-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    rgba(255, 255, 255, 0) 20%,
    rgba(255, 255, 255, 0.55) 50%,
    rgba(255, 255, 255, 0) 80%
  );
  transform: translateX(-100%);
  animation: shimmerMove 1.8s linear infinite;
}

.waiting-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.waiting-title {
  margin: 0;
  font-size: 18px;
  color: #111827;
}

.waiting-message {
  margin: 0;
  color: #475569;
  line-height: 1.7;
  font-size: 15px;
}

.waiting-actions {
  display: flex;
  gap: 12px;
  margin-top: 6px;
}

.refresh-button {
  appearance: none;
  border: 1px solid #0f172a;
  background: #0f172a;
  color: #ffffff;
  border-radius: 999px;
  padding: 10px 18px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.refresh-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes shimmerMove {
  100% {
    transform: translateX(100%);
  }
}

@media (max-width: 1100px) {
  .selected-preview-frame {
    width: 200px;
    height: 300px;
  }
}

@media (max-width: 900px) {
  .review-waiting-card {
    grid-template-columns: 1fr;
  }

  .waiting-preview-frame {
    width: 100%;
    max-width: 260px;
  }

  .review-candidate-grid {
    grid-template-columns: 1fr;
  }

  .review-scene-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .review-scene-card {
    padding: 16px;
  }

  .scene-subtext {
    font-size: 14px;
  }

  .selected-preview-frame {
    width: 180px;
    height: 280px;
  }
}
</style>