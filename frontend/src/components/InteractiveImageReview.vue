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

const props = defineProps<{
  items: ImageReviewSelectedAsset[]
  apiBaseUrl: string
  loading: boolean
  selectingSceneId: string
}>()

const emit = defineEmits<{
  (
    e: 'select-asset',
    payload: {
      sceneId: string
      assetRef: ImageAssetRef
    }
  ): void
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
</script>

<template>
  <section v-if="items.length > 0" class="result-panel">
    <h2 class="section-title">Interactive Image Review</h2>

    <div class="review-scene-grid">
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
  margin-bottom: 12px;
}

.review-candidate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.asset-select-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid #d1d5db;
  background: #f8fafc;
  cursor: pointer;
  text-align: left;
}

.asset-select-card.active {
  border-color: #111827;
  background: #eef2ff;
}

.asset-select-card:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.review-selected-image {
  max-width: 280px;
}
</style>