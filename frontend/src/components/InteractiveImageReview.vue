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
  state: 'waiting' | 'refreshing' | 'done' | 'failed'
  error_message?: string
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
      state: 'waiting' | 'refreshing' | 'done' | 'failed'
      errorMessage?: string
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
  progressText?: string
  progressPercent?: number
  canCancel?: boolean
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
  (e: 'retry-scene', sceneId: string): void
  (e: 'cancel-refresh'): void
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

function onRetryScene(sceneId: string) {
  emit('retry-scene', sceneId)
}

function onCancelRefresh() {
  emit('cancel-refresh')
}

function placeholderStatusText(state: 'waiting' | 'refreshing' | 'done' | 'failed'): string {
  if (state === 'refreshing') {
    return '正在生成'
  }
  if (state === 'done') {
    return '已完成'
  }
  if (state === 'failed') {
    return '生成失败'
  }
  return '等待生成'
}

function selectedStatusCopy(state: 'waiting' | 'refreshing' | 'done' | 'failed'): string {
  if (state === 'refreshing') {
    return '正在生成当前预览图'
  }
  if (state === 'done') {
    return '当前预览图已生成'
  }
  if (state === 'failed') {
    return '当前预览图生成失败'
  }
  return '等待生成当前预览图'
}

function reviewStatusLabel(status: string | undefined): string {
  if (status === 'manually_selected') {
    return '已手动确认'
  }
  if (status === 'auto_selected') {
    return '已自动选择'
  }
  return status || '-'
}

function candidateStatusCopy(state: 'waiting' | 'refreshing' | 'done' | 'failed', index: 'A' | 'B'): string {
  if (state === 'refreshing') {
    return `正在生成候选图 ${index}`
  }
  if (state === 'done') {
    return `候选图 ${index} 已生成`
  }
  if (state === 'failed') {
    return `候选图 ${index} 生成失败`
  }
  return `等待生成候选图 ${index}`
}

function candidateLabel(candidate: ImageAssetRef, fallbackIndex: number): string {
  const fallbackLabel = String.fromCharCode('A'.charCodeAt(0) + fallbackIndex)
  const source = [
    candidate.file_name,
    candidate.relative_path,
    candidate.public_url,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()

  const match = source.match(/candidate[_-]([a-z0-9]+)/)
  if (!match) {
    return fallbackLabel
  }

  const suffix = match[1]
  if (suffix.length === 1 && /[a-z]/.test(suffix)) {
    return suffix.toUpperCase()
  }

  return suffix
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
        errorMessage: placeholder.error_message,
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

    <div v-if="progressText" class="review-progress">
      <div class="review-progress-head">
        <div class="review-progress-copy">{{ progressText }}</div>
        <button
          v-if="canCancel"
          type="button"
          class="cancel-refresh-button"
          @click="onCancelRefresh"
        >
          停止生成
        </button>
      </div>
      <div class="review-progress-track" aria-hidden="true">
        <div
          class="review-progress-fill"
          :style="{ width: `${Math.max(0, Math.min(100, progressPercent || 0))}%` }"
        ></div>
      </div>
    </div>

    <article v-if="showWaitingCard && renderEntries.length === 0" class="review-waiting-card">
      <div class="waiting-preview-frame">
        <div class="placeholder-card shimmer-active">
          <div class="placeholder-art">
            <div class="placeholder-badge">PLACEHOLDER</div>

            <div class="placeholder-canvas">
              <div class="placeholder-sky"></div>
              <div class="placeholder-sun"></div>
              <div class="placeholder-cloud placeholder-cloud-left"></div>
              <div class="placeholder-cloud placeholder-cloud-right"></div>
              <div class="placeholder-hill placeholder-hill-back"></div>
              <div class="placeholder-hill placeholder-hill-front"></div>
              <div class="placeholder-water"></div>
              <div class="placeholder-tree placeholder-tree-left"></div>
              <div class="placeholder-tree placeholder-tree-right"></div>
              <div class="placeholder-caption-bar"></div>
            </div>
          </div>
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
          <button
            v-if="canCancel"
            type="button"
            class="cancel-refresh-button"
            @click="onCancelRefresh"
          >
            停止生成
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
          'review-scene-card-failed': entry.kind === 'placeholder' && entry.state === 'failed',
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
              progressive_scene_refresh / {{ placeholderStatusText(entry.state) }}
            </p>
          </div>

          <span class="summary-status">
            {{
              entry.kind === 'item'
                ? (selectingSceneId === entry.sceneId ? '切换中' : reviewStatusLabel(entry.item.review_status))
                : placeholderStatusText(entry.state)
            }}
          </span>
        </div>

        <template v-if="entry.kind === 'item'">
          <div class="preview-row">
            <div class="preview-card preview-card-selected">
              <div class="preview-visual-frame">
                <img
                  v-if="isImageAsset(assetRefPath(entry.item.selected_asset_ref))"
                  class="preview-visual-image"
                  :src="toAssetHref(assetRefPath(entry.item.selected_asset_ref))"
                  :alt="entry.sceneTitle || 'selected-image'"
                />
                <div v-else class="placeholder-card">
                  <div class="placeholder-art">
                    <div class="placeholder-badge">PLACEHOLDER</div>

                    <div class="placeholder-canvas">
                      <div class="placeholder-sky"></div>
                      <div class="placeholder-sun"></div>
                      <div class="placeholder-cloud placeholder-cloud-left"></div>
                      <div class="placeholder-cloud placeholder-cloud-right"></div>
                      <div class="placeholder-hill placeholder-hill-back"></div>
                      <div class="placeholder-hill placeholder-hill-front"></div>
                      <div class="placeholder-water"></div>
                      <div class="placeholder-tree placeholder-tree-left"></div>
                      <div class="placeholder-tree placeholder-tree-right"></div>
                      <div class="placeholder-caption-bar"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="preview-info-panel">
                <div class="preview-info-head">
                  <span class="preview-title">当前预览</span>
                  <span class="preview-state-tag preview-state-tag-done">已生成</span>
                </div>

                <div class="asset-code-wrap asset-code-wrap-compact">
                  <code class="asset-code-text">
                    {{ assetRefPath(entry.item.selected_asset_ref) || '-' }}
                  </code>
                </div>

                <a
                  v-if="isImageAsset(assetRefPath(entry.item.selected_asset_ref))"
                  class="selected-open-link"
                  :href="toAssetHref(assetRefPath(entry.item.selected_asset_ref))"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open original
                </a>
              </div>
            </div>
          </div>

          <div class="detail-block detail-block-tight">
            <div class="candidate-header">
              <span class="preview-title">候选图</span>
              <span class="candidate-count">
                {{ (entry.item.candidate_asset_refs || []).length || 2 }} candidates
              </span>
            </div>

            <div class="review-candidate-grid">
              <button
                v-for="(candidate, index) in entry.item.candidate_asset_refs || []"
                :key="candidate.relative_path || candidate.file_name || candidate.public_url"
                type="button"
                class="asset-select-card"
                :class="{
                  active: isSameAssetRef(candidate, entry.item.selected_asset_ref),
                }"
                :disabled="loading || selectingSceneId === entry.sceneId"
                @click="onSelect(entry.sceneId, candidate)"
              >
                <div class="preview-card preview-card-candidate">
                  <div class="preview-visual-frame preview-visual-frame-candidate">
                    <img
                      v-if="isImageAsset(assetRefPath(candidate))"
                      class="preview-visual-image"
                      :src="toAssetHref(assetRefPath(candidate))"
                      :alt="candidate.file_name || 'candidate-image'"
                    />

                    <div v-else class="placeholder-card">
                      <div class="placeholder-art">
                        <div class="placeholder-badge">PLACEHOLDER</div>

                        <div class="placeholder-canvas">
                          <div class="placeholder-sky"></div>
                          <div class="placeholder-sun"></div>
                          <div class="placeholder-cloud placeholder-cloud-left"></div>
                          <div class="placeholder-cloud placeholder-cloud-right"></div>
                          <div class="placeholder-hill placeholder-hill-back"></div>
                          <div class="placeholder-hill placeholder-hill-front"></div>
                          <div class="placeholder-water"></div>
                          <div class="placeholder-tree placeholder-tree-left"></div>
                          <div class="placeholder-tree placeholder-tree-right"></div>
                          <div class="placeholder-caption-bar"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="preview-info-panel">
                    <div class="preview-info-head">
                      <span class="preview-title">候选图 {{ candidateLabel(candidate, index) }}</span>
                      <span
                        class="preview-state-tag"
                        :class="
                          isSameAssetRef(candidate, entry.item.selected_asset_ref)
                            ? 'preview-state-tag-done'
                            : 'preview-state-tag-waiting'
                        "
                      >
                        {{
                          isSameAssetRef(candidate, entry.item.selected_asset_ref)
                            ? '已选中'
                            : '可切换'
                        }}
                      </span>
                    </div>

                    <code class="candidate-file-chip">{{ candidate.file_name || '-' }}</code>
                  </div>
                </div>
              </button>

              <div
                v-if="(entry.item.candidate_asset_refs || []).length === 0"
                class="asset-select-card asset-select-card-static"
              >
                <div class="preview-card preview-card-candidate">
                  <div class="preview-visual-frame preview-visual-frame-candidate">
                    <div class="placeholder-card">
                      <div class="placeholder-art">
                        <div class="placeholder-badge">PLACEHOLDER</div>

                        <div class="placeholder-canvas">
                          <div class="placeholder-sky"></div>
                          <div class="placeholder-sun"></div>
                          <div class="placeholder-cloud placeholder-cloud-left"></div>
                          <div class="placeholder-cloud placeholder-cloud-right"></div>
                          <div class="placeholder-hill placeholder-hill-back"></div>
                          <div class="placeholder-hill placeholder-hill-front"></div>
                          <div class="placeholder-water"></div>
                          <div class="placeholder-tree placeholder-tree-left"></div>
                          <div class="placeholder-tree placeholder-tree-right"></div>
                          <div class="placeholder-caption-bar"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="preview-info-panel">
                    <div class="preview-info-head">
                      <span class="preview-title">候选图 A</span>
                      <span class="preview-state-tag preview-state-tag-waiting">等待</span>
                    </div>

                    <div class="placeholder-status-copy">等待生成候选图 A</div>
                  </div>
                </div>
              </div>

              <div
                v-if="(entry.item.candidate_asset_refs || []).length === 0"
                class="asset-select-card asset-select-card-static"
              >
                <div class="preview-card preview-card-candidate">
                  <div class="preview-visual-frame preview-visual-frame-candidate">
                    <div class="placeholder-card">
                      <div class="placeholder-art">
                        <div class="placeholder-badge">PLACEHOLDER</div>

                        <div class="placeholder-canvas">
                          <div class="placeholder-sky"></div>
                          <div class="placeholder-sun"></div>
                          <div class="placeholder-cloud placeholder-cloud-left"></div>
                          <div class="placeholder-cloud placeholder-cloud-right"></div>
                          <div class="placeholder-hill placeholder-hill-back"></div>
                          <div class="placeholder-hill placeholder-hill-front"></div>
                          <div class="placeholder-water"></div>
                          <div class="placeholder-tree placeholder-tree-left"></div>
                          <div class="placeholder-tree placeholder-tree-right"></div>
                          <div class="placeholder-caption-bar"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="preview-info-panel">
                    <div class="preview-info-head">
                      <span class="preview-title">候选图 B</span>
                      <span class="preview-state-tag preview-state-tag-waiting">等待</span>
                    </div>

                    <div class="placeholder-status-copy">等待生成候选图 B</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="preview-row">
            <div class="preview-card preview-card-selected">
              <div
                class="preview-visual-frame"
                :class="{ 'shimmer-active': entry.state === 'refreshing' }"
              >
                <div class="placeholder-card">
                  <div class="placeholder-art">
                    <div class="placeholder-badge">PLACEHOLDER</div>

                    <div class="placeholder-canvas">
                      <div class="placeholder-sky"></div>
                      <div class="placeholder-sun"></div>
                      <div class="placeholder-cloud placeholder-cloud-left"></div>
                      <div class="placeholder-cloud placeholder-cloud-right"></div>
                      <div class="placeholder-hill placeholder-hill-back"></div>
                      <div class="placeholder-hill placeholder-hill-front"></div>
                      <div class="placeholder-water"></div>
                      <div class="placeholder-tree placeholder-tree-left"></div>
                      <div class="placeholder-tree placeholder-tree-right"></div>
                      <div class="placeholder-caption-bar"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="preview-info-panel">
                <div class="preview-info-head">
                  <span class="preview-title">当前预览</span>
                  <span
                    class="preview-state-tag"
                    :class="
                      entry.state === 'refreshing'
                        ? 'preview-state-tag-refreshing'
                        : entry.state === 'failed'
                          ? 'preview-state-tag-failed'
                        : 'preview-state-tag-waiting'
                    "
                  >
                    {{
                      entry.state === 'refreshing'
                        ? '生成中'
                        : entry.state === 'failed'
                          ? '失败'
                          : '等待中'
                    }}
                  </span>
                </div>

                <div class="asset-code-wrap asset-code-wrap-compact">
                  <code class="asset-code-text">pending://{{ entry.sceneId }}/selected</code>
                </div>

                <div class="placeholder-status-copy">
                  {{ selectedStatusCopy(entry.state) }}
                </div>

                <div
                  v-if="entry.state === 'failed' && entry.errorMessage"
                  class="placeholder-error-copy"
                >
                  {{ entry.errorMessage }}
                </div>

                <button
                  v-if="entry.state === 'failed'"
                  type="button"
                  class="retry-scene-button"
                  :disabled="loading || refreshing || selectingSceneId === entry.sceneId"
                  @click="onRetryScene(entry.sceneId)"
                >
                  重试该场景
                </button>
              </div>
            </div>
          </div>

          <div class="detail-block detail-block-tight">
            <div class="candidate-header">
              <span class="preview-title">候选图</span>
              <span class="candidate-count">2 candidates</span>
            </div>

            <div class="review-candidate-grid">
              <div class="asset-select-card asset-select-card-static">
                <div class="preview-card preview-card-candidate">
                  <div
                    class="preview-visual-frame preview-visual-frame-candidate"
                    :class="{ 'shimmer-active': entry.state === 'refreshing' }"
                  >
                    <div class="placeholder-card">
                      <div class="placeholder-art">
                        <div class="placeholder-badge">PLACEHOLDER</div>

                        <div class="placeholder-canvas">
                          <div class="placeholder-sky"></div>
                          <div class="placeholder-sun"></div>
                          <div class="placeholder-cloud placeholder-cloud-left"></div>
                          <div class="placeholder-cloud placeholder-cloud-right"></div>
                          <div class="placeholder-hill placeholder-hill-back"></div>
                          <div class="placeholder-hill placeholder-hill-front"></div>
                          <div class="placeholder-water"></div>
                          <div class="placeholder-tree placeholder-tree-left"></div>
                          <div class="placeholder-tree placeholder-tree-right"></div>
                          <div class="placeholder-caption-bar"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="preview-info-panel">
                    <div class="preview-info-head">
                      <span class="preview-title">候选图 A</span>
                      <span
                        class="preview-state-tag"
                        :class="
                          entry.state === 'refreshing'
                            ? 'preview-state-tag-refreshing'
                            : entry.state === 'failed'
                              ? 'preview-state-tag-failed'
                            : 'preview-state-tag-waiting'
                        "
                      >
                        {{
                          entry.state === 'refreshing'
                            ? '生成中'
                            : entry.state === 'failed'
                              ? '失败'
                              : '等待中'
                        }}
                      </span>
                    </div>

                    <div class="placeholder-status-copy">
                      {{ candidateStatusCopy(entry.state, 'A') }}
                    </div>
                  </div>
                </div>
              </div>

              <div class="asset-select-card asset-select-card-static">
                <div class="preview-card preview-card-candidate">
                  <div
                    class="preview-visual-frame preview-visual-frame-candidate"
                    :class="{ 'shimmer-active': entry.state === 'refreshing' }"
                  >
                    <div class="placeholder-card">
                      <div class="placeholder-art">
                        <div class="placeholder-badge">PLACEHOLDER</div>

                        <div class="placeholder-canvas">
                          <div class="placeholder-sky"></div>
                          <div class="placeholder-sun"></div>
                          <div class="placeholder-cloud placeholder-cloud-left"></div>
                          <div class="placeholder-cloud placeholder-cloud-right"></div>
                          <div class="placeholder-hill placeholder-hill-back"></div>
                          <div class="placeholder-hill placeholder-hill-front"></div>
                          <div class="placeholder-water"></div>
                          <div class="placeholder-tree placeholder-tree-left"></div>
                          <div class="placeholder-tree placeholder-tree-right"></div>
                          <div class="placeholder-caption-bar"></div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="preview-info-panel">
                    <div class="preview-info-head">
                      <span class="preview-title">候选图 B</span>
                      <span
                        class="preview-state-tag"
                        :class="
                          entry.state === 'refreshing'
                            ? 'preview-state-tag-refreshing'
                            : entry.state === 'failed'
                              ? 'preview-state-tag-failed'
                            : 'preview-state-tag-waiting'
                        "
                      >
                        {{
                          entry.state === 'refreshing'
                            ? '生成中'
                            : entry.state === 'failed'
                              ? '失败'
                              : '等待中'
                        }}
                      </span>
                    </div>

                    <div class="placeholder-status-copy">
                      {{ candidateStatusCopy(entry.state, 'B') }}
                    </div>
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
  padding: 14px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.section-title {
  margin: 0 0 10px;
  font-size: 16px;
  line-height: 1.4;
  color: #111827;
  text-align: center;
}

.review-progress {
  margin: 0 0 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.review-progress-copy {
  flex: 1;
  min-width: 0;
  color: #334155;
  font-size: 13px;
  font-weight: 700;
  line-height: 1.4;
  text-align: left;
}

.review-progress-track {
  width: 100%;
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e2e8f0;
}

.review-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: #2563eb;
  transition: width 180ms ease;
}

.summary-status {
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.detail-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.detail-block-tight {
  margin-top: 12px;
}

.detail-text {
  color: #111827;
  line-height: 1.5;
}

.scene-subtext {
  margin: 6px 0 0;
  font-size: 14px;
  color: #64748b;
}

.asset-code-wrap {
  padding: 10px 12px;
  border-radius: 8px;
  background: #f3f1eb;
}

.asset-code-wrap-compact {
  padding: 8px 10px;
}

.asset-code-text {
  display: block;
  color: #111827;
  line-height: 1.45;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: anywhere;
}

.review-scene-grid {
  display: grid;
  gap: 14px;
}

.review-scene-card {
  padding: 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.review-scene-card-placeholder {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.review-scene-card-refreshing {
  border-color: #cbd5e1;
}

.review-scene-card-failed {
  border-color: #fecaca;
  background: #fffafa;
}

.review-scene-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.scene-meta-block {
  min-width: 0;
}

.scene-title-text {
  display: block;
  color: #111827;
  font-size: 17px;
  line-height: 1.35;
  word-break: break-word;
}

.preview-row {
  display: flex;
  flex-direction: column;
}

.preview-card {
  display: grid;
  grid-template-columns: 192px minmax(0, 1fr);
  gap: 14px;
  align-items: stretch;
  padding: 10px;
  border-radius: 14px;
  background: #fbfcfe;
  border: 1px solid #e6ebf2;
}

.preview-card-selected,
.preview-card-candidate {
  min-height: 120px;
}

.preview-visual-frame {
  width: 192px;
  aspect-ratio: 16 / 9;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #d7dee8;
  background: #eef2f6;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.preview-visual-frame-candidate {
  aspect-ratio: 16 / 9;
}

.preview-visual-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.preview-info-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  min-width: 0;
}

.preview-info-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.preview-title {
  color: #475569;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.preview-state-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.preview-state-tag-done {
  background: #e8f7ee;
  color: #15803d;
}

.preview-state-tag-waiting {
  background: #f3f4f6;
  color: #6b7280;
}

.preview-state-tag-refreshing {
  background: #eaf2ff;
  color: #2563eb;
}

.preview-state-tag-failed {
  background: #fee2e2;
  color: #b91c1c;
}

.selected-open-link {
  width: fit-content;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
}

.selected-open-link:hover {
  text-decoration: underline;
}

.placeholder-status-copy {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
}

.placeholder-error-copy {
  color: #b91c1c;
  font-size: 12px;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.retry-scene-button {
  width: fit-content;
  min-height: 34px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #b91c1c;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.retry-scene-button:hover:not(:disabled) {
  background: #ffe4e6;
}

.retry-scene-button:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.candidate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.candidate-count {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.review-candidate-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(280px, 1fr));
  gap: 12px;
}

.asset-select-card {
  appearance: none;
  border: 1px solid #dbe1ea;
  background: #ffffff;
  border-radius: 14px;
  padding: 0;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    transform 0.2s ease;
  overflow: hidden;
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
  opacity: 0.7;
}

.asset-select-card-static {
  cursor: default;
}

.candidate-file-chip {
  display: inline-block;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 6px;
  background: #f3f1eb;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.35;
  word-break: break-all;
}

.placeholder-card {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(180deg, #eef2f6 0%, #e5eaef 100%);
}

.placeholder-art {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.placeholder-badge {
  position: absolute;
  top: 46%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 3;
  padding: 0;
  background: transparent;
  color: rgba(100, 116, 139, 0.92);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  white-space: nowrap;
  border-radius: 0;
  box-shadow: none;
}
.placeholder-canvas {
  position: absolute;
  inset: 16px 14px 14px 14px;
  border-radius: 12px;
  overflow: hidden;
  background: #f3f5f7;
  border: 1px solid #d7dee5;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.placeholder-sky {
  position: absolute;
  inset: 0 0 38% 0;
  background: linear-gradient(180deg, #e9edf1 0%, #dde4ea 100%);
}

.placeholder-cloud {
  position: absolute;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
}

.placeholder-cloud::before,
.placeholder-cloud::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.55);
}

.placeholder-cloud-left {
  top: 22%;
  left: 18%;
  width: 34px;
}

.placeholder-cloud-left::before {
  width: 16px;
  height: 16px;
  left: 4px;
  bottom: 2px;
}

.placeholder-cloud-left::after {
  width: 14px;
  height: 14px;
  right: 5px;
  bottom: 1px;
}

.placeholder-cloud-right {
  top: 18%;
  right: 16%;
  width: 28px;
}

.placeholder-cloud-right::before {
  width: 13px;
  height: 13px;
  left: 2px;
  bottom: 1px;
}

.placeholder-cloud-right::after {
  width: 12px;
  height: 12px;
  right: 3px;
  bottom: 1px;
}

.placeholder-hill {
  position: absolute;
  bottom: 24%;
  border-radius: 50% 50% 0 0;
}

.placeholder-hill-back {
  left: -6%;
  width: 76%;
  height: 24%;
  background: #cfd6dd;
}

.placeholder-hill-front {
  right: -8%;
  width: 84%;
  height: 30%;
  background: #bcc6cf;
}

.placeholder-water {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 24%;
  background: linear-gradient(180deg, #b8c2cb 0%, #aeb9c3 100%);
}

.placeholder-sun {
  position: absolute;
  top: 16%;
  right: 18%;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #c7d0d8;
  box-shadow: 0 0 0 6px rgba(199, 208, 216, 0.26);
}

.placeholder-tree {
  position: absolute;
  bottom: 18%;
  width: 6px;
  background: #97a5b2;
  border-radius: 999px;
}

.placeholder-tree::before {
  content: '';
  position: absolute;
  left: 50%;
  bottom: 70%;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #c9d1d8;
  transform: translateX(-50%);
}

.placeholder-tree-left {
  left: 20%;
  height: 18%;
}

.placeholder-tree-right {
  right: 22%;
  height: 15%;
}

.placeholder-caption-bar {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 10px;
  height: 8px;
  border-radius: 999px;
  background: #d8dfe6;
}
.shimmer-active::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    rgba(255, 255, 255, 0) 18%,
    rgba(255, 255, 255, 0.58) 46%,
    rgba(255, 255, 255, 0) 74%
  );
  transform: translateX(-120%);
  animation: reviewShimmer 1.6s linear infinite;
  pointer-events: none;
}

.review-waiting-card {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: 20px;
  align-items: center;
  padding: 18px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.waiting-preview-frame {
  width: 180px;
  height: 220px;
  border-radius: 16px;
  border: 1px solid #dbe3ee;
  background: #eef2f6;
  overflow: hidden;
  position: relative;
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
  line-height: 1.65;
  font-size: 14px;
}

.waiting-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
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

.cancel-refresh-button {
  appearance: none;
  flex-shrink: 0;
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #334155;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    color 0.2s ease,
    transform 0.2s ease;
}

.cancel-refresh-button:hover {
  border-color: #ef4444;
  color: #b91c1c;
  transform: translateY(-1px);
}

@keyframes reviewShimmer {
  100% {
    transform: translateX(120%);
  }
}

@media (max-width: 900px) {
  .review-waiting-card {
    grid-template-columns: 1fr;
  }

  .waiting-preview-frame {
    width: 100%;
    max-width: 180px;
  }

  .review-candidate-grid {
    grid-template-columns: 1fr;
  }

  .review-scene-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .preview-card {
    grid-template-columns: 1fr;
  }

  .preview-visual-frame {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .review-scene-card {
    padding: 12px;
  }

  .scene-subtext {
    font-size: 13px;
  }

  .preview-card {
    padding: 10px;
  }
}
</style>
