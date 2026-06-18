<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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

type ApiErrorDetail = {
  code?: string
  scene_id?: string
  provider?: string
  message?: string
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

type ImageReviewRefreshSceneResponse = {
  workflow_id?: string
  session_id?: string
  run_id?: string
  scene_id?: string
  scene_image_asset?: Record<string, unknown>
  scene_review_item?: Record<string, unknown>
  image_assets?: Record<string, unknown>
  image_review?: Record<string, unknown>
  video_prompts?: Record<string, unknown>
  timestamp?: string
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
  state: 'waiting' | 'refreshing' | 'done' | 'failed'
  error_message?: string
}

const userHasInteractedWithImages = ref(false)

const DEFAULT_WORKFLOW_FORM: any = {
  sessionId: 'demo-session-001',
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
const finalVideoAudioEnabled = ref(true)
const recentFinalVideoUrls = ref<string[]>([])

function pushRecentFinalVideoUrl(url: string) {
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

  // Persist the full list so refreshes don't drop earlier takes —
  // STORAGE_KEY_VIDEO_URL only ever held the latest one.
  try {
    localStorage.setItem(
      STORAGE_KEY_RECENT_VIDEOS,
      JSON.stringify(recentFinalVideoUrls.value),
    )
  } catch {
    /* quota / serialisation failures are non-fatal */
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

  try {
    if (recentFinalVideoUrls.value.length > 0) {
      localStorage.setItem(
        STORAGE_KEY_RECENT_VIDEOS,
        JSON.stringify(recentFinalVideoUrls.value),
      )
    } else {
      localStorage.removeItem(STORAGE_KEY_RECENT_VIDEOS)
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
      localStorage.removeItem(STORAGE_KEY_PAYLOAD)
      localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
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
const sceneImageVersions = ref<Record<string, number>>({})
const imageReviewRefreshCancelled = ref(false)
// Reactive mirror of STORAGE_KEY_REFRESH_CANCELLED — true iff THIS workflow's
// image refresh was paused by user cancel. Used to distinguish "已暂停" (user
// chose to stop) from "失败" (API/network error) in placeholder copy, since
// localStorage itself isn't reactive.
const imageRefreshPausedByUser = ref(false)
let reviewAutoRefreshFiredOnce = false
let imageReviewAutoRefreshTimer: number | null = null
let imageReviewRefreshAbortController: AbortController | null = null
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

const isWorkflowReadyForRender = computed(() => {
  const response = currentWorkflowResponse.value
  if (!response) return false

  const outputs = response.outputs || {}
  const storyboard = outputs.storyboard as any
  const imageAssets = outputs.image_assets as any
  const audioSegments = outputs.audio_segments as any

  const scenes = Array.isArray(storyboard?.scenes) ? storyboard.scenes : []
  const imageAssetList = Array.isArray(imageAssets?.assets) ? imageAssets.assets : []
  const audioItems = Array.isArray(audioSegments?.items) ? audioSegments.items : []
  const audioEnabled = audioSegments?.enabled === true
  const audioOk = !audioEnabled || audioItems.length > 0

  return (
    scenes.length > 0 &&
    imageAssetList.length >= scenes.length &&
    audioOk
  )
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
// Set of URLs the user has explicitly removed from history. Without this,
// a page refresh would re-import the deleted URL because the workflow
// outputs.json on disk still references it — applyWorkflowResponse would
// extract finalVideoUrl and push it back into RECENT_VIDEOS. The blacklist
// is consulted in pushRecentFinalVideoUrl + applyWorkflowResponse so the
// deletion survives reload without touching backend files.
const STORAGE_KEY_DELETED_VIDEOS = 'jinsie_deleted_video_urls'
const STORAGE_KEY_DEV = 'jinsie_dev_mode'
const STORAGE_KEY_WORKFLOW = 'jinsie_workflow_id'
const STORAGE_KEY_PAYLOAD = 'jinsie_workflow_payload'
// Persists "user explicitly cancelled image refresh for this workflow_id".
// Survives Landing → Studio nav so auto-resume does NOT restart a run
// the user just stopped. Cleared by: starting a new workflow, manually
// clicking "立即生成候选图", or finishing a successful refresh+render.
const STORAGE_KEY_REFRESH_CANCELLED = 'jinsie_workflow_refresh_cancelled'
const STORAGE_KEY_FORM = 'jinsie_workflow_form'

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
  localStorage.setItem(STORAGE_KEY_DEV, enabled ? '1' : '0')
  if (!enabled && activeTab.value === 'debug') {
    activeTab.value = 'run'
  }
})

function toggleDevMode() {
  devMode.value = !devMode.value
}

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

onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('dev') === '1') {
    devMode.value = true
  } else {
    devMode.value = localStorage.getItem(STORAGE_KEY_DEV) === '1'
  }

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
      workflowForm.value = { ...DEFAULT_WORKFLOW_FORM, ...savedForm }
    } catch { /* ignore malformed */ }
  }

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

  const savedVideoUrl = localStorage.getItem(STORAGE_KEY_VIDEO_URL)
  if (savedVideoUrl) {
    // Only push to the recent-videos list — do NOT restore finalVideoUrl.value here.
    // finalVideoUrl is only set by applyWorkflowResponse so it always matches the
    // current workflow response, never bleeds in from a previous completed run.
    pushRecentFinalVideoUrl(savedVideoUrl)
  }

  // Reattach to any in-flight workflow regardless of how we got here
  // (reload, SPA navigation from /, fresh tab open). The workflow_id in
  // localStorage is the source of truth; the previous `isReload` gate
  // silently dropped resume on SPA nav, which made "go to Landing during
  // a generation then come back" look like the run was lost.
  const savedWorkflowId = localStorage.getItem(STORAGE_KEY_WORKFLOW)

  // Restore the "user paused image refresh" reactive mirror so post-remount
  // placeholder copy says "已暂停" instead of "失败" (latter is reserved for
  // actual API/network failures). Marker is auth'd against current workflow_id.
  try {
    const markerWf = localStorage.getItem(STORAGE_KEY_REFRESH_CANCELLED) || ''
    if (markerWf && savedWorkflowId && markerWf === savedWorkflowId) {
      imageRefreshPausedByUser.value = true
    }
  } catch { /* ignore */ }

  if (savedWorkflowId) {
    const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8004'

    const reconnectInFlight = (statusData: any) => {
      const status = String(statusData?.status || '').trim().toLowerCase()
      const isProcessing = status === 'processing'
      const isCancelling = status === 'cancel_requested'
      if (!isProcessing && !isCancelling) return false

      // Restore the running-UI surface so cancel button / timeline /
      // progress bar / generation animation all wake up.
      loading.value = true
      workflowStatusData.value = statusData
      activeWorkflowId.value = savedWorkflowId
      cancelRequested.value = isCancelling
      // Leave activeTab alone — Landing entries set it to 'run' (which
      // already shows the timeline + CTA "正在生成…"); reload restores
      // last tab; neither needs to be overridden here.

      waitForAsyncWorkflowOutputs(savedWorkflowId)
        .then(asyncData => {
          if (asyncData) {
            // Same blacklist guard as the direct-results path below —
            // if the user already deleted this run's final video, don't
            // resurrect it on async reattach either.
            const restoredFinalUrl = extractFinalVideoUrl(asyncData)
            if (restoredFinalUrl && deletedVideoUrlsSet.value.has(restoredFinalUrl)) {
              try {
                localStorage.removeItem(STORAGE_KEY_WORKFLOW)
                localStorage.removeItem(STORAGE_KEY_PAYLOAD)
                localStorage.removeItem(STORAGE_KEY_VIDEO_URL)
                localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
              } catch { /* ignore */ }
              currentWorkflowPayload.value = null
              return
            }
            applyWorkflowResponse(asyncData)
            // Match runWorkflow()'s post-completion path so the deferred
            // candidate-image refresh kicks in automatically (sets
            // refreshingImageReview=true → CTA + progress bar reflect it).
            // Without this, the user lands on "立即生成候选图" with no
            // running indicators even though refreshImageReview is the
            // expected next step.
            scheduleImageReviewAutoRefreshIfNeeded()
          }
        })
        .catch(() => {})
        .finally(() => {
          // Workflow reached a terminal state — clear the per-run handles
          // so the cancel button / activeWorkflowId disappear cleanly.
          loading.value = false
          activeWorkflowId.value = ''
          cancelRequested.value = false
        })
      return true
    }

    fetch(`${base}/v1/workflow/results/${savedWorkflowId}`)
      .then(r => {
        if (r.status === 404) return { __notFound: true } as any
        return r.ok ? r.json() : null
      })
      .then(data => {
        if (!data) return
        if (data.__notFound) {
          // Outputs not on disk yet — the run may still be in flight.
          return fetch(`${base}/v1/workflow/status/${savedWorkflowId}`)
            .then(r => r.ok ? r.json() : null)
            .then(statusData => {
              // If the previous server crashed mid-run, the backend marks
              // status as 'abandoned' on startup. Wipe the stale
              // workflow_id from localStorage so we don't keep re-attaching
              // to a dead run on every reload.
              const stale = String(statusData?.status || '').trim().toLowerCase()
              if (stale === 'abandoned' || stale === 'cancelled' || stale === 'failed') {
                try {
                  localStorage.removeItem(STORAGE_KEY_WORKFLOW)
                  localStorage.removeItem(STORAGE_KEY_PAYLOAD)
                  localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
                } catch { /* ignore */ }
                return
              }
              reconnectInFlight(statusData)
            })
            .catch(() => {})
        }
        if (data.outputs || data.steps) {
          // Defensive guard: if the fetched workflow's final-video URL is
          // on the user's deletion blacklist, they've already discarded
          // this run. Calling applyWorkflowResponse would populate
          // currentWorkflowResponse with the deleted run's data, which
          // then triggers the isWorkflowReadyForRender watcher and gets
          // stuck on "等待用户触发渲染" because the URL is blocked from
          // restoration but the rest of the response is live. Wipe the
          // persisted workflow keys and bail so the new tab loads to a
          // clean idle state instead of resurrecting the deleted run.
          const restoredFinalUrl = extractFinalVideoUrl(data as WorkflowRunResponse)
          if (restoredFinalUrl && deletedVideoUrlsSet.value.has(restoredFinalUrl)) {
            try {
              localStorage.removeItem(STORAGE_KEY_WORKFLOW)
              localStorage.removeItem(STORAGE_KEY_PAYLOAD)
              localStorage.removeItem(STORAGE_KEY_VIDEO_URL)
              localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
            } catch { /* ignore */ }
            currentWorkflowPayload.value = null
            return
          }
          applyWorkflowResponse(data)
          resumePendingSceneGenerationAfterRestore()
        }
      })
      .catch(() => {/* silently ignore — server may not be up yet */})
  }
})

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

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

  if (refreshingImageReview.value) {
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

  const queue = sceneRefreshQueue.value
  if (queue.length === 0) {
    return {
      text: '候选图生成中',
      percent: 0,
    }
  }

  // Counter alignment fix: top bar must show the SAME numerator AND
  // denominator as the body counter (`FinalVideoPanel:187`) so the user
  // never sees two different "X/Y" values for the same in-flight run.
  // Previously the top used `(currentIndex+1)/sceneRefreshQueue.length`
  // — current position over refresh-queue length, which differs from
  // the body's "completed/total". Now both use "completed/total". The
  // current scene's natural title is still appended after the count
  // for context.
  const placeholders = reviewPlaceholders.value
  const totalScenes = placeholders.length || queue.length

  const currentIndexInQueue = Math.max(queue.indexOf(sceneRefreshingId.value), 0)
  const currentSceneId = sceneRefreshingId.value || queue[currentIndexInQueue] || ''
  const currentPlaceholder = placeholders.find(
    (item) => item.scene_id === currentSceneId,
  )
  const currentSceneTitle = currentPlaceholder?.scene_title || currentSceneId

  const completedCount = placeholders.filter(
    (item) => ['done', 'failed'].includes(item.state),
  ).length

  return {
    text: `候选图生成中：${completedCount}/${totalScenes}${
      currentSceneTitle ? ` · ${currentSceneTitle}` : ''
    }`,
    percent: Math.max(
      5,
      Math.min(100, Math.round((completedCount / totalScenes) * 100)),
    ),
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
}

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

function audioSpeakerLabel(speaker?: string): string {
  const value = String(speaker || '').trim()
  return value ? `配音：${value}` : '配音信息待确认'
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
        pushRecentFinalVideoUrl(finalVideoUrl.value)
        localStorage.setItem(STORAGE_KEY_VIDEO_URL, finalVideoUrl.value)
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
  syncReviewPlaceholders(data)

  const sessionId = data.session_id || workflowForm.value.sessionId
  if (sessionId) {
    localStorage.setItem(STORAGE_KEY_SESSION, sessionId)
  }
  const workflowId = data.workflow_id
  if (workflowId) {
    localStorage.setItem(STORAGE_KEY_WORKFLOW, workflowId)
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

  if (!imagesDeferredToRefresh && !hasSelectedAssets) {
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

  return scenes.map((scene: unknown) => {
    const sceneRecord = scene as Record<string, unknown>
    const sceneId = String(sceneRecord.scene_id || '')
    const sceneTitle = String(sceneRecord.scene_title || sceneId || 'unknown-scene')
    return {
      scene_id: sceneId,
      scene_title: sceneTitle,
      state: doneSceneIds.has(sceneId) ? 'done' : 'waiting',
    }
  })
}

function syncReviewPlaceholders(data: WorkflowRunResponse) {
  reviewPlaceholders.value = buildReviewPlaceholdersFromStoryboard(data)
}

function markPlaceholderState(
  sceneId: string,
  state: 'waiting' | 'refreshing' | 'done' | 'failed',
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

function formatImageReviewUserError(sceneId: string, status: number, errorBody: unknown): string {
  const body = errorBody as Record<string, unknown> | null
  const detailValue = body && typeof body === 'object' ? body.detail : undefined
  const detail =
    detailValue && typeof detailValue === 'object' ? (detailValue as ApiErrorDetail) : null
  const detailSceneId = detail?.scene_id || sceneId
  const code = String(detail?.code || '').toUpperCase()

  if (status >= 500 || code === 'IMAGE_GENERATION_FAILED') {
    return `${detailSceneId} 候选图生成失败：图片服务暂时不可用，请稍后重试。`
  }

  if (status === 408 || status === 429) {
    return `${detailSceneId} 候选图生成失败：图片服务响应较慢，请稍后重试。`
  }

  return `${detailSceneId} 候选图生成失败：请稍后重试。`
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
}

async function renderFinalVideoIfReady(baseResponse: WorkflowRunResponse) {
  if (!currentWorkflowPayload.value) return
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

  // 允许无声视频
  // 只有在 audio_segments 存在且明确 enabled=true 但没有生成时才阻止
  const audioEnabled = audioSegments?.enabled === true

  if (audioEnabled && audioItems.length === 0) return

  const payload = {
    workflow_id: baseResponse.workflow_id || currentWorkflowPayload.value.workflow_id,
    session_id: baseResponse.session_id || currentWorkflowPayload.value.session_id,
    run_id: baseResponse.run_id || '',
    workflow_input: currentWorkflowPayload.value.input,
    image_assets: imageAssets || {},
    audio_segments: audioSegments || {},
    subtitles: subtitles || {},
  }

  finalVideoRendering.value = true
  finalVideoRenderInFlight.value = true

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
  } finally {
    finalVideoRenderInFlight.value = false
    finalVideoRendering.value = false
  }
}

async function refreshImageReviewScene(sceneId: string, signal?: AbortSignal, qualityTierOverride?: string, preserveSeed: boolean = false) {
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
  markPlaceholderState(sceneId, 'refreshing')

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
  }

  let response: Response
  try {
    response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    console.warn('[image-review] refresh-scene network error', sceneId, error)
    throw new Error(`${sceneId} 候选图生成失败：网络连接不稳定，请稍后重试。`)
  }

  if (!response.ok) {
    let message = ''
    try {
      const errorBody = await response.json()
      console.warn('[image-review] refresh-scene failed', sceneId, response.status, errorBody)
      message = formatImageReviewUserError(sceneId, response.status, errorBody)
    } catch {
      const detail = await response.text().catch(() => '')
      console.warn('[image-review] refresh-scene failed', sceneId, response.status, detail)
      message =
        response.status >= 500
          ? `${sceneId} 候选图生成失败：图片服务暂时不可用，请稍后重试。`
          : `${sceneId} 候选图生成失败：请稍后重试。`
    }

    throw new Error(message)
  }

  const data: ImageReviewRefreshSceneResponse = await response.json()

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

  // Cache-bust ONLY at the URL building stage (toAssetHref reads this
  // map and appends ?v=ts). We must NOT mutate the underlying asset
  // paths here — those flow into /v1/final-video/render's payload and
  // are used by the backend to locate the actual files on disk. A
  // `?_=ts` suffix on relative_path would make the backend search for
  // a non-existent file and silently break the final video.
  sceneImageVersions.value = {
    ...sceneImageVersions.value,
    [sceneId]: Date.now(),
  }

  applyWorkflowResponse(mergedResponse)
  markPlaceholderState(sceneId, 'done')
}

async function retryImageReviewScene(sceneId: string) {
  if (!sceneId || refreshingImageReview.value || sceneRefreshingId.value) {
    return
  }

  errorMessage.value = ''
  imageReviewRefreshAbortController = new AbortController()

  try {
    await refreshImageReviewScene(sceneId, imageReviewRefreshAbortController.signal)
    if (workflowForm.value.renderMode === 'auto' && currentWorkflowResponse.value) {
      void renderFinalVideoIfReady(currentWorkflowResponse.value)
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      markPlaceholderState(sceneId, 'waiting')
      return
    }

    const message = error instanceof Error ? error.message : '候选图场景重试失败'
    markPlaceholderState(sceneId, 'failed', message)
    errorMessage.value = message
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
  // Workflow cancel beats image-refresh cancel when both could apply —
  // server-side cancel covers the whole run, abort only stops the
  // frontend loop.
  if (loading.value && activeWorkflowId.value) {
    void cancelWorkflow()
    return
  }
  if (refreshingImageReview.value) {
    cancelImageReviewRefresh()
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

// Bound to the "立即生成候选图" deferred-banner button. The user explicitly
// asking to (re)start refresh means we must clear the persistent cancel
// marker before invoking the refresh loop — otherwise the auto-resume
// guard would still treat this workflow as cancelled on next mount.
function triggerManualImageRefresh() {
  clearImageRefreshCancelledMarker()
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

function performDiscardCurrentDraft() {
  showDiscardConfirm.value = false

  // Stop any in-flight image refresh.
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  imageReviewRefreshCancelled.value = false
  refreshingImageReview.value = false
  sceneRefreshQueue.value = []
  sceneRefreshingId.value = ''
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

  // Regenerate the session id. The backend's RunnerSessionStore keys
  // its in-memory `previous_session_data` (last_story / last_storyboard /
  // last_render_plan) by session_id; reusing the same session_id after
  // a discard would seed the next run's session_memory_summary with the
  // previous run's topic — the cleanest fix is to mint a fresh session
  // on discard so the backend treats the next run as brand new.
  workflowForm.value.sessionId = `demo-session-${Date.now().toString(36)}`

  // Clear draft-related localStorage. Also clear SESSION so a page
  // reload between discard and the next run doesn't restore the stale
  // session id. FORM / TAB / DEV / RECENT_VIDEOS / LAST_VIDEO_URL stay
  // (those are user-level state, not part of this draft).
  try {
    localStorage.removeItem(STORAGE_KEY_WORKFLOW)
    localStorage.removeItem(STORAGE_KEY_PAYLOAD)
    localStorage.removeItem(STORAGE_KEY_REFRESH_CANCELLED)
    localStorage.removeItem(STORAGE_KEY_SESSION)
  } catch { /* ignore */ }

  // Drop the user back on 创作故事 — clean starting point for the next run.
  activeTab.value = 'run'
}

async function refreshImageReview() {
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

  try {
    for (const sceneId of sceneRefreshQueue.value) {
      if (imageReviewRefreshCancelled.value) {
        break
      }

      imageReviewRefreshAbortController = new AbortController()
      try {
        await refreshImageReviewScene(sceneId, imageReviewRefreshAbortController.signal)
      } catch (error) {
        if (
          imageReviewRefreshCancelled.value ||
          (error instanceof DOMException && error.name === 'AbortError')
        ) {
          markPlaceholderState(sceneId, 'waiting')
          break
        }

        const message = error instanceof Error ? error.message : '候选图分场景刷新失败'
        failures.push(message)
        markPlaceholderState(sceneId, 'failed', message)
      } finally {
        imageReviewRefreshAbortController = null
      }
    }
  } finally {
    sceneRefreshingId.value = ''
    sceneRefreshQueue.value = []
    refreshingImageReview.value = false
    imageReviewRefreshCancelled.value = false
    imageReviewRefreshAbortController = null
  }

  if (failures.length > 0) {
    errorMessage.value = `部分候选图生成失败：${failures.length}/${refreshTotal} 个场景未完成。图片服务暂时不可用，请在 Review 中重试失败场景或稍后再试。`
    return
  }

  if (workflowForm.value.renderMode === 'auto' && currentWorkflowResponse.value) {
    void renderFinalVideoIfReady(currentWorkflowResponse.value)
  }
}
function scheduleImageReviewAutoRefreshIfNeeded() {
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
  if (restoreAutoRefreshFired) return
  const hasPending = reviewPlaceholders.value.some((p) => p.state === 'waiting')
  if (!hasPending) return
  if (!currentWorkflowPayload.value) return
  if (finalVideoUrl.value) return
  // Respect persistent user cancel — Landing → Studio nav must not undo
  // the user's "stop generating" action.
  if (isImageRefreshUserCancelled()) return

  restoreAutoRefreshFired = true
  // Fire immediately — same render tick as applyWorkflowResponse, so
  // refreshingImageReview = true masks the deferred-banner from the
  // very first paint.
  if (!refreshingImageReview.value && reviewPlaceholders.value.some((p) => p.state === 'waiting')) {
    void refreshImageReview()
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
    workflowRunElapsedSec.value = Math.floor((Date.now() - startedAt) / 1000)
    await new Promise((resolve) => window.setTimeout(resolve, intervalMs))
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

async function runWorkflow() {
  // Defensive belt: abort any lingering image refresh from a previous
  // (cancelled but not discarded) run before we start a brand new one.
  // Without this, an orphan refresh promise could resolve mid-run and
  // overwrite the new image_review / selected_assets with stale data.
  imageReviewRefreshAbortController?.abort()
  imageReviewRefreshAbortController = null
  imageReviewRefreshCancelled.value = false
  imageRefreshPausedByUser.value = false
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
    form.sessionId.trim() || `demo-session-${Date.now().toString(36)}`

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

  if (form.voiceMode === 'character') {
    inputPayload.character_speaker_profiles = {
      narrator: form.narratorVoiceStyle,
      main_character: form.childVoiceStyle,
      secondary_character: form.motherVoiceStyle,
    }

    inputPayload.structured_characters_enabled = enableStructuredCharacters

    if (enableStructuredCharacters) {
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
  }

  const stepsSet = new Set(selectedSteps.value)

  if (form.subtitleEnabled) {
    stepsSet.add('subtitles')
  }

  const workflowId = `storybook-demo-${Date.now()}`

  const payload = {
    workflow_id: workflowId,
    session_id: sessionId,
    input: inputPayload,
    steps: Array.from(stepsSet).map((name) => ({ name })),
  }
  currentWorkflowPayload.value = payload as WorkflowRunPayload
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
  <StudioLayout v-model="activeTab" :tabs="studioTabs" :dev-mode="devMode" @toggle-dev="toggleDevMode">
    <template #progress>
      <StudioProgress
        :visible="
          workflowIsProcessing ||
          refreshingImageReview ||
          awaitingManualRender ||
          finalVideoRenderInFlight ||
          Boolean(sceneRefreshingId)
        "
        :percent="
          singleSceneRetryActive
            ? 75
            : finalVideoRenderInFlight
              ? 92
              : awaitingManualRender
                ? 85
                : (workflowStatusProgress ?? (refreshingImageReview ? reviewRefreshProgress.percent : 0))
        "
        :label="
          singleSceneRetryActive
            ? `正在为 ${sceneRefreshingId} 重新生成候选图`
            : finalVideoRenderInFlight
              ? '正在合成视频（音频、字幕、画面拼接中）'
              : awaitingManualRender
                ? '候选图已就绪，等待你点击「生成视频」'
                : (workflowIsProcessing ? workflowRunStatusMessage : reviewRefreshProgress.text)
        "
        :cancellable="phaseCancellable && !awaitingManualRender && !singleSceneRetryActive"
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
        :recent-video-urls="recentFinalVideoUrls"
        :render-in-flight="finalVideoRenderInFlight"
        :is-processing="workflowIsProcessing"
        :refreshing-images="refreshingImageReview"
        :awaiting-manual-render="awaitingManualRender"
        :status-label="workflowRunStatusMessage || (refreshingImageReview ? reviewRefreshProgress.text : '')"
        :completed-steps="workflowStatusData?.completed_steps ?? 0"
        :total-steps="workflowStatusData?.total_steps ?? 0"
        :cancellable="phaseCancellable"
        :cancel-requested="cancelRequestedAny"
        :example-topics="EXAMPLE_TOPICS"
        @set-topic="setExampleTopic"
        @cancel="cancelActivePhase"
        @delete-video="requestDeleteRecentVideo"
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
              <span v-else-if="finalVideoUrl" class="badge badge-ok" style="font-size:0.6rem;">已完成</span>
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
                :render-mode="workflowForm.renderMode"
                :scene-refreshing-id="sceneRefreshingId"
                @render="renderFinalVideoIfReady(currentWorkflowResponse || {})"
                :show-render-button="workflowForm.renderMode === 'auto'"
              />
              <div v-if="workflowForm.renderMode === 'manual' && !isWorkflowReadyForRender" class="manual-hint" style="text-align:center;padding:0.5rem 0 0;">
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
        <section
          v-if="mockAudioIndexUrl || mockAudioSceneGroups.length > 0 || mockAudioDirectoryText"
          class="result-panel"
        >
          <h2 class="section-title">配音素材</h2>
          <p class="mock-audio-intro">这里沉淀本次生成的配音片段，方便核对场景声音素材。</p>

          <div v-if="mockAudioSceneGroups.length > 0" class="mock-audio-scenes">
            <article
              v-for="group in mockAudioSceneGroups"
              :key="group.scene_id || 'unknown-scene'"
              class="mock-audio-scene-card"
            >
              <div class="mock-audio-scene-head">
                <strong>{{ sceneDisplayName(group.scene_id) }}</strong>
                <span>{{ (group.assets || []).length }} 个片段</span>
              </div>

              <ul class="mock-audio-asset-list">
                <li
                  v-for="(asset, index) in group.assets || []"
                  :key="asset.asset_id || asset.segment_id || asset.file_name"
                  class="mock-audio-asset-item"
                >
                  <div class="mock-audio-asset-main">
                    <strong>{{ audioAssetTitle(index) }}</strong>
                    <span class="mock-audio-meta">
                      {{ audioSpeakerLabel(asset.speaker) }} · {{ formatAudioDuration(asset.duration_estimate_sec) }}
                    </span>
                  </div>

                  <a
                    v-if="asset.public_url"
                    class="asset-link"
                    :href="`${apiBaseUrl}${asset.public_url}`"
                    target="_blank"
                    rel="noreferrer"
                  >
                    打开音频
                  </a>
                </li>
              </ul>
            </article>
          </div>

          <p v-else class="mock-audio-empty">暂无可展示的配音素材。</p>

          <details
            v-if="mockAudioIndexUrl || mockAudioSceneGroups.length > 0 || mockAudioDirectoryText"
            class="mock-audio-details"
          >
            <summary>开发者信息</summary>
            <div v-if="mockAudioIndexUrl" class="mock-audio-link-row">
              <span class="mock-audio-label">索引文件</span>
              <a
                class="asset-link"
                :href="`${apiBaseUrl}${mockAudioIndexUrl}`"
                target="_blank"
                rel="noreferrer"
              >
                打开 index.json
              </a>
              <code>{{ mockAudioIndexUrl }}</code>
            </div>
            <div
              v-for="group in mockAudioSceneGroups"
              :key="`${group.scene_id || 'unknown-scene'}-developer`"
              class="mock-audio-link-row"
            >
              <span class="mock-audio-label">{{ group.scene_id || 'unknown-scene' }}</span>
              <code
                v-for="asset in group.assets || []"
                :key="asset.asset_id || asset.segment_id || asset.file_name"
              >
                {{ asset.file_name || '-' }} · {{ asset.public_url || '-' }}
              </code>
            </div>
            <pre v-if="mockAudioDirectoryText" class="light-result compact-result">{{ mockAudioDirectoryText }}</pre>
          </details>
        </section>
      </section>
      <section v-if="activeTab === 'debug'" class="debug-layout">
        <div v-if="!hasDebugContent" class="review-empty-state glass-card animate-fade-in">
          <div class="review-empty-icon" aria-hidden="true">⚙</div>
          <div class="review-empty-title">尚无诊断数据</div>
          <p class="review-empty-desc">请先运行一次 Workflow，生成 Steps Summary 和原始 JSON 调试信息。</p>
        </div>

        <template v-else>
          <DiagnosticsPanel
            :workflow-id="currentWorkflowResponse?.workflow_id"
            :run-id="currentWorkflowResponse?.run_id"
            :session-id="currentWorkflowResponse?.session_id"
            :generation-source="storyDiagnostics?.generationSource"
            :fallback-reason="storyDiagnostics?.fallbackReason !== 'None' ? storyDiagnostics?.fallbackReason : undefined"
          >
            <template #json>{{ runDiagnosticsJson }}</template>
          </DiagnosticsPanel>

          <div v-if="stepSummaries.length > 0" class="glass-card debug-steps-card animate-fade-in">
            <div class="review-section-header">
              <span class="review-section-icon" aria-hidden="true">≡</span>
              <span class="review-section-title">Steps Summary</span>
              <button class="btn-ghost copy-diag-btn" @click="copyDiagnosticsJson" style="font-size:0.7rem;padding:0.25rem 0.6rem;">
                {{ diagCopied ? '✓ Copied' : 'Copy JSON' }}
              </button>
            </div>
            <div class="debug-steps-body">
              <article v-for="item in stepSummaries" :key="item.name" class="summary-item">
                <div class="summary-head">
                  <strong>{{ item.name }}</strong>
                  <span class="summary-status">{{ item.status }}</span>
                </div>
                <pre class="summary-preview">{{ item.preview }}</pre>
              </article>
            </div>
          </div>

          <div v-if="resultText" class="glass-card animate-fade-in">
            <div class="review-section-header">
              <span class="review-section-icon" aria-hidden="true">{ }</span>
              <span class="review-section-title">Raw JSON</span>
            </div>
            <div style="padding:1rem 1.25rem;">
              <pre class="result">{{ resultText }}</pre>
            </div>
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
</template>

<style scoped>
/* ── Homepage 2-column grid ── */
.studio-home-grid {
  display: grid;
  grid-template-columns: 420px 1fr;
  gap: 1.5rem;
  align-items: start;
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
    grid-template-columns: 1fr;
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
.review-images-card {
  overflow: hidden;
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
