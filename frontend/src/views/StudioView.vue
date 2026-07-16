<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import StudioLayout from '../components/studio/StudioLayout.vue'
import StudioProgress from '../components/studio/StudioProgress.vue'
import StudioCreatePanel from '../components/studio/StudioCreatePanel.vue'
import StudioPreviewPanel from '../components/studio/StudioPreviewPanel.vue'
import DiagnosticsPanel from '../components/studio/DiagnosticsPanel.vue'
import InteractiveImageReview from '../components/InteractiveImageReview.vue'
import WorkflowResultsPanel from '../components/WorkflowResultsPanel.vue'
import WorkflowRunPanel from '../components/WorkflowRunPanel.vue'
import InspirationLibraryPanel from '../components/InspirationLibraryPanel.vue'
import type { InspirationItem } from '../data/inspirationLibrary'
import FinalVideoPanel from '../components/FinalVideoPanel.vue'
import {
  summarizeImageGeneration,
  summarizeWorkflowProgress,
  type ImageGenerationSummary,
  type SceneGenerationState,
  type WorkflowProgressSummary,
} from '../lib/workflowState'

type StepName = string

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

type WorkflowRunPayload = {
  workflow_id: string
  session_id: string
  input: Record<string, unknown>
  steps: Array<{ name: StepName }>
}

type WorkflowStatusResponse = {
  workflow_id?: string
  status?: string
  message?: string
  current_step?: string
  current_step_index?: number
  completed_steps?: number
  total_steps?: number
  progress_percent?: number
}

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

type ImageReviewSelectResponse = {
  workflow_id?: string
  session_id?: string
  run_id?: string
  scene_id?: string
  image_review?: Record<string, unknown>
  image_assets?: Record<string, unknown>
  video_prompts?: Record<string, unknown>
  timestamp?: string
  final_video?: Record<string, unknown>
  audio_segments?: Record<string, unknown>
  subtitles?: Record<string, unknown>
  storyboard?: Record<string, unknown>
}

type ReviewWaitingState =
  | 'idle'
  | 'deferred_pending'
  | 'refreshing'
  | 'rate_limited_retrying'
  | 'ready'

type StructuredCharacterInput = {
  display_name: string
  species: string
  role_type: 'primary' | 'secondary'
  visual_traits: string
  forbidden_traits: string
}

type AudioSceneAsset = {
  asset_id?: string
  segment_id?: string
  speaker?: string
  file_name?: string
  public_url?: string
  duration_estimate_sec?: number
}

type AudioSceneGroup = {
  scene_id?: string
  assets?: AudioSceneAsset[]
}

type AudioDirectoryAssetFile = {
  asset_id?: string
  file_name?: string
  metadata_file?: string
  metadata_public_url?: string
}

type AudioDirectoryManifest = {
  run_directory?: string
  public_base_url?: string
  index_file?: string
  index_public_url?: string
  asset_files?: AudioDirectoryAssetFile[]
}

type AudioSegmentsOutput = {
  directory_manifest?: AudioDirectoryManifest
  scene_asset_map?: AudioSceneGroup[]
}

type SampleAssetPaths = {
  notes?: string
  clean_video?: string
  watermarked_video?: string
  input_screenshot?: string
  result_screenshots?: string[]
}

type KlingSample = {
  sample_id?: string
  scene_id?: string
  generated_scene_id?: string
  status?: string
  notes?: string
  assets?: SampleAssetPaths
}

type SamplesSummaryResponse = {
  providers?: string[]
  total_sample_count?: number
  provider_stats?: Record<
    string,
    {
      sample_count?: number
      latest_sample_id?: string
      available_scene_ids?: string[]
    }
  >
}

type ImageRefreshTaskResponse = {
  task_id: string
  workflow_id: string
  run_id: string
  scene_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  result?: Record<string, unknown>
  error?: string
}

type ImageRefreshTaskBatchResponse = {
  workflow_id: string
  run_id: string
  found: boolean
  tasks: ImageRefreshTaskResponse[]
}

type FinalVideoRenderResponse = {
  workflow_id?: string
  session_id?: string
  run_id?: string
  final_video?: Record<string, unknown>
  timestamp?: string
}

type ReviewPlaceholderItem = {
  scene_id: string
  scene_title: string
  state: 'waiting' | 'queued' | 'refreshing' | 'confirming' | 'done' | 'failed'
  error_message?: string
}

const userHasInteractedWithImages = ref(false)

const createStudioSessionId = () => `studio-session-${Date.now().toString(36)}`
const createStoryWorkflowId = () => `story-video-${Date.now()}`

const DEFAULT_WORKFLOW_FORM: any = {
  sessionId: 'studio-session-001',
  topic: '写一个关于小猫冒险的故事',
  audience: 'children',
  tone: 'warm',
  visualStyle: 'cute_chibi_anime',
  characterStyle: 'animal',
  voiceStyle: 'warm_female',
  voiceoverEnabled: true,
  voiceMode: 'single',
  narratorVoiceStyle: 'warm_female',
  motherVoiceStyle: 'warm_female',
  childVoiceStyle: 'gentle_child',
  durationSec: 120,
  language: 'zh-CN',
  subtitleEnabled: true,
  videoProvider: 'mock',
  outputMode: 'full_video',

  structuredCharactersEnabled: false,
  primaryCharacterDisplayName: '',
  primaryCharacterSpecies: '',
  primaryCharacterVisualTraits: '',
  primaryCharacterForbiddenTraits: '',
  secondaryCharacterDisplayName: '',
  secondaryCharacterSpecies: '',
  secondaryCharacterVisualTraits: '',
  secondaryCharacterForbiddenTraits: '',
  renderMode: 'auto',
  audioEnabled: true,
  qualityTier: 'quality',
}

const STEP_OPTIONS: Array<{ label: string; value: StepName }> = [
  { label: '故事生成',   value: 'story' },
  { label: '分镜规划',   value: 'storyboard' },
  { label: '图像提示词', value: 'image_prompts' },
  { label: '图像资源',   value: 'image_assets' },
  { label: '视频提示词', value: 'video_prompts' },
  { label: '对白脚本',   value: 'dialogue_script' },
  { label: '音频片段',   value: 'audio_segments' },
  { label: '旁白生成',   value: 'narration' },
  { label: '字幕生成',   value: 'subtitles' },
  { label: '渲染计划',   value: 'render_plan' },
  { label: '最终视频',   value: 'final_video' },
]

const DEFAULT_STEPS: StepName[] = [
  'story',
  'storyboard',
  'image_prompts',
  'image_assets',
  'video_prompts',
  'dialogue_script',
  'audio_segments',
  'narration',
  'subtitles',
  'render_plan',
  'final_video',
]

function workflowStepLabel(stepName: string): string {
  return (
    STEP_OPTIONS.find((item) => item.value === stepName)?.label ||
    stepName
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  )
}

const loading = ref(false)
const finalVideoRenderInFlight = ref(false)
const errorMessage = ref('')
const workflowRunElapsedSec = ref(0)
const workflowStatusData = ref<WorkflowStatusResponse | null>(null)
const resultText = ref('')

// The workflow_id of the currently in-flight run — needed to POST cancel.
const activeWorkflowId = ref<string>('')
// True after user clicks cancel and before the runner reaches its next
// checkpoint; UI flips button text to "正在取消…".
const cancelRequested = ref(false)

const storyText = ref('')
/** Raw JSON of `outputs.story` — the full LLM step output (title,
 *  text, generation_source, provider_used, fallback_reason, segments,
 *  etc.). Exposed to WorkflowResultsPanel so the 生成细节 "故事"
 *  section has a real raw view, not just the narrative text. */
const storyOutputText = computed(() => {
  const story = currentWorkflowResponse.value?.outputs?.story
  if (!story || typeof story !== 'object') return ''
  try {
    return JSON.stringify(story, null, 2)
  } catch {
    return ''
  }
})
const storyboardText = ref('')
const imagePromptsText = ref('')
const imageAssetsText = ref('')
const imageReviewText = ref('')
const videoPromptsText = ref('')
const narrationText = ref('')
const subtitlesText = ref('')
const renderPlanText = ref('')
const finalVideoText = ref('')
const finalVideoUrl = ref('')
type VideoPreviewLoadState = 'idle' | 'loading' | 'ready' | 'retrying' | 'failed'
const VIDEO_PREVIEW_RETRY_DELAYS_MS = [1000, 2500] as const
const videoPreviewLoadState = ref<VideoPreviewLoadState>('idle')
const videoPreviewRetryCount = ref(0)
const videoPreviewRetryVersion = ref(0)
let videoPreviewRetryTimer: number | null = null

function clearVideoPreviewRetryTimer() {
  if (videoPreviewRetryTimer == null) return
  window.clearTimeout(videoPreviewRetryTimer)
  videoPreviewRetryTimer = null
}

const videoPreviewUrl = computed(() => {
  const url = finalVideoUrl.value
  if (!url || videoPreviewRetryVersion.value === 0) return url
  const hashIndex = url.indexOf('#')
  const base = hashIndex >= 0 ? url.slice(0, hashIndex) : url
  const hash = hashIndex >= 0 ? url.slice(hashIndex) : ''
  const separator = base.includes('?') ? '&' : '?'
  return `${base}${separator}preview_retry=${videoPreviewRetryVersion.value}${hash}`
})
const videoPreviewPlayerKey = computed(
  () => `${finalVideoUrl.value || 'idle'}::${videoPreviewRetryVersion.value}`,
)
const videoPreviewStatusText = computed(() => {
  if (videoPreviewLoadState.value === 'loading') return '视频已生成，正在加载预览…'
  if (videoPreviewLoadState.value === 'retrying') return '视频预览加载失败，正在重试…'
  if (videoPreviewLoadState.value === 'ready') return '视频预览已就绪'
  if (videoPreviewLoadState.value === 'failed') return '视频预览加载失败'
  return ''
})

watch(finalVideoUrl, (url) => {
  clearVideoPreviewRetryTimer()
  videoPreviewRetryCount.value = 0
  videoPreviewRetryVersion.value = 0
  videoPreviewLoadState.value = url ? 'loading' : 'idle'
}, { immediate: true })

function markVideoPreviewReady() {
  if (!finalVideoUrl.value) return
  clearVideoPreviewRetryTimer()
  videoPreviewLoadState.value = 'ready'
}

function handleVideoPreviewError() {
  const failedUrl = finalVideoUrl.value
  if (
    !failedUrl ||
    videoPreviewLoadState.value === 'failed' ||
    videoPreviewRetryTimer != null
  ) return
  if (videoPreviewRetryCount.value >= VIDEO_PREVIEW_RETRY_DELAYS_MS.length) {
    videoPreviewLoadState.value = 'failed'
    return
  }

  const delay = VIDEO_PREVIEW_RETRY_DELAYS_MS[videoPreviewRetryCount.value]
  videoPreviewRetryCount.value += 1
  videoPreviewLoadState.value = 'retrying'
  videoPreviewRetryTimer = window.setTimeout(() => {
    videoPreviewRetryTimer = null
    if (finalVideoUrl.value !== failedUrl) return
    videoPreviewRetryVersion.value += 1
    videoPreviewLoadState.value = 'loading'
  }, delay)
}

function reloadVideoPreviewManually() {
  if (!finalVideoUrl.value) return
  clearVideoPreviewRetryTimer()
  videoPreviewRetryCount.value = 0
  videoPreviewRetryVersion.value += 1
  videoPreviewLoadState.value = 'loading'
}

onBeforeUnmount(clearVideoPreviewRetryTimer)
const finalVideoAudioEnabled = ref(true)
const recentFinalVideoUrls = ref<string[]>([])

// Parallel metadata map for the history list. Kept separate from the
// string[] of URLs so existing read sites (delete, dedupe, etc.) stay
// simple — they only deal with URLs. Hover labels, card subtitles and
// future analytics read from this map.
//
// Schema (per URL): { title?, topic?, createdAt?, posterUrl?, workflowId?, runId? }
// All fields optional — old entries from before this commit have no
// metadata and gracefully fall back to "视频 N".
export interface RecentVideoMeta {
  title?: string
  topic?: string
  createdAt?: string
  posterUrl?: string
  workflowId?: string
  runId?: string
}
const recentVideoMetadata = ref<Record<string, RecentVideoMeta>>({})

function pushRecentFinalVideoUrl(url: string, meta?: RecentVideoMeta) {
  const u = String(url || '').trim()
  if (!u) return
  // Respect the user-driven deletion blacklist so a deleted URL stays
  // gone after page reload / reattach.
  if (deletedVideoUrlsSet.value.has(u)) return

  // 去重：最新的放最前
  recentFinalVideoUrls.value = [
    u,
    ...recentFinalVideoUrls.value.filter((item) => item !== u),
  ].slice(0, 10)

  // Existing values win so a later SPA restore cannot overwrite the
  // generation-time title/topic. Newly available fields (notably posterUrl
  // for records written by older builds) are still allowed to backfill.
  if (meta) {
    const existing = recentVideoMetadata.value[u]
    recentVideoMetadata.value = {
      ...recentVideoMetadata.value,
      [u]: existing
        ? {
            ...meta,
            ...existing,
            posterUrl: meta.posterUrl || existing.posterUrl,
            workflowId: existing.workflowId || meta.workflowId,
            runId: existing.runId || meta.runId,
          }
        : meta,
    }
  }
  // Drop metadata entries whose URL is no longer in the list so the
  // map doesn't grow unbounded as users churn history.
  const liveUrlSet = new Set(recentFinalVideoUrls.value)
  recentVideoMetadata.value = Object.fromEntries(
    Object.entries(recentVideoMetadata.value).filter(([key]) => liveUrlSet.has(key)),
  )

  // Persist both the URL list and the metadata map. STORAGE_KEY_VIDEO_URL
  // only ever held the latest one; the meta key is new.
  try {
    localStorage.setItem(
      STORAGE_KEY_RECENT_VIDEOS,
      JSON.stringify(recentFinalVideoUrls.value),
    )
    localStorage.setItem(
      STORAGE_KEY_RECENT_VIDEO_META,
      JSON.stringify(recentVideoMetadata.value),
    )
  } catch {
    /* quota / serialisation failures are non-fatal */
  }
}

// Pulls a human-readable title (LLM-generated story title) out of the
// given workflow response object. Takes the response as an arg
// instead of reading `currentWorkflowResponse.value` because the
// caller in applyWorkflowResponse runs *before* the ref assignment
// (look at the order in applyWorkflowResponse: pushRecentFinalVideoUrl
// is called on line ~1885, currentWorkflowResponse.value = data is on
// line ~1898). Reading the ref here would see the *previous* run's
// title — or null on cold start — so every new history card silently
// fell back to "视频 N". Taking the data param fixes this without
// reordering the larger applyWorkflowResponse pipeline.
function deriveVideoMeta(response: WorkflowRunResponse | null | undefined): RecentVideoMeta | undefined {
  if (!response) return undefined
  const story = response.outputs?.story as
    | Record<string, unknown>
    | undefined
  const title =
    story && typeof story.title === 'string' ? story.title.trim() : ''
  const topic = (workflowForm.value?.topic || '').trim()
  const storyboard = response.outputs?.storyboard as Record<string, unknown> | undefined
  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes : []
  const firstSceneId = scenes.length > 0 && scenes[0] && typeof scenes[0] === 'object'
    ? String((scenes[0] as Record<string, unknown>).scene_id || '')
    : ''
  const imageReview = response.outputs?.image_review as Record<string, unknown> | undefined
  const selectedAssets = Array.isArray(imageReview?.selected_assets)
    ? imageReview.selected_assets
    : []
  const firstSelected = selectedAssets.find(
    (item) =>
      item &&
      typeof item === 'object' &&
      String((item as Record<string, unknown>).scene_id || '') === firstSceneId,
  ) || selectedAssets[0]
  const selectedAssetRef = firstSelected && typeof firstSelected === 'object'
    ? (firstSelected as Record<string, unknown>).selected_asset_ref
    : undefined
  const posterPath = selectedAssetRef && typeof selectedAssetRef === 'object'
    ? String(
        (selectedAssetRef as Record<string, unknown>).thumbnail_url ||
        (selectedAssetRef as Record<string, unknown>).thumbnail_path ||
        (selectedAssetRef as Record<string, unknown>).public_url ||
        (selectedAssetRef as Record<string, unknown>).relative_path ||
        '',
      )
    : ''
  const posterVersion = selectedAssetRef && typeof selectedAssetRef === 'object'
    ? (
        (selectedAssetRef as Record<string, unknown>).thumbnail_version ||
        (selectedAssetRef as Record<string, unknown>).version
      )
    : undefined
  const posterBaseUrl = toAssetHref(posterPath)
  const posterUrl = posterBaseUrl && posterVersion != null
    ? `${posterBaseUrl}${posterBaseUrl.includes('?') ? '&' : '?'}v=${encodeURIComponent(String(posterVersion))}`
    : posterBaseUrl
  if (!title && !topic && !posterUrl && !response.workflow_id && !response.run_id) {
    return undefined
  }
  return {
    title: title || undefined,
    topic: topic || undefined,
    createdAt: new Date().toISOString(),
    posterUrl: posterUrl || undefined,
    workflowId: response.workflow_id || undefined,
    runId: response.run_id || undefined,
  }
}

/* ── History video delete ───────────────────────────────────────────
   The history list is just URLs persisted in localStorage; no backend
   record exists, so removal here never touches `assets/mock/*`.

   Two-step UX so the dialog matches the rest of the studio:
     1. `requestDeleteRecentVideo(url)` opens a themed confirm dialog
        (deleteVideoTarget holds the pending URL).
     2. `performDeleteRecentVideo()` runs the actual deletion after the
        user clicks 删除 in the dialog.

   To make the deletion survive a page reload we maintain a SET of
   deleted URLs in localStorage. Without that, applyWorkflowResponse
   would re-read outputs.json on reattach and push the URL right back
   into the recent list. The set is consulted by
   `pushRecentFinalVideoUrl` and `applyWorkflowResponse` so the
   blacklisted URL can't sneak back in. */
const deleteVideoTarget = ref<string | null>(null)
const deletedVideoUrlsSet = ref<Set<string>>(new Set())

function persistDeletedVideoUrlsSet() {
  try {
    if (deletedVideoUrlsSet.value.size > 0) {
      localStorage.setItem(
        STORAGE_KEY_DELETED_VIDEOS,
        JSON.stringify(Array.from(deletedVideoUrlsSet.value)),
      )
    } else {
      localStorage.removeItem(STORAGE_KEY_DELETED_VIDEOS)
    }
  } catch {
    /* localStorage quota / unavailability is non-fatal */
  }
}

function requestDeleteRecentVideo(url: string) {
  const target = String(url || '').trim()
  if (!target) return
  deleteVideoTarget.value = target
}

function cancelDeleteRecentVideo() {
  deleteVideoTarget.value = null
}

function performDeleteRecentVideo() {
  const target = deleteVideoTarget.value
  deleteVideoTarget.value = null
  if (!target) return

  // Strip from the recent list FIRST so any reactive consumer sees the
  // post-delete state.
  recentFinalVideoUrls.value = recentFinalVideoUrls.value.filter(
    (item) => item !== target,
  )

  // Drop the deleted URL's metadata too so the map doesn't keep growing
  // a tail of orphaned entries.
  if (recentVideoMetadata.value[target]) {
    const { [target]: _omit, ...rest } = recentVideoMetadata.value
    void _omit
    recentVideoMetadata.value = rest
  }

  try {
    if (recentFinalVideoUrls.value.length > 0) {
      localStorage.setItem(
        STORAGE_KEY_RECENT_VIDEOS,
        JSON.stringify(recentFinalVideoUrls.value),
      )
    } else {
      localStorage.removeItem(STORAGE_KEY_RECENT_VIDEOS)
    }
    if (Object.keys(recentVideoMetadata.value).length > 0) {
      localStorage.setItem(
        STORAGE_KEY_RECENT_VIDEO_META,
        JSON.stringify(recentVideoMetadata.value),
      )
    } else {
      localStorage.removeItem(STORAGE_KEY_RECENT_VIDEO_META)
    }
  } catch {
    /* UI state still reflects the deletion */
  }

  const wasCurrent = finalVideoUrl.value === target

  if (wasCurrent) {
    // CRITICAL: deleting the currently-playing video is treated as
    // discarding the run that produced it. If we only clear
    // `finalVideoUrl` and leave `currentWorkflowResponse` /
    // `STORAGE_KEY_WORKFLOW` in place, two reactive paths immediately
    // try to "finish" the run and restart generation:
    //
    //   · The watcher on `isWorkflowReadyForRender` (the auto-render
    //     trigger) uses `if (finalVideoUrl.value) return` as its
    //     "already done" guard. With finalVideoUrl emptied but the
    //     completed response still present, the guard fails and the
    //     watcher calls renderFinalVideoIfReady() → backend re-renders.
    //
    //   · `resumePendingSceneGenerationAfterRestore()` uses the same
    //     finalVideoUrl guard. On any subsequent restore / nav back,
    //     it sees pending placeholders + empty finalVideoUrl and fires
    //     `refreshImageReview()` → backend regenerates candidate images.
    //
    // The only safe fix is to fully sever the workflow association the
    // same way 放弃当前生成 does: wipe response / payload / status /
    // placeholders / per-step text + drop the persisted workflow_id /
    // payload / refresh-cancel marker. The blacklist below is kept as
    // belt-and-suspenders in case any other code path still tries to
    // restore the URL by string match.
    finalVideoUrl.value = ''
    finalVideoText.value = ''
    finalVideoAudioEnabled.value = true
    finalVideoRenderInFlight.value = false
    finalVideoRendering.value = false

    currentWorkflowResponse.value = null
    currentWorkflowPayload.value = null
    workflowStatusData.value = null
    activeWorkflowId.value = ''
    loading.value = false
    cancelRequested.value = false
    workflowRunElapsedSec.value = 0

    // Stop any in-flight image refresh so it can't resolve after this
    // wipe and overwrite the cleaned state with stale data.
    imageReviewRefreshAbortController?.abort()
    imageReviewRefreshAbortController = null
    refreshingImageReview.value = false
    imageReviewRefreshCancelled.value = false
    imageRefreshPausedByUser.value = false
    sceneRefreshQueue.value = []
    sceneRefreshingId.value = ''
    clearImageReviewAutoRefreshTimer()
    reviewAutoRefreshFiredOnce = false
    restoreAutoRefreshFired = false

    // Drop every per-run preview field so review tab doesn't keep
    // showing the deleted run's story / images / audio.
    storyText.value = ''
    storyboardText.value = ''
    imagePromptsText.value = ''
    imageAssetsText.value = ''
    imageReviewText.value = ''
    videoPromptsText.value = ''
    narrationText.value = ''
    subtitlesText.value = ''
    renderPlanText.value = ''
    stepSummaries.value = []
    characterCandidatesText.value = ''
    characterManifestText.value = ''
    resultText.value = ''
    reviewPlaceholders.value = []
    selectingSceneId.value = ''
    userHasInteractedWithImages.value = false
    mockAudioIndexUrl.value = ''
    mockAudioSceneGroups.value = []
    mockAudioSegmentTextMap.value = {}
    mockAudioDirectoryText.value = ''
    errorMessage.value = ''

    // Forget the workflow on disk too. Without these removals, a page
    // refresh would re-read outputs.json via the reattach path and the
    // blacklist would only intercept finalVideoUrl — currentWorkflow-
    // Response would still be populated, re-triggering the watcher
    // chain described above.
    try {
      localStorage.removeItem(STORAGE_KEY_VIDEO_URL)
      localStorage.removeItem(STORAGE_KEY_WORKFLOW)
      localStorage.removeItem(STORAGE_KEY_RUN)
      localStorage.removeItem(STORAGE_KEY_PAYLOAD)
      localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
      clearFinalVideoRenderMarker()
    } catch { /* ignore */ }
  }

  // Persist the deletion as a defensive backstop. Even after the full
  // workflow wipe above, if any other code path (e.g. SPA nav from the
  // Landing showcase that reads outputs by direct URL) tries to push
  // the URL back into recent list, the blacklist will reject it.
  deletedVideoUrlsSet.value = new Set(deletedVideoUrlsSet.value)
  deletedVideoUrlsSet.value.add(target)
  persistDeletedVideoUrlsSet()
}
const finalVideoRendering = ref(false)
const workflowForm = ref<any>({ ...DEFAULT_WORKFLOW_FORM })
function onUpdateFormState(next: any) {
  console.log('[parent] onUpdateFormState audioEnabled=', next.audioEnabled, 'voiceoverEnabled=', next.voiceoverEnabled)
  workflowForm.value = next
}

function onUpdateSelectedSteps(next: StepName[]) {
  selectedSteps.value = next
}
const characterCandidatesText = ref('')
const characterManifestText = ref('')

const mockAudioIndexUrl = ref('')
const mockAudioSceneGroups = ref<AudioSceneGroup[]>([])
const mockAudioDirectoryText = ref('')
// scene_id → ordered list of segment text (parallel to the audio
// assets array of the same scene). Lets the Review-tab audio panel
// show "what this segment is saying" next to the player link.
const mockAudioSegmentTextMap = ref<Record<string, string[]>>({})

const samplesLoading = ref(false)
const samplesErrorMessage = ref('')
const samplesSummary = ref<SamplesSummaryResponse | null>(null)
const klingSamples = ref<KlingSample[]>([])
const selectedSampleId = ref('')
const selectedSampleDetail = ref<KlingSample | null>(null)
const selectedSampleNotesText = ref('')
const selectedSampleNotesLoading = ref(false)

const selectedSteps = ref<StepName[]>([...DEFAULT_STEPS])
const stepSummaries = ref<Array<{ name: string; status: string; preview: string }>>(
  []
)
const currentWorkflowResponse = ref<WorkflowRunResponse | null>(null)
const currentWorkflowPayload = ref<WorkflowRunPayload | null>(null)
const selectingSceneId = ref('')
const refreshingImageReview = ref(false)
const sceneRefreshQueue = ref<string[]>([])
const sceneRefreshingId = ref('')
const reviewPlaceholders = ref<ReviewPlaceholderItem[]>([])

// Per-scene image cache-busting version counter. Bumped each time a
// scene's candidates are successfully regenerated via the per-scene
// "重新生成" button. Without this the browser keeps serving the cached
// image file (backend overwrites the same file path on regen) and the
// user sees the OLD image. The map is passed into InteractiveImageReview
// and appended as `?v=${version}` to that scene's image URLs.
const sceneImageVersions = ref<Record<string, string | number>>({})
const sceneTaskIds = ref<Record<string, string>>({})
const imageStateHydrating = ref(false)
const imageReviewRefreshCancelled = ref(false)
// Reactive mirror of STORAGE_KEY_REFRESH_CANCELLED — true iff THIS workflow's
// image refresh was paused by user cancel. Used to distinguish "已暂停" (user
// chose to stop) from "失败" (API/network error) in placeholder copy, since
// localStorage itself isn't reactive.
const imageRefreshPausedByUser = ref(false)
let reviewAutoRefreshFiredOnce = false
let imageReviewAutoRefreshTimer: number | null = null
let imageReviewRefreshAbortController: AbortController | null = null
let activeImageReviewPollingKey = ''
let imageReviewPollingGeneration = 0
let wakeImageReviewPolling: (() => void) | null = null
let imageReviewVisibilityRefreshRequested = false
let workflowRestorePromise: Promise<void> | null = null
let finalVideoRecoveryTimer: number | null = null
let finalVideoRecoveryInFlight = false
let workflowLifecycleGeneration = 0
let studioViewUnmounted = false
const submittedImageTaskSceneIdsByWorkflow = new Map<string, Set<string>>()
type ViewTab = 'run' | 'review' | 'assets' | 'debug'
const activeTab = ref<ViewTab>('run')
const devMode = ref(false)

const studioTabs = computed(() => {
  const tabs: Array<{ id: string; label: string; icon: string; badge?: string }> = [
    { id: 'run', label: '创作故事', icon: '✦' },
    { id: 'review', label: '画面审核', icon: '◈' },
    { id: 'assets', label: '灵感参考', icon: '◇' },
  ]
  if (devMode.value) {
    tabs.push({ id: 'debug', label: '开发诊断', icon: '⚙' })
  }
  return tabs
})

const imageGenerationSummary = computed<ImageGenerationSummary>(() =>
  summarizeImageGeneration(
    reviewPlaceholders.value.map((item) => ({
      scene_id: item.scene_id,
      state: (
        item.state === 'done'
          ? 'ready'
          : item.state === 'refreshing'
            ? 'generating'
            : item.state === 'waiting'
              ? 'pending'
              : item.state
      ) as SceneGenerationState,
    })),
  ),
)

const isWorkflowReadyForRender = computed(() => {
  const response = currentWorkflowResponse.value
  if (!response) return false

  const outputs = response.outputs || {}
  const storyboard = outputs.storyboard as any
  const audioSegments = outputs.audio_segments as any

  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes : []
  const audioItems = Array.isArray(audioSegments?.items) ? audioSegments.items : []
  const audioEnabled = audioSegments?.enabled === true
  const audioOk = !audioEnabled || audioItems.length > 0

  // image_assets.assets includes status='failed' placeholders (B1), so
  // length alone can hit scene_count on a partially-failed run. Exclude
  // those — otherwise the auto-render watcher sees ready=true and the
  // manual hint banner ("候选图尚未就绪") incorrectly disappears.
  return (
    scenes.length > 0 &&
    imageGenerationSummary.value.readyCount >= scenes.length &&
    imageGenerationSummary.value.failedCount === 0 &&
    audioOk
  )
})

// Exposed for the manual-mode hint below (and any other consumer that
// needs to distinguish "still generating" from "stopped with failures").
const hasImageFailures = computed(() => {
  return imageGenerationSummary.value.failedCount > 0
})

watch(
  () => activeTab.value,
  (tab: ViewTab) => {
    if (tab !== 'assets') return

    // 避免重复加载：已有数据或正在加载时不再拉
    if (samplesLoading.value) return
    if (samplesSummary.value) return
    if (klingSamples.value && klingSamples.value.length > 0) return

    void loadSampleAssets()
  }
)

watch(
  () => isWorkflowReadyForRender.value,
  (ready) => {
    if (!ready) return
    if (workflowForm.value.renderMode !== 'auto') return
    if (!currentWorkflowResponse.value) return
    // Don't re-render if the video was already generated (e.g. after page reload).
    // outputs.json now persists final_video after render, so this guard handles
    // both the in-memory URL and the persisted status check inside renderFinalVideoIfReady.
    if (finalVideoUrl.value) return

    renderFinalVideoIfReady(currentWorkflowResponse.value)
  }
)

const STORAGE_KEY_TAB = 'jinsie_active_tab'
const STORAGE_KEY_SESSION = 'jinsie_session_id'
const STORAGE_KEY_VIDEO_URL = 'jinsie_last_video_url'
const STORAGE_KEY_RECENT_VIDEOS = 'jinsie_recent_video_urls'
// Parallel storage for history-video metadata (title, topic, createdAt
// per URL). Kept separate from the URL list above so existing reads
// don't have to change shape; new reads (hover tooltip, card subtitle)
// look this up by URL.
const STORAGE_KEY_RECENT_VIDEO_META = 'jinsie_recent_video_meta'
// Set of URLs the user has explicitly removed from history. Without this,
// a page refresh would re-import the deleted URL because the workflow
// outputs.json on disk still references it — applyWorkflowResponse would
// extract finalVideoUrl and push it back into RECENT_VIDEOS. The blacklist
// is consulted in pushRecentFinalVideoUrl + applyWorkflowResponse so the
// deletion survives reload without touching backend files.
const STORAGE_KEY_DELETED_VIDEOS = 'jinsie_deleted_video_urls'
const STORAGE_KEY_DEV = 'jinsie_dev_mode'
const STORAGE_KEY_WORKFLOW = 'jinsie_workflow_id'
const STORAGE_KEY_RUN = 'jinsie_run_id'
const STORAGE_KEY_PAYLOAD = 'jinsie_workflow_payload'
const STORAGE_KEY_FINAL_VIDEO_RENDER = 'jinsie_final_video_render_state'
const FINAL_VIDEO_RENDER_MARKER_TTL_MS = 2 * 60 * 60 * 1000
// Persists "user explicitly cancelled image refresh for this workflow_id".
// Survives Landing → Studio nav so auto-resume does NOT restart a run
// the user just stopped. Cleared by: starting a new workflow, manually
// clicking "立即生成候选图", or finishing a successful refresh+render.
const STORAGE_KEY_REFRESH_CANCELLED = 'jinsie_workflow_refresh_cancelled'
const STORAGE_KEY_IMAGE_TASKS = 'jinsie_image_refresh_tasks'
const STORAGE_KEY_FORM = 'jinsie_workflow_form'

type FinalVideoRenderMarker = {
  workflowId: string
  runId: string
  startedAt: number
}

function persistActiveWorkflowIdentity(workflowId: string, runId = '') {
  const normalizedWorkflowId = String(workflowId || '').trim()
  const normalizedRunId = String(runId || '').trim()
  if (normalizedWorkflowId) localStorage.setItem(STORAGE_KEY_WORKFLOW, normalizedWorkflowId)
  if (normalizedRunId) localStorage.setItem(STORAGE_KEY_RUN, normalizedRunId)
}

function readFinalVideoRenderMarker(workflowId = ''): FinalVideoRenderMarker | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<FinalVideoRenderMarker>
    const marker: FinalVideoRenderMarker = {
      workflowId: String(parsed.workflowId || '').trim(),
      runId: String(parsed.runId || '').trim(),
      startedAt: Number(parsed.startedAt || 0),
    }
    const stale = !marker.workflowId || !marker.startedAt ||
      Date.now() - marker.startedAt > FINAL_VIDEO_RENDER_MARKER_TTL_MS
    const mismatched = Boolean(workflowId && marker.workflowId !== workflowId)
    if (stale || mismatched) {
      if (stale) localStorage.removeItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
      return null
    }
    return marker
  } catch {
    localStorage.removeItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
    return null
  }
}

function persistFinalVideoRenderMarker(workflowId: string, runId = '') {
  const marker: FinalVideoRenderMarker = {
    workflowId: String(workflowId || '').trim(),
    runId: String(runId || '').trim(),
    startedAt: Date.now(),
  }
  if (!marker.workflowId) return
  localStorage.setItem(STORAGE_KEY_FINAL_VIDEO_RENDER, JSON.stringify(marker))
}

function clearFinalVideoRenderMarker(workflowId = '') {
  try {
    if (!workflowId) {
      localStorage.removeItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
      return
    }
    const raw = localStorage.getItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
    if (!raw) return
    const marker = JSON.parse(raw) as Partial<FinalVideoRenderMarker>
    if (String(marker.workflowId || '') === workflowId) {
      localStorage.removeItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
    }
  } catch {
    localStorage.removeItem(STORAGE_KEY_FINAL_VIDEO_RENDER)
  }
}

function imageTaskStorageKey(workflowId: string, runId: string) {
  return `${workflowId}:${runId}`
}

function loadSceneTaskIds(workflowId: string, runId: string) {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY_IMAGE_TASKS) || '{}')
    const stored = all?.[imageTaskStorageKey(workflowId, runId)]
    sceneTaskIds.value = stored && typeof stored === 'object' ? { ...stored } : {}
  } catch {
    sceneTaskIds.value = {}
  }
}

function persistSceneTaskIds(workflowId: string, runId: string) {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY_IMAGE_TASKS) || '{}')
    all[imageTaskStorageKey(workflowId, runId)] = sceneTaskIds.value
    localStorage.setItem(STORAGE_KEY_IMAGE_TASKS, JSON.stringify(all))
  } catch {
    /* best-effort route recovery */
  }
}

function migrateLegacyWorkflowForm(form: Record<string, any>) {
  const topic = String(form.topic || '')
  const displayName = String(form.primaryCharacterDisplayName || '')
  const species = String(form.primaryCharacterSpecies || '')
  const isLegacyToyCar =
    topic.includes('主角是小红') &&
    topic.includes('可爱小汽车') &&
    (displayName === '小红' || species.includes('小汽车'))

  if (!isLegacyToyCar) return form

  return {
    ...form,
    topic: topic.replaceAll('小红', '嘟嘟小车'),
    structuredCharactersEnabled: true,
    primaryCharacterDisplayName: '嘟嘟小车',
    primaryCharacterSpecies: '小汽车',
    primaryCharacterForbiddenTraits: [
      '不要人物',
      '不要小女孩',
      '不要红衣服',
      '不要红帽子',
      String(form.primaryCharacterForbiddenTraits || ''),
    ]
      .filter(Boolean)
      .join('、'),
  }
}

watch(activeTab, (tab) => {
  localStorage.setItem(STORAGE_KEY_TAB, tab)
  // Animation is handled inside StudioLayout's watch on modelValue
})

watch(workflowForm, (form) => {
  try {
    localStorage.setItem(STORAGE_KEY_FORM, JSON.stringify(form))
  } catch { /* ignore quota errors */ }
}, { deep: true })

watch(devMode, (enabled) => {
  if (!enabled && activeTab.value === 'debug') {
    activeTab.value = 'run'
  }
  syncDevModeToUrl(enabled)
})

// Keep ?dev=1 in the URL in lock-step with the runtime devMode flag so
// the URL is never lying about which mode the user is in. Without this,
// users could land via ?dev=1, press Cmd/Ctrl+Shift+D to turn dev off,
// and then a refresh would silently re-enable dev (because the URL
// still said dev=1) — that mismatch is exactly the "状态不统一"
// confusion reported. Uses history.replaceState (not router.replace)
// so we don't trigger any route guards or remounts.
function syncDevModeToUrl(enabled: boolean) {
  const url = new URL(window.location.href)
  const current = url.searchParams.get('dev')
  if (enabled) {
    if (current === '1') return
    url.searchParams.set('dev', '1')
  } else {
    if (current === null) return
    url.searchParams.delete('dev')
  }
  window.history.replaceState({}, '', url.toString())
}

// Lightweight inline toast for dev-mode toggle feedback. Empty
// string = hidden. Auto-clears after 1500ms.
const devModeToast = ref('')
let devModeToastTimer: ReturnType<typeof setTimeout> | null = null

// Generic non-blocking notice toast (mirrors devModeToast pattern but
// styled distinctly). Used for outcomes that should be highly visible
// but don't change the UI state machine — e.g. 重新生成 failure where
// the prior image is still valid and the workflow is unchanged.
//
// Position is TOP-CENTER (not bottom-right) so it sits in the user's
// active reading zone rather than under floating action buttons. The
// `tone` field tints the border + leading icon — 'warn' covers
// soft-error cases like "retry failed but state preserved". Duration
// default is generous (8s) and the user can dismiss any time by
// clicking the toast.
const inlineNotice = ref<{ text: string; tone: 'info' | 'warn' } | null>(null)
let inlineNoticeTimer: ReturnType<typeof setTimeout> | null = null
function showInlineNotice(text: string, tone: 'info' | 'warn' = 'info', durationMs = 8000) {
  inlineNotice.value = { text, tone }
  if (inlineNoticeTimer) clearTimeout(inlineNoticeTimer)
  inlineNoticeTimer = setTimeout(() => {
    inlineNotice.value = null
    inlineNoticeTimer = null
  }, durationMs)
}
function dismissInlineNotice() {
  inlineNotice.value = null
  if (inlineNoticeTimer) {
    clearTimeout(inlineNoticeTimer)
    inlineNoticeTimer = null
  }
}

function toggleDevMode() {
  devMode.value = !devMode.value
  devModeToast.value = devMode.value ? 'Dev mode 已开启' : 'Dev mode 已关闭'
  if (devModeToastTimer) clearTimeout(devModeToastTimer)
  devModeToastTimer = setTimeout(() => {
    devModeToast.value = ''
    devModeToastTimer = null
  }, 1500)
}

// Global keyboard shortcut for the dev-mode toggle. Cmd/Ctrl+Shift+D —
// avoids browser-default bookmarks (Cmd+D) by adding Shift. The dev
// button in the sidebar was removed; this is now the only in-app way
// to toggle (URL ?dev=1 still works as the cold-start entry).
function onGlobalKeydown(event: KeyboardEvent) {
  const isMacToggle = event.metaKey && event.shiftKey && (event.key === 'd' || event.key === 'D')
  const isWinToggle = event.ctrlKey && event.shiftKey && (event.key === 'd' || event.key === 'D')
  if (isMacToggle || isWinToggle) {
    event.preventDefault()
    toggleDevMode()
  }
}

onBeforeUnmount(() => {
  studioViewUnmounted = true
  window.removeEventListener('keydown', onGlobalKeydown)
  window.removeEventListener('pageshow', onStudioPageShow)
  document.removeEventListener('visibilitychange', onImageReviewVisibilityChange)
  clearFinalVideoRecoveryTimer()
  clearImageReviewAutoRefreshTimer()
  imageReviewPollingGeneration += 1
  activeImageReviewPollingKey = ''
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  if (devModeToastTimer) {
    clearTimeout(devModeToastTimer)
    devModeToastTimer = null
  }
  if (inlineNoticeTimer) {
    clearTimeout(inlineNoticeTimer)
    inlineNoticeTimer = null
  }
})

const EXAMPLE_TOPICS = ['小兔子和乌龟赛跑', '小狐狸学画画', '小熊猫的第一次冒险']

function setExampleTopic(topic: string) {
  workflowForm.value = { ...workflowForm.value, topic }
}

// Called when the user clicks "用此 X 创作" inside InspirationLibraryPanel.
// Shallow-merges the item's prefill payload into the workflow form and
// switches to the 创作故事 tab so the user lands on the form ready to
// review / run. Smooth-scroll the form into view for the same reason —
// without it the tab swap is silent and the user has to scan the page
// to confirm anything happened.
function onApplyInspiration(item: InspirationItem) {
  workflowForm.value = { ...workflowForm.value, ...item.prefill }
  // Snapshot the topic-at-fill-time so the "topic changed, characters
  // may not match" warning doesn't fire immediately after the preset
  // applied (topic + characters were filled *together*, they're in
  // sync by construction).
  topicAtCharacterFill.value = String(workflowForm.value.topic || '')
  activeTab.value = 'run'
  // Defer the scroll until Vue has rendered the run tab, otherwise the
  // form anchor doesn't exist yet.
  requestAnimationFrame(() => {
    const anchor = document.querySelector('.run-form, .workflow-run-form')
    if (anchor && 'scrollIntoView' in anchor) {
      (anchor as HTMLElement).scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  })
}

// ── Topic-changed-but-characters-still-stale warning ────────────────
//
// When the user changes the topic significantly after structured
// character fields are already populated (e.g. they applied the
// 「波波·小海豹」preset then later changed topic to "讲一个小兔子
// 的故事"), the form ends up in a self-contradictory state — the
// generation result will mix species from the preset character with
// the new topic intent.
//
// Detection: compare the live topic against `topicAtCharacterFill`,
// the snapshot taken either at preset-apply or at the last time the
// user dismissed this warning. If the first 20 characters differ AND
// any structured character field is populated, surface a confirmation
// modal asking the user to either clear or keep.

const topicAtCharacterFill = ref<string>('')
const topicChangeWarningOpen = ref<boolean>(false)
let topicChangeDebounce: ReturnType<typeof setTimeout> | null = null

const hasCharacterFields = computed<boolean>(() => {
  const f = workflowForm.value || {}
  return Boolean(
    (f.primaryCharacterDisplayName || '').trim() ||
      (f.primaryCharacterSpecies || '').trim() ||
      (f.primaryCharacterVisualTraits || '').trim() ||
      (f.secondaryCharacterDisplayName || '').trim() ||
      (f.secondaryCharacterSpecies || '').trim() ||
      (f.secondaryCharacterVisualTraits || '').trim(),
  )
})

/** Two topics are "significantly different" iff their first 20
 *  characters don't match. Picked 20 because:
 *  - typo fixes / appended phrases usually keep the prefix intact
 *  - a full rewrite reliably changes the opening
 *  - cheap to compute, no Levenshtein nonsense
 */
function topicIsSignificantlyDifferent(a: string, b: string): boolean {
  const sa = String(a || '').trim()
  const sb = String(b || '').trim()
  if (sa === sb) return false
  if (!sa || !sb) return true
  return sa.slice(0, 20) !== sb.slice(0, 20)
}

watch(
  () => workflowForm.value?.topic || '',
  (newTopic) => {
    if (topicChangeDebounce) clearTimeout(topicChangeDebounce)
    // 1s after the user stops typing — long enough to feel "they
    // committed" but short enough that they remember which edit
    // we're warning about.
    topicChangeDebounce = setTimeout(() => {
      if (!hasCharacterFields.value) return
      if (!topicIsSignificantlyDifferent(newTopic, topicAtCharacterFill.value)) return
      topicChangeWarningOpen.value = true
    }, 1000)
  },
)

function clearCharacterFieldsAfterTopicChange() {
  workflowForm.value = {
    ...workflowForm.value,
    structuredCharactersEnabled: false,
    primaryCharacterDisplayName: '',
    primaryCharacterSpecies: '',
    primaryCharacterVisualTraits: '',
    primaryCharacterForbiddenTraits: '',
    secondaryCharacterDisplayName: '',
    secondaryCharacterSpecies: '',
    secondaryCharacterVisualTraits: '',
    secondaryCharacterForbiddenTraits: '',
  }
  topicAtCharacterFill.value = String(workflowForm.value.topic || '')
  topicChangeWarningOpen.value = false
}

function keepCharacterFieldsAfterTopicChange() {
  // Re-snapshot so we don't keep nagging on every subsequent keystroke.
  // The user has made a conscious decision; respect it for *this* topic.
  topicAtCharacterFill.value = String(workflowForm.value.topic || '')
  topicChangeWarningOpen.value = false
}

onMounted(() => {
  studioViewUnmounted = false
  // Global keyboard shortcut for the dev-mode toggle (Cmd/Ctrl+Shift+D).
  window.addEventListener('keydown', onGlobalKeydown)
  window.addEventListener('pageshow', onStudioPageShow)
  document.addEventListener('visibilitychange', onImageReviewVisibilityChange)

  // URL is the single source of truth for dev mode. localStorage used to
  // mirror this, but having two sources caused "remove ?dev=1 from URL,
  // dev still on" bugs because the localStorage value silently won.
  // Clean up the legacy key so existing users don't get sticky state.
  const urlParams = new URLSearchParams(window.location.search)
  devMode.value = urlParams.get('dev') === '1'
  localStorage.removeItem(STORAGE_KEY_DEV)

  // Always restore the studio shell from localStorage, regardless of how
  // we got here (reload / SPA nav from Landing / direct URL / new tab).
  //   • Tab: Landing entries pre-write 'run' so SPA nav still lands on
  //     创作故事, while direct refresh restores the last visited tab.
  //   • Form / session / payload: needed so the image-refresh loop can
  //     auto-resume when reattaching to an in-flight workflow — without
  //     a restored payload, resumePendingSceneGenerationAfterRestore()
  //     bails out and the user sees "立即生成候选图" instead of progress.
  const savedTab = localStorage.getItem(STORAGE_KEY_TAB) as ViewTab | null
  if (savedTab && ['run', 'review', 'assets'].includes(savedTab)) {
    activeTab.value = savedTab
  } else if (savedTab === 'debug' && devMode.value) {
    activeTab.value = 'debug'
  }

  const savedFormStr = localStorage.getItem(STORAGE_KEY_FORM)
  if (savedFormStr) {
    try {
      const savedForm = JSON.parse(savedFormStr)
      // Normalize known legacy enum values (whitespace → underscores)
      // so dropdowns don't accumulate a stray "cute chibi anime" option.
      if (savedForm.visualStyle === 'cute chibi anime') {
        savedForm.visualStyle = 'cute_chibi_anime'
      }
      // V1.0 visible-option coercion. WorkflowRunPanel hides
      // storyboard_preview / assets_only / en-US / storybook from
      // their respective selects; if a stored form carries one of
      // those legacy values, snap it back to the supported default
      // so the dropdown doesn't render with a blank current value.
      if (savedForm.outputMode && savedForm.outputMode !== 'full_video') {
        savedForm.outputMode = 'full_video'
      }
      if (savedForm.language && savedForm.language !== 'zh-CN') {
        savedForm.language = 'zh-CN'
      }
      if (savedForm.videoProvider && savedForm.videoProvider !== 'mock') {
        savedForm.videoProvider = 'mock'
      }
      workflowForm.value = {
        ...DEFAULT_WORKFLOW_FORM,
        ...migrateLegacyWorkflowForm(savedForm),
      }
    } catch { /* ignore malformed */ }
  }

  // Snapshot the restored topic so the watcher's first emit doesn't
  // immediately trigger the "topic changed" warning. Without this the
  // baseline starts as empty string, so any saved topic looks like a
  // dramatic change on first paint and pops the modal.
  topicAtCharacterFill.value = String(workflowForm.value.topic || '')

  const savedSessionId = localStorage.getItem(STORAGE_KEY_SESSION)
  if (savedSessionId) {
    workflowForm.value.sessionId = savedSessionId
  }

  // Restore payload so refresh-scene API calls (and the auto-resume
  // path in resumePendingSceneGenerationAfterRestore) have the original
  // workflow_input.
  const savedPayloadStr = localStorage.getItem(STORAGE_KEY_PAYLOAD)
  if (savedPayloadStr) {
    try {
      currentWorkflowPayload.value = JSON.parse(savedPayloadStr) as WorkflowRunPayload
    } catch {
      // ignore malformed payload
    }
  }

  // Restore the user's "deleted from history" set BEFORE rebuilding
  // recentFinalVideoUrls / pushing savedVideoUrl, so a blacklisted URL
  // can't re-enter the list during init.
  const savedDeletedVideosStr = localStorage.getItem(STORAGE_KEY_DELETED_VIDEOS)
  if (savedDeletedVideosStr) {
    try {
      const parsedDeleted = JSON.parse(savedDeletedVideosStr)
      if (Array.isArray(parsedDeleted)) {
        deletedVideoUrlsSet.value = new Set(
          parsedDeleted.filter(
            (item): item is string =>
              typeof item === 'string' && item.length > 0,
          ),
        )
      }
    } catch {
      /* corrupt JSON — treat as empty blacklist */
    }
  }

  // Restore the full recent-videos list first (so multi-session history
  // survives a refresh); then push the last video url for de-dup.
  const savedRecentVideosStr = localStorage.getItem(STORAGE_KEY_RECENT_VIDEOS)
  if (savedRecentVideosStr) {
    try {
      const parsed = JSON.parse(savedRecentVideosStr)
      if (Array.isArray(parsed)) {
        recentFinalVideoUrls.value = parsed
          .filter((item): item is string => typeof item === 'string' && item.length > 0)
          // Strip any previously-deleted URL that might still linger in
          // the recent list (e.g. older builds wrote it without checking).
          .filter((item) => !deletedVideoUrlsSet.value.has(item))
          .slice(0, 10)
      }
    } catch {
      /* corrupt JSON — fall back to empty list */
    }
  }

  // Restore the parallel metadata map (added after the URL list, so
  // entries from older builds simply have no metadata and gracefully
  // fall back to "视频 N" in the UI).
  const savedRecentMetaStr = localStorage.getItem(STORAGE_KEY_RECENT_VIDEO_META)
  if (savedRecentMetaStr) {
    try {
      const parsed = JSON.parse(savedRecentMetaStr)
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        const liveUrlSet = new Set(recentFinalVideoUrls.value)
        recentVideoMetadata.value = Object.fromEntries(
          Object.entries(parsed as Record<string, unknown>)
            .filter(([url, meta]) => liveUrlSet.has(url) && meta && typeof meta === 'object')
            .map(([url, meta]) => [url, meta as RecentVideoMeta]),
        )
      }
    } catch {
      /* corrupt JSON — drop metadata; URLs still work */
    }
  }

  const savedVideoUrl = localStorage.getItem(STORAGE_KEY_VIDEO_URL)
  if (savedVideoUrl) {
    // Only push to the recent-videos list — do NOT restore finalVideoUrl.value here.
    // finalVideoUrl is only set by applyWorkflowResponse so it always matches the
    // current workflow response, never bleeds in from a previous completed run.
    pushRecentFinalVideoUrl(savedVideoUrl)
  }

  void restorePersistedWorkflowState('mount')
})

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

function clearPersistedWorkflowIdentity(workflowId = '') {
  try {
    localStorage.removeItem(STORAGE_KEY_WORKFLOW)
    localStorage.removeItem(STORAGE_KEY_RUN)
    localStorage.removeItem(STORAGE_KEY_PAYLOAD)
    localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
    clearFinalVideoRenderMarker(workflowId)
  } catch { /* best-effort local recovery cleanup */ }
}

function clearFinalVideoRecoveryTimer() {
  if (finalVideoRecoveryTimer !== null) {
    window.clearTimeout(finalVideoRecoveryTimer)
    finalVideoRecoveryTimer = null
  }
}

function invalidateWorkflowLifecycleRecovery() {
  workflowLifecycleGeneration += 1
  workflowRestorePromise = null
  finalVideoRecoveryInFlight = false
  imageStateHydrating.value = false
  clearFinalVideoRecoveryTimer()
}

function isCurrentWorkflowLifecycle(workflowId: string, generation: number): boolean {
  if (studioViewUnmounted || generation !== workflowLifecycleGeneration) return false
  return String(localStorage.getItem(STORAGE_KEY_WORKFLOW) || '').trim() === workflowId
}

function reconcileRestoredFinalVideoState(workflowId: string) {
  if (finalVideoUrl.value) {
    clearFinalVideoRenderMarker(workflowId)
    clearFinalVideoRecoveryTimer()
    finalVideoRenderInFlight.value = false
    finalVideoRendering.value = false
    return
  }

  const marker = readFinalVideoRenderMarker(workflowId)
  finalVideoRenderInFlight.value = Boolean(marker)
  finalVideoRendering.value = Boolean(marker)
  if (marker) scheduleFinalVideoAuthoritativeRecovery(workflowId)
}

function scheduleFinalVideoAuthoritativeRecovery(
  workflowId: string,
  delayMs = 0,
  recoveryGeneration = workflowLifecycleGeneration,
) {
  if (
    !isCurrentWorkflowLifecycle(workflowId, recoveryGeneration) ||
    !workflowId ||
    finalVideoUrl.value ||
    finalVideoRecoveryTimer !== null ||
    finalVideoRecoveryInFlight
  ) {
    return
  }
  if (!readFinalVideoRenderMarker(workflowId)) {
    finalVideoRenderInFlight.value = false
    finalVideoRendering.value = false
    return
  }

  finalVideoRecoveryTimer = window.setTimeout(async () => {
    finalVideoRecoveryTimer = null
    if (!isCurrentWorkflowLifecycle(workflowId, recoveryGeneration)) return
    if (!readFinalVideoRenderMarker(workflowId)) return
    if (finalVideoRecoveryInFlight) return
    finalVideoRecoveryInFlight = true
    try {
      const data = await fetchAuthoritativeWorkflow(workflowId)
      if (!isCurrentWorkflowLifecycle(workflowId, recoveryGeneration)) return
      if (!readFinalVideoRenderMarker(workflowId)) return
      applyWorkflowResponse(data)
      reconcileRestoredFinalVideoState(workflowId)
    } catch {
      // The render request can finish before outputs.json is updated. Keep
      // the persisted marker and retry the authoritative GET only.
    } finally {
      if (recoveryGeneration === workflowLifecycleGeneration) {
        finalVideoRecoveryInFlight = false
      }
    }

    if (
      isCurrentWorkflowLifecycle(workflowId, recoveryGeneration) &&
      !finalVideoUrl.value &&
      readFinalVideoRenderMarker(workflowId)
    ) {
      scheduleFinalVideoAuthoritativeRecovery(
        workflowId,
        document.hidden ? 10_000 : 2_500,
        recoveryGeneration,
      )
    }
  }, delayMs)
}

function isDeletedWorkflowResponse(data: WorkflowRunResponse): boolean {
  const restoredFinalUrl = extractFinalVideoUrl(data)
  if (!restoredFinalUrl || !deletedVideoUrlsSet.value.has(restoredFinalUrl)) return false
  clearPersistedWorkflowIdentity(String(data.workflow_id || ''))
  localStorage.removeItem(STORAGE_KEY_VIDEO_URL)
  currentWorkflowPayload.value = null
  return true
}

async function restorePersistedWorkflowState(
  _reason: 'mount' | 'visibility' | 'pageshow',
): Promise<void> {
  if (workflowRestorePromise) return workflowRestorePromise

  const savedWorkflowId = String(localStorage.getItem(STORAGE_KEY_WORKFLOW) || '').trim()
  if (!savedWorkflowId) return
  if (loading.value && activeWorkflowId.value === savedWorkflowId) return
  const restoreGeneration = workflowLifecycleGeneration

  const restorePromise = (async () => {
    if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
    imageStateHydrating.value = true
    const renderMarker = readFinalVideoRenderMarker(savedWorkflowId)
    finalVideoRenderInFlight.value = Boolean(renderMarker)
    finalVideoRendering.value = Boolean(renderMarker)

    try {
      if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
      const markerWorkflowId = localStorage.getItem(STORAGE_KEY_REFRESH_CANCELLED) || ''
      imageRefreshPausedByUser.value = markerWorkflowId === savedWorkflowId

      const resultsResponse = await fetch(
        `${apiBaseUrl}/v1/workflow/results/${encodeURIComponent(savedWorkflowId)}`,
      )
      if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
      if (resultsResponse.ok) {
        const data = (await resultsResponse.json()) as WorkflowRunResponse
        if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
        if (isDeletedWorkflowResponse(data)) return
        applyWorkflowResponse(data)
        imageStateHydrating.value = false
        resumePendingSceneGenerationAfterRestore()
        reconcileRestoredFinalVideoState(savedWorkflowId)
        return
      }
      if (resultsResponse.status !== 404) return

      const statusResponse = await fetch(
        `${apiBaseUrl}/v1/workflow/status/${encodeURIComponent(savedWorkflowId)}`,
      )
      if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
      if (!statusResponse.ok) return
      const statusData = (await statusResponse.json()) as WorkflowStatusResponse
      if (!isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) return
      const status = String(statusData.status || '').trim().toLowerCase()

      if (status === 'abandoned' || status === 'cancelled' || status === 'failed') {
        clearPersistedWorkflowIdentity(savedWorkflowId)
        return
      }
      if (status !== 'processing' && status !== 'cancel_requested') return

      loading.value = true
      workflowStatusData.value = statusData
      activeWorkflowId.value = savedWorkflowId
      cancelRequested.value = status === 'cancel_requested'
      const asyncData = await waitForAsyncWorkflowOutputs(savedWorkflowId)
      if (
        asyncData &&
        isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration) &&
        !isDeletedWorkflowResponse(asyncData)
      ) {
        applyWorkflowResponse(asyncData)
        imageStateHydrating.value = false
        scheduleImageReviewAutoRefreshIfNeeded()
        reconcileRestoredFinalVideoState(savedWorkflowId)
      }
    } catch {
      // Mobile resume is best-effort; pageshow/visibility will retry when
      // connectivity returns without creating a new workflow or task.
    } finally {
      if (isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration)) {
        imageStateHydrating.value = false
      }
      if (
        isCurrentWorkflowLifecycle(savedWorkflowId, restoreGeneration) &&
        loading.value &&
        activeWorkflowId.value === savedWorkflowId
      ) {
        loading.value = false
        activeWorkflowId.value = ''
        cancelRequested.value = false
      }
    }
  })()
  workflowRestorePromise = restorePromise

  try {
    await restorePromise
  } finally {
    if (workflowRestorePromise === restorePromise) workflowRestorePromise = null
  }
}

function onStudioPageShow() {
  void restorePersistedWorkflowState('pageshow')
}

const canSubmit = computed(() => {
  return (
    workflowForm.value.topic.trim().length > 0 &&
    selectedSteps.value.length > 0 &&
    !loading.value &&
    !refreshingImageReview.value
  )
})

const imageReviewSelectedAssets = computed<ImageReviewSelectedAsset[]>(() => {
  const value = currentWorkflowResponse.value?.outputs?.image_review
  if (!value || typeof value !== 'object') {
    return []
  }

  const selectedAssets = (value as Record<string, unknown>).selected_assets
  return Array.isArray(selectedAssets) ? (selectedAssets as ImageReviewSelectedAsset[]) : []
})

const imageReviewItems = computed(() => {
  const value = currentWorkflowResponse.value?.outputs?.image_review
  if (!value || typeof value !== 'object') {
    return []
  }

  const selectedAssets = (value as Record<string, unknown>).selected_assets
  return Array.isArray(selectedAssets) ? selectedAssets : []
})

// Map of scene_id → narration text (the human-readable script TTS reads
// for this scene). Surfaced in InteractiveImageReview as a per-card
// description so the user knows what each candidate's scene is ABOUT —
// far more useful than the structural image-generation prompt, which
// is hundreds of lines of cast-lock / consistency-rule prompt
// engineering boilerplate.
const sceneNarrationMap = computed<Record<string, string>>(() => {
  const result: Record<string, string> = {}
  const storyboard = currentWorkflowResponse.value?.outputs?.storyboard as
    | Record<string, unknown>
    | undefined
  const scenes = storyboard?.scenes
  if (!Array.isArray(scenes)) return result
  for (const scene of scenes) {
    if (!scene || typeof scene !== 'object') continue
    const sceneObj = scene as Record<string, unknown>
    const sceneId = String(sceneObj.scene_id || '').trim()
    if (!sceneId) continue
    const narration = String(sceneObj.narration || '').trim()
    if (narration) result[sceneId] = narration
  }
  return result
})

// scene_id → scene_title from the storyboard. Used by the audio panel
// to show "礁石上的波波" instead of generic "场景 01" — matches the
// image-review card pattern.
const sceneTitleMap = computed<Record<string, string>>(() => {
  const result: Record<string, string> = {}
  const storyboard = currentWorkflowResponse.value?.outputs?.storyboard as
    | Record<string, unknown>
    | undefined
  const scenes = storyboard?.scenes
  if (!Array.isArray(scenes)) return result
  for (const scene of scenes) {
    if (!scene || typeof scene !== 'object') continue
    const sceneObj = scene as Record<string, unknown>
    const sceneId = String(sceneObj.scene_id || '').trim()
    if (!sceneId) continue
    const title = String(sceneObj.scene_title || '').trim()
    if (title) result[sceneId] = title
  }
  return result
})


const hasReviewContent = computed(() => {
  return Boolean(
    imageReviewSelectedAssets.value.length > 0 ||
      storyText.value ||
      storyboardText.value ||
      imagePromptsText.value ||
      imageAssetsText.value ||
      imageReviewText.value ||
      videoPromptsText.value ||
      narrationText.value ||
      subtitlesText.value ||
      renderPlanText.value ||
      characterCandidatesText.value ||
      characterManifestText.value
  )
})

const storyDiagnostics = computed(() => {
  const story = currentWorkflowResponse.value?.outputs?.story

  if (!story || typeof story !== 'object') {
    return null
  }

  const storyRecord = story as Record<string, unknown>
  const text = typeof storyRecord.text === 'string' ? storyRecord.text : ''
  const compactText = text.replace(/\s+/g, '')

  return {
    title: typeof storyRecord.title === 'string' ? storyRecord.title : '—',
    generationSource:
      typeof storyRecord.generation_source === 'string'
        ? storyRecord.generation_source
        : '—',
    providerUsed:
      typeof storyRecord.provider_used === 'string'
        ? storyRecord.provider_used
        : '—',
    fallbackReason:
      typeof storyRecord.fallback_reason === 'string' &&
      storyRecord.fallback_reason.trim()
        ? storyRecord.fallback_reason
        : 'None',
    characterCount: compactText.length,
  }
})

const hasDebugContent = computed(() => {
  return Boolean(
    storyDiagnostics.value ||
      stepSummaries.value.length > 0 ||
      resultText.value
  )
})

const runDiagnosticsJson = computed(() => {
  const resp = currentWorkflowResponse.value
  const imageAssets = resp?.outputs?.image_assets as Record<string, unknown> | undefined
  return JSON.stringify(
    {
      run_id: resp?.run_id || '—',
      session_id: resp?.session_id || '—',
      provider: imageAssets?.provider || '—',
      status: resp?.status || '—',
      story: storyDiagnostics.value,
      steps: stepSummaries.value.map((s) => ({ name: s.name, status: s.status })),
      error: errorMessage.value || null,
    },
    null,
    2
  )
})

const diagCopied = ref(false)
function copyDiagnosticsJson() {
  navigator.clipboard.writeText(runDiagnosticsJson.value).then(() => {
    diagCopied.value = true
    setTimeout(() => { diagCopied.value = false }, 1500)
  }).catch(() => {})
}

const rawJsonCopied = ref(false)
function copyRawJson() {
  navigator.clipboard.writeText(resultText.value).then(() => {
    rawJsonCopied.value = true
    setTimeout(() => { rawJsonCopied.value = false }, 1500)
  }).catch(() => {})
}

// Per-step copy: remembers which step was most recently copied so the
// button briefly shows ✓ on the right item only.
const copiedStepName = ref<string | null>(null)
function copyStepPreview(item: { name: string; preview: string }) {
  navigator.clipboard.writeText(item.preview).then(() => {
    copiedStepName.value = item.name
    setTimeout(() => {
      if (copiedStepName.value === item.name) copiedStepName.value = null
    }, 1500)
  }).catch(() => {})
}

// Inline copy for the DiagnosticsPanel summary (workflow IDs + story
// generation source). One button → all visible fields as compact JSON.
const diagSummaryCopied = ref(false)
function copyDiagSummary() {
  const resp = currentWorkflowResponse.value
  const summary = {
    workflow_id: resp?.workflow_id,
    run_id: resp?.run_id,
    session_id: resp?.session_id,
    generation_source: storyDiagnostics.value?.generationSource,
    fallback_reason: storyDiagnostics.value?.fallbackReason !== 'None'
      ? storyDiagnostics.value?.fallbackReason
      : null,
  }
  navigator.clipboard.writeText(JSON.stringify(summary, null, 2)).then(() => {
    diagSummaryCopied.value = true
    setTimeout(() => { diagSummaryCopied.value = false }, 1500)
  }).catch(() => {})
}

// Human-readable byte count for step output previews. Keeps step
// headers scannable instead of showing raw char counts.
function formatPreviewSize(len: number): string {
  if (len < 1024) return `${len} 字符`
  return `${(len / 1024).toFixed(1)} KB`
}

const workflowIsProcessing = computed(() => {
  const response = currentWorkflowResponse.value
  const status = String(response?.status || '').trim().toLowerCase()
  return Boolean(loading.value || (status === 'processing' && !response?.outputs))
})

// Manual-mode wait state — assets are ready for video render but the user
// hasn't clicked the "生成视频" button yet. Distinct from the three
// "active phase" flags (processing / refreshing / rendering) because
// nothing is running on the backend; we still want the top progress bar
// and the workflow-chain visualization to STAY visible so the user
// doesn't think the run silently stopped. Without this, the chain &
// top bar both vanish during the wait and the page looks frozen.
const awaitingManualRender = computed(() => {
  return Boolean(
    workflowForm.value.renderMode === 'manual' &&
      isWorkflowReadyForRender.value &&
      !finalVideoUrl.value &&
      !finalVideoRenderInFlight.value &&
      !workflowIsProcessing.value &&
      !refreshingImageReview.value &&
      currentWorkflowResponse.value,
  )
})

// "Single-scene retry" = the user clicked "重新生成" on ONE done scene
// AFTER the initial workflow finished. We must distinguish this from
// the bulk image refresh that the initial workflow runs — the bulk
// loop also sets `sceneRefreshingId` as it walks each scene, but the
// correct UI copy for that is "正在生成候选图 (X/Y)", not "正在为 X
// 重新生成". The discriminator is `refreshingImageReview`: it's only
// true during the bulk refresh, never during user-triggered single
// retries.
const singleSceneRetryActive = computed(() => {
  return Boolean(sceneRefreshingId.value) && !refreshingImageReview.value
})

function formatElapsedTime(totalSec: number): string {
  const normalizedSec = Math.max(0, Math.floor(totalSec))
  const minutes = Math.floor(normalizedSec / 60)
  const seconds = normalizedSec % 60
  if (minutes <= 0) {
    return `${seconds} 秒`
  }
  return `${minutes} 分 ${seconds} 秒`
}

// Single source of truth for the workflow lifecycle. Components downstream
// (CTA, progress bar, video preview, image review) should derive their
// running / cancelling / idle visuals from this rather than reading the
// individual loading / refreshing / cancelRequested refs.
type RuntimeState = 'idle' | 'running' | 'cancelling'
const runtimeState = computed<RuntimeState>(() => {
  const anyRunning =
    loading.value || refreshingImageReview.value || finalVideoRenderInFlight.value
  if (cancelRequested.value && anyRunning) return 'cancelling'
  if (anyRunning) return 'running'
  return 'idle'
})

// Standard cancelling copy — every place that used to read "正在生成…"
// during workflow run should swap to this when runtimeState === 'cancelling'.
const cancellingLabel = '正在取消生成，等待当前步骤结束…'

const workflowRunStatusMessage = computed(() => {
  // While the user is cancelling, every running surface should reflect that
  // single state, regardless of which step the runner is on.
  if (runtimeState.value === 'cancelling') {
    return cancellingLabel
  }

  if (!workflowIsProcessing.value) {
    return ''
  }

  const elapsed = formatElapsedTime(workflowRunElapsedSec.value)
  const statusData = workflowStatusData.value
  const currentStep = String(statusData?.current_step || '').trim()
  const currentStepLabel = currentStep ? workflowStepLabel(currentStep) : ''
  const completedSteps =
    typeof statusData?.completed_steps === 'number' ? statusData.completed_steps : null
  const totalSteps =
    typeof statusData?.total_steps === 'number' ? statusData.total_steps : null
  const stepCopy =
    currentStepLabel && totalSteps
      ? `当前步骤：${currentStepLabel}（${completedSteps ?? 0}/${totalSteps}）。`
      : currentStepLabel
        ? `当前步骤：${currentStepLabel}。`
        : ''

  if (workflowRunElapsedSec.value < 60) {
    return `Workflow 运行中，已等待 ${elapsed}。${stepCopy}`
  }

  return `Workflow 仍在运行，已等待 ${elapsed}。${stepCopy}真实接口较慢时可能需要几分钟，请保持页面打开。`
})

// Unified cleanup invoked when the server confirms a workflow has been
// cancelled (status === 'cancelled'). Brings every running indicator back
// to idle so the UI no longer needs a page refresh after a cancel.
// NOTE: text fields / reviewPlaceholders / payload are intentionally NOT
// wiped here — after a cancel the user still needs to see what was
// produced so they can decide between "立即生成候选图" (resume) and
// "放弃当前生成" (full reset via performDiscardCurrentDraft).
function resetWorkflowRuntimeState() {
  loading.value = false
  cancelRequested.value = false
  activeWorkflowId.value = ''
  finalVideoRenderInFlight.value = false
  finalVideoRendering.value = false
  refreshingImageReview.value = false
  workflowRunElapsedSec.value = 0
  workflowStatusData.value = null
  currentWorkflowResponse.value = null
  imageReviewRefreshCancelled.value = false
  imageRefreshPausedByUser.value = false
  sceneRefreshQueue.value = []
  sceneRefreshingId.value = ''
  selectingSceneId.value = ''
  clearImageReviewAutoRefreshTimer()
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  try {
    localStorage.removeItem(STORAGE_KEY_WORKFLOW)
    localStorage.removeItem(STORAGE_KEY_RUN)
    clearFinalVideoRenderMarker()
  } catch {
    /* localStorage unavailable — best-effort */
  }
}

const workflowStatusProgress = computed(() => {
  const progress = workflowStatusData.value?.progress_percent
  if (typeof progress !== 'number' || !Number.isFinite(progress)) {
    return null
  }
  return Math.max(0, Math.min(100, Math.round(progress)))
})

const workflowProgressSummary = computed<WorkflowProgressSummary>(() =>
  summarizeWorkflowProgress({
    completed: Boolean(finalVideoUrl.value),
    rendering: finalVideoRenderInFlight.value,
    awaitingRender: awaitingManualRender.value,
    workflowPercent: workflowStatusProgress.value,
    images: imageGenerationSummary.value,
  }),
)

const reviewEmptyStateText = computed(() => {
  if (workflowIsProcessing.value) {
    return `${workflowRunStatusMessage.value} 故事和分镜生成完成后会自动在 Review 页展示选图和结果。`
  }
  return '生成结果仅保留在当前页面会话中，刷新后需要重新生成。请先在「创作故事」页签输入故事主题，并点击「开始创作」生成内容。'
})


const imageAssetsOutput = computed<Record<string, unknown>>(() => {
  const imageAssets = currentWorkflowResponse.value?.outputs?.image_assets
  return imageAssets && typeof imageAssets === 'object'
    ? (imageAssets as Record<string, unknown>)
    : {}
})

const reviewWaitingState = computed<ReviewWaitingState>(() => {
  if (imageReviewSelectedAssets.value.length > 0) {
    return 'ready'
  }

  if (
    imageGenerationSummary.value.generatingCount > 0 ||
    imageGenerationSummary.value.queuedCount > 0
  ) {
    return 'refreshing'
  }

  const imageAssetsStatus = String(imageAssetsOutput.value.status || '').trim()
  const imageAssetsReason = String(imageAssetsOutput.value.reason || '').trim()

  if (imageAssetsStatus === 'retrying') {
    return 'rate_limited_retrying'
  }

  if (imageAssetsStatus === 'pending' && imageAssetsReason === 'deferred_to_refresh') {
    return 'deferred_pending'
  }

  return 'idle'
})

const reviewRefreshProgress = computed(() => {
  if (!refreshingImageReview.value) {
    return {
      text: '',
      percent: 0,
    }
  }

  return {
    text: workflowProgressSummary.value.stageLabel,
    percent: workflowProgressSummary.value.stagePercent ?? 0,
  }
})

// Banner shown on the 画面审核 tab to let the user (re)start the deferred
// image-refresh loop. Covers two distinct states:
//   • fresh deferred — no scenes done yet, status=pending, reason=deferred_to_refresh
//   • partial paused — some scenes done (after a user cancel mid-flight where
//     the backend completed an in-flight scene before the abort actually took
//     effect, leaving outputs.json with 1..N-1 selected_assets while the
//     persistent cancel marker prevents auto-resume). Without this banner the
//     user has no obvious affordance to continue and the panel labels look
//     misleadingly "in progress".
const canResumeImageRefresh = computed(() => {
  if (refreshingImageReview.value) return false
  if (loading.value) return false
  if (finalVideoRenderInFlight.value) return false
  if (finalVideoUrl.value) return false
  if (!currentWorkflowPayload.value) return false
  if (reviewWaitingState.value === 'deferred_pending') return true
  return reviewPlaceholders.value.some((p) => p.state === 'waiting')
})

const deferredBannerLabel = computed(() => {
  const total = reviewPlaceholders.value.length
  const done = reviewPlaceholders.value.filter((p) => p.state === 'done').length
  if (total > 0 && done > 0 && done < total) {
    return `候选图已暂停（${done}/${total}）`
  }
  return '候选图尚未生成'
})

const deferredBannerCta = computed(() => {
  const done = reviewPlaceholders.value.filter((p) => p.state === 'done').length
  return done > 0 ? '继续生成候选图' : '立即生成候选图'
})

function assetRefPath(assetRef?: ImageAssetRef): string {
  if (!assetRef) {
    return ''
  }
  return assetRef.public_url || assetRef.relative_path || ''
}

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

  const normalizedBase = apiBaseUrl.replace(/\/+$/, '')
  const normalizedPath = trimmed.startsWith('/') ? trimmed : `/${trimmed}`

  return `${normalizedBase}${normalizedPath}`
}

function stringifyPretty(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

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
  return ''
}

function extractStoryboardText(data: WorkflowRunResponse): string {
  const storyboard = data.outputs?.storyboard
  if (
    storyboard &&
    typeof storyboard === 'object' &&
    'scenes' in storyboard &&
    Array.isArray(storyboard.scenes)
  ) {
    return stringifyPretty(storyboard.scenes)
  }
  return ''
}

function extractNarrationText(data: WorkflowRunResponse): string {
  const narration = data.outputs?.narration
  if (
    narration &&
    typeof narration === 'object' &&
    'full_text' in narration &&
    typeof narration.full_text === 'string'
  ) {
    return narration.full_text
  }
  return ''
}

function extractImagePromptsText(data: WorkflowRunResponse): string {
  const value = data.outputs?.image_prompts
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}
function extractImageAssetsText(data: WorkflowRunResponse): string {
  const value = data.outputs?.image_assets
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}
function extractVideoPromptsText(data: WorkflowRunResponse): string {
  const value = data.outputs?.video_prompts
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}

function extractSubtitlesText(data: WorkflowRunResponse): string {
  const subtitles = data.outputs?.subtitles
  if (
    subtitles &&
    typeof subtitles === 'object' &&
    'srt_preview' in subtitles &&
    typeof subtitles.srt_preview === 'string'
  ) {
    return subtitles.srt_preview
  }
  return ''
}

function extractRenderPlanText(data: WorkflowRunResponse): string {
  const renderPlan = data.outputs?.render_plan
  if (renderPlan && typeof renderPlan === 'object') {
    return stringifyPretty(renderPlan)
  }
  return ''
}

function extractFinalVideoText(data: WorkflowRunResponse): string {
  const finalVideo = data.outputs?.final_video
  if (finalVideo && typeof finalVideo === 'object') {
    return stringifyPretty(finalVideo)
  }
  return ''
}

function extractFinalVideoUrl(data: WorkflowRunResponse): string {
  const finalVideo = data.outputs?.final_video
  if (!finalVideo || typeof finalVideo !== 'object') {
    return ''
  }

  const publicUrl = String((finalVideo as Record<string, unknown>).public_url || '').trim()
  if (!publicUrl) {
    return ''
  }

  if (publicUrl.startsWith('http://') || publicUrl.startsWith('https://')) {
    return publicUrl
  }

  return `${apiBaseUrl}${publicUrl}`
}

function extractCharacterCandidatesText(data: WorkflowRunResponse): string {
  const value = data.outputs?.character_candidates
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}

function extractCharacterManifestText(data: WorkflowRunResponse): string {
  const value = data.outputs?.character_manifest
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}
function extractImageReviewText(data: WorkflowRunResponse): string {
  const value = data.outputs?.image_review
  if (value && typeof value === 'object') {
    return stringifyPretty(value)
  }
  return ''
}
function extractMockAudioOutput(data: WorkflowRunResponse): AudioSegmentsOutput | null {
  const audioSegments = data.outputs?.audio_segments
  if (!audioSegments || typeof audioSegments !== 'object') {
    return null
  }
  return audioSegments as AudioSegmentsOutput
}

function extractMockAudioState(data: WorkflowRunResponse) {
  const audioOutput = extractMockAudioOutput(data)

  mockAudioIndexUrl.value = audioOutput?.directory_manifest?.index_public_url || ''
  mockAudioSceneGroups.value = Array.isArray(audioOutput?.scene_asset_map)
    ? audioOutput.scene_asset_map || []
    : []
  mockAudioDirectoryText.value =
    audioOutput?.directory_manifest ? stringifyPretty(audioOutput.directory_manifest) : ''

  // Build a scene_id → array<text> map from narration.segments so the
  // audio panel can show what each segment is saying. Segments come
  // back in order per scene, so the i-th audio asset under a scene
  // maps to the i-th text in that scene's list. The map is recomputed
  // every workflow apply so stale text from a previous run never
  // leaks into a fresh take.
  const narrationOutput = data?.outputs?.narration as
    | { segments?: Array<{ scene_id?: string; text?: string }> }
    | undefined
  const segs = Array.isArray(narrationOutput?.segments)
    ? narrationOutput?.segments || []
    : []
  const map: Record<string, string[]> = {}
  for (const seg of segs) {
    const sid = String(seg?.scene_id || '').trim()
    const text = String(seg?.text || '').trim()
    if (!sid || !text) continue
    ;(map[sid] = map[sid] || []).push(text)
  }
  mockAudioSegmentTextMap.value = map
}

// Audio-asset display helpers used by the "配音素材" panel under the
// Review tab. Kept here (rather than colocated with the component)
// because the mockAudio* refs they format also live in this file.
function sceneDisplayName(sceneId?: string): string {
  const value = String(sceneId || '').trim()
  const match = value.match(/(?:scene[-_]?|^)(\d+)/i)
  if (match) {
    return `场景 ${match[1].padStart(2, '0')}`
  }
  return value || '未命名场景'
}

function audioAssetTitle(index: number): string {
  return `音频片段 ${String(index + 1).padStart(2, '0')}`
}

function formatAudioDuration(seconds?: number): string {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds <= 0) {
    return '时长待确认'
  }
  return `约 ${Math.round(seconds)} 秒`
}

function formatPreview(output?: Record<string, unknown>): string {
  if (!output) {
    return ''
  }

  if (typeof output.text === 'string') {
    return output.text
  }

  if ('scenes' in output && Array.isArray(output.scenes)) {
    return stringifyPretty(output.scenes)
  }

  if ('prompts' in output && Array.isArray(output.prompts)) {
    return stringifyPretty(output.prompts)
  }

  if (typeof output.full_text === 'string') {
    return output.full_text
  }

  if (typeof output.srt_preview === 'string') {
    return output.srt_preview
  }

  if ('edit_plan' in output && output.edit_plan) {
    return stringifyPretty(output)
  }

  return stringifyPretty(output)
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

function hasCompleteImageAssets(data: WorkflowRunResponse): boolean {
  const storyboard = data.outputs?.storyboard as Record<string, unknown> | undefined
  const imageAssets = data.outputs?.image_assets as Record<string, unknown> | undefined
  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes : []
  const assets = Array.isArray(imageAssets?.assets) ? imageAssets.assets : []
  const failedCount =
    typeof imageAssets?.failed_count === 'number' ? imageAssets.failed_count : 0
  const failedSceneIds = Array.isArray(imageAssets?.failed_scene_ids)
    ? imageAssets.failed_scene_ids
    : []
  const failedFromStatus = assets.some((asset) => {
    const status = (asset as Record<string, unknown> | null)?.status
    return typeof status === 'string' && status.toLowerCase() === 'failed'
  })
  const generatedCount =
    typeof imageAssets?.generated_count === 'number'
      ? imageAssets.generated_count
      : assets.length - failedCount

  return (
    scenes.length > 0 &&
    generatedCount >= scenes.length &&
    failedCount === 0 &&
    failedSceneIds.length === 0 &&
    !failedFromStatus
  )
}

function isGenericNetworkRequestError(message: string): boolean {
  return [
    'Failed to fetch',
    'Load failed',
    'NetworkError when attempting to fetch resource.',
  ].includes(String(message || '').trim())
}

function applyWorkflowResponse(data: WorkflowRunResponse) {
  storyText.value = extractStoryText(data)
  storyboardText.value = extractStoryboardText(data)
  imagePromptsText.value = extractImagePromptsText(data)
  imageAssetsText.value = extractImageAssetsText(data)
  imageReviewText.value = extractImageReviewText(data)
  videoPromptsText.value = extractVideoPromptsText(data)
  narrationText.value = extractNarrationText(data)
  subtitlesText.value = extractSubtitlesText(data)
  renderPlanText.value = extractRenderPlanText(data)
  finalVideoText.value = extractFinalVideoText(data)
  finalVideoAudioEnabled.value = (data.outputs as any)?.final_video?.audio_enabled ?? true
  {
    const extractedVideoUrl = extractFinalVideoUrl(data)
    // If the user has explicitly deleted this URL from history, do NOT
    // resurrect it on reattach / outputs reload. Without this guard a
    // page refresh after delete would re-import the URL via the
    // workflow_id→outputs.json restore path.
    if (extractedVideoUrl && deletedVideoUrlsSet.value.has(extractedVideoUrl)) {
      finalVideoUrl.value = ''
    } else {
      finalVideoUrl.value = extractedVideoUrl
      if (finalVideoUrl.value) {
        pushRecentFinalVideoUrl(finalVideoUrl.value, deriveVideoMeta(data))
        localStorage.setItem(STORAGE_KEY_VIDEO_URL, finalVideoUrl.value)
        clearFinalVideoRenderMarker(String(data.workflow_id || ''))
        clearFinalVideoRecoveryTimer()
        finalVideoRenderInFlight.value = false
        finalVideoRendering.value = false
        // Pipeline is fully done — drop the "user cancelled refresh"
        // marker so a brand-new workflow after this isn't blocked.
        clearImageRefreshCancelledMarker()
      }
    }
  }
  extractMockAudioState(data)
  stepSummaries.value = buildStepSummaries(data)
  characterCandidatesText.value = extractCharacterCandidatesText(data)
  characterManifestText.value = extractCharacterManifestText(data)
  resultText.value = stringifyPretty(data)
  currentWorkflowResponse.value = data
  if (data.workflow_id && data.run_id) {
    loadSceneTaskIds(data.workflow_id, data.run_id)
  }
  const selectedAssets = (data.outputs?.image_review as Record<string, unknown> | undefined)
    ?.selected_assets
  if (Array.isArray(selectedAssets)) {
    const stableVersions: Record<string, string | number> = {}
    for (const raw of selectedAssets) {
      if (!raw || typeof raw !== 'object') continue
      const item = raw as Record<string, unknown>
      const sceneId = String(item.scene_id || '')
      const candidates = Array.isArray(item.candidate_asset_refs)
        ? item.candidate_asset_refs
        : []
      const version = candidates
        .map((candidate) =>
          candidate && typeof candidate === 'object'
            ? (candidate as Record<string, unknown>).version
            : undefined,
        )
        .find((value) => typeof value === 'string' || typeof value === 'number')
      if (sceneId && version != null) stableVersions[sceneId] = version
    }
    sceneImageVersions.value = stableVersions
  }
  syncReviewPlaceholders(data)

  // A transient workflow/status fetch can fail after the backend has already
  // completed and persisted every candidate. Once the recovered response
  // proves all scenes succeeded, that generic browser error is stale. Keep
  // every specific image/render/validation error intact.
  if (hasCompleteImageAssets(data) && isGenericNetworkRequestError(errorMessage.value)) {
    errorMessage.value = ''
  }

  const sessionId = data.session_id || workflowForm.value.sessionId
  if (sessionId) {
    localStorage.setItem(STORAGE_KEY_SESSION, sessionId)
  }
  const workflowId = data.workflow_id
  if (workflowId) {
    persistActiveWorkflowIdentity(workflowId, data.run_id || '')
  }
}

function buildReviewPlaceholdersFromStoryboard(data: WorkflowRunResponse): ReviewPlaceholderItem[] {
  const storyboard = data.outputs?.storyboard as Record<string, unknown> | undefined
  const scenesValue = storyboard?.scenes
  const scenes = Array.isArray(scenesValue) ? scenesValue : []

  const imageReview = data.outputs?.image_review as Record<string, unknown> | undefined
  const imageAssets = data.outputs?.image_assets as Record<string, unknown> | undefined

  // Only build placeholder "waiting" cards when images are actually pending or
  // already partially generated. If the run had no image generation step at all,
  // skip the placeholders — they'd be permanently stuck with no way to resolve.
  const imagesDeferredToRefresh =
    String(imageAssets?.status || '') === 'pending' &&
    String(imageAssets?.reason || '') === 'deferred_to_refresh'
  const hasSelectedAssets =
    Array.isArray(imageReview?.selected_assets) &&
    (imageReview?.selected_assets as unknown[]).length > 0
  const hasExplicitFailures =
    (typeof imageAssets?.failed_count === 'number' && imageAssets.failed_count > 0) ||
    (Array.isArray(imageAssets?.failed_scene_ids) && imageAssets.failed_scene_ids.length > 0)

  if (!imagesDeferredToRefresh && !hasSelectedAssets && !hasExplicitFailures) {
    return []
  }

  const selectedAssetsValue = imageReview?.selected_assets
  const selectedAssets = Array.isArray(selectedAssetsValue) ? selectedAssetsValue : []

  const doneSceneIds = new Set(
    selectedAssets
      .map((item: unknown) =>
        item && typeof item === 'object'
          ? String((item as Record<string, unknown>).scene_id || '')
          : '',
      )
      .filter(Boolean),
  )

  // Scenes the backend already marked as `status: 'failed'` in
  // image_assets.assets. After B1 (image_provider failures persisted
  // as placeholders), these are explicit dead scenes and must NOT
  // render as "waiting" — that copy implies generation is still
  // pending, which would confuse the user into thinking the workflow
  // is still working.
  const imageAssetList = Array.isArray((imageAssets as Record<string, unknown>)?.assets)
    ? ((imageAssets as Record<string, unknown>).assets as unknown[])
    : []
  const failedSceneIds = new Set<string>([
    ...(Array.isArray(imageAssets?.failed_scene_ids)
      ? imageAssets.failed_scene_ids.map((id) => String(id || '')).filter(Boolean)
      : []),
    ...(
    imageAssetList
      .map((item: unknown) => {
        if (!item || typeof item !== 'object') return ''
        const rec = item as Record<string, unknown>
        return String(rec.status || '').toLowerCase() === 'failed'
          ? String(rec.scene_id || '')
          : ''
      })
      .filter(Boolean)
    ),
  ])

  // Legacy outputs (written before B1) silently dropped failed scenes
  // — image_assets.assets just had fewer entries than storyboard
  // scenes and no `failed` marker anywhere. In that case the only
  // signal we have is "the workflow is already done" (final_video is
  // present): a scene that's missing from selected_assets in a
  // terminal run can't still be "waiting" — it must be a failure.
  const finalVideo = data.outputs?.final_video as Record<string, unknown> | undefined
  const finalVideoStatus = String(finalVideo?.status || '').toLowerCase()
  const workflowIsTerminal =
    Boolean(finalVideo?.public_url) ||
    finalVideoStatus === 'generated' ||
    finalVideoStatus === 'degraded'

  // The render step now also records `missing_scene_ids` when it
  // produces a degraded video. Trust that list when present — it's
  // the authoritative source for "rendered without this scene".
  const renderMissingSceneIds = new Set(
    (Array.isArray((finalVideo as Record<string, unknown>)?.missing_scene_ids)
      ? ((finalVideo as Record<string, unknown>).missing_scene_ids as unknown[])
      : []
    )
      .map((id) => String(id || ''))
      .filter(Boolean),
  )

  return scenes.map((scene: unknown) => {
    const sceneRecord = scene as Record<string, unknown>
    const sceneId = String(sceneRecord.scene_id || '')
    const sceneTitle = String(sceneRecord.scene_title || sceneId || 'unknown-scene')

    let state: ReviewPlaceholderItem['state']
    if (doneSceneIds.has(sceneId)) {
      state = 'done'
    } else if (failedSceneIds.has(sceneId) || renderMissingSceneIds.has(sceneId)) {
      state = 'failed'
    } else if (workflowIsTerminal) {
      // Legacy / unmarked: workflow ended without this scene's asset
      state = 'failed'
    } else if (sceneTaskIds.value[sceneId]) {
      state = 'confirming'
    } else {
      state = 'waiting'
    }

    return {
      scene_id: sceneId,
      scene_title: sceneTitle,
      state,
      error_message:
        state === 'failed' ? '该场景图片生成失败' : undefined,
    }
  })
}

function syncReviewPlaceholders(data: WorkflowRunResponse) {
  reviewPlaceholders.value = buildReviewPlaceholdersFromStoryboard(data)
}

function markPlaceholderState(
  sceneId: string,
  state: ReviewPlaceholderItem['state'],
  errorMessage = '',
) {
  reviewPlaceholders.value = reviewPlaceholders.value.map((item) =>
    item.scene_id === sceneId
      ? {
          ...item,
          state,
          error_message: errorMessage || undefined,
        }
      : item,
  )
}

async function fetchSamplesSummary() {
  const response = await fetch(`${apiBaseUrl}/v1/samples/summary`)
  if (!response.ok) {
    throw new Error(`Samples summary HTTP ${response.status}`)
  }
  const data: SamplesSummaryResponse = await response.json()
  samplesSummary.value = data
}

async function fetchKlingSamples() {
  const response = await fetch(`${apiBaseUrl}/v1/samples/kling/real`)
  if (!response.ok) {
    throw new Error(`Kling samples HTTP ${response.status}`)
  }

  const data = (await response.json()) as { samples?: KlingSample[] }
  klingSamples.value = Array.isArray(data.samples) ? data.samples : []

  if (!selectedSampleId.value && klingSamples.value.length > 0) {
    selectedSampleId.value = klingSamples.value[0].sample_id || ''
  }
}

async function fetchSampleDetail(sampleId: string) {
  if (!sampleId) {
    selectedSampleDetail.value = null
    return
  }

  const response = await fetch(`${apiBaseUrl}/v1/samples/kling/real/${sampleId}`)
  if (!response.ok) {
    throw new Error(`Sample detail HTTP ${response.status}`)
  }

  const data: KlingSample = await response.json()
  selectedSampleDetail.value = data
}

async function fetchSampleNotesText(notesPath?: string) {
  if (!notesPath) {
    selectedSampleNotesText.value = ''
    return
  }

  selectedSampleNotesLoading.value = true

  try {
    const response = await fetch(toAssetHref(notesPath))
    if (!response.ok) {
      throw new Error(`Sample notes HTTP ${response.status}`)
    }

    selectedSampleNotesText.value = await response.text()
  } catch (error) {
    selectedSampleNotesText.value =
      error instanceof Error ? `Failed to load notes: ${error.message}` : 'Failed to load notes'
  } finally {
    selectedSampleNotesLoading.value = false
  }
}

async function loadSampleAssets() {
  samplesLoading.value = true
  samplesErrorMessage.value = ''

  try {
    await fetchSamplesSummary()
    await fetchKlingSamples()

    if (selectedSampleId.value) {
      await fetchSampleDetail(selectedSampleId.value)
      await fetchSampleNotesText(selectedSampleDetail.value?.assets?.notes)
    } else {
      selectedSampleDetail.value = null
      selectedSampleNotesText.value = ''
    }

  } catch (error) {
    samplesErrorMessage.value =
      error instanceof Error ? error.message : 'Failed to load sample assets'
  } finally {
    samplesLoading.value = false
  }
}

async function selectImageAsset(sceneId: string, assetRef: ImageAssetRef) {
  if (!sceneId || !assetRefPath(assetRef)) {
    return
  }

  if (!currentWorkflowResponse.value || !currentWorkflowPayload.value) {
    errorMessage.value = '请先运行一次 workflow，再进行手动选图。'
    return
  }

  const outputs = currentWorkflowResponse.value.outputs || {}
  const imageReview = outputs.image_review
  const storyboard = outputs.storyboard

  if (!imageReview || typeof imageReview !== 'object') {
    errorMessage.value = '当前缺少 image_review 数据。'
    return
  }

  if (!storyboard || typeof storyboard !== 'object') {
    errorMessage.value = '当前缺少 storyboard 数据。'
    return
  }

  selectingSceneId.value = sceneId
  errorMessage.value = ''

  const payload = {
    workflow_id: currentWorkflowResponse.value.workflow_id || currentWorkflowPayload.value.workflow_id,
    session_id:
      currentWorkflowResponse.value.session_id || currentWorkflowPayload.value.session_id,
    run_id: currentWorkflowResponse.value.run_id || '',
    scene_id: sceneId,
    selected_asset_ref: assetRef,
    image_review: imageReview,
    storyboard,
    workflow_input: currentWorkflowPayload.value.input,
    video_provider:
      typeof currentWorkflowPayload.value.input?.video_provider === 'string'
        ? currentWorkflowPayload.value.input.video_provider
        : workflowForm.value.videoProvider,
  }

  try {
    const response = await fetch(`${apiBaseUrl}/v1/image-review/select`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data: ImageReviewSelectResponse = await response.json()

    const mergedResponse: WorkflowRunResponse = {
      ...(currentWorkflowResponse.value || {}),
      workflow_id: data.workflow_id || currentWorkflowResponse.value.workflow_id,
      session_id: data.session_id || currentWorkflowResponse.value.session_id,
      run_id: data.run_id || currentWorkflowResponse.value.run_id,
      outputs: {
        ...(currentWorkflowResponse.value.outputs || {}),
        image_assets:
          data.image_assets || currentWorkflowResponse.value.outputs?.image_assets || {},
        image_review:
          data.image_review || currentWorkflowResponse.value.outputs?.image_review || {},
        video_prompts:
          data.video_prompts || currentWorkflowResponse.value.outputs?.video_prompts || {},
      },
    }

    applyWorkflowResponse(mergedResponse)
    userHasInteractedWithImages.value = true
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '手动选图请求失败'
  } finally {
    selectingSceneId.value = ''
  }
}

function clearImageReviewAutoRefreshTimer() {
  if (imageReviewAutoRefreshTimer !== null) {
    window.clearTimeout(imageReviewAutoRefreshTimer)
    imageReviewAutoRefreshTimer = null
  }
  wakeImageReviewPolling?.()
  wakeImageReviewPolling = null
}

function onImageReviewVisibilityChange() {
  if (document.hidden) return
  imageReviewVisibilityRefreshRequested = true
  wakeImageReviewPolling?.()
  void restorePersistedWorkflowState('visibility')
}

function waitForImageReviewBatchPoll(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }

    let settled = false
    const finish = () => {
      if (settled) return
      settled = true
      if (imageReviewAutoRefreshTimer !== null) {
        window.clearTimeout(imageReviewAutoRefreshTimer)
        imageReviewAutoRefreshTimer = null
      }
      signal.removeEventListener('abort', onAbort)
      wakeImageReviewPolling = null
      resolve()
    }
    const onAbort = () => {
      if (settled) return
      settled = true
      if (imageReviewAutoRefreshTimer !== null) {
        window.clearTimeout(imageReviewAutoRefreshTimer)
        imageReviewAutoRefreshTimer = null
      }
      wakeImageReviewPolling = null
      reject(new DOMException('Aborted', 'AbortError'))
    }

    wakeImageReviewPolling = finish
    signal.addEventListener('abort', onAbort, { once: true })
    imageReviewAutoRefreshTimer = window.setTimeout(finish, ms)
  })
}

function resolveWorkflowPayloadForRender(baseResponse: WorkflowRunResponse): WorkflowRunPayload | null {
  if (currentWorkflowPayload.value?.input) return currentWorkflowPayload.value

  try {
    const savedPayload = localStorage.getItem(STORAGE_KEY_PAYLOAD)
    if (savedPayload) {
      const parsed = JSON.parse(savedPayload) as Partial<WorkflowRunPayload>
      if (parsed && typeof parsed.input === 'object' && parsed.input) {
        const restored: WorkflowRunPayload = {
          workflow_id: String(parsed.workflow_id || baseResponse.workflow_id || ''),
          session_id: String(parsed.session_id || baseResponse.session_id || ''),
          input: parsed.input as Record<string, unknown>,
          steps: Array.isArray(parsed.steps) ? parsed.steps as Array<{ name: StepName }> : [],
        }
        currentWorkflowPayload.value = restored
        return restored
      }
    }
  } catch {
    /* malformed localStorage payload — fall through to response fallback */
  }

  const responseInput = baseResponse.input || baseResponse.workflow_input
  if (responseInput && typeof responseInput === 'object' && !Array.isArray(responseInput)) {
    const restored: WorkflowRunPayload = {
      workflow_id: String(baseResponse.workflow_id || ''),
      session_id: String(baseResponse.session_id || ''),
      input: responseInput as Record<string, unknown>,
      steps: [],
    }
    currentWorkflowPayload.value = restored
    return restored
  }

  return null
}

async function renderFinalVideoIfReady(baseResponse: WorkflowRunResponse) {
  const payloadForRender = resolveWorkflowPayloadForRender(baseResponse)
  if (!payloadForRender) {
    errorMessage.value = '缺少本次生成的 workflow 输入参数，请回到「创作故事」重新开始生成。'
    return
  }
  const renderWorkflowId = String(
    baseResponse.workflow_id || payloadForRender.workflow_id || '',
  ).trim()
  const renderGeneration = workflowLifecycleGeneration
  if (!isCurrentWorkflowLifecycle(renderWorkflowId, renderGeneration)) return
  const existingRenderMarker = readFinalVideoRenderMarker(renderWorkflowId)
  if (existingRenderMarker) {
    finalVideoRendering.value = true
    finalVideoRenderInFlight.value = true
    scheduleFinalVideoAuthoritativeRecovery(renderWorkflowId)
    return
  }
  if (finalVideoRendering.value || finalVideoRenderInFlight.value) return

  const outputs = baseResponse.outputs || {}
  const storyboard = outputs.storyboard as Record<string, unknown> | undefined
  const imageAssets = outputs.image_assets as Record<string, unknown> | undefined
  const audioSegments = outputs.audio_segments as Record<string, unknown> | undefined
  const subtitles = outputs.subtitles as Record<string, unknown> | undefined
  const finalVideo = outputs.final_video as Record<string, unknown> | undefined

  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes : []
  const imageAssetList = Array.isArray(imageAssets?.assets) ? imageAssets.assets : []
  const audioItems = Array.isArray(audioSegments?.items) ? audioSegments.items : []

  const finalVideoStatus = typeof finalVideo?.status === 'string' ? finalVideo.status : ''
  const finalVideoEnabled = finalVideo?.enabled === true

  if (finalVideoEnabled && finalVideoStatus === 'generated') return
  if (scenes.length === 0) return
  if (imageAssetList.length < scenes.length) return

  // Per-scene failures (B1) inflate imageAssetList.length to scene_count
  // with status='failed' placeholders. The length check above can't tell
  // them apart, so check the explicit failure signals here. Without this,
  // auto-mode would POST /v1/final-video/render on a partially-failed
  // workflow — the backend would 4xx (B2 gate), but better to short-circuit.
  const failedCountRaw = imageAssets?.failed_count
  const failedCount = typeof failedCountRaw === 'number' ? failedCountRaw : 0
  const failedIds = Array.isArray(imageAssets?.failed_scene_ids)
    ? (imageAssets.failed_scene_ids as unknown[]).length
    : 0
  const hasFailedFromStatus = imageAssetList.some((a) => {
    const status = (a as Record<string, unknown> | null)?.status
    return typeof status === 'string' && status.toLowerCase() === 'failed'
  })
  if (failedCount > 0 || failedIds > 0 || hasFailedFromStatus) return

  // 允许无声视频
  // 只有在 audio_segments 存在且明确 enabled=true 但没有生成时才阻止
  const audioEnabled = audioSegments?.enabled === true

  if (audioEnabled && audioItems.length === 0) return

  const payload = {
    workflow_id: renderWorkflowId,
    session_id: baseResponse.session_id || payloadForRender.session_id,
    run_id: baseResponse.run_id || '',
    workflow_input: payloadForRender.input,
    image_assets: imageAssets || {},
    audio_segments: audioSegments || {},
    subtitles: subtitles || {},
  }

  persistFinalVideoRenderMarker(renderWorkflowId, String(payload.run_id || ''))
  finalVideoRendering.value = true
  finalVideoRenderInFlight.value = true
  errorMessage.value = ''

  try {
    const response = await fetch(`${apiBaseUrl}/v1/final-video/render`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data: FinalVideoRenderResponse = await response.json()
    if (!isCurrentWorkflowLifecycle(renderWorkflowId, renderGeneration)) return
    if (!readFinalVideoRenderMarker(renderWorkflowId)) return

    const mergedResponse: WorkflowRunResponse = {
      ...(baseResponse || {}),
      workflow_id: data.workflow_id || baseResponse.workflow_id,
      session_id: data.session_id || baseResponse.session_id,
      run_id: data.run_id || baseResponse.run_id,
      outputs: {
        ...(baseResponse.outputs || {}),
        final_video: data.final_video || baseResponse.outputs?.final_video || {},
      },
    }

    applyWorkflowResponse(mergedResponse)
    reconcileRestoredFinalVideoState(renderWorkflowId)
  } catch (error) {
    clearFinalVideoRenderMarker(renderWorkflowId)
    if (!isCurrentWorkflowLifecycle(renderWorkflowId, renderGeneration)) return
    const message = error instanceof Error ? error.message : 'Request failed'
    errorMessage.value = `最终视频生成失败：${message}`
  } finally {
    if (
      isCurrentWorkflowLifecycle(renderWorkflowId, renderGeneration) &&
      !readFinalVideoRenderMarker(renderWorkflowId)
    ) {
      finalVideoRenderInFlight.value = false
      finalVideoRendering.value = false
    }
  }
}

function waitForTaskPoll(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }
    const onAbort = () => {
      window.clearTimeout(timer)
      reject(new DOMException('Aborted', 'AbortError'))
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)
    signal?.addEventListener('abort', onAbort, { once: true })
  })
}

async function fetchAuthoritativeWorkflow(workflowId: string, signal?: AbortSignal) {
  const response = await fetch(
    `${apiBaseUrl}/v1/workflow/results/${encodeURIComponent(workflowId)}`,
    { signal },
  )
  if (!response.ok) throw new Error(`Workflow outputs HTTP ${response.status}`)
  return (await response.json()) as WorkflowRunResponse
}

function getAuthoritativeReadySceneIds(data: WorkflowRunResponse): Set<string> {
  const selectedAssets = (
    data.outputs?.image_review as Record<string, unknown> | undefined
  )?.selected_assets
  return new Set(
    (Array.isArray(selectedAssets) ? selectedAssets : [])
      .map((item) =>
        item && typeof item === 'object'
          ? String((item as Record<string, unknown>).scene_id || '')
          : '',
      )
      .filter(Boolean),
  )
}

async function lookupSceneTask(
  workflowId: string,
  runId: string,
  sceneId: string,
  signal?: AbortSignal,
) {
  const query = new URLSearchParams({ workflow_id: workflowId, run_id: runId, scene_id: sceneId })
  const response = await fetch(
    `${apiBaseUrl}/v1/image-review/refresh-scene-task?${query.toString()}`,
    { signal },
  )
  if (response.status === 404) return null
  if (!response.ok) throw new Error(`Image task lookup HTTP ${response.status}`)
  return (await response.json()) as ImageRefreshTaskResponse
}

async function refreshImageReviewScene(
  sceneId: string,
  signal?: AbortSignal,
  qualityTierOverride?: string,
  preserveSeed: boolean = false,
  // IDs of scenes that have *terminally* failed during the caller's
  // current activity (bulk refresh loop OR all previously-recorded
  // failures from outputs.json on a single-scene retry). Forwarded
  // to the backend so image_assets only writes failed placeholders
  // for these — not for scenes still queued for processing.
  knownFailedSceneIds?: string[],
  retryFailed: boolean = false,
  allowCreate: boolean = true,
) {
  if (!currentWorkflowResponse.value || !currentWorkflowPayload.value) {
    return
  }

  const outputs = currentWorkflowResponse.value.outputs || {}
  const storyboard = outputs.storyboard
  const imageReview = outputs.image_review

  if (!storyboard || typeof storyboard !== 'object') {
    errorMessage.value = '当前缺少 storyboard 数据。'
    return
  }

  sceneRefreshingId.value = sceneId
  markPlaceholderState(sceneId, sceneTaskIds.value[sceneId] ? 'confirming' : 'queued')

  const payload = {
    workflow_id: currentWorkflowResponse.value.workflow_id || currentWorkflowPayload.value.workflow_id,
    session_id:
      currentWorkflowResponse.value.session_id || currentWorkflowPayload.value.session_id,
    run_id: currentWorkflowResponse.value.run_id || '',
    scene_id: sceneId,
    storyboard,
    workflow_input: qualityTierOverride
      ? { ...currentWorkflowPayload.value.input, quality_tier: qualityTierOverride }
      : currentWorkflowPayload.value.input,
    image_review: imageReview && typeof imageReview === 'object' ? imageReview : {},
    character_manifest:
      outputs.character_manifest && typeof outputs.character_manifest === 'object'
        ? outputs.character_manifest
        : {},
    image_prompts:
      outputs.image_prompts && typeof outputs.image_prompts === 'object'
        ? outputs.image_prompts
        : {},
    video_provider:
      typeof currentWorkflowPayload.value.input?.video_provider === 'string'
        ? currentWorkflowPayload.value.input.video_provider
        : workflowForm.value.videoProvider,
    preserve_seed: preserveSeed,
    known_failed_scene_ids: knownFailedSceneIds ?? [],
  }

  const workflowId = String(payload.workflow_id)
  const runId = String(payload.run_id)
  let task: ImageRefreshTaskResponse | null = null
  let pollDelay = 2000

  if (retryFailed && allowCreate) {
    const response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene-task`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, retry_failed: true }),
      signal,
    })
    if (!response.ok) throw new Error(`Image task recreate HTTP ${response.status}`)
    task = (await response.json()) as ImageRefreshTaskResponse
  }

  while (!task) {
    try {
      const knownTaskId = sceneTaskIds.value[sceneId]
      if (knownTaskId) {
        const response = await fetch(
          `${apiBaseUrl}/v1/image-review/refresh-scene-task/${encodeURIComponent(knownTaskId)}`,
          { signal },
        )
        if (response.ok) task = (await response.json()) as ImageRefreshTaskResponse
        else if (response.status === 404) task = await lookupSceneTask(workflowId, runId, sceneId, signal)
        else throw new Error(`Image task HTTP ${response.status}`)
      } else {
        task = await lookupSceneTask(workflowId, runId, sceneId, signal)
        if (!task) {
          if (!allowCreate) {
            markPlaceholderState(sceneId, 'waiting')
            return
          }
          const response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene-task`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...payload, retry_failed: retryFailed }),
            signal,
          })
          if (!response.ok) throw new Error(`Image task create HTTP ${response.status}`)
          task = (await response.json()) as ImageRefreshTaskResponse
        }
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      markPlaceholderState(sceneId, 'confirming')
      await waitForTaskPoll(pollDelay, signal)
      pollDelay = Math.min(5000, pollDelay + 750)
    }
  }

  while (task.status === 'failed' && retryFailed) {
    try {
      const response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene-task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, retry_failed: true }),
        signal,
      })
      if (!response.ok) throw new Error(`Image task retry HTTP ${response.status}`)
      task = (await response.json()) as ImageRefreshTaskResponse
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      markPlaceholderState(sceneId, 'confirming')
      await waitForTaskPoll(pollDelay, signal)
      pollDelay = Math.min(5000, pollDelay + 750)
    }
  }

  sceneTaskIds.value = { ...sceneTaskIds.value, [sceneId]: task.task_id }
  persistSceneTaskIds(workflowId, runId)

  while (true) {
    if (task.status === 'succeeded') {
      markPlaceholderState(sceneId, 'confirming')
      try {
        const authoritative = await fetchAuthoritativeWorkflow(workflowId, signal)
        applyWorkflowResponse(authoritative)
        markPlaceholderState(sceneId, 'done')
        return
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error
        markPlaceholderState(sceneId, 'confirming')
      }
    } else if (task.status === 'failed') {
      // One final identity lookup runs the backend file reconcile. Only an
      // explicit failed state with no recoverable A/B files becomes failed.
      let recovered: ImageRefreshTaskResponse | null
      try {
        recovered = await lookupSceneTask(workflowId, runId, sceneId, signal)
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error
        markPlaceholderState(sceneId, 'confirming')
        await waitForTaskPoll(pollDelay, signal)
        pollDelay = Math.min(5000, pollDelay + 750)
        continue
      }
      if (recovered?.status === 'succeeded') {
        task = recovered
        continue
      }
      throw new Error(`${sceneId} 候选图生成失败：${task.error || '服务端任务失败'}`)
    } else {
      markPlaceholderState(sceneId, task.status === 'running' ? 'refreshing' : 'queued')
    }

    await waitForTaskPoll(pollDelay, signal)
    pollDelay = Math.min(5000, pollDelay + 500)
    try {
      const response = await fetch(
        `${apiBaseUrl}/v1/image-review/refresh-scene-task/${encodeURIComponent(task.task_id)}`,
        { signal },
      )
      if (!response.ok) throw new Error(`Image task poll HTTP ${response.status}`)
      task = (await response.json()) as ImageRefreshTaskResponse
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      markPlaceholderState(sceneId, 'confirming')
    }
  }
}

async function retryImageReviewScene(sceneId: string) {
  if (!sceneId || refreshingImageReview.value || sceneRefreshingId.value) {
    return
  }

  errorMessage.value = ''
  imageReviewRefreshAbortController = new AbortController()

  // ── Intent detection ────────────────────────────────────────────
  // Two callers, two semantics:
  //   • 重试该场景 (failed-card button)  → scene has NO valid image;
  //     failure here is bad, must propagate through the failure UI.
  //   • 重新生成 (done-card ↻ button)   → scene already has a valid
  //     image (still in selected_assets); failure here is harmless,
  //     old image preserved, state unchanged.
  // Discriminator: presence in image_review.selected_assets.
  const priorOutputsSnapshot = currentWorkflowResponse.value?.outputs || {}
  const priorReview = priorOutputsSnapshot.image_review as
    | Record<string, unknown>
    | undefined
  const priorSelected = Array.isArray(priorReview?.selected_assets)
    ? priorReview.selected_assets
    : []
  const hadPriorSuccess = priorSelected.some(
    (s: any) =>
      s && typeof s === 'object' && String(s.scene_id || '').trim() === sceneId,
  )

  // ── finalVideoUrl handling ──────────────────────────────────────
  // Clear ONLY in the 重试该场景 case. The 重新生成 button only shows
  // when no video exists yet (so finalVideoUrl is already empty), but
  // making the conditional explicit prevents a future state shift from
  // accidentally wiping a valid video. Original side-effects of the
  // clear were:
  //   1. FinalVideoPanel falls through to placeholder + animation
  //   2. renderFinalVideoIfReady's URL guard no longer short-circuits
  //   3. per-scene 重新生成 button reappears
  // All three only matter when the workflow was previously blocked by
  // a missing scene — i.e. !hadPriorSuccess.
  if (!hadPriorSuccess) {
    finalVideoUrl.value = ''
  }

  // Carry forward the prior failed-scene list so the backend keeps
  // those marked as failed during this retry's image_assets rebuild.
  // EXCLUDE the current scene — if its retry succeeds, the backend's
  // selected_assets check naturally drops it from failures anyway, but
  // sending it would also work; if it fails again, main.py's failure
  // handler will add it back.
  const priorImageAssets = priorOutputsSnapshot.image_assets as
    | Record<string, unknown>
    | undefined
  const priorFailedIds = priorImageAssets?.failed_scene_ids
  const knownFailed: string[] = Array.isArray(priorFailedIds)
    ? (priorFailedIds as unknown[])
        .map((id) => String(id || '').trim())
        .filter((id) => Boolean(id) && id !== sceneId)
    : []

  try {
    await refreshImageReviewScene(
      sceneId,
      imageReviewRefreshAbortController.signal,
      undefined,
      false,
      knownFailed,
      true,
    )
    if (workflowForm.value.renderMode === 'auto' && currentWorkflowResponse.value) {
      void renderFinalVideoIfReady(currentWorkflowResponse.value)
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      markPlaceholderState(sceneId, 'waiting')
      return
    }

    const message = error instanceof Error ? error.message : '候选图场景重试失败'
    if (hadPriorSuccess) {
      // 重新生成 failed: original image still in selected_assets, all
      // pipeline state is intact (assetsReady stays true, 生成视频 button
      // stays visible, no failure cascade). Revert the 'refreshing'
      // placeholder back to 'done' so the card returns to its prior
      // visual, and surface the failure via a non-blocking toast.
      markPlaceholderState(sceneId, 'done')
      showInlineNotice(
        `${sceneId} 重新生成失败，已保留原图。${message}`,
        'warn',
      )
    } else {
      markPlaceholderState(sceneId, 'failed', message)
      errorMessage.value = message
    }
  } finally {
    sceneRefreshingId.value = ''
    imageReviewRefreshAbortController = null
  }
}


// Unified "stop the current in-flight work" affordance. The Studio runs
// two distinct cancellable phases:
//   - initial workflow (story / storyboard / etc.) → server-side cancel
//   - candidate image refresh (per-scene loop)     → frontend AbortController
// They share the same "取消生成" button in WorkflowRunPanel / StudioProgress
// / StudioPreviewPanel; this dispatcher routes to the right implementation
// based on which phase is actually running.
const phaseInFlight = computed(() => {
  return loading.value || refreshingImageReview.value || finalVideoRenderInFlight.value
})
const phaseCancellable = computed(() => phaseInFlight.value && !cancelRequestedAny.value)
const cancelRequestedAny = computed(() =>
  cancelRequested.value || imageReviewRefreshCancelled.value,
)
function cancelActivePhase() {
  // Candidate-image refresh can overlap with the workflow completion
  // handoff for one render tick. If the user sees/cancels "候选图生成中",
  // stop that refresh first; otherwise we may only cancel the already
  // completed workflow while the refresh-scene request keeps running.
  if (refreshingImageReview.value) {
    cancelImageReviewRefresh()
    return
  }
  if (loading.value && activeWorkflowId.value) {
    void cancelWorkflow()
    return
  }
}

async function cancelWorkflow() {
  // Cancellation only makes sense while a run is actually in flight and
  // we know which workflow_id to target. Re-clicking the button has no
  // additional effect — the registry is idempotent.
  const workflowId = activeWorkflowId.value
  if (!workflowId || cancelRequested.value) {
    return
  }
  cancelRequested.value = true
  try {
    await fetch(`${apiBaseUrl}/v1/workflow/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: workflowId }),
    })
    // Don't flip loading off here — the polling loop will see the status
    // turn 'cancelled' once the runner reaches its next checkpoint and
    // resolve the run normally.
  } catch (error) {
    // Network failure shouldn't lock the UI; allow the user to retry.
    cancelRequested.value = false
    errorMessage.value =
      error instanceof Error ? `取消失败：${error.message}` : '取消失败'
  }
}

function cancelImageReviewRefresh() {
  if (!refreshingImageReview.value) {
    return
  }

  imageReviewRefreshCancelled.value = true
  imageReviewRefreshAbortController?.abort()

  if (sceneRefreshingId.value) {
    markPlaceholderState(sceneRefreshingId.value, 'waiting')
  }

  // Persist "this workflow's image refresh was cancelled by the user"
  // so a subsequent mount (Landing → Studio nav) doesn't auto-restart
  // the loop we just stopped. Cleared by: starting a new workflow,
  // manual "立即生成候选图" click, or full pipeline completion.
  const wfId =
    currentWorkflowResponse.value?.workflow_id ||
    currentWorkflowPayload.value?.workflow_id ||
    localStorage.getItem(STORAGE_KEY_WORKFLOW) ||
    ''
  if (wfId) {
    try { localStorage.setItem(STORAGE_KEY_REFRESH_CANCELLED, wfId) } catch { /* ignore */ }
    imageRefreshPausedByUser.value = true
    notifyBackendImageRefreshCancel(wfId)
  }

  errorMessage.value = '已取消剩余候选图生成。'
}

// Returns true if the user explicitly cancelled image refresh for THIS
// workflow_id (persisted in localStorage). Used by auto-resume paths so
// nav-back / reload doesn't re-trigger a run the user just stopped.
function isImageRefreshUserCancelled(): boolean {
  const cancelledFor = (() => {
    try { return localStorage.getItem(STORAGE_KEY_REFRESH_CANCELLED) || '' } catch { return '' }
  })()
  if (!cancelledFor) return false
  const currentWfId =
    currentWorkflowResponse.value?.workflow_id ||
    currentWorkflowPayload.value?.workflow_id ||
    localStorage.getItem(STORAGE_KEY_WORKFLOW) ||
    ''
  return Boolean(currentWfId && currentWfId === cancelledFor)
}

function clearImageRefreshCancelledMarker() {
  try { localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED) } catch { /* ignore */ }
  imageRefreshPausedByUser.value = false
}

function notifyBackendImageRefreshCancel(workflowId: string) {
  const normalizedWorkflowId = String(workflowId || '').trim()
  if (!normalizedWorkflowId) return
  void fetch(`${apiBaseUrl}/v1/workflow/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      workflow_id: normalizedWorkflowId,
      scope: 'image_refresh',
    }),
  }).catch(() => {
    /* best-effort: local marker + AbortController still pause this tab */
  })
}

async function clearBackendCancelMarker(workflowId: string) {
  const normalizedWorkflowId = String(workflowId || '').trim()
  if (!normalizedWorkflowId) return
  try {
    await fetch(`${apiBaseUrl}/v1/workflow/cancel/clear`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: normalizedWorkflowId }),
    })
  } catch {
    /* best-effort; a stale server marker will surface as a cancelled refresh */
  }
}

// Bound to the "立即生成候选图" deferred-banner button. The user explicitly
// asking to (re)start refresh means we must clear the persistent cancel
// marker before invoking the refresh loop — otherwise the auto-resume
// guard would still treat this workflow as cancelled on next mount.
async function triggerManualImageRefresh() {
  const wfId =
    currentWorkflowResponse.value?.workflow_id ||
    currentWorkflowPayload.value?.workflow_id ||
    localStorage.getItem(STORAGE_KEY_WORKFLOW) ||
    ''
  clearImageRefreshCancelledMarker()
  await clearBackendCancelMarker(wfId)
  imageReviewRefreshCancelled.value = false
  errorMessage.value = ''
  void refreshImageReview()
}

// "放弃当前生成" — the explicit-discard exit for a draft the user no longer
// wants to continue. Distinct from cancel: cancel pauses (banner stays so the
// user can resume), discard wipes the draft entirely and lands on a clean
// creation tab. Preserves the form inputs (so the user can tweak and retry)
// and the recent-videos history (those are past completed runs, not this draft).
//
// Two-step UX: discardCurrentDraft() opens the themed confirm dialog;
// performDiscardCurrentDraft() runs the actual reset once the user confirms.
// Native window.confirm was avoided because it can't be themed and broke the
// dark/pearl aesthetic.
const showDiscardConfirm = ref(false)

function discardCurrentDraft() {
  showDiscardConfirm.value = true
}

function cancelDiscardDialog() {
  showDiscardConfirm.value = false
}

// Confirm-before-rerun guard: when the current workflow has unresolved
// failed scenes (hasImageFailures), clicking "开始创作" would silently
// throw away the partially-generated story / candidates / failure list.
// The retry-failed-scene path in 画面审核 is the intended way to repair
// the run; this dialog catches users who clicked 开始创作 thinking it
// would fix the failure, and gives them an explicit choice.
const showStartRunConfirm = ref(false)
function cancelStartRunDialog() {
  showStartRunConfirm.value = false
}
function confirmStartRunDiscardingFailures() {
  showStartRunConfirm.value = false
  void executeRunWorkflow()
}

function performDiscardCurrentDraft() {
  showDiscardConfirm.value = false

  // Stop any in-flight image refresh.
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  imageReviewRefreshCancelled.value = false
  refreshingImageReview.value = false
  sceneRefreshQueue.value = []
  sceneRefreshingId.value = ''
  sceneTaskIds.value = {}
  clearImageReviewAutoRefreshTimer()
  reviewAutoRefreshFiredOnce = false
  restoreAutoRefreshFired = false
  // Reactive mirror — without this, the cancelled-refresh marker copy
  // would leak into the next run's placeholder text.
  imageRefreshPausedByUser.value = false

  // Wipe everything that applyWorkflowResponse populates.
  currentWorkflowResponse.value = null
  currentWorkflowPayload.value = null
  storyText.value = ''
  storyboardText.value = ''
  imagePromptsText.value = ''
  imageAssetsText.value = ''
  imageReviewText.value = ''
  videoPromptsText.value = ''
  narrationText.value = ''
  subtitlesText.value = ''
  renderPlanText.value = ''
  finalVideoText.value = ''
  finalVideoUrl.value = ''
  finalVideoAudioEnabled.value = true
  stepSummaries.value = []
  characterCandidatesText.value = ''
  characterManifestText.value = ''
  resultText.value = ''
  reviewPlaceholders.value = []
  errorMessage.value = ''
  workflowStatusData.value = null
  activeWorkflowId.value = ''
  cancelRequested.value = false
  loading.value = false
  finalVideoRenderInFlight.value = false
  finalVideoRendering.value = false
  // Additional in-flight UI state — without these the next run could
  // briefly inherit the cancelled run's per-scene selection / timing.
  workflowRunElapsedSec.value = 0
  selectingSceneId.value = ''
  userHasInteractedWithImages.value = false
  mockAudioIndexUrl.value = ''
  mockAudioSceneGroups.value = []
  mockAudioDirectoryText.value = ''
  mockAudioSegmentTextMap.value = {}

  // Regenerate the session id. The backend's RunnerSessionStore keys
  // its in-memory `previous_session_data` (last_story / last_storyboard /
  // last_render_plan) by session_id; reusing the same session_id after
  // a discard would seed the next run's session_memory_summary with the
  // previous run's topic — the cleanest fix is to mint a fresh session
  // on discard so the backend treats the next run as brand new.
  workflowForm.value.sessionId = createStudioSessionId()

  // Clear draft-related localStorage. Also clear SESSION so a page
  // reload between discard and the next run doesn't restore the stale
  // session id. FORM / TAB / DEV / RECENT_VIDEOS / LAST_VIDEO_URL stay
  // (those are user-level state, not part of this draft).
  try {
    localStorage.removeItem(STORAGE_KEY_WORKFLOW)
    localStorage.removeItem(STORAGE_KEY_RUN)
    localStorage.removeItem(STORAGE_KEY_PAYLOAD)
    localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
    localStorage.removeItem(STORAGE_KEY_SESSION)
    clearFinalVideoRenderMarker()
  } catch { /* ignore */ }

  // Drop the user back on 创作故事 — clean starting point for the next run.
  activeTab.value = 'run'
}

function buildImageRefreshTaskPayload(
  sceneId: string,
  knownFailedSceneIds: string[],
) {
  if (!currentWorkflowResponse.value || !currentWorkflowPayload.value) return null
  const outputs = currentWorkflowResponse.value.outputs || {}
  const storyboard = outputs.storyboard
  if (!storyboard || typeof storyboard !== 'object') return null

  return {
    workflow_id:
      currentWorkflowResponse.value.workflow_id || currentWorkflowPayload.value.workflow_id,
    session_id:
      currentWorkflowResponse.value.session_id || currentWorkflowPayload.value.session_id,
    run_id: currentWorkflowResponse.value.run_id || '',
    scene_id: sceneId,
    storyboard,
    workflow_input: currentWorkflowPayload.value.input,
    image_review:
      outputs.image_review && typeof outputs.image_review === 'object'
        ? outputs.image_review
        : {},
    character_manifest:
      outputs.character_manifest && typeof outputs.character_manifest === 'object'
        ? outputs.character_manifest
        : {},
    image_prompts:
      outputs.image_prompts && typeof outputs.image_prompts === 'object'
        ? outputs.image_prompts
        : {},
    video_provider:
      typeof currentWorkflowPayload.value.input?.video_provider === 'string'
        ? currentWorkflowPayload.value.input.video_provider
        : workflowForm.value.videoProvider,
    preserve_seed: false,
    known_failed_scene_ids: knownFailedSceneIds,
  }
}

async function fetchImageRefreshTaskBatch(
  workflowId: string,
  runId: string,
  signal: AbortSignal,
) {
  const query = new URLSearchParams({ workflow_id: workflowId, run_id: runId })
  const response = await fetch(
    `${apiBaseUrl}/v1/image-review/refresh-scene-tasks?${query.toString()}`,
    { signal },
  )
  if (!response.ok) throw new Error(`Image task batch HTTP ${response.status}`)
  return (await response.json()) as ImageRefreshTaskBatchResponse
}

async function createImageRefreshTask(
  sceneId: string,
  retryFailed: boolean,
  knownFailedSceneIds: string[],
  signal: AbortSignal,
) {
  const payload = buildImageRefreshTaskPayload(sceneId, knownFailedSceneIds)
  if (!payload) throw new Error(`Unable to build image task payload for ${sceneId}`)
  const response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene-task`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, retry_failed: retryFailed }),
    signal,
  })
  if (!response.ok) throw new Error(`Image task create HTTP ${response.status}`)
  return (await response.json()) as ImageRefreshTaskResponse
}

async function pollImageRefreshTasksForWorkflow(
  sceneIds: string[],
  failedSceneIds: Set<string>,
  allowCreate: boolean,
  workflowId: string,
  runId: string,
  workflowKey: string,
  generation: number,
  signal: AbortSignal,
) {
  const retriedFailedSceneIds = new Set<string>()
  const observedSucceededSceneIds = new Set<string>()
  const syncedSucceededSceneIds = new Set<string>()
  const submittedSceneIds = (() => {
    const existing = submittedImageTaskSceneIdsByWorkflow.get(workflowKey)
    if (existing) return existing
    const created = new Set<string>()
    submittedImageTaskSceneIdsByWorkflow.set(workflowKey, created)
    return created
  })()

  while (!signal.aborted) {
    if (
      generation !== imageReviewPollingGeneration ||
      activeImageReviewPollingKey !== workflowKey
    ) {
      throw new DOMException('Superseded', 'AbortError')
    }

    let batch: ImageRefreshTaskBatchResponse
    try {
      batch = await fetchImageRefreshTaskBatch(workflowId, runId, signal)
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      for (const sceneId of sceneIds) markPlaceholderState(sceneId, 'confirming')
      const delay = document.hidden ? 20000 : 5000
      await waitForImageReviewBatchPoll(delay, signal)
      continue
    }
    if (
      generation !== imageReviewPollingGeneration ||
      activeImageReviewPollingKey !== workflowKey
    ) {
      throw new DOMException('Superseded', 'AbortError')
    }

    const taskByScene = new Map(batch.tasks.map((task) => [task.scene_id, task]))

    for (const sceneId of sceneIds) {
      if (signal.aborted || generation !== imageReviewPollingGeneration) {
        throw new DOMException('Superseded', 'AbortError')
      }
      let task = taskByScene.get(sceneId)
      const shouldRetryFailed = Boolean(
        task?.status === 'failed' &&
        failedSceneIds.has(sceneId) &&
        !retriedFailedSceneIds.has(sceneId),
      )
      const shouldCreateMissing = Boolean(
        !task &&
        allowCreate &&
        !submittedSceneIds.has(sceneId) &&
        !observedSucceededSceneIds.has(sceneId),
      )
      if (shouldCreateMissing || shouldRetryFailed) {
        task = await createImageRefreshTask(
          sceneId,
          shouldRetryFailed,
          Array.from(failedSceneIds),
          signal,
        )
        if (
          generation !== imageReviewPollingGeneration ||
          activeImageReviewPollingKey !== workflowKey
        ) {
          throw new DOMException('Superseded', 'AbortError')
        }
        if (shouldRetryFailed) retriedFailedSceneIds.add(sceneId)
        submittedSceneIds.add(sceneId)
        taskByScene.set(sceneId, task)
      }
      if (task?.task_id) {
        sceneTaskIds.value = { ...sceneTaskIds.value, [sceneId]: task.task_id }
      }
    }
    persistSceneTaskIds(workflowId, runId)

    let hasActiveTask = false
    let hasSucceededTask = false
    const newlySucceededSceneIds: string[] = []
    const scenesNeedingResultSync: string[] = []
    const failures: string[] = []
    sceneRefreshingId.value = ''

    for (const sceneId of sceneIds) {
      const task = taskByScene.get(sceneId)
      if (!task) {
        if (submittedSceneIds.has(sceneId)) {
          hasActiveTask = true
          sceneRefreshingId.value ||= sceneId
          markPlaceholderState(sceneId, 'confirming')
        } else {
          markPlaceholderState(sceneId, 'waiting')
        }
        continue
      }
      if (task.status === 'queued') {
        hasActiveTask = true
        sceneRefreshingId.value ||= sceneId
        markPlaceholderState(sceneId, 'queued')
      } else if (task.status === 'running') {
        hasActiveTask = true
        sceneRefreshingId.value ||= sceneId
        markPlaceholderState(sceneId, 'refreshing')
      } else if (task.status === 'succeeded') {
        hasSucceededTask = true
        if (!observedSucceededSceneIds.has(sceneId)) {
          observedSucceededSceneIds.add(sceneId)
          newlySucceededSceneIds.push(sceneId)
        }
        if (syncedSucceededSceneIds.has(sceneId)) {
          markPlaceholderState(sceneId, 'done')
        } else {
          scenesNeedingResultSync.push(sceneId)
          markPlaceholderState(sceneId, 'confirming')
        }
      } else {
        const message = `${sceneId} 候选图生成失败：${task.error || '服务端任务失败'}`
        failures.push(message)
        failedSceneIds.add(sceneId)
        markPlaceholderState(sceneId, 'failed', message)
      }
    }

    // A batch can report several newly succeeded scenes at once. Pull the
    // authoritative workflow snapshot once for the whole batch, then let the
    // existing selected_assets -> placeholders -> imageGenerationSummary chain
    // advance readyCount. A failed/missing snapshot leaves the scenes in
    // confirming so the next batch-poll iteration retries only this read.
    if (
      hasActiveTask &&
      (newlySucceededSceneIds.length > 0 || scenesNeedingResultSync.length > 0)
    ) {
      try {
        const authoritative = await fetchAuthoritativeWorkflow(workflowId, signal)
        if (
          generation !== imageReviewPollingGeneration ||
          activeImageReviewPollingKey !== workflowKey
        ) {
          throw new DOMException('Superseded', 'AbortError')
        }
        applyWorkflowResponse(authoritative)
        const authoritativeReadySceneIds = getAuthoritativeReadySceneIds(authoritative)
        for (const sceneId of scenesNeedingResultSync) {
          if (authoritativeReadySceneIds.has(sceneId)) {
            syncedSucceededSceneIds.add(sceneId)
            markPlaceholderState(sceneId, 'done')
          } else {
            markPlaceholderState(sceneId, 'confirming')
          }
        }
        // applyWorkflowResponse rebuilds placeholders from persisted assets.
        // Restore the finer task states for scenes that are still in flight.
        for (const sceneId of sceneIds) {
          const task = taskByScene.get(sceneId)
          if (task?.status === 'queued') markPlaceholderState(sceneId, 'queued')
          if (task?.status === 'running') markPlaceholderState(sceneId, 'refreshing')
        }
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') throw error
        for (const sceneId of scenesNeedingResultSync) {
          markPlaceholderState(sceneId, 'confirming')
        }
      }
    }

    if (!hasActiveTask) {
      if (hasSucceededTask) {
        try {
          // Keep one final authoritative reconciliation after every task is
          // terminal, even if incremental snapshots already populated scenes.
          const authoritative = await fetchAuthoritativeWorkflow(workflowId, signal)
          if (
            generation !== imageReviewPollingGeneration ||
            activeImageReviewPollingKey !== workflowKey
          ) {
            throw new DOMException('Superseded', 'AbortError')
          }
          applyWorkflowResponse(authoritative)
          const authoritativeReadySceneIds = getAuthoritativeReadySceneIds(authoritative)
          for (const sceneId of sceneIds) {
            if (taskByScene.get(sceneId)?.status !== 'succeeded') continue
            if (authoritativeReadySceneIds.has(sceneId)) {
              syncedSucceededSceneIds.add(sceneId)
              markPlaceholderState(sceneId, 'done')
            } else {
              markPlaceholderState(sceneId, 'confirming')
            }
          }
          const hasUnsyncedSucceededTask = sceneIds.some(
            (sceneId) =>
              taskByScene.get(sceneId)?.status === 'succeeded' &&
              !syncedSucceededSceneIds.has(sceneId),
          )
          if (!hasUnsyncedSucceededTask) return failures
        } catch (error) {
          if (error instanceof DOMException && error.name === 'AbortError') throw error
          for (const sceneId of scenesNeedingResultSync) {
            markPlaceholderState(sceneId, 'confirming')
          }
        }
      } else {
        return failures
      }
    }

    const visibilityDelay = document.hidden ? 20000 : 5000
    const delay = imageReviewVisibilityRefreshRequested ? 0 : visibilityDelay
    imageReviewVisibilityRefreshRequested = false
    await waitForImageReviewBatchPoll(delay, signal)
  }

  throw new DOMException('Aborted', 'AbortError')
}

async function refreshImageReview(allowCreate = true) {
  if (!currentWorkflowResponse.value || !currentWorkflowPayload.value) {
    return
  }

  if (refreshingImageReview.value) {
    return
  }

  const storyboard = currentWorkflowResponse.value.outputs?.storyboard as Record<string, unknown> | undefined
  const scenesValue = storyboard?.scenes
  const scenes = Array.isArray(scenesValue) ? scenesValue : []
  if (scenes.length === 0) {
    errorMessage.value = '当前缺少 storyboard.scenes 数据。'
    return
  }

  const imageReview = currentWorkflowResponse.value.outputs?.image_review as Record<string, unknown> | undefined
  const selectedAssetsValue = imageReview?.selected_assets
  const selectedAssets = Array.isArray(selectedAssetsValue) ? selectedAssetsValue : []

  const doneSceneIds = new Set(
    selectedAssets
      .map((item: unknown) =>
        item && typeof item === 'object'
          ? String((item as Record<string, unknown>).scene_id || '')
          : '',
      )
      .filter(Boolean),
  )

  sceneRefreshQueue.value = scenes
    .map((scene) => String((scene as Record<string, unknown>).scene_id || ''))
    .filter((sceneId) => sceneId && !doneSceneIds.has(sceneId))

  if (sceneRefreshQueue.value.length === 0) {
    return
  }

  refreshingImageReview.value = true
  imageReviewRefreshCancelled.value = false
  errorMessage.value = ''

  const failures: string[] = []
  const refreshTotal = sceneRefreshQueue.value.length

  // Failed scene_ids accumulated during *this* loop. Forwarded to the
  // backend on each refresh-scene call so image_assets only writes
  // 'failed' placeholders for scenes that genuinely terminally failed
  // (not for scenes still queued for processing). Seeded from the
  // current outputs in case a prior partial-failure run left some
  // failed scenes that we're resuming over.
  const failedSceneIds = new Set<string>()
  const priorImageAssets = currentWorkflowResponse.value?.outputs?.image_assets as
    | Record<string, unknown>
    | undefined
  const priorFailedIds = priorImageAssets?.failed_scene_ids
  if (Array.isArray(priorFailedIds)) {
    for (const id of priorFailedIds) {
      const sid = String(id || '').trim()
      if (sid) failedSceneIds.add(sid)
    }
  }

  const workflowId = String(
    currentWorkflowResponse.value.workflow_id || currentWorkflowPayload.value.workflow_id || '',
  )
  const runId = String(currentWorkflowResponse.value.run_id || '')
  const workflowKey = imageTaskStorageKey(workflowId, runId)
  if (!workflowId || !runId) {
    refreshingImageReview.value = false
    errorMessage.value = '当前缺少 workflow_id 或 run_id。'
    return
  }
  if (activeImageReviewPollingKey === workflowKey) {
    refreshingImageReview.value = false
    return
  }

  imageReviewPollingGeneration += 1
  const generation = imageReviewPollingGeneration
  if (activeImageReviewPollingKey && activeImageReviewPollingKey !== workflowKey) {
    imageReviewRefreshAbortController?.abort()
  }
  activeImageReviewPollingKey = workflowKey

  try {
    imageReviewRefreshAbortController = new AbortController()
    const signal = imageReviewRefreshAbortController.signal
    failures.push(
      ...(await pollImageRefreshTasksForWorkflow(
        [...sceneRefreshQueue.value],
        failedSceneIds,
        allowCreate,
        workflowId,
        runId,
        workflowKey,
        generation,
        signal,
      )),
    )
  } catch (error) {
    if (
      !imageReviewRefreshCancelled.value &&
      !(error instanceof DOMException && error.name === 'AbortError')
    ) {
      const message = error instanceof Error ? error.message : '候选图任务状态查询失败'
      failures.push(message)
    }
  } finally {
    if (generation === imageReviewPollingGeneration) {
      sceneRefreshingId.value = ''
      sceneRefreshQueue.value = []
      refreshingImageReview.value = false
      imageReviewRefreshCancelled.value = false
      imageReviewRefreshAbortController = null
      activeImageReviewPollingKey = ''
      clearImageReviewAutoRefreshTimer()
    }
  }

  if (failures.length > 0) {
    errorMessage.value = `部分候选图生成失败：${failures.length}/${refreshTotal} 个场景未完成。图片服务暂时不可用，请在 Review 中重试失败场景或稍后再试。`
    return
  }

  // The loop completed without a failed scene. Clear only a stale generic
  // network error; specific validation or render errors belong to their own
  // phase and must remain visible.
  if (
    currentWorkflowResponse.value &&
    hasCompleteImageAssets(currentWorkflowResponse.value) &&
    isGenericNetworkRequestError(errorMessage.value)
  ) {
    errorMessage.value = ''
  }

  if (workflowForm.value.renderMode === 'auto' && currentWorkflowResponse.value) {
    void renderFinalVideoIfReady(currentWorkflowResponse.value)
  }
}
function scheduleImageReviewAutoRefreshIfNeeded() {
  if (imageStateHydrating.value) return
  if (reviewWaitingState.value !== 'deferred_pending' || reviewAutoRefreshFiredOnce) {
    return
  }
  // Respect the user's explicit cancel — don't auto-restart a refresh
  // they just stopped. Manual click of "立即生成候选图" clears the marker.
  if (isImageRefreshUserCancelled()) return

  reviewAutoRefreshFiredOnce = true
  clearImageReviewAutoRefreshTimer()
  if (refreshingImageReview.value) return
  void refreshImageReview()
}

// Called after page-refresh / SPA-nav restore. Triggers generation for scenes
// still 'waiting' (not in selected_assets). Safe to call even when some scenes
// are already done — refreshImageReview() skips doneSceneIds internally.
//
// Guards:
//   - if the CURRENT workflow's response already contains a final_video
//     URL, the run is fully done and we don't want to clobber it with a
//     fresh image-refresh cycle.
//   - recentFinalVideoUrls is NOT a valid guard: it accumulates videos
//     from prior runs and would block auto-refresh for any new workflow
//     after a user has ever produced a video before. Use finalVideoUrl
//     (per-workflow) only.
let restoreAutoRefreshFired = false
function resumePendingSceneGenerationAfterRestore() {
  if (imageStateHydrating.value) return
  if (restoreAutoRefreshFired) return
  const hasRecoverableTask = reviewPlaceholders.value.some((p) =>
    ['waiting', 'queued', 'refreshing', 'confirming'].includes(p.state),
  )
  if (!hasRecoverableTask) return
  if (!currentWorkflowPayload.value) return
  if (finalVideoUrl.value) return
  // Respect persistent user cancel — Landing → Studio nav must not undo
  // the user's "stop generating" action.
  if (isImageRefreshUserCancelled()) return

  restoreAutoRefreshFired = true
  // Fire immediately — same render tick as applyWorkflowResponse, so
  // refreshingImageReview = true masks the deferred-banner from the
  // very first paint.
  if (
    !refreshingImageReview.value &&
    reviewPlaceholders.value.some((p) =>
      ['waiting', 'queued', 'refreshing', 'confirming'].includes(p.state),
    )
  ) {
    void refreshImageReview(false)
  }
}

async function waitForAsyncWorkflowOutputs(
  workflowId: string,
  maxAttempts = 1200,
  intervalMs = 1500,
): Promise<WorkflowRunResponse | null> {
  const normalizedWorkflowId = String(workflowId || '').trim()
  if (!normalizedWorkflowId) {
    return null
  }

  const startedAt = Date.now()

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (studioViewUnmounted) return null
    workflowRunElapsedSec.value = Math.floor((Date.now() - startedAt) / 1000)
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs))
    if (studioViewUnmounted) return null
    workflowRunElapsedSec.value = Math.floor((Date.now() - startedAt) / 1000)

    const statusResponse = await fetch(
      `${apiBaseUrl}/v1/workflow/status/${encodeURIComponent(normalizedWorkflowId)}?ts=${Date.now()}`,
    )

    if (statusResponse.status === 404) {
      continue
    }

    if (!statusResponse.ok) {
      throw new Error(`Workflow status HTTP ${statusResponse.status}`)
    }

    const statusData = (await statusResponse.json()) as WorkflowStatusResponse
    workflowStatusData.value = statusData
    const status = String(statusData.status || '').trim().toLowerCase()

    if (status === 'processing' || status === 'cancel_requested') {
      // Either still working or waiting for the next checkpoint to honour
      // the cancel — keep polling until we reach a terminal state.
      continue
    }

    if (status === 'cancelled' || status === 'abandoned') {
      // Soft-terminate: don't throw (cancel/server-restart isn't an error).
      // Unify the UI back to idle here so every running surface — top
      // progress bar, CTA, timeline, video preview, image review — drops
      // "生成中" without waiting for a page refresh.
      // 'abandoned' is written by the backend on startup for status files
      // left orphaned by a previous server crash; treat it identically
      // so stale workflow_ids in localStorage don't lock the UI forever.
      resetWorkflowRuntimeState()
      return null
    }

    if (status === 'failed') {
      throw new Error(statusData.message || 'Workflow failed')
    }

    if (status !== 'completed') {
      throw new Error(`Unknown workflow status: ${statusData.status || 'empty'}`)
    }

    const outputsResponse = await fetch(
      `${apiBaseUrl}/assets/mock/${encodeURIComponent(normalizedWorkflowId)}/outputs.json?ts=${Date.now()}`,
    )

    if (!outputsResponse.ok) {
      throw new Error(`Workflow outputs HTTP ${outputsResponse.status}`)
    }

    return (await outputsResponse.json()) as WorkflowRunResponse
  }

  throw new Error(
    `Workflow 仍在处理中，前端已等待 ${formatElapsedTime(workflowRunElapsedSec.value)}。请稍后刷新状态或检查后端日志。`,
  )
}

// Public entry called by WorkflowRunPanel's "开始创作" button. Wraps
// the real implementation in a confirm-before-discard guard for the
// failure-recovery state — if image_assets has unresolved failures, a
// new run would silently wipe the partial work and the user might
// have meant to retry instead. Confirmation routes to executeRunWorkflow.
async function runWorkflow() {
  if (hasImageFailures.value) {
    showStartRunConfirm.value = true
    return
  }
  await executeRunWorkflow()
}

async function executeRunWorkflow() {
  // Defensive belt: abort any lingering image refresh from a previous
  // (cancelled but not discarded) run before we start a brand new one.
  // Without this, an orphan refresh promise could resolve mid-run and
  // overwrite the new image_review / selected_assets with stale data.
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  imageReviewRefreshCancelled.value = false
  imageRefreshPausedByUser.value = false
  sceneTaskIds.value = {}
  sceneImageVersions.value = {}
  // Drop the previous run's "paused by user" marker so its presence in
  // localStorage doesn't shape this run's UI copy.
  try {
    localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
  } catch { /* ignore */ }

  clearImageReviewAutoRefreshTimer()
  resultText.value = ''
  currentWorkflowResponse.value = null
  currentWorkflowPayload.value = null
  selectingSceneId.value = ''
  refreshingImageReview.value = false
  sceneRefreshQueue.value = []
  sceneRefreshingId.value = ''
  reviewPlaceholders.value = []
  storyText.value = ''
  storyboardText.value = ''
  imagePromptsText.value = ''
  imageAssetsText.value = ''
  imageReviewText.value = ''
  videoPromptsText.value = ''
  narrationText.value = ''
  subtitlesText.value = ''
  renderPlanText.value = ''
  characterCandidatesText.value = ''
  characterManifestText.value = ''
  reviewAutoRefreshFiredOnce = false
  clearImageReviewAutoRefreshTimer()
  finalVideoText.value = ''
  finalVideoUrl.value = ''
  finalVideoRendering.value = false
  finalVideoRenderInFlight.value = false
  stepSummaries.value = []
  errorMessage.value = ''
  workflowStatusData.value = null
  userHasInteractedWithImages.value = false
  mockAudioIndexUrl.value = ''
  mockAudioSceneGroups.value = []
  mockAudioDirectoryText.value = ''
  mockAudioSegmentTextMap.value = {}
  activeTab.value = 'review'

  const form = workflowForm.value
  console.log('RENDER MODE SENT', form.renderMode)
  console.log('AUDIO ENABLED SENT', form.audioEnabled)
  // ---- characters: manual override (when enabled) ----
  const manualCharacters: StructuredCharacterInput[] = form.structuredCharactersEnabled
    ? [
        ...(form.primaryCharacterDisplayName.trim() || form.primaryCharacterSpecies.trim()
          ? [
              {
                display_name: form.primaryCharacterDisplayName.trim(),
                species: form.primaryCharacterSpecies.trim(),
                role_type: 'primary' as const,
                visual_traits: form.primaryCharacterVisualTraits.trim(),
                forbidden_traits: form.primaryCharacterForbiddenTraits.trim(),
              },
            ]
          : []),
        ...(form.secondaryCharacterDisplayName.trim() || form.secondaryCharacterSpecies.trim()
          ? [
              {
                display_name: form.secondaryCharacterDisplayName.trim(),
                species: form.secondaryCharacterSpecies.trim(),
                role_type: 'secondary' as const,
                visual_traits: form.secondaryCharacterVisualTraits.trim(),
                forbidden_traits: form.secondaryCharacterForbiddenTraits.trim(),
              },
            ]
          : []),
      ]
    : []

  // ---- characters: auto derive from topic (default path) ----
  function inferPrimaryFromTopic(topic: string): StructuredCharacterInput[] {
    const t = (topic || '').trim()
    if (!t) return []
    const lower = t.toLowerCase()

    // 先覆盖高频：猫/狗/兔/龟（足够验证“换动物也稳”）
    const hitCat = t.includes('猫') || lower.includes('cat') || lower.includes('kitten')
    if (hitCat) {
      return [
        {
          display_name: '小猫',
          species: 'cat',
          role_type: 'primary',
          visual_traits:
            'domestic kitten, round cat face, short muzzle, moderate-sized triangular ears, visible whiskers, cat-like paws, long cat tail',
          forbidden_traits:
            'fox snout, fennec fox ears, raccoon mask, mouse face, rabbit ears, turtle shell',
        },
      ]
    }

    const hitDog = t.includes('狗') || lower.includes('dog') || lower.includes('puppy')
    if (hitDog) {
      return [
        {
          display_name: '小狗',
          species: 'dog',
          role_type: 'primary',
          visual_traits:
            'cute puppy, round friendly face, moderate ears, dog-like paws, dog tail',
          forbidden_traits:
            'fox snout, fennec fox ears, raccoon mask, mouse face, rabbit ears, turtle shell',
        },
      ]
    }

    const hitRabbit = t.includes('兔') || lower.includes('rabbit') || lower.includes('bunny')
    if (hitRabbit) {
      return [
        {
          display_name: '小兔子',
          species: 'rabbit',
          role_type: 'primary',
          visual_traits: 'cute bunny, long rabbit ears, round face, fluffy fur',
          forbidden_traits:
            'cat ears, fox snout, turtle shell, raccoon mask, mouse face',
        },
      ]
    }

    const hitTurtle = t.includes('乌龟') || t.includes('龟') || lower.includes('turtle')
    if (hitTurtle) {
      return [
        {
          display_name: '小乌龟',
          species: 'turtle',
          role_type: 'primary',
          visual_traits: 'cute turtle, round shell, short legs',
          forbidden_traits:
            'rabbit ears, cat ears, fox snout, raccoon mask, mouse face',
        },
      ]
    }

    return []
  }

  const autoCharacters: StructuredCharacterInput[] =
    manualCharacters.length > 0 ? [] : inferPrimaryFromTopic(form.topic)

  const finalCharacters: StructuredCharacterInput[] =
    manualCharacters.length > 0 ? manualCharacters : autoCharacters

  // 关键：是否启用结构化角色，不再由 checkbox 决定
  const enableStructuredCharacters = finalCharacters.length > 0

  const primaryCharacter =
    finalCharacters.find((item) => item.role_type === 'primary') || finalCharacters[0]

  const secondaryCharacter = finalCharacters.find(
    (item) => item.role_type === 'secondary',
  )

  const mainCharacterDisplay = String(primaryCharacter?.display_name || '').trim()
  const mainCharacterSpecies = String(primaryCharacter?.species || '').trim()
  const secondaryCharacterDisplay = String(secondaryCharacter?.display_name || '').trim()
  const secondaryCharacterSpecies = String(secondaryCharacter?.species || '').trim()

  const sessionId =
    form.sessionId.trim() || createStudioSessionId()

  const inputPayload: Record<string, unknown> = {
    topic: form.topic.trim(),
    audience: form.audience,
    tone: form.tone,
    visual_style: form.visualStyle,
    character_style: form.characterStyle,
    voice_style: form.voiceStyle,
    voiceover_enabled: form.audioEnabled ? form.voiceoverEnabled : false,
    voice_mode: form.voiceMode,
    duration_sec: form.durationSec,
    language: form.language,
    subtitle_enabled: form.subtitleEnabled,
    video_provider: form.videoProvider,
    output_mode: form.outputMode,
    render_mode: form.renderMode,
    audio_enabled: form.audioEnabled,
    quality_tier: form.qualityTier || 'quality',
  }

  // Single-narrator mode: send `speaker_profiles.narrator` derived from
  // the "旁白配音" dropdown so the user's pick controls the narrator
  // voice. Previously only `voice_style` (the now-hidden "配音风格"
  // dropdown) reached the backend in single mode, making the "旁白配音"
  // dropdown a no-op — users picked 温暖男声 there and heard 温柔女声
  // because the backend's `speaker_profiles.narrator` was filling in
  // from `voice_style` (or its schema default before #133). Now
  // 旁白配音 is the single source of truth for single-mode narration.
  if (form.voiceMode === 'single') {
    inputPayload.speaker_profiles = {
      narrator: form.narratorVoiceStyle,
    }
  }

  if (form.voiceMode === 'multi') {
    inputPayload.speaker_profiles = {
      narrator: form.narratorVoiceStyle,
      mother: form.motherVoiceStyle,
      child: form.childVoiceStyle,
    }
  }

  // Voice-mode-specific: only character mode needs per-character voice
  // assignments. This payload is genuinely voice-domain.
  if (form.voiceMode === 'character') {
    inputPayload.character_speaker_profiles = {
      narrator: form.narratorVoiceStyle,
      main_character: form.childVoiceStyle,
      secondary_character: form.motherVoiceStyle,
    }
  }

  // Character-identity payload — flows in EVERY voice mode. Previously
  // these fields were nested inside the `voiceMode === 'character'`
  // block, which coupled "who the character is" with "how each character
  // is voiced". Wrong: character identity (species, name, visual traits)
  // governs story generation + image-prompt anchoring regardless of
  // voice configuration. A single-voice narrator can still tell a story
  // about 波波 the 小海豹 with the structured visual lock attached.
  if (enableStructuredCharacters) {
    inputPayload.structured_characters_enabled = true
    inputPayload.characters = finalCharacters
  }

  if (mainCharacterDisplay || mainCharacterSpecies) {
    inputPayload.main_character = mainCharacterSpecies || mainCharacterDisplay
    inputPayload.main_character_display = mainCharacterDisplay
    inputPayload.main_character_species = mainCharacterSpecies
  }

  if (secondaryCharacterDisplay || secondaryCharacterSpecies) {
    inputPayload.secondary_character =
      secondaryCharacterSpecies || secondaryCharacterDisplay
    inputPayload.secondary_character_display = secondaryCharacterDisplay
    inputPayload.secondary_character_species = secondaryCharacterSpecies
  }

  // Dev-mode opt-in: keeps the story-step template fallback reachable
  // so the downstream pipeline (storyboard / images / audio / video)
  // can still be exercised when the LLM endpoint is unreachable. In
  // production runs (devMode=false) the backend raises and the FE
  // shows the failure banner with a retry CTA. Dev-only runs still
  // get a `generation_source=template_fallback` chip in the dev
  // diagnostics panel so it's never confused with real AI output.
  if (devMode.value) {
    inputPayload.dev_mode = true
  }

  const stepsSet = new Set(selectedSteps.value)

  if (form.subtitleEnabled) {
    stepsSet.add('subtitles')
  }

  const workflowId = createStoryWorkflowId()

  const payload = {
    workflow_id: workflowId,
    session_id: sessionId,
    input: inputPayload,
    steps: Array.from(stepsSet).map((name) => ({ name })),
  }
  currentWorkflowPayload.value = payload as WorkflowRunPayload
  invalidateWorkflowLifecycleRecovery()
  clearFinalVideoRenderMarker()
  localStorage.removeItem(STORAGE_KEY_RUN)
  persistActiveWorkflowIdentity(workflowId)
  localStorage.setItem(STORAGE_KEY_PAYLOAD, JSON.stringify(payload))
  // New workflow starts clean — any prior "user cancelled image refresh"
  // marker shouldn't haunt this fresh run.
  clearImageRefreshCancelledMarker()

  // ✅ 点击 Run 立刻给 UI 反馈（跨 tab 都能感知）
  loading.value = true
  activeWorkflowId.value = workflowId
  cancelRequested.value = false
  workflowRunElapsedSec.value = 0
  workflowStatusData.value = {
    workflow_id: workflowId,
    status: 'processing',
    current_step: stepsSet.values().next().value || '',
    current_step_index: 1,
    completed_steps: 0,
    total_steps: stepsSet.size,
    progress_percent: 0,
  }
  errorMessage.value = ''
  finalVideoText.value = ''
  finalVideoUrl.value = ''
  finalVideoRenderInFlight.value = false
  finalVideoRendering.value = false
  // Clear any stale per-scene retry state from the previous workflow run.
  // Without this, the top progress bar and FinalVideoPanel keep showing
  // "正在为 scene_XX 重新生成候选图" on top of the new initial workflow.
  sceneRefreshingId.value = ''
  sceneImageVersions.value = {}

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
      workflowForm.value.sessionId = data.session_id
    }

    applyWorkflowResponse(data)

    if (!data.outputs && typeof data.workflow_id === 'string' && data.workflow_id.trim()) {
      const asyncData = await waitForAsyncWorkflowOutputs(data.workflow_id)
      if (asyncData) {
        applyWorkflowResponse(asyncData)
      }
    }

    scheduleImageReviewAutoRefreshIfNeeded()

  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loading.value = false
    activeWorkflowId.value = ''
    cancelRequested.value = false
  }
}
</script>

<template>
  <StudioLayout v-model="activeTab" :tabs="studioTabs" :dev-mode="devMode">
    <template #progress>
      <StudioProgress
        :visible="
          workflowIsProcessing ||
          refreshingImageReview ||
          awaitingManualRender ||
          finalVideoRenderInFlight ||
          Boolean(sceneRefreshingId) ||
          hasImageFailures
        "
        :percent="workflowProgressSummary.overallPercent ?? 0"
        :indeterminate="workflowProgressSummary.indeterminate"
        :label="
          cancelRequestedAny
            ? cancellingLabel
            : (workflowProgressSummary.stageLabel || workflowRunStatusMessage)
        "
        :cancellable="phaseCancellable && !awaitingManualRender && !singleSceneRetryActive && !hasImageFailures"
        :cancel-requested="cancelRequestedAny"
        @cancel="cancelActivePhase"
      />
    </template>
    <div class="studio-tab-content">
    <section v-if="activeTab === 'run'" class="studio-home-grid">
      <StudioCreatePanel
        :loading="loading || refreshingImageReview || finalVideoRenderInFlight || awaitingManualRender || Boolean(sceneRefreshingId)"
        :cancel-requested="cancelRequestedAny"
      >
        <WorkflowRunPanel
          :loading="loading || refreshingImageReview || finalVideoRenderInFlight || awaitingManualRender || Boolean(sceneRefreshingId)"
          :can-submit="canSubmit"
          :error-message="errorMessage"
          :form-state="workflowForm"
          :selected-steps="selectedSteps"
          :step-options="STEP_OPTIONS"
          :cancellable="phaseCancellable"
          :cancel-requested="cancelRequestedAny"
          :status-label="workflowRunStatusMessage || (refreshingImageReview ? reviewRefreshProgress.text : '')"
          :elapsed-sec="workflowRunElapsedSec"
          :completed-steps="workflowStatusData?.completed_steps ?? 0"
          :current-step-index="workflowStatusData?.current_step_index ?? 0"
          :total-steps="workflowStatusData?.total_steps ?? 0"
          @update:form-state="onUpdateFormState"
          @update:selected-steps="onUpdateSelectedSteps"
          @run="runWorkflow"
          @cancel="cancelActivePhase"
        />
      </StudioCreatePanel>

      <StudioPreviewPanel
        :final-video-url="finalVideoUrl"
        :video-preview-url="videoPreviewUrl"
        :video-player-key="videoPreviewPlayerKey"
        :video-load-state="videoPreviewLoadState"
        :video-status-text="videoPreviewStatusText"
        :recent-video-urls="recentFinalVideoUrls"
        :recent-video-metadata="recentVideoMetadata"
        :render-in-flight="finalVideoRenderInFlight"
        :is-processing="workflowIsProcessing"
        :refreshing-images="refreshingImageReview"
        :awaiting-manual-render="awaitingManualRender"
        :has-image-failures="hasImageFailures"
        :scene-refreshing-id="sceneRefreshingId"
        :status-label="
          singleSceneRetryActive
            ? `正在重新生成 ${sceneRefreshingId}`
            : (workflowRunStatusMessage || (refreshingImageReview ? reviewRefreshProgress.text : ''))
        "
        :completed-steps="workflowStatusData?.completed_steps ?? 0"
        :total-steps="workflowStatusData?.total_steps ?? 0"
        :cancellable="phaseCancellable"
        :cancel-requested="cancelRequestedAny"
        :example-topics="EXAMPLE_TOPICS"
        @set-topic="setExampleTopic"
        @cancel="cancelActivePhase"
        @delete-video="requestDeleteRecentVideo"
        @video-ready="markVideoPreviewReady"
        @video-error="handleVideoPreviewError"
        @reload-video="reloadVideoPreviewManually"
      />
    </section>
      <section v-if="activeTab === 'review'" class="review-layout">
        <template v-if="hasReviewContent || workflowIsProcessing || refreshingImageReview || finalVideoRenderInFlight">
          <!-- Video card -->
          <div class="glass-card review-video-card animate-fade-in">
            <div class="review-section-header">
              <span class="review-section-icon" aria-hidden="true">▶</span>
              <span class="review-section-title">最终视频</span>
              <span v-if="finalVideoRenderInFlight" class="badge badge-arc" style="font-size:0.6rem;">渲染中</span>
              <span v-else-if="finalVideoUrl && videoPreviewLoadState === 'ready'" class="badge badge-ok" style="font-size:0.6rem;">已完成</span>
              <span v-else-if="finalVideoUrl && videoPreviewLoadState === 'failed'" class="badge badge-warn" style="font-size:0.6rem;">加载失败</span>
              <span v-else-if="finalVideoUrl" class="badge badge-arc" style="font-size:0.6rem;">加载中</span>
              <span v-if="finalVideoAudioEnabled === false" class="badge badge-warn" style="font-size:0.6rem;">无声</span>
              <!-- Manual render CTA is rendered inside `FinalVideoPanel`'s
                   body so it sits next to the "等待用户触发渲染" copy and
                   the placeholder progress bar (where the user is
                   actually looking). Keeping it in the panel body also
                   means the styling stays in one place and uses the
                   active theme's gradient (--arc-400 / --prism-400). -->
            </div>
            <div class="review-video-body">
              <FinalVideoPanel
                :final-video-url="finalVideoUrl"
                :video-preview-url="videoPreviewUrl"
                :video-player-key="videoPreviewPlayerKey"
                :video-load-state="videoPreviewLoadState"
                :video-status-text="videoPreviewStatusText"
                :final-video-text="finalVideoText"
                :workflow-response="currentWorkflowResponse"
                :render-in-flight="finalVideoRenderInFlight"
                :loading="workflowIsProcessing || refreshingImageReview || finalVideoRenderInFlight || Boolean(sceneRefreshingId)"
                :refreshing-images="refreshingImageReview"
                :cancel-requested="cancelRequested"
                :paused-by-user="imageRefreshPausedByUser"
                :error-message="errorMessage"
                :workflow-status-message="workflowRunStatusMessage"
                :workflow-status-progress="workflowStatusProgress"
                :image-generation-summary="imageGenerationSummary"
                :workflow-progress-summary="workflowProgressSummary"
                :render-mode="workflowForm.renderMode"
                :scene-refreshing-id="sceneRefreshingId"
                @render="renderFinalVideoIfReady(currentWorkflowResponse || {})"
                @video-ready="markVideoPreviewReady"
                @video-error="handleVideoPreviewError"
                @reload-video="reloadVideoPreviewManually"
                @discard="discardCurrentDraft"
                :show-render-button="workflowForm.renderMode === 'auto'"
              />
              <div v-if="workflowForm.renderMode === 'manual' && !isWorkflowReadyForRender && !hasImageFailures" class="manual-hint" style="text-align:center;padding:0.5rem 0 0;">
                等待候选图与音频生成完成…
              </div>
            </div>
          </div>

          <!-- Deferred banner: shown for fresh deferred state AND for partial
               paused state (after the user cancelled mid-flight). Keeps the
               "继续生成" affordance visible so the user isn't stuck looking at
               a static partial-progress placeholder with no way forward.
               "放弃当前生成" is the explicit exit — wipes the draft entirely
               so the user isn't forced to either resume or start a new topic. -->
          <div
            v-if="canResumeImageRefresh"
            class="deferred-generate-banner"
          >
            <span>{{ deferredBannerLabel }}</span>
            <div class="deferred-actions">
              <button class="deferred-discard-btn" @click="discardCurrentDraft">放弃当前生成</button>
              <button class="deferred-generate-btn" @click="triggerManualImageRefresh()">{{ deferredBannerCta }}</button>
            </div>
          </div>

          <!-- Image review + results -->
          <template v-if="hasReviewContent">
            <div class="glass-card review-images-card animate-fade-in">
              <div class="review-section-header">
                <span class="review-section-icon" aria-hidden="true">◈</span>
                <span class="review-section-title">画面审核</span>
                <span
                  v-if="refreshingImageReview || cancelRequested"
                  class="badge badge-arc"
                  style="font-size:0.6rem;"
                >{{ cancelRequested ? '取消中' : '生成中' }}</span>
              </div>
              <div class="review-images-body">
                <InteractiveImageReview
                  :items="imageReviewItems"
                  :story-text="storyText"
                  :placeholders="reviewPlaceholders"
                  :api-base-url="apiBaseUrl"
                  :loading="loading || refreshingImageReview || Boolean(sceneRefreshingId)"
                  :selecting-scene-id="selectingSceneId || sceneRefreshingId"
                  :progress-text="cancelRequested ? cancellingLabel : reviewRefreshProgress.text"
                  :progress-percent="reviewRefreshProgress.percent"
                  :can-cancel="refreshingImageReview"
                  :cancel-requested="cancelRequested"
                  :cancellable="Boolean(activeWorkflowId)"
                  :video-generated="Boolean(finalVideoUrl)"
                  :render-mode="workflowForm.renderMode"
                  :scene-image-versions="sceneImageVersions"
                  :scene-narration-map="sceneNarrationMap"
                  @select-asset="({ sceneId, assetRef }) => selectImageAsset(sceneId, assetRef)"
                  @retry-scene="retryImageReviewScene"
                  @cancel-refresh="cancelImageReviewRefresh"
                  @cancel-workflow="cancelWorkflow"
                />
              </div>
            </div>
            <WorkflowResultsPanel
              :story-text="storyText"
              :story-output-text="storyOutputText"
              :storyboard-text="storyboardText"
              :image-prompts-text="imagePromptsText"
              :image-assets-text="imageAssetsText"
              :image-review-text="imageReviewText"
              :video-prompts-text="videoPromptsText"
              :narration-text="narrationText"
              :subtitles-text="subtitlesText"
              :render-plan-text="renderPlanText"
              :character-candidates-text="characterCandidatesText"
              :character-manifest-text="characterManifestText"
            />

            <!-- 配音素材 — per-scene TTS asset inspection. Lives in
                 the Review tab because it's "check the output of the
                 last workflow", same semantic family as the image
                 review above. (Previously lived under 素材库 / 灵感
                 参考; that tab's role is now "creation starters",
                 which doesn't fit a results inspector.) Only renders
                 when the current workflow actually produced audio
                 segments — hidden cleanly when not applicable. -->
            <details
              v-if="mockAudioIndexUrl || mockAudioSceneGroups.length > 0 || mockAudioDirectoryText"
              class="glass-card review-audio-card animate-fade-in"
            >
              <summary class="review-audio-summary">
                <span class="review-section-icon" aria-hidden="true">▤</span>
                <span class="review-section-title">配音素材</span>
                <span class="review-audio-summary-count">
                  {{ mockAudioSceneGroups.length }} 个场景 ·
                  {{ mockAudioSceneGroups.reduce((n, g) => n + ((g.assets || []).length), 0) }} 段音频
                </span>
                <span class="review-audio-summary-chevron" aria-hidden="true">▸</span>
              </summary>

              <div v-if="mockAudioSceneGroups.length > 0" class="review-audio-scenes">
                <article
                  v-for="group in mockAudioSceneGroups"
                  :key="group.scene_id || 'unknown-scene'"
                  class="review-audio-scene"
                >
                  <header class="review-audio-scene-head">
                    <div class="review-audio-scene-title-block">
                      <strong>{{ sceneDisplayName(group.scene_id) }}</strong>
                      <span
                        v-if="sceneTitleMap[group.scene_id || '']"
                        class="review-audio-scene-title"
                      >· {{ sceneTitleMap[group.scene_id || ''] }}</span>
                    </div>
                    <span class="review-audio-count">{{ (group.assets || []).length }} 个片段</span>
                  </header>
                  <ul class="review-audio-asset-list">
                    <li
                      v-for="(asset, index) in group.assets || []"
                      :key="asset.asset_id || asset.segment_id || asset.file_name"
                      class="review-audio-asset-item"
                    >
                      <!-- Decorative waveform glyph — visual landmark so each
                           segment row has a left-edge anchor instead of
                           starting with raw text. Pure CSS bars, no SVG. -->
                      <div class="review-audio-wave" aria-hidden="true">
                        <span></span><span></span><span></span><span></span>
                      </div>
                      <div class="review-audio-asset-main">
                        <div class="review-audio-asset-row">
                          <strong>{{ audioAssetTitle(index) }}</strong>
                          <span
                            class="review-audio-speaker-pill"
                            :class="`review-audio-speaker-pill--${(asset.speaker || 'unknown').toLowerCase()}`"
                          >{{ asset.speaker || 'unknown' }}</span>
                          <span class="review-audio-duration">
                            {{ formatAudioDuration(asset.duration_estimate_sec) }}
                          </span>
                        </div>
                        <!-- Spoken text — pulled from outputs.narration.segments
                             matched by index within the scene. Mirrors the
                             image card's "画面内容" so the audio side carries
                             the same semantic weight: each segment shows
                             what it's saying, not just file metadata. -->
                        <p
                          v-if="(mockAudioSegmentTextMap[group.scene_id || ''] || [])[index]"
                          class="review-audio-text"
                        >
                          {{ (mockAudioSegmentTextMap[group.scene_id || ''] || [])[index] }}
                        </p>
                      </div>
                      <a
                        v-if="asset.public_url"
                        class="review-audio-play"
                        :href="`${apiBaseUrl}${asset.public_url}`"
                        target="_blank"
                        rel="noreferrer"
                        :title="`播放 ${audioAssetTitle(index)}`"
                        aria-label="打开音频"
                      >
                        <span aria-hidden="true">▶</span>
                      </a>
                    </li>
                  </ul>
                </article>
              </div>

              <details v-if="mockAudioIndexUrl || mockAudioDirectoryText" class="review-audio-details">
                <summary>开发者信息</summary>
                <div v-if="mockAudioIndexUrl" class="review-audio-dev-row">
                  <span class="review-audio-dev-label">索引文件</span>
                  <a
                    class="review-audio-play-inline"
                    :href="`${apiBaseUrl}${mockAudioIndexUrl}`"
                    target="_blank"
                    rel="noreferrer"
                  >
                    打开 index.json ↗
                  </a>
                  <code>{{ mockAudioIndexUrl }}</code>
                </div>
                <pre v-if="mockAudioDirectoryText" class="light-result compact-result">{{ mockAudioDirectoryText }}</pre>
              </details>
            </details>
          </template>
        </template>

        <div v-else class="review-empty-state glass-card animate-fade-in">
          <div class="review-empty-icon" aria-hidden="true">◈</div>
          <div class="review-empty-title">尚无画面内容</div>
          <p class="review-empty-desc">{{ reviewEmptyStateText }}</p>
        </div>
      </section>
      <section v-if="activeTab === 'assets'">
        <InspirationLibraryPanel @apply="onApplyInspiration" />
      </section>
      <section v-if="activeTab === 'debug'" class="debug-layout">
        <div v-if="!hasDebugContent" class="review-empty-state glass-card animate-fade-in">
          <div class="review-empty-icon" aria-hidden="true">⚙</div>
          <div class="review-empty-title">尚无诊断数据</div>
          <p class="review-empty-desc">请先运行一次 Workflow，生成 Steps Summary 和原始 JSON 调试信息。</p>
        </div>

        <template v-else>
          <!-- Quick-scan summary: IDs to grep server logs with + LLM
               source so you can tell at a glance whether you're looking
               at a real LLM run or a template fallback. -->
          <div class="glass-card animate-fade-in">
            <div class="debug-section-header">
              <div class="debug-section-title-row">
                <span class="review-section-icon" aria-hidden="true">⚠</span>
                <span class="review-section-title">Developer Diagnostics</span>
                <button class="btn-ghost debug-copy-btn" @click="copyDiagSummary">
                  {{ diagSummaryCopied ? '✓ 已复制' : '复制摘要' }}
                </button>
              </div>
              <p class="debug-help">用 workflow_id / run_id 跟 server 日志对账；用 generation_source 判断本次故事是真 LLM 还是兜底模板。</p>
            </div>
            <div class="debug-diag-body">
              <DiagnosticsPanel
                :workflow-id="currentWorkflowResponse?.workflow_id"
                :run-id="currentWorkflowResponse?.run_id"
                :session-id="currentWorkflowResponse?.session_id"
                :generation-source="storyDiagnostics?.generationSource"
                :fallback-reason="storyDiagnostics?.fallbackReason !== 'None' ? storyDiagnostics?.fallbackReason : undefined"
              />
            </div>
          </div>

          <div v-if="stepSummaries.length > 0" class="glass-card debug-steps-card animate-fade-in">
            <div class="debug-section-header">
              <div class="debug-section-title-row">
                <span class="review-section-icon" aria-hidden="true">≡</span>
                <span class="review-section-title">Steps Summary</span>
                <button class="btn-ghost debug-copy-btn" @click="copyDiagnosticsJson">
                  {{ diagCopied ? '✓ 已复制摘要' : '复制全部摘要' }}
                </button>
              </div>
              <p class="debug-help">各步执行状态 + 输出预览。点击单步展开查看截断后的 JSON；右侧 ⧉ 复制该步完整 preview 文本。耗时暂未由后端记录。</p>
            </div>
            <div class="debug-steps-body">
              <details v-for="item in stepSummaries" :key="item.name" class="summary-item">
                <summary class="summary-head">
                  <span class="summary-chevron" aria-hidden="true">▸</span>
                  <strong>{{ item.name }}</strong>
                  <span :class="['summary-status-badge', `status-${(item.status || '').toLowerCase()}`]">{{ item.status }}</span>
                  <span class="summary-size">{{ formatPreviewSize(item.preview.length) }}</span>
                  <button class="btn-ghost summary-copy-btn"
                          :title="`复制 ${item.name} preview`"
                          @click.prevent.stop="copyStepPreview(item)">
                    {{ copiedStepName === item.name ? '✓' : '⧉' }}
                  </button>
                </summary>
                <pre class="summary-preview">{{ item.preview }}</pre>
              </details>
            </div>
          </div>

          <!-- Full response JSON. Collapsed by default — it's the entire
               workflow output (often >100KB) and was the runaway that
               made this tab scroll for ~20 screens. Now bounded with
               internal scroll + copy. -->
          <div v-if="resultText" class="glass-card animate-fade-in">
            <details class="debug-raw-details">
              <summary class="debug-section-header debug-raw-summary">
                <div class="debug-section-title-row">
                  <span class="review-section-icon debug-raw-chevron" aria-hidden="true">▸</span>
                  <span class="review-section-title">Raw JSON</span>
                  <button class="btn-ghost debug-copy-btn" @click.prevent.stop="copyRawJson">
                    {{ rawJsonCopied ? '✓ 已复制' : '复制完整 JSON' }}
                  </button>
                </div>
                <p class="debug-help">完整 workflow response — story / storyboard / image_prompts / image_assets / audio / render_plan。默认折叠。</p>
              </summary>
              <div class="debug-raw-body">
                <pre class="result">{{ resultText }}</pre>
              </div>
            </details>
          </div>
        </template>
    </section>
    </div>
  </StudioLayout>

  <!-- Themed confirm dialog for "放弃当前生成". Teleported to body so the
       backdrop covers the whole viewport, including sidebar / progress bar.
       Tokens-only — adapts to gold/blue/purple/pearl automatically. -->
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="showDiscardConfirm"
        class="confirm-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="cancelDiscardDialog"
      >
        <div class="confirm-dialog">
          <h3 class="confirm-title">放弃当前生成</h3>
          <p class="confirm-message">已生成的候选图、故事内容将不再可用；表单输入和历史视频会保留。</p>
          <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-ghost" @click="cancelDiscardDialog">取消</button>
            <button class="confirm-btn confirm-btn-primary" @click="performDiscardCurrentDraft">放弃</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Confirm dialog for "开始创作" when the current run has unresolved
       image failures. Catches the easy misclick where the user thinks
       开始创作 will repair the failure (it won't — the right path is
       重试该场景 in 画面审核). Confirmed click routes to executeRunWorkflow
       which actually discards the prior state and runs a new pipeline. -->
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="showStartRunConfirm"
        class="confirm-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="cancelStartRunDialog"
      >
        <div class="confirm-dialog">
          <h3 class="confirm-title">开始新一轮创作？</h3>
          <p class="confirm-message">
            当前轮还有候选图失败未处理。开始新创作会丢弃当前的故事、分镜与候选图。<br>
            想保留当前进度？请在「画面审核」点击对应场景的「重试该场景」。
          </p>
          <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-ghost" @click="cancelStartRunDialog">取消</button>
            <button class="confirm-btn confirm-btn-primary" @click="confirmStartRunDiscardingFailures">
              丢弃并新建
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="deleteVideoTarget"
        class="confirm-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="cancelDeleteRecentVideo"
      >
        <div class="confirm-dialog">
          <h3 class="confirm-title">从历史记录中删除该视频？</h3>
          <p class="confirm-message">这只会移除本地历史记录，不会删除已生成的文件。</p>
          <div class="confirm-actions">
            <button class="confirm-btn confirm-btn-ghost" @click="cancelDeleteRecentVideo">取消</button>
            <button class="confirm-btn confirm-btn-primary" @click="performDeleteRecentVideo">删除</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Topic-changed-but-characters-stale warning. Fires 1s after the
       user stops editing the topic IF structured character fields are
       populated AND the new topic's opening differs significantly
       from the snapshot. Either action updates the snapshot so we
       don't keep nagging on this same edit. Own <Transition> wrapper
       because Vue's <Transition> requires exactly one child. -->
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="topicChangeWarningOpen"
        class="confirm-overlay"
        role="dialog"
        aria-modal="true"
        @click.self="keepCharacterFieldsAfterTopicChange"
      >
        <div class="confirm-dialog">
          <h3 class="confirm-title">主题变了，要清空已填的角色配置吗？</h3>
          <p class="confirm-message">
            你刚修改了故事主题，但角色名 / 物种 / 外观这些字段还停留在之前的设定。
            如果新主题里的主角跟原来不同（比如从"小海豹"换成"小兔子"），
            建议清空让系统按新主题自动推断；如果只是润色文字、主角不变，可以保留。
          </p>
          <div class="confirm-actions">
            <button
              class="confirm-btn confirm-btn-ghost"
              @click="keepCharacterFieldsAfterTopicChange"
            >保留角色</button>
            <button
              class="confirm-btn confirm-btn-primary"
              @click="clearCharacterFieldsAfterTopicChange"
            >清空角色</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Dev mode toggle toast — small bottom-centred chip that confirms
       the shortcut fired and tells the user which state they're now
       in. Auto-fades after 1.5s. Lives outside the studio layout so
       it isn't clipped by sidebar/header overflow. -->
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div v-if="devModeToast" class="dev-mode-toast" role="status">
        {{ devModeToast }}
      </div>
    </Transition>
  </Teleport>

  <!-- Generic non-blocking notice toast — top-center, prominent, click
       to dismiss. Used for outcomes that the user should clearly know
       about but that don't change the UI state machine (e.g. 重新生成
       failed but original image preserved). -->
  <Teleport to="body">
    <Transition name="confirm-fade">
      <div
        v-if="inlineNotice"
        class="inline-notice"
        :class="`inline-notice--${inlineNotice.tone}`"
        role="alert"
        @click="dismissInlineNotice"
      >
        <span class="inline-notice__icon" aria-hidden="true">
          {{ inlineNotice.tone === 'warn' ? '⚠' : 'ℹ' }}
        </span>
        <span class="inline-notice__text">{{ inlineNotice.text }}</span>
        <button
          type="button"
          class="inline-notice__close"
          aria-label="关闭提示"
          @click.stop="dismissInlineNotice"
        >×</button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
/* ── Homepage 2-column grid ── */
.studio-home-grid {
  display: grid;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
  gap: 1.5rem;
  align-items: start;
}

.studio-home-grid > * {
  min-width: 0;
  max-width: 100%;
}

/* Right column (preview panel) stays visible while form scrolls.
   align-self:start + height:auto so panel fits content instead of
   stretching to viewport — avoids huge whitespace below short content. */
.studio-home-grid > :nth-child(2) {
  position: sticky;
  top: 1rem;
  align-self: start;
  max-height: calc(100vh - 2rem);
  display: flex;
  flex-direction: column;
}

@media (max-width: 960px) {
  .studio-home-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .studio-home-grid > :nth-child(2) {
    position: static;
    max-height: none;
  }
}

/* ── Review tab ── */
.review-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.review-video-card,
.review-images-card,
.review-audio-card {
  overflow: hidden;
}

@media (max-width: 768px) {
  .studio-home-grid {
    gap: 1rem;
  }

  .review-layout {
    gap: 1rem;
  }

  .review-audio-summary {
    align-items: flex-start;
    flex-wrap: wrap;
    padding: 0.75rem 1rem;
  }

  .review-audio-summary-count {
    width: 100%;
    margin-left: 1.5rem;
    white-space: normal;
  }

  .review-audio-scenes {
    padding: 0.875rem 1rem 1rem;
  }
}

/* 配音素材 — collapsible card. Closed by default so it doesn't
   dominate the Review tab; expand to inspect TTS output per scene.
   Inner styling drops the dev-tool "wall of text" look: speaker
   pills, mini waveform glyph, circular play button. */
.review-audio-card {
  display: block;
}
.review-audio-card[open] .review-audio-summary-chevron {
  transform: rotate(90deg);
}
.review-audio-summary {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  padding: 0.875rem 1.25rem;
  cursor: pointer;
  list-style: none;
  border-bottom: 1px solid transparent;
  background: linear-gradient(90deg, rgba(245,158,11,0.05) 0%, transparent 60%);
  transition: border-color 0.18s ease, background 0.18s ease;
}
.review-audio-summary::-webkit-details-marker { display: none; }
.review-audio-card[open] .review-audio-summary {
  border-bottom-color: rgba(245,158,11,0.12);
}
.review-audio-summary-count {
  margin-left: auto;
  font-size: 0.6875rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.review-audio-summary-chevron {
  color: var(--arc-300);
  font-size: 0.6875rem;
  transition: transform 0.18s ease;
}

.review-audio-scenes {
  padding: 1rem 1.25rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.review-audio-scene {
  padding: 0.875rem 1rem;
  border-radius: 12px;
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
}
.review-audio-scene-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 0.75rem;
}
.review-audio-scene-head strong {
  font-size: 0.875rem;
  color: var(--text-primary);
  letter-spacing: 0.01em;
}
.review-audio-scene-title-block {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}
.review-audio-scene-title {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  font-weight: 500;
}
.review-audio-count {
  font-size: 0.6875rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

.review-audio-asset-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.review-audio-asset-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border-subtle);
}
.review-audio-asset-item:last-child { border-bottom: 0; }

/* Mini waveform — decorative left-edge anchor. 4 vertical bars with
   alternating heights, animated on hover so each segment row reads
   as an "audio thing", not just text. */
.review-audio-wave {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-top: 4px;
  height: 14px;
}
.review-audio-wave span {
  width: 2px;
  background: var(--arc-300);
  border-radius: 1px;
  opacity: 0.55;
  transition: opacity 0.18s ease;
}
.review-audio-wave span:nth-child(1) { height: 30%; }
.review-audio-wave span:nth-child(2) { height: 75%; }
.review-audio-wave span:nth-child(3) { height: 50%; }
.review-audio-wave span:nth-child(4) { height: 90%; }
.review-audio-asset-item:hover .review-audio-wave span { opacity: 1; }

.review-audio-asset-main {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}
.review-audio-asset-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.review-audio-asset-row strong {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-secondary);
}

/* Speaker pills — same shape, different tint per speaker so the
   reader can scan "who's talking" without reading the label. Fallback
   for unknown roles is a neutral pill. */
.review-audio-speaker-pill {
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  background: var(--surface-overlay-strong);
  color: var(--text-secondary);
}
.review-audio-speaker-pill--narrator {
  color: color-mix(in srgb, var(--arc-200) 90%, var(--text-primary));
  border-color: color-mix(in srgb, var(--arc-300) 36%, transparent);
  background: color-mix(in srgb, var(--arc-300) 14%, transparent);
}
.review-audio-speaker-pill--mother {
  color: #f5b8d8;
  border-color: rgba(244, 114, 182, 0.32);
  background: rgba(244, 114, 182, 0.10);
}
.review-audio-speaker-pill--child {
  color: #a7d8ff;
  border-color: rgba(96, 165, 250, 0.32);
  background: rgba(96, 165, 250, 0.10);
}

.review-audio-duration {
  font-size: 0.6875rem;
  color: var(--text-muted);
  margin-left: auto;
}

/* Spoken text — mirrors the image-card "画面内容" pattern. Slightly
   indented from the wave anchor so eye can naturally trace from the
   waveform → speaker pill → spoken line. */
.review-audio-text {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.65;
  color: var(--text-primary);
  letter-spacing: 0.01em;
}

/* Circular play button — replaces the wordy "打开音频 ↗" link.
   Visual landmark on the right; touching aria-label for screen readers. */
.review-audio-play {
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-300) 12%, transparent);
  color: var(--arc-300);
  font-size: 0.625rem;
  text-decoration: none;
  margin-top: 2px;
  transition: background 0.18s ease, border-color 0.18s ease, transform 0.12s ease;
}
.review-audio-play:hover {
  background: color-mix(in srgb, var(--arc-300) 26%, transparent);
  border-color: var(--arc-300);
}
.review-audio-play:active { transform: scale(0.94); }
.review-audio-play-inline {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--arc-300);
  text-decoration: none;
  margin-right: 8px;
}
.review-audio-play-inline:hover { color: var(--arc-200); }
.review-audio-details {
  padding: 0 1.25rem 1.25rem;
}
.review-audio-details summary {
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--arc-300);
  padding: 0.5rem 0;
}
.review-audio-dev-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0.3rem 0;
  font-size: 0.75rem;
}
.review-audio-dev-row code {
  font-size: 0.6875rem;
  color: var(--text-muted);
  background: var(--surface-overlay-soft);
  padding: 1px 6px;
  border-radius: 4px;
}
.review-audio-dev-label {
  font-weight: 600;
  color: var(--text-secondary);
  white-space: nowrap;
}

.review-section-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.25rem 0.75rem;
  border-bottom: 1px solid rgba(245,158,11,0.12);
  background: linear-gradient(90deg, rgba(245,158,11,0.05) 0%, transparent 60%);
}

.review-section-icon {
  background: linear-gradient(135deg, var(--arc-400), var(--prism-400));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-size: 0.875rem;
  line-height: 1;
}

.review-section-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text-primary);
  flex: 1;
  letter-spacing: 0.02em;
}

.review-render-btn {
  font-size: 0.75rem;
  padding: 0.375rem 0.875rem;
}

.review-video-body,
.review-images-body {
  padding: 1.25rem;
}

.review-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 280px;
  text-align: center;
  gap: 0.75rem;
  padding: 2rem;
}

.review-empty-icon {
  font-size: 2rem;
  color: var(--arc-400);
  opacity: 0.4;
}

.review-empty-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-secondary);
}

.review-empty-desc {
  font-size: 0.875rem;
  color: var(--text-muted);
  line-height: 1.7;
  max-width: 42ch;
  margin: 0;
}

/* ── Diagnostics tab ── */
.debug-layout {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.debug-steps-body {
  padding: 1rem 1.25rem;
}

/* Section header for the debug tab — title + action on row 1, explainer
   prose on row 2. Two rows avoids the overflow / truncation that happens
   when (icon + title + long Chinese help text + button) all fight for
   width on narrow viewports. */
.debug-section-header {
  padding: 0.75rem 1.25rem 0.5rem;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.debug-section-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.debug-section-title-row .review-section-title {
  flex: 1;
  min-width: 0;
}
.debug-help {
  margin: 0.35rem 0 0;
  padding-left: 1.5rem; /* aligns with title text past the icon */
  font-size: 0.72rem;
  color: var(--text-muted);
  font-weight: 400;
  line-height: 1.45;
}

.debug-copy-btn {
  font-size: 0.72rem;
  padding: 0.3rem 0.7rem;
  border-radius: 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Collapsible Raw-JSON section. <details>/<summary> default markers
   are hidden; the inline ▸ chevron rotates on open. */
.debug-raw-details > summary { list-style: none; cursor: pointer; user-select: none; }
.debug-raw-details > summary::-webkit-details-marker { display: none; }
.debug-raw-chevron {
  color: var(--text-muted);
  transition: transform 180ms ease;
  display: inline-block;
  font-size: 0.7rem;
}
.debug-raw-details[open] > .debug-raw-summary .debug-raw-chevron {
  transform: rotate(90deg);
}
.debug-raw-body {
  padding: 0.75rem 1.25rem 1.25rem;
}
/* Override the loose .result default (#0f172a blue) so the Raw JSON
   block actually inherits the studio's themed surface tokens instead
   of looking like a foreign element pasted in from a Tailwind demo. */
.debug-raw-body .result {
  max-height: 480px;
  margin: 0;
  background: var(--surface-overlay-strong, rgba(0,0,0,0.32));
  border: 1px solid var(--border-glass, rgba(255,255,255,0.06));
  color: var(--text-secondary);
  font-size: 0.72rem;
}

/* Step-preview JSON snippets were also unbounded — a long "storyboard"
   step preview would scroll for many screens inside Steps Summary.
   Bounded with internal scroll. */
.summary-preview {
  max-height: 200px;
  overflow: auto;
  background: var(--surface-overlay, rgba(0,0,0,0.20));
  border: 1px solid var(--border-glass, rgba(255,255,255,0.04));
  border-radius: 6px;
  padding: 0.5rem 0.7rem;
}

/* Each step is a collapsible <details>. Default markers hidden;
   chevron rotates open. Header is scannable: name + status + size +
   copy. Preview JSON only renders when expanded. */
details.summary-item > summary { list-style: none; cursor: pointer; user-select: none; }
details.summary-item > summary::-webkit-details-marker { display: none; }
details.summary-item .summary-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.4rem 0;
}
.summary-chevron {
  color: var(--text-muted);
  font-size: 0.7rem;
  transition: transform 180ms ease;
  display: inline-block;
  width: 0.7rem;
}
details.summary-item[open] > summary .summary-chevron { transform: rotate(90deg); }

.summary-status-badge {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-family: var(--font-mono, monospace);
}
.summary-status-badge.status-completed {
  background: rgba(34,197,94,0.12);
  color: rgba(134,239,172,0.92);
  border: 1px solid rgba(34,197,94,0.30);
}
.summary-status-badge.status-failed,
.summary-status-badge.status-error {
  background: rgba(239,68,68,0.14);
  color: rgba(252,165,165,0.95);
  border: 1px solid rgba(239,68,68,0.34);
}
.summary-status-badge.status-skipped {
  background: rgba(120,120,120,0.14);
  color: rgba(200,200,200,0.85);
  border: 1px solid rgba(120,120,120,0.30);
}
.summary-status-badge.status-pending,
.summary-status-badge.status-running {
  background: rgba(245,158,11,0.12);
  color: rgba(252,211,77,0.95);
  border: 1px solid rgba(245,158,11,0.30);
}
.summary-size {
  flex: 1;
  font-size: 0.7rem;
  color: var(--text-muted);
  font-family: var(--font-mono, monospace);
}
.summary-copy-btn {
  font-size: 0.85rem;
  padding: 0.15rem 0.5rem;
  border-radius: 5px;
  line-height: 1;
}

/* DiagnosticsPanel embedded inside the dev tab — strip its own card
   chrome so it doesn't get a card-inside-a-card double border. */
.debug-diag-body {
  padding: 0 0.5rem 0.75rem;
}
.debug-diag-body .diagnostics-panel {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
.debug-diag-body .diagnostics-panel__header { display: none; }

.diag-header-panel {
  margin-top: 0;
}

.diag-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.diag-header-row .section-title {
  margin: 0;
}

.copy-diag-btn {
  border: 1px solid rgba(245,158,11,0.18);
  background: var(--glass-bg);
  color: var(--text-secondary);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}

.summary-status {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--arc-300);
  font-family: var(--font-mono, monospace);
}

.summary-preview,
.light-result {
  margin: 8px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.75rem;
  line-height: 1.6;
  color: var(--text-secondary);
}

.summary-item {
  padding: 0.75rem 0;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}

.summary-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.summary-item strong {
  font-size: 0.8125rem;
  color: var(--text-primary);
  font-family: var(--font-mono, monospace);
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  line-height: 1.4;
  color: var(--text-primary);
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

.detail-row,
.detail-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-label {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
}

.detail-text {
  color: var(--text-primary);
  line-height: 1.6;
}

.asset-list {
  margin: 0;
  padding-left: 18px;
}

.asset-list li {
  margin-bottom: 8px;
}

.compact-result {
  margin: 0;
  max-height: 220px;
}

.asset-link {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  margin-top: 6px;
  color: var(--arc-300);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
}

.asset-link:hover {
  text-decoration: underline;
}

.asset-list-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.asset-image {
  display: block;
  width: 100%;
  max-width: 520px;
  border-radius: 10px;
  border: 1px solid rgba(245,158,11,0.10);
  background: var(--glass-bg);
  margin-top: 8px;
}

.asset-video {
  display: block;
  width: 100%;
  max-width: 520px;
  border-radius: 10px;
  margin-top: 8px;
  background: #000000;
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

.asset-grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
  padding-left: 0;
  list-style: none;
}

.asset-grid-list .asset-list-item {
  padding: 10px;
  border: 1px solid rgba(245,158,11,0.10);
  border-radius: 10px;
  background: var(--glass-bg);
}

.review-scene-grid {
  display: grid;
  gap: 16px;
}

.review-scene-card {
  padding: 16px;
  border-radius: 14px;
  background: var(--glass-bg);
  border: 1px solid rgba(245,158,11,0.10);
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
  border: 1px solid rgba(245,158,11,0.18);
  background: var(--glass-bg);
  cursor: pointer;
  text-align: left;
}

.asset-select-card.active {
  border-color: rgba(245,158,11,0.50);
  background: rgba(245,158,11,0.08);
}

.asset-select-card:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.review-selected-image {
  max-width: 280px;
}

.notes-preview-block {
  margin-top: 10px;
}

.notes-preview {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid rgba(245,158,11,0.10);
  background: var(--glass-bg);
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 320px;
  overflow: auto;
  text-align: left;
}
.mock-audio-link-row {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 16px;
  padding: 14px;
  border: 1px solid rgba(245,158,11,0.10);
  border-radius: 12px;
  background: var(--glass-bg);
}

.mock-audio-intro,
.mock-audio-empty {
  margin: 0 0 14px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.mock-audio-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
}

.mock-audio-scenes {
  display: grid;
  gap: 14px;
}

.mock-audio-scene-card {
  border: 1px solid rgba(245,158,11,0.10);
  border-radius: 14px;
  padding: 16px;
  background: var(--glass-bg);
}

.mock-audio-scene-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.mock-audio-asset-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  gap: 10px;
}

.mock-audio-asset-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--glass-bg);
  border: 1px solid rgba(245,158,11,0.10);
}

.mock-audio-asset-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.mock-audio-asset-main strong {
  color: var(--arc-300);
  font-size: 13px;
}

.mock-audio-meta {
  font-size: 13px;
  color: var(--text-muted);
}

.mock-audio-details {
  margin-top: 16px;
}

.mock-audio-details summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
}

.final-video-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
}

.final-video-placeholder-inner {
  width: min(520px, 80%);
  text-align: center;
  color: #e5e7eb;
}

.final-video-summary-card {
  margin-bottom: 20px;
}

.final-video-summary-ready,
.final-video-summary-waiting {
  border-radius: 16px;
  padding: 24px;
  background: linear-gradient(160deg, rgba(22,16,5,0.85) 0%, rgba(14,11,4,0.80) 100%);
  border: 1px solid rgba(245,158,11,0.10);
}

.final-video-hero {
  margin-bottom: 20px;
  position: relative;
}

.final-video-shell {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 20px;
  overflow: hidden;
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
}

.final-video-player {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
  background: #0f172a;
}

.final-video-status {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 10px;
}

.final-video-desc {
  font-size: 15px;
  color: #475569;
  line-height: 1.7;
}

.final-video-progress {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.08);
  margin-top: 18px;
  overflow: hidden;
}

.final-video-progress-bar {
  display: block;
  width: 35%;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #60a5fa, #a78bfa);
  animation: final-video-loading 1.2s ease-in-out infinite;
}

.final-video-progress-bar.waiting {
  width: 45%;
  animation: none;
  opacity: 0.72;
}
.review-video-placeholder {
  min-height: 320px;
}

.render-mode-switch {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 14px;
}

.render-mode-switch .label {
  font-weight: 600;
  opacity: 0.85;
}

.mode-option {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}

.silent-badge {
  position: absolute;
  top: 0;
  right: 12px;
  background: rgba(0,0,0,0.6);
  color: #fff;
  padding: 4px 8px;
  font-size: 12px;
  border-radius: 6px;
}

.manual-render-wrapper {
  text-align: center;
  margin-top: 20px;
}

.manual-render-primary {
  padding: 14px 36px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 999px;
  border: none;
  background: linear-gradient(90deg, #6366f1, #8b5cf6);
  color: #fff;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.35);
  transition: all 0.2s ease;
}

.manual-render-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 32px rgba(99, 102, 241, 0.45);
}

.manual-render-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.manual-hint {
  font-size: 14px;
  opacity: 0.7;
  margin-top: 8px;
}

/* Deferred banner — theme-aware (gold/blue/purple/pearl all via tokens).
   Was previously hardcoded tan/orange which clashed with all 4 themes. */
.deferred-generate-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
  background: var(--glass-bg);
  backdrop-filter: blur(16px) saturate(140%);
  -webkit-backdrop-filter: blur(16px) saturate(140%);
  border: 1px solid var(--border-glass);
  border-radius: 12px;
  margin-bottom: 16px;
  font-size: 0.875rem;
  color: var(--text-primary);
  box-shadow: var(--shadow-glass);
}

.deferred-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.deferred-generate-btn {
  padding: 8px 18px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-300) 22%, transparent),
    color-mix(in srgb, var(--arc-400) 30%, transparent)
  );
  color: var(--text-primary);
  border: 1px solid color-mix(in srgb, var(--arc-300) 50%, transparent);
  border-radius: 8px;
  font-size: 0.875rem;
  cursor: pointer;
  font-weight: 600;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.deferred-generate-btn:hover {
  border-color: var(--arc-300);
  box-shadow: 0 0 18px color-mix(in srgb, var(--arc-300) 25%, transparent);
}

.deferred-discard-btn {
  padding: 7px 14px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-glass);
  border-radius: 8px;
  font-size: 0.8125rem;
  cursor: pointer;
  font-weight: 500;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease;
}
.deferred-discard-btn:hover {
  border-color: color-mix(in srgb, var(--text-primary) 32%, transparent);
  background: color-mix(in srgb, var(--text-primary) 6%, transparent);
  color: var(--text-primary);
}

/* ── "放弃当前生成" confirm dialog ─────────────────────────────────────
   Teleported to body. Uses theme tokens so it adapts across all 4 themes
   without per-theme overrides. */
/* Dev-mode shortcut feedback chip — bottom-centred pill, gold border,
   short auto-dismiss. Light pointer-events:none so a stuck-open toast
   never blocks clicks on the actual UI. */
/* Anchored just past the sidebar's right edge (sidebar ≈ 84px wide on
   desktop) and at the same vertical band as the DEV chip — so the
   transient confirmation appears in the same visual zone as the
   persistent indicator. Avoids the macOS Dock (bottom edges) and the
   ThemeSwitcher (top-right). */
.dev-mode-toast {
  position: fixed;
  top: 16px;
  left: 96px;
  z-index: 1400;
  padding: 7px 12px;
  border-radius: 8px;
  background: rgba(20, 16, 8, 0.92);
  color: var(--arc-200);
  border: 1px solid var(--border-arc);
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.36);
  pointer-events: none;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
@media (max-width: 720px) {
  .dev-mode-toast {
    left: 16px;
    top: 62px;
  }
}

/* Generic notice toast — top-center, prominent, click to dismiss.
   Distinct shape from dev-mode-toast (which is a tiny corner pill) so
   the user reads this as a real notification rather than a passive
   status chip. `tone` variants tint the border + leading icon. */
.inline-notice {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1500;
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px 12px 16px;
  border-radius: 12px;
  background: rgba(18, 14, 8, 0.96);
  color: var(--text-primary);
  border: 1px solid color-mix(in srgb, var(--text-secondary) 30%, transparent);
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.01em;
  line-height: 1.5;
  max-width: min(560px, calc(100vw - 32px));
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.50),
              0 4px 12px rgba(0, 0, 0, 0.30);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  cursor: pointer;
}
.inline-notice--info {
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.50),
              0 0 0 1px color-mix(in srgb, var(--arc-300) 20%, transparent);
}
.inline-notice--warn {
  border-color: color-mix(in srgb, #f59e0b 65%, transparent);
  background: rgba(28, 18, 8, 0.96);
  box-shadow: 0 20px 48px rgba(0, 0, 0, 0.55),
              0 0 0 1px color-mix(in srgb, #f59e0b 30%, transparent);
}
.inline-notice__icon {
  flex: 0 0 auto;
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 0.875rem;
  font-weight: 700;
}
.inline-notice--info .inline-notice__icon {
  color: var(--arc-200);
  background: color-mix(in srgb, var(--arc-300) 18%, transparent);
}
.inline-notice--warn .inline-notice__icon {
  color: #fbbf24;
  background: color-mix(in srgb, #f59e0b 20%, transparent);
}
.inline-notice__text {
  flex: 1 1 auto;
  min-width: 0;
}
.inline-notice__close {
  flex: 0 0 auto;
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 1.25rem;
  font-family: inherit;
  cursor: pointer;
  padding: 0 4px;
  margin-left: 4px;
  border-radius: 4px;
  line-height: 1;
  transition: color 0.15s ease, background 0.15s ease;
}
.inline-notice__close:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.06);
}
@media (max-width: 720px) {
  .inline-notice { top: 64px; padding: 10px 12px; font-size: 0.8125rem; }
}

.confirm-overlay {
  position: fixed;
  inset: 0;
  /* Lighter than 0.55 so the dialog reads as "card on top" instead of
     "dark hole on darker hole". 0.42 still dims the studio surface enough
     to clearly indicate focus without crushing contrast. */
  background: rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

/* Dialog surface — glass-bg-light alone is too translucent on a dark overlay,
   so we layer a champagne arc-300 tint on top to lift the surface and give it
   warmth. The gradient + inset highlight + stronger arc border make the panel
   read as a card. Pearl theme: arc tint blends with the near-white glass to a
   soft warm cream — still legible. */
.confirm-dialog {
  width: min(460px, 100%);
  background:
    linear-gradient(
      180deg,
      color-mix(in srgb, var(--arc-300) 14%, var(--glass-bg-light)),
      color-mix(in srgb, var(--arc-400) 7%, var(--glass-bg-light))
    );
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  border: 1px solid color-mix(in srgb, var(--arc-300) 38%, var(--border-glass));
  border-radius: 16px;
  padding: 22px 24px 18px;
  box-shadow:
    0 24px 60px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 color-mix(in srgb, var(--arc-300) 22%, transparent);
  color: var(--text-primary);
}

.confirm-title {
  margin: 0 0 10px;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.confirm-message {
  margin: 0 0 22px;
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--text-muted);
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.confirm-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease, box-shadow 150ms ease;
}

.confirm-btn-ghost {
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-glass);
}
.confirm-btn-ghost:hover {
  color: var(--text-primary);
  border-color: color-mix(in srgb, var(--text-primary) 32%, transparent);
  background: color-mix(in srgb, var(--text-primary) 6%, transparent);
}

.confirm-btn-primary {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-300) 24%, transparent),
    color-mix(in srgb, var(--arc-400) 32%, transparent)
  );
  color: var(--text-primary);
  border: 1px solid color-mix(in srgb, var(--arc-300) 55%, transparent);
}
.confirm-btn-primary:hover {
  border-color: var(--arc-300);
  box-shadow: 0 0 22px color-mix(in srgb, var(--arc-300) 28%, transparent);
}

.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 160ms ease;
}
.confirm-fade-enter-active .confirm-dialog,
.confirm-fade-leave-active .confirm-dialog {
  transition: transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1);
}
.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}
.confirm-fade-enter-from .confirm-dialog,
.confirm-fade-leave-to .confirm-dialog {
  transform: translateY(8px) scale(0.98);
}
@keyframes final-video-loading {
  0% { transform: translateX(-120%); }
  100% { transform: translateX(320%); }
}

@media (max-width: 768px) {
  .mock-audio-asset-item,
  .mock-audio-scene-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
