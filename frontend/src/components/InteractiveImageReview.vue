<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import InlineStatusPulse from './studio/InlineStatusPulse.vue'

type ImageAssetRef = {
  scene_id?: string
  file_name?: string
  relative_path?: string
  public_url?: string
  mime_type?: string
  provider?: string
  version?: string | number
  thumbnail_url?: string
  thumbnail_path?: string
  thumbnail_version?: string | number
  width?: number
  height?: number
  size_bytes?: number
  thumbnail_width?: number
  thumbnail_height?: number
  thumbnail_size_bytes?: number
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
  state: 'waiting' | 'queued' | 'refreshing' | 'confirming' | 'done' | 'failed'
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
      state: 'waiting' | 'queued' | 'refreshing' | 'confirming' | 'done' | 'failed'
      errorMessage?: string
    }

const props = defineProps<{
  items: ImageReviewSelectedAsset[]
  storyText?: string
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
  // True after the user clicks "取消生成" on the workflow run — every
  // "正在生成…" label inside this panel must switch to "正在取消生成…".
  cancelRequested?: boolean
  // True while a workflow run is still in flight at the App level. Drives
  // the lightweight "取消生成" entry inside this panel so the user can
  // cancel the whole workflow without leaving the review tab.
  cancellable?: boolean
  // True once the final video has been rendered. Locks every candidate
  // selection — once a video exists, the image roster the video was built
  // from must not change underneath it (the displayed selection would no
  // longer match the actual video frames).
  videoGenerated?: boolean
  // Render mode drives whether the per-scene "重新生成" button is
  // exposed. In 'auto' mode the system kicks off final video rendering
  // as soon as all candidates are ready, so a per-scene regenerate
  // button has no time to be useful and would just confuse users. In
  // 'manual' mode the user is reviewing before clicking "生成视频",
  // and they're the natural audience for regenerating a single bad
  // scene without re-running the entire workflow.
  renderMode?: 'auto' | 'manual'
  // Map of scene_id → version-counter for image cache-busting. When a
  // scene is regenerated the new image file overwrites the OLD one
  // at the same file path (e.g. scene_03__candidate_a.png), and
  // browsers happily serve the cached image since the URL hasn't
  // changed. Appending `?v=${sceneImageVersions[sceneId]}` to every
  // image URL forces a fresh fetch after each per-scene refresh.
  sceneImageVersions?: Record<string, string | number>
  // Map of scene_id → narration text (the TTS script for this scene).
  // Surfaced inline on each candidate's card so the user knows what
  // each scene is ABOUT in plain language. This is the user-readable
  // story moment — NOT the structural image-gen prompt, which is
  // hundreds of lines of cast-lock boilerplate and not useful to show.
  sceneNarrationMap?: Record<string, string>
}>()

type ImageLoadState = 'loading' | 'ready' | 'retrying' | 'failed'
const IMAGE_RETRY_DELAYS_MS = [500, 1000, 2000] as const
const imageRetryAttempts = ref<Record<string, number>>({})
const imageRetryVersions = ref<Record<string, number>>({})
const imageLoadStates = ref<Record<string, ImageLoadState>>({})
const imageRetryTimers = new Map<string, number>()

// A scene's candidates are locked when:
//   • the final video already exists for this run (any swap would let
//     the displayed selection diverge from the rendered video), OR
//   • the scene was auto-selected by the system (auto means auto —
//     a manual override would defeat the "auto" guarantee in the UI).
// Locked candidates still RENDER, but the click handler / focus state /
// "可切换" label all switch to a read-only treatment so the user
// understands the choice is final for this run.
function isSelectionLocked(item: ImageReviewSelectedAsset): boolean {
  if (props.videoGenerated) {
    return true
  }
  const source = String(item?.selection_source || '').trim().toLowerCase()
  return source === 'auto' || source === 'auto_selected'
}

const storyExpanded = ref(false)

// scene_ids whose narration is currently expanded in-place. Replaces
// the old modal-based "详情" flow (which scroll-jumped users from a
// deep scene card back to the top of the viewport — disorienting).
// Now "详情" toggles line-clamp off for just that one card; "收起"
// puts it back. Each card expands independently.
const expandedNarrations = ref<Set<string>>(new Set())
function toggleNarration(sceneId: string) {
  const next = new Set(expandedNarrations.value)
  if (next.has(sceneId)) next.delete(sceneId)
  else next.add(sceneId)
  expandedNarrations.value = next
}
const normalizedStoryText = computed(() => String(props.storyText || '').trim())
const storyNeedsToggle = computed(() => normalizedStoryText.value.length > 260)
const visibleStoryText = computed(() => {
  if (!normalizedStoryText.value) {
    return '故事生成后将在这里展示。'
  }
  if (storyExpanded.value || !storyNeedsToggle.value) {
    return normalizedStoryText.value
  }
  return `${normalizedStoryText.value.slice(0, 260).trim()}...`
})

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
  // Top-level workflow cancel (uses App.vue cancelWorkflow). Distinct from
  // 'cancel-refresh' which only stops the current image-refresh batch.
  (e: 'cancel-workflow'): void
}>()

function toAssetHref(
  path?: string,
  sceneId?: string,
  stableVersion?: string | number,
  retryVersion = 0,
): string {
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

  // Cache-bust per scene: backend overwrites the same file path on
  // regenerate, so without a version param the browser will keep
  // showing the cached old image. The parent bumps the per-scene
  // version after each successful refresh; absent / zero versions
  // are treated as "no bust needed" so unchanged scenes don't refetch.
  const version = stableVersion ?? (sceneId ? props.sceneImageVersions?.[sceneId] : undefined)
  const queryParts: string[] = []
  if (version != null && String(version).length > 0 && String(version) !== '0') {
    queryParts.push(`v=${encodeURIComponent(String(version))}`)
  }
  if (retryVersion > 0) queryParts.push(`retry=${retryVersion}`)
  if (queryParts.length === 0) return `${normalizedBase}${normalizedPath}`
  const separator = normalizedPath.includes('?') ? '&' : '?'
  return `${normalizedBase}${normalizedPath}${separator}${queryParts.join('&')}`
}

function assetRefPath(assetRef?: ImageAssetRef): string {
  if (!assetRef) {
    return ''
  }
  return assetRef.public_url || assetRef.relative_path || ''
}

function cardAssetPath(assetRef?: ImageAssetRef): string {
  if (!assetRef) return ''
  return (
    assetRef.thumbnail_url ||
    assetRef.thumbnail_path ||
    assetRef.public_url ||
    assetRef.relative_path ||
    ''
  )
}

function cardAssetVersion(assetRef?: ImageAssetRef): string | number | undefined {
  if (!assetRef) return undefined
  return assetRef.thumbnail_url || assetRef.thumbnail_path
    ? assetRef.thumbnail_version
    : assetRef.version
}

function imageLoadKey(assetRef: ImageAssetRef | undefined, sceneId: string): string {
  return `${sceneId}:${cardAssetPath(assetRef)}:${cardAssetVersion(assetRef) || ''}`
}

function imageLoadState(assetRef: ImageAssetRef | undefined, sceneId: string): ImageLoadState {
  return imageLoadStates.value[imageLoadKey(assetRef, sceneId)] || 'loading'
}

function cardAssetHref(assetRef: ImageAssetRef | undefined, sceneId: string): string {
  const key = imageLoadKey(assetRef, sceneId)
  return toAssetHref(
    cardAssetPath(assetRef),
    sceneId,
    cardAssetVersion(assetRef),
    imageRetryVersions.value[key] || 0,
  )
}

function originalAssetHref(assetRef: ImageAssetRef | undefined, sceneId: string): string {
  return toAssetHref(assetRefPath(assetRef), sceneId, assetRef?.version)
}

function setImageLoadState(key: string, state: ImageLoadState) {
  imageLoadStates.value = { ...imageLoadStates.value, [key]: state }
}

function clearImageRetryTimer(key: string) {
  const timer = imageRetryTimers.get(key)
  if (timer == null) return
  window.clearTimeout(timer)
  imageRetryTimers.delete(key)
}

function markImageReady(assetRef: ImageAssetRef | undefined, sceneId: string) {
  const key = imageLoadKey(assetRef, sceneId)
  clearImageRetryTimer(key)
  setImageLoadState(key, 'ready')
}

function retryImageGet(assetRef: ImageAssetRef | undefined, sceneId: string) {
  const key = imageLoadKey(assetRef, sceneId)
  if (!cardAssetPath(assetRef) || imageRetryTimers.has(key)) return
  const current = imageRetryAttempts.value[key] || 0
  if (current >= IMAGE_RETRY_DELAYS_MS.length) {
    setImageLoadState(key, 'failed')
    return
  }
  setImageLoadState(key, 'retrying')
  const timer = window.setTimeout(() => {
    imageRetryTimers.delete(key)
    imageRetryAttempts.value = { ...imageRetryAttempts.value, [key]: current + 1 }
    imageRetryVersions.value = {
      ...imageRetryVersions.value,
      [key]: (imageRetryVersions.value[key] || 0) + 1,
    }
    setImageLoadState(key, 'loading')
  }, IMAGE_RETRY_DELAYS_MS[current])
  imageRetryTimers.set(key, timer)
}

function reloadImageManually(assetRef: ImageAssetRef | undefined, sceneId: string) {
  const key = imageLoadKey(assetRef, sceneId)
  if (!cardAssetPath(assetRef)) return
  clearImageRetryTimer(key)
  imageRetryAttempts.value = { ...imageRetryAttempts.value, [key]: 0 }
  imageRetryVersions.value = {
    ...imageRetryVersions.value,
    [key]: (imageRetryVersions.value[key] || 0) + 1,
  }
  setImageLoadState(key, 'loading')
}

function openOriginalAsset(assetRef: ImageAssetRef | undefined, sceneId: string) {
  const href = originalAssetHref(assetRef, sceneId)
  if (href) window.open(href, '_blank', 'noopener,noreferrer')
}

const assetVersionSignature = computed(() =>
  props.items
    .flatMap((item) => [item.selected_asset_ref, ...(item.candidate_asset_refs || [])])
    .map((assetRef) => `${cardAssetPath(assetRef)}:${cardAssetVersion(assetRef) || ''}`)
    .join('|'),
)

watch(assetVersionSignature, () => {
  for (const timer of imageRetryTimers.values()) window.clearTimeout(timer)
  imageRetryTimers.clear()
  imageRetryAttempts.value = {}
  imageRetryVersions.value = {}
  imageLoadStates.value = {}
})

onBeforeUnmount(() => {
  for (const timer of imageRetryTimers.values()) window.clearTimeout(timer)
  imageRetryTimers.clear()
})

function assetRefDebugPath(assetRef?: ImageAssetRef): string {
  if (!assetRef) {
    return '-'
  }
  return assetRef.relative_path || assetRef.public_url || assetRef.file_name || '-'
}

function isImageAsset(path?: string): boolean {
  if (!path) {
    return false
  }

  // Strip query string and hash before checking the file extension —
  // cache-bust suffixes (e.g. "?_=1718999999") make the raw URL end in
  // the timestamp, not in ".png", which previously caused isImageAsset
  // to fail and fall back to the CSS placeholder graphic.
  const pathPart = path.split(/[?#]/)[0].toLowerCase()
  return (
    pathPart.endsWith('.png') ||
    pathPart.endsWith('.jpg') ||
    pathPart.endsWith('.jpeg') ||
    pathPart.endsWith('.webp') ||
    pathPart.endsWith('.gif')
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

function placeholderStatusText(state: ReviewPlaceholderItem['state']): string {
  if (state === 'queued') return '排队中'
  if (state === 'refreshing') {
    return props.cancelRequested ? '正在取消生成' : '正在生成'
  }
  if (state === 'confirming') return '结果确认中'
  if (state === 'done') {
    return '已完成'
  }
  if (state === 'failed') {
    return '生成失败'
  }
  return props.cancelRequested ? '正在取消生成' : '等待生成'
}

function selectedStatusCopy(state: ReviewPlaceholderItem['state']): string {
  if (state === 'queued') return '任务已提交，等待执行'
  if (state === 'refreshing') {
    return props.cancelRequested
      ? '正在取消生成…'
      : '正在生成当前预览图'
  }
  if (state === 'confirming') return '任务可能仍在服务器执行，请勿重复提交'
  if (state === 'done') {
    return '当前预览图已生成'
  }
  if (state === 'failed') {
    return '当前预览图生成失败'
  }
  return props.cancelRequested
    ? '正在取消生成…'
    : '等待生成当前预览图'
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

function candidateStatusCopy(state: ReviewPlaceholderItem['state'], index: 'A' | 'B'): string {
  if (state === 'queued') return `候选图 ${index} 排队中`
  if (state === 'refreshing') {
    return props.cancelRequested
      ? `候选图 ${index} 正在取消生成…`
      : `正在生成候选图 ${index}`
  }
  if (state === 'confirming') return `候选图 ${index} 结果确认中`
  if (state === 'done') {
    return `候选图 ${index} 已生成`
  }
  if (state === 'failed') {
    return `候选图 ${index} 生成失败`
  }
  return props.cancelRequested
    ? `候选图 ${index} 正在取消生成…`
    : `等待生成候选图 ${index}`
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

function sceneNumberLabel(sceneId?: string): string {
  const match = sceneId?.match(/(?:scene[-_]?|^)(\d+)/i)
  if (!match) return ''
  return match[1].padStart(2, '0')
}

function formatSceneDisplayTitle(title: string, narration?: string): string {
  const value = String(title || '').trim()
  if (!value) return value
  if (/[。！？!?…]$/.test(value)) return value

  const narrationText = String(narration || '').trim()
  const continuation = narrationText.startsWith(value)
    ? narrationText.slice(value.length).trimStart()
    : ''
  const continuesWithoutPunctuation =
    Boolean(continuation) && !/^[，。！？、；：,.!?;:）】》」』"']/.test(continuation)

  const endsLikeConnector = /[的和与及在被把让给从向]$/.test(value)
  const endsLikeOpenQuantifier = /(一个又一个|一只又一只|一条又一条|一片又一片|一座又一座|一朵又一朵)$/.test(value)
  const endsLikeVisualFragment =
    /(毛色|眼睛|耳朵|尾巴|皮肤|花纹|身体|腹部|背部|脸颊|鼻子|嘴巴|翅膀|爪子|帽子|衣服)$/.test(value)
  const hasOpenVisualDescription =
    /有着/.test(value) && /(色|毛|眼|耳|尾|皮|纹|身|腹|背|脸|鼻|嘴|翅|爪|帽|衣)$/.test(value)

  return continuesWithoutPunctuation || endsLikeConnector || endsLikeOpenQuantifier || endsLikeVisualFragment || hasOpenVisualDescription
    ? `${value}…`
    : value
}

function sceneDisplayTitle(entry: ReviewRenderEntry): string {
  const rawTitle = String(entry.sceneTitle || '').trim()
  const rawSceneId = String(entry.sceneId || '').trim()
  const technicalTitle = !rawTitle || rawTitle === rawSceneId || rawTitle === 'unknown-scene'
  if (!technicalTitle) {
    return formatSceneDisplayTitle(rawTitle, props.sceneNarrationMap?.[entry.sceneId])
  }

  const sceneNumber = sceneNumberLabel(rawSceneId)
  return sceneNumber ? `场景 ${sceneNumber}` : '场景'
}

function sceneAssetTitle(entry: ReviewRenderEntry, label: string): string {
  const sceneNumber = sceneNumberLabel(entry.sceneId)
  return sceneNumber ? `场景 ${sceneNumber} · ${label}` : label
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
    // If the placeholder is actively refreshing (e.g. user clicked the
    // per-scene "重新生成" button on a done scene), the placeholder's
    // refreshing animation takes priority over the stale done item.
    // Without this, the matched item path wins and the user sees the
    // OLD image unchanged while the background API call runs — there's
    // no visual indication anything's happening, and once the new image
    // arrives it appears to "just change" without any progress feedback.
    if (
      matchedItem &&
      placeholder.state !== 'refreshing' &&
      placeholder.state !== 'queued' &&
      placeholder.state !== 'confirming' &&
      placeholder.state !== 'waiting' &&
      placeholder.state !== 'failed'
    ) {
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
      // Still remove from itemMap so the loop below doesn't re-add the
      // stale done card after the placeholder; once refresh completes,
      // markPlaceholderState(sceneId, 'done') flips the state and the
      // matched-item branch above will pick up the FRESH item on the
      // next render.
      if (matchedItem) {
        itemMap.delete(sceneId)
      }
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
    <h2 class="section-title">画面审核</h2>

    <article class="story-content-card">
      <div class="story-content-head">
        <div>
          <h3 class="story-content-title">故事内容</h3>
          <p class="story-content-desc">图片将根据这段故事生成分镜与画面。</p>
        </div>
        <span
          class="story-content-state"
          :class="{ 'story-content-state-empty': !normalizedStoryText }"
        >
          {{ normalizedStoryText ? '已生成' : '等待生成' }}
        </span>
      </div>

      <p
        class="story-content-text"
        :class="{ 'story-content-text-empty': !normalizedStoryText }"
      >
        {{ visibleStoryText }}
      </p>

      <button
        v-if="storyNeedsToggle"
        type="button"
        class="story-toggle-button"
        @click="storyExpanded = !storyExpanded"
      >
        {{ storyExpanded ? '收起' : '展开全文' }}
      </button>
    </article>

    <!-- Progress text only — bar is shown in the global sticky header -->
    <div v-if="progressText" class="review-progress-inline">
      <InlineStatusPulse
        class="review-progress-copy"
        :variant="cancelRequested ? 'cancelling' : 'running'"
        :text="progressText"
      />
      <button
        v-if="canCancel"
        type="button"
        class="cancel-refresh-button"
        @click="onCancelRefresh"
      >
        停止生成
      </button>
      <!-- Workflow-level cancel — separate concept from canCancel (which
           only stops the image-refresh batch). Visible whenever a workflow
           run is still in flight. -->
      <button
        v-if="cancellable"
        type="button"
        class="cancel-workflow-link"
        :disabled="cancelRequested"
        @click="$emit('cancel-workflow')"
      >
        {{ cancelRequested ? '正在取消…' : '取消生成' }}
      </button>
    </div>

    <!-- Lightweight workflow cancel entry shown when there's no progress
         text (initial workflow phase before image refresh kicks in). -->
    <div
      v-else-if="cancellable"
      class="review-workflow-cancel-bar"
    >
      <InlineStatusPulse
        class="review-workflow-cancel-text"
        :variant="cancelRequested ? 'cancelling' : 'running'"
        :text="cancelRequested ? '正在取消生成，等待当前步骤结束' : '工作流运行中'"
      />
      <button
        type="button"
        class="cancel-workflow-link"
        :disabled="cancelRequested"
        @click="$emit('cancel-workflow')"
      >
        {{ cancelRequested ? '正在取消…' : '取消生成' }}
      </button>
    </div>

    <article v-if="showWaitingCard && renderEntries.length === 0" class="review-waiting-card">
      <!-- Illustration -->
      <div class="waiting-illus">
        <svg class="waiting-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <!-- Photo frame -->
          <rect x="10" y="16" width="80" height="68" rx="8" stroke="currentColor" stroke-width="1.8" stroke-opacity="0.55"/>
          <!-- Top bar -->
          <rect x="10" y="16" width="80" height="16" rx="8" fill="currentColor" fill-opacity="0.07"/>
          <!-- Landscape mountains -->
          <path d="M10 70 L32 45 L48 60 L65 38 L90 70 V84 H10 Z" fill="currentColor" fill-opacity="0.12"/>
          <path d="M10 78 L32 55 L48 68 L65 48 L90 78" stroke="currentColor" stroke-width="1.4" stroke-opacity="0.40" stroke-linecap="round" stroke-linejoin="round"/>
          <!-- Sun / circle -->
          <circle cx="74" cy="32" r="8" stroke="currentColor" stroke-width="1.6" stroke-opacity="0.50"/>
          <circle cx="74" cy="32" r="4" fill="currentColor" fill-opacity="0.30"/>
          <!-- Shimmer lines -->
          <line x1="24" y1="24" x2="50" y2="24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-opacity="0.35"/>
          <line x1="24" y1="24" x2="36" y2="24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-opacity="0.55"/>
        </svg>
        <div class="waiting-illus-glow"/>
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
              {{ sceneDisplayTitle(entry) }}
            </strong>
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
                  v-if="
                    isImageAsset(cardAssetPath(entry.item.selected_asset_ref)) &&
                    ['loading', 'ready'].includes(
                      imageLoadState(entry.item.selected_asset_ref, entry.sceneId),
                    )
                  "
                  class="preview-visual-image"
                  :src="cardAssetHref(entry.item.selected_asset_ref, entry.sceneId)"
                  :alt="entry.sceneTitle || 'selected-image'"
                  :width="entry.item.selected_asset_ref?.thumbnail_width || 480"
                  :height="entry.item.selected_asset_ref?.thumbnail_height || 270"
                  loading="eager"
                  decoding="async"
                  fetchpriority="high"
                  @load="markImageReady(entry.item.selected_asset_ref, entry.sceneId)"
                  @error="retryImageGet(entry.item.selected_asset_ref, entry.sceneId)"
                />
                <div
                  v-else-if="isImageAsset(cardAssetPath(entry.item.selected_asset_ref))"
                  class="placeholder-card image-load-placeholder"
                >
                  <div class="image-load-message">
                    <span>
                      {{
                        imageLoadState(entry.item.selected_asset_ref, entry.sceneId) === 'retrying'
                          ? '图片加载重试中…'
                          : '图片暂时加载失败'
                      }}
                    </span>
                    <div
                      v-if="imageLoadState(entry.item.selected_asset_ref, entry.sceneId) === 'failed'"
                      class="image-load-actions"
                    >
                      <button
                        type="button"
                        @click.stop="reloadImageManually(entry.item.selected_asset_ref, entry.sceneId)"
                      >重新加载</button>
                      <button
                        type="button"
                        @click.stop="openOriginalAsset(entry.item.selected_asset_ref, entry.sceneId)"
                      >查看原图</button>
                    </div>
                  </div>
                </div>
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
                  <span class="preview-title">{{ sceneAssetTitle(entry, '当前图') }}</span>
                  <span class="preview-state-tag preview-state-tag-done">已生成</span>
                </div>

                <!-- Inline narration. Default state clamps to 2 lines
                     so the card height is stable. Long narrations get a
                     "详情" toggle that expands the SAME paragraph in
                     place (no modal — the old modal flow scroll-jumped
                     users back to the viewport top, which was
                     disorienting when expanding a card N screens down).
                     The eyebrow label gives paragraph context so the
                     floating sentence reads as "this scene's narration"
                     and not loose body text. -->
                <p
                  v-if="sceneNarrationMap?.[entry.sceneId]"
                  class="narration-inline-text"
                  :class="{ 'is-expanded': expandedNarrations.has(entry.sceneId) }"
                ><span class="narration-eyebrow">画面内容 ·</span>{{ sceneNarrationMap[entry.sceneId] }}<button
                    v-if="(sceneNarrationMap[entry.sceneId] || '').length > 140"
                    type="button"
                    class="narration-detail-link"
                    @click="toggleNarration(entry.sceneId)"
                  >{{ expandedNarrations.has(entry.sceneId) ? '收起' : '详情' }}</button></p>

                <div class="action-row">
                  <a
                    v-if="isImageAsset(assetRefPath(entry.item.selected_asset_ref))"
                    class="selected-open-link"
                    :href="originalAssetHref(entry.item.selected_asset_ref, entry.sceneId)"
                    target="_blank"
                    rel="noreferrer"
                  >
                    ↗ 查看原图
                  </a>

                  <!-- Manual-mode regenerate. Only useful while the user is
                       still reviewing — once a final video exists the
                       candidates are locked (the displayed selection must
                       match what was baked in). In auto mode the system
                       renders as soon as candidates are ready, so the
                       button has no time window to be useful. -->
                  <button
                    v-if="renderMode === 'manual' && !videoGenerated"
                    type="button"
                    class="regen-scene-button"
                    :disabled="loading || selectingSceneId === entry.sceneId"
                    :title="'对当前场景画面不满意时，重新生成两张候选图'"
                    @click="onRetryScene(entry.sceneId)"
                  >
                    ↻ 重新生成
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="detail-block detail-block-tight">
            <div class="candidate-header">
              <span class="preview-title">候选图</span>
              <span class="candidate-count">
                {{ (entry.item.candidate_asset_refs || []).length || 2 }} 张候选
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
                  'asset-select-card-locked': isSelectionLocked(entry.item),
                }"
                :disabled="
                  loading ||
                  selectingSceneId === entry.sceneId ||
                  isSelectionLocked(entry.item)
                "
                :title="
                  isSelectionLocked(entry.item)
                    ? (videoGenerated
                        ? '视频已生成，候选图不可再切换'
                        : '已自动选择，自动模式下不可手动切换')
                    : undefined
                "
                @click="onSelect(entry.sceneId, candidate)"
              >
                <div class="preview-card preview-card-candidate">
                  <div class="preview-visual-frame preview-visual-frame-candidate">
                    <img
                      v-if="
                        isImageAsset(cardAssetPath(candidate)) &&
                        ['loading', 'ready'].includes(imageLoadState(candidate, entry.sceneId))
                      "
                      class="preview-visual-image"
                      :src="cardAssetHref(candidate, entry.sceneId)"
                      :alt="candidate.file_name || 'candidate-image'"
                      :width="candidate.thumbnail_width || 480"
                      :height="candidate.thumbnail_height || 270"
                      loading="lazy"
                      decoding="async"
                      fetchpriority="low"
                      @load="markImageReady(candidate, entry.sceneId)"
                      @error="retryImageGet(candidate, entry.sceneId)"
                    />

                    <div
                      v-else-if="isImageAsset(cardAssetPath(candidate))"
                      class="placeholder-card image-load-placeholder"
                    >
                      <div class="image-load-message">
                        <span>
                          {{
                            imageLoadState(candidate, entry.sceneId) === 'retrying'
                              ? '图片加载重试中…'
                              : '图片暂时加载失败'
                          }}
                        </span>
                        <div
                          v-if="imageLoadState(candidate, entry.sceneId) === 'failed'"
                          class="image-load-actions"
                        >
                          <span
                            role="button"
                            tabindex="0"
                            @click.stop="reloadImageManually(candidate, entry.sceneId)"
                          >重新加载</span>
                          <span
                            role="link"
                            tabindex="0"
                            @click.stop="openOriginalAsset(candidate, entry.sceneId)"
                          >查看原图</span>
                        </div>
                      </div>
                    </div>

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
                      <span class="preview-title">
                        {{ sceneAssetTitle(entry, `候选 ${candidateLabel(candidate, index)}`) }}
                      </span>
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
                            : (isSelectionLocked(entry.item)
                                ? (videoGenerated ? '已锁定' : '自动模式')
                                : '可切换')
                        }}
                      </span>
                    </div>

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
                  <span class="preview-title">{{ sceneAssetTitle(entry, '当前图') }}</span>
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
                        ? (cancelRequested ? '取消中' : '生成中')
                        : entry.state === 'failed'
                          ? '失败'
                          : (cancelRequested ? '取消中' : '等待中')
                    }}
                  </span>
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
              <span class="candidate-count">2 张候选</span>
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
                            ? (cancelRequested ? '取消中' : '生成中')
                            : entry.state === 'failed'
                              ? '失败'
                              : (cancelRequested ? '取消中' : '等待中')
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
                            ? (cancelRequested ? '取消中' : '生成中')
                            : entry.state === 'failed'
                              ? '失败'
                              : (cancelRequested ? '取消中' : '等待中')
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

        <details class="scene-developer-info">
          <summary>开发者信息</summary>

          <div class="developer-info-grid">
            <div class="developer-info-row">
              <span class="developer-info-label">场景 ID</span>
              <code>{{ entry.sceneId || '-' }}</code>
            </div>

            <template v-if="entry.kind === 'item'">
              <div class="developer-info-row">
                <span class="developer-info-label">筛选策略</span>
                <code>{{ entry.item.selection_source || '-' }}</code>
              </div>
              <div class="developer-info-row">
                <span class="developer-info-label">生成策略</span>
                <code>{{ entry.item.selection_mode || '-' }}</code>
              </div>
              <div class="developer-info-row">
                <span class="developer-info-label">当前图路径</span>
                <code>{{ assetRefDebugPath(entry.item.selected_asset_ref) }}</code>
              </div>
              <div
                v-for="(candidate, index) in entry.item.candidate_asset_refs || []"
                :key="candidate.relative_path || candidate.file_name || candidate.public_url || index"
                class="developer-info-row"
              >
                <span class="developer-info-label">候选 {{ candidateLabel(candidate, index) }} 路径</span>
                <code>{{ assetRefDebugPath(candidate) }}</code>
              </div>
              <div v-if="entry.item.prompt" class="developer-info-row">
                <span class="developer-info-label">图片提示词</span>
                <code>{{ entry.item.prompt }}</code>
              </div>
            </template>

            <template v-else>
              <div class="developer-info-row">
                <span class="developer-info-label">生成策略</span>
                <code>progressive_scene_refresh</code>
              </div>
              <div class="developer-info-row">
                <span class="developer-info-label">当前图路径</span>
                <code>pending://{{ entry.sceneId }}/selected</code>
              </div>
              <div class="developer-info-row">
                <span class="developer-info-label">候选 A 路径</span>
                <code>pending://{{ entry.sceneId }}/candidate_a</code>
              </div>
              <div class="developer-info-row">
                <span class="developer-info-label">候选 B 路径</span>
                <code>pending://{{ entry.sceneId }}/candidate_b</code>
              </div>
            </template>
          </div>
        </details>
      </article>
    </div>

  </section>
</template>

<style scoped>
.result-panel {
  margin-top: 0;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: none;
}

.section-title {
  margin: 0 0 10px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  text-align: left;
}

.story-content-card {
  margin: 0 0 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--glass-bg);
  border: 1px solid rgba(245,158,11,0.12);
  box-shadow: var(--shadow-glass);
}

.story-content-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.story-content-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
  font-weight: 700;
}

.story-content-desc {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 0.75rem;
  line-height: 1.5;
}

.story-content-state {
  flex-shrink: 0;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(245,158,11,0.14);
  color: var(--arc-300);
  font-size: 12px;
  font-weight: 700;
  line-height: 24px;
}

.story-content-state-empty {
  background: rgba(255,255,255,0.07);
  color: var(--text-muted);
}

.story-content-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  line-height: 1.85;
  white-space: pre-wrap;
}

.story-content-text-empty {
  color: var(--text-muted);
}

.story-toggle-button {
  margin-top: 10px;
  width: fit-content;
  border: none;
  background: transparent;
  color: var(--arc-300);
  cursor: pointer;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 700;
  padding: 0;
}

.story-toggle-button:hover {
  color: var(--arc-200);
  text-decoration: underline;
}

/* Inline progress — just text + cancel, no duplicate bar */
.review-progress-inline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 0 0 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(245,158,11,0.06);
  border: 1px solid rgba(245,158,11,0.12);
}

.review-progress-copy {
  flex: 1;
  min-width: 0;
  color: var(--arc-300);
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.4;
}

.summary-status {
  color: var(--arc-300);
  font-size: 0.75rem;
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
  color: var(--text-secondary);
  line-height: 1.5;
}

.scene-subtext {
  margin: 6px 0 0;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.asset-code-wrap {
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-overlay-strong);
}

.asset-code-wrap-compact {
  padding: 8px 10px;
}

.asset-code-text {
  display: block;
  color: var(--text-secondary);
  line-height: 1.45;
  font-size: 0.75rem;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: anywhere;
  font-family: var(--font-mono, monospace);
}

.review-scene-grid {
  display: grid;
  gap: 14px;
}

.review-scene-card {
  padding: 14px;
  border-radius: 16px;
  background: var(--glass-bg);
  border: 1px solid var(--border-glass);
  box-shadow: var(--shadow-glass);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.review-scene-card:hover {
  border-color: var(--border-arc);
  box-shadow: var(--shadow-glass), 0 0 0 1px var(--border-glass);
}

.review-scene-card-placeholder {
  background: var(--glass-bg-light);
  border-color: var(--border-glass);
}

.review-scene-card-refreshing {
  border-color: var(--border-arc);
  box-shadow: var(--shadow-glass), var(--glow-arc);
}

.review-scene-card-failed {
  border-color: rgba(248,113,133,0.35);
  background: rgba(248,113,133,0.05);
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
  color: var(--text-primary);
  font-size: 1.0625rem;
  font-weight: 600;
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
  background: var(--glass-bg);
  border: 1px solid var(--border-glass);
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
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-strong);
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
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
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
  background: rgba(245,158,11,0.14);
  color: var(--arc-300);
}

.preview-state-tag-waiting {
  background: rgba(255,255,255,0.07);
  color: var(--text-muted);
}

/* Pearl (light) theme: the dark-theme `rgba(255,255,255,0.07)` bg is
   white-at-7% which is invisible against pearl's white surface. Swap
   to a soft champagne wash matching the page accent system. */
:root[data-theme="pearl"] .preview-state-tag-waiting {
  background: rgba(200, 154, 85, 0.08);
  color: var(--text-muted);
}

.preview-state-tag-refreshing {
  background: rgba(245,158,11,0.15);
  color: var(--arc-300);
}

.preview-state-tag-failed {
  background: rgba(248,113,133,0.15);
  color: #f87171;
}

/* Three actions on the same row share an explicit pill shape.
   Using `height` (not `min-height`) + `inline-flex` + `align-items:
   center` on all three guarantees they render at the EXACT same
   pixel height regardless of <a> vs <button> intrinsic differences.
   Individual `margin-top` is dropped — the parent .action-row
   handles spacing via `gap`. */
.selected-open-link,
.regen-scene-button {
  height: 32px;
  padding: 0 12px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.8125rem;
  font-weight: 600;
  font-family: inherit;
  line-height: 1;
  box-sizing: border-box;
  margin-top: 0;
  white-space: nowrap;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  text-decoration: none;
}

.selected-open-link {
  border: 1px solid rgba(245, 158, 11, 0.32);
  background: rgba(245, 158, 11, 0.06);
  color: var(--arc-300);
}
.selected-open-link:hover {
  background: rgba(245, 158, 11, 0.14);
  border-color: rgba(245, 158, 11, 0.52);
  color: var(--arc-200);
  text-decoration: none;
}

.placeholder-status-copy {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  line-height: 1.5;
}

.placeholder-error-copy {
  color: #f87171;
  font-size: 0.75rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.retry-scene-button {
  width: fit-content;
  min-height: 32px;
  padding: 0 14px;
  border-radius: 8px;
  border: 1px solid rgba(248,113,133,0.35);
  background: rgba(248,113,133,0.10);
  color: #fca5a5;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}

.retry-scene-button:hover:not(:disabled) {
  background: rgba(248,113,133,0.18);
  border-color: rgba(248,113,133,0.55);
}

.retry-scene-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.regen-scene-button {
  border: 1px solid rgba(245,158,11,0.32);
  background: rgba(245,158,11,0.10);
  color: var(--arc-300);
}
.regen-scene-button:hover:not(:disabled) {
  background: rgba(245,158,11,0.18);
  border-color: rgba(245,158,11,0.52);
}
.regen-scene-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
:root[data-theme="pearl"] .selected-open-link,
:root[data-theme="pearl"] .regen-scene-button {
  border-color: rgba(200, 154, 85, 0.35);
  background: rgba(200, 154, 85, 0.10);
  color: var(--arc-300);
}
:root[data-theme="pearl"] .selected-open-link:hover,
:root[data-theme="pearl"] .regen-scene-button:hover:not(:disabled) {
  background: rgba(200, 154, 85, 0.18);
  border-color: rgba(200, 154, 85, 0.55);
}

.regen-scene-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* Narration paragraph with inline label prefix. Putting the "画面内容"
   label as a <span> INSIDE the <p> (not as a separate flex item) means
   wrapped lines start at the paragraph's left edge — no awkward
   indent on the second line. The eyebrow inherits the text baseline
   naturally because it's part of the inline flow. */
.narration-eyebrow {
  margin-right: 8px;
  color: var(--text-muted);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  vertical-align: baseline;
}
.narration-inline-text {
  margin: 4px 0 8px;
  color: var(--text-secondary, #c8c8c8);
  font-size: 0.875rem;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  transition: -webkit-line-clamp 200ms ease;
}
.narration-inline-text.is-expanded {
  -webkit-line-clamp: unset;
  line-clamp: unset;
  overflow: visible;
}
.narration-detail-link {
  display: inline;
  margin-left: 6px;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--arc-300, #fbbf24);
  font-family: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  vertical-align: baseline;
}
.narration-detail-link:hover {
  text-decoration: underline;
}

/* Buttons row — groups 查看原图 + ↻ 重新生成 into one horizontal
   action band, separated from the narration above. */
.action-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.candidate-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.candidate-count {
  color: var(--text-muted);
  font-size: 0.75rem;
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
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
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
  border-color: rgba(245,158,11,0.38);
  box-shadow: 0 4px 20px rgba(245,158,11,0.14), 0 0 0 1px rgba(245,158,11,0.10);
  transform: translateY(-1px);
}

.asset-select-card.active {
  border-color: var(--arc-400);
  box-shadow: 0 0 0 2px rgba(245,158,11,0.22), 0 0 24px rgba(245,158,11,0.18);
  background: rgba(245,158,11,0.06);
}

.asset-select-card:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* Locked candidates keep their image readable (so the user still sees
   what was selected) but lose hover-affordance — the cursor becomes
   not-allowed and the un-selected card visibly recedes so it doesn't
   look like a live click target. The .active rule above still wins on
   the selected card, so the chosen one stays highlighted. */
.asset-select-card-locked {
  cursor: not-allowed;
}
.asset-select-card-locked:not(.active) {
  opacity: 0.55;
}

.asset-select-card-static {
  cursor: default;
}

.candidate-file-chip {
  display: inline-block;
  max-width: 100%;
  padding: 3px 7px;
  border-radius: 5px;
  background: var(--surface-overlay-strong);
  color: var(--text-muted);
  font-size: 0.6875rem;
  line-height: 1.35;
  word-break: break-all;
  font-family: var(--font-mono, monospace);
}

.scene-developer-info {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid rgba(245,158,11,0.08);
}

.scene-developer-info summary {
  width: fit-content;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.scene-developer-info summary:hover {
  color: var(--arc-300);
}

.developer-info-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.developer-info-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--surface-overlay-strong);
  border: 1px solid rgba(245,158,11,0.07);
}

.developer-info-label {
  color: var(--text-muted);
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.developer-info-row code {
  color: var(--text-secondary);
  font-size: 0.75rem;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  overflow-wrap: anywhere;
  font-family: var(--font-mono, monospace);
}

/* ── Dark placeholder artwork — theme-aware glass landscape.
   All accent colours are derived from --arc-* / --border-glass tokens,
   so the placeholder picks up champagne in black-gold, ice blue in 极夜蓝调,
   and violet in 暗紫星芒. Pearl Dawn keeps its warm storybook look via
   the :root[data-theme="pearl"] overrides further down. ── */
.placeholder-card {
  position: relative;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    160deg,
    color-mix(in srgb, var(--arc-400) 4%, #0a0a0d) 0%,
    color-mix(in srgb, var(--arc-400) 2%, #0e0e12) 100%
  );
}

.image-load-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-load-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  color: var(--text-muted);
  font-size: 0.75rem;
  text-align: center;
}

.image-load-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.image-load-actions button,
.image-load-actions span {
  border: 0;
  background: transparent;
  color: var(--arc-300);
  cursor: pointer;
  font: inherit;
  font-weight: 700;
}

.placeholder-art {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.placeholder-badge {
  display: none;
}

.placeholder-canvas {
  position: absolute;
  inset: 14px 12px 12px 12px;
  border-radius: 10px;
  overflow: hidden;
  background: #0a0a0d;
  border: 1px solid var(--border-glass);
}

.placeholder-sky {
  position: absolute;
  inset: 0 0 38% 0;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 14%, #16161e) 0%,
    color-mix(in srgb, var(--arc-400) 6%, #0e0e16) 100%
  );
}

.placeholder-cloud {
  position: absolute;
  height: 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 42%, transparent);
}

.placeholder-cloud::before,
.placeholder-cloud::after {
  content: '';
  position: absolute;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 42%, transparent);
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
  background: color-mix(in srgb, var(--arc-400) 18%, #1c1c26);
}

.placeholder-hill-front {
  right: -8%;
  width: 84%;
  height: 30%;
  background: color-mix(in srgb, var(--arc-400) 26%, #15151e);
}

.placeholder-water {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 24%;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 10%, #10101a) 0%,
    color-mix(in srgb, var(--arc-400) 4%, #08080d) 100%
  );
}

.placeholder-sun {
  position: absolute;
  top: 16%;
  right: 18%;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--arc-300);
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--arc-300) 16%, transparent),
    0 0 8px color-mix(in srgb, var(--arc-300) 22%, transparent);
}

.placeholder-tree {
  position: absolute;
  bottom: 18%;
  width: 5px;
  background: color-mix(in srgb, var(--arc-400) 10%, #060608);
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
  background: color-mix(in srgb, var(--arc-400) 10%, #060608);
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
  height: 6px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-300) 14%, transparent);
}
.shimmer-active::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    transparent 18%,
    color-mix(in srgb, var(--arc-300) 14%, transparent) 46%,
    transparent 74%
  );
  transform: translateX(-120%);
  animation: reviewShimmer 1.6s linear infinite;
  pointer-events: none;
}

/* ─── Pearl Dawn — stronger shimmer overlay (generation in progress) ─── */
:root[data-theme="pearl"] .shimmer-active::after {
  background: linear-gradient(
    110deg,
    rgba(255, 193, 80, 0) 12%,
    rgba(255, 193, 80, 0.40) 45%,
    rgba(255, 215, 130, 0.55) 50%,
    rgba(255, 193, 80, 0.40) 55%,
    rgba(255, 193, 80, 0) 88%
  );
  mix-blend-mode: normal;
}

/* ─── Pearl Dawn — replace deep brown landscape with cream-gold ─── */
:root[data-theme="pearl"] .placeholder-card {
  background: linear-gradient(160deg, #fdf9eb 0%, #faf3df 100%);
}
:root[data-theme="pearl"] .placeholder-canvas {
  background: #fdf6df;
  border: 1px solid rgba(200,154,85,0.20);
}
:root[data-theme="pearl"] .placeholder-sky {
  background: linear-gradient(180deg, #fff5d8 0%, #fdebc2 100%);
}
:root[data-theme="pearl"] .placeholder-cloud,
:root[data-theme="pearl"] .placeholder-cloud::before,
:root[data-theme="pearl"] .placeholder-cloud::after {
  background: rgba(255,255,255,0.85);
}
:root[data-theme="pearl"] .placeholder-hill-back  { background: #f0d89a; }
:root[data-theme="pearl"] .placeholder-hill-front { background: #e6c478; }
:root[data-theme="pearl"] .placeholder-water {
  background: linear-gradient(180deg, #fbe6b3 0%, #f4d68c 100%);
}
:root[data-theme="pearl"] .placeholder-sun {
  background: rgba(255,193,80,0.55);
  box-shadow: 0 0 0 6px rgba(255,193,80,0.20), 0 0 22px rgba(255,193,80,0.32);
}
:root[data-theme="pearl"] .placeholder-tree,
:root[data-theme="pearl"] .placeholder-tree::before { background: #c89a55; }
:root[data-theme="pearl"] .placeholder-caption-bar { background: rgba(200,154,85,0.18); }


.review-waiting-card {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 24px;
  align-items: center;
  padding: 24px 20px;
  border-radius: 16px;
  background: rgba(245,158,11,0.04);
  border: 1px solid rgba(245,158,11,0.14);
}

.waiting-illus {
  position: relative;
  width: 110px;
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.waiting-svg {
  width: 100px;
  height: 100px;
  color: var(--arc-300);
  filter: drop-shadow(0 0 14px rgba(245,158,11,0.35));
  animation: waitingPulse 3s ease-in-out infinite;
}

.waiting-illus-glow {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(245,158,11,0.10) 0%, transparent 70%);
  animation: waitingPulse 3s ease-in-out infinite;
}

@keyframes waitingPulse {
  0%,100% { opacity: 0.70; transform: scale(1); }
  50%      { opacity: 1.00; transform: scale(1.04); }
}

.waiting-copy {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.waiting-title {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text-primary);
}

.waiting-message {
  margin: 0;
  color: var(--text-secondary);
  line-height: 1.65;
  font-size: 0.875rem;
}

.waiting-actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.refresh-button {
  appearance: none;
  border: none;
  background: linear-gradient(90deg, var(--arc-400), var(--prism-500));
  color: #fff;
  border-radius: 999px;
  padding: 10px 20px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  box-shadow: 0 4px 14px rgba(245,158,11,0.30);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.refresh-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(245,158,11,0.42);
}

.refresh-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cancel-refresh-button {
  appearance: none;
  flex-shrink: 0;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(255,255,255,0.05);
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 0.8125rem;
  font-weight: 700;
  cursor: pointer;
  font-family: inherit;
  transition:
    border-color 0.2s ease,
    color 0.2s ease,
    background 0.2s ease,
    transform 0.2s ease;
}

.cancel-refresh-button:hover {
  border-color: rgba(248,113,133,0.50);
  color: #fca5a5;
  background: rgba(248,113,133,0.08);
  transform: translateY(-1px);
}

/* Lightweight workflow-cancel pill — sits alongside / inside the inline
   progress strip without competing with the larger image-refresh stop. */
.cancel-workflow-link {
  appearance: none;
  flex-shrink: 0;
  border: 1px solid color-mix(in srgb, var(--text-muted) 55%, transparent);
  background: transparent;
  color: var(--text-secondary);
  border-radius: 999px;
  padding: 4px 11px;
  font-size: 0.6875rem;
  font-family: inherit;
  letter-spacing: 0.02em;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.cancel-workflow-link:hover:not(:disabled) {
  border-color: rgba(248, 113, 133, 0.55);
  color: #fca5a5;
  background: rgba(248, 113, 133, 0.06);
}
.cancel-workflow-link:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

/* Independent strip shown when there's no progressText (initial workflow
   phase before image refresh kicks in). */
.review-workflow-cancel-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 4px 0 8px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
}
.review-workflow-cancel-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  letter-spacing: 0.02em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
