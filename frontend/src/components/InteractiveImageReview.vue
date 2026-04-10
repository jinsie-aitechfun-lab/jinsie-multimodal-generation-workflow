<script setup lang="ts">
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

type ReviewWaitingState =
  | 'idle'
  | 'deferred_pending'
  | 'refreshing'
  | 'rate_limited_retrying'
  | 'ready'

const props = defineProps<{
  items: ImageReviewSelectedAsset[]
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
</script>

<template>
  <section v-if="items.length > 0 || showWaitingCard" class="result-panel">
    <h2 class="section-title">Interactive Image Review</h2>

    <article v-if="showWaitingCard && items.length === 0" class="review-waiting-card">
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

    <div v-if="items.length > 0" class="review-scene-grid">
      <article
        v-for="item in items"
        :key="item.scene_id || item.scene_title"
        class="review-scene-card"
      >
        <div class="review-scene-head">
          <div>
            <strong>{{ item.scene_title || item.scene_id || 'unknown-scene' }}</strong>
            <p class="detail-text">
              {{ item.selection_source || '-' }} / {{ item.selection_mode || '-' }}
            </p>
          </div>

          <span class="summary-status">
            {{ selectingSceneId === item.scene_id ? 'Switching...' : item.review_status || '-' }}
          </span>
        </div>

        <div class="detail-block">
          <span class="detail-label">Current Selected</span>
          <code>{{ assetRefPath(item.selected_asset_ref) || '-' }}</code>

          <a
            v-if="isImageAsset(assetRefPath(item.selected_asset_ref))"
            class="asset-image-link"
            :href="toAssetHref(assetRefPath(item.selected_asset_ref))"
            target="_blank"
            rel="noreferrer"
          >
            <img
              class="asset-image asset-image-thumbnail review-selected-image"
              :src="toAssetHref(assetRefPath(item.selected_asset_ref))"
              :alt="item.scene_title || item.scene_id || 'selected-image'"
            />
          </a>
        </div>

        <div class="detail-block">
          <span class="detail-label">Candidate Assets</span>

          <div class="review-candidate-grid">
            <button
              v-for="candidate in item.candidate_asset_refs || []"
              :key="candidate.relative_path || candidate.file_name || candidate.public_url"
              type="button"
              class="asset-select-card"
              :class="{
                active: isSameAssetRef(candidate, item.selected_asset_ref),
              }"
              :disabled="loading || selectingSceneId === item.scene_id"
              @click="onSelect(item.scene_id || '', candidate)"
            >
              <span class="detail-label">
                {{ isSameAssetRef(candidate, item.selected_asset_ref) ? 'Selected' : 'Click to Select' }}
              </span>

              <code>{{ candidate.file_name || '-' }}</code>

              <img
                v-if="isImageAsset(assetRefPath(candidate))"
                class="asset-image asset-image-thumbnail"
                :src="toAssetHref(assetRefPath(candidate))"
                :alt="candidate.file_name || 'candidate-image'"
              />
            </button>
          </div>
        </div>
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
}

.summary-status {
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
}

.detail-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-label {
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
}

.detail-text {
  color: #111827;
  line-height: 1.6;
}

.asset-image {
  display: block;
  width: 100%;
  max-width: 520px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #ffffff;
  margin-top: 8px;
}

.asset-image-link {
  display: inline-block;
  width: fit-content;
  margin-top: 8px;
}

.asset-image-thumbnail {
  max-width: 240px;
  max-height: 180px;
  object-fit: cover;
  cursor: pointer;
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

.review-scene-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.review-candidate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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

.review-selected-image {
  max-width: 280px;
  max-height: 220px;
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

@media (max-width: 900px) {
  .review-waiting-card {
    grid-template-columns: 1fr;
  }

  .waiting-preview-frame {
    width: 100%;
    max-width: 260px;
  }
}
</style>