<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import InteractiveImageReview from './components/InteractiveImageReview.vue'
import WorkflowResultsPanel from './components/WorkflowResultsPanel.vue'
import WorkflowRunPanel from './components/WorkflowRunPanel.vue'
import SampleAssetsPanel from './components/SampleAssetsPanel.vue'
import FinalVideoPanel from './components/FinalVideoPanel.vue'
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
  visualStyle: 'cute chibi anime',
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
  { label: 'Story', value: 'story' },
  { label: 'Storyboard', value: 'storyboard' },
  { label: 'Image Prompts', value: 'image_prompts' },
  { label: 'Image Assets', value: 'image_assets' },
  { label: 'Video Prompts', value: 'video_prompts' },
  { label: 'Dialogue Script', value: 'dialogue_script' },
  { label: 'Audio Segments', value: 'audio_segments' },
  { label: 'Narration', value: 'narration' },
  { label: 'Subtitles', value: 'subtitles' },
  { label: 'Render Plan', value: 'render_plan' },
  { label: 'Final Video', value: 'final_video' },
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

  // 去重：最新的放最前
  recentFinalVideoUrls.value = [
    u,
    ...recentFinalVideoUrls.value.filter((item) => item !== u),
  ].slice(0, 10)
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
const imageReviewRefreshCancelled = ref(false)
let reviewAutoRefreshFiredOnce = false
let imageReviewAutoRefreshTimer: number | null = null
let imageReviewRefreshAbortController: AbortController | null = null
type ViewTab = 'run' | 'review' | 'assets' | 'debug'
const activeTab = ref<ViewTab>('run')
const devMode = ref(false)

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

    renderFinalVideoIfReady(currentWorkflowResponse.value)
  }
)

const STORAGE_KEY_TAB = 'jinsie_active_tab'
const STORAGE_KEY_SESSION = 'jinsie_session_id'
const STORAGE_KEY_VIDEO_URL = 'jinsie_last_video_url'
const STORAGE_KEY_DEV = 'jinsie_dev_mode'

watch(activeTab, (tab) => {
  localStorage.setItem(STORAGE_KEY_TAB, tab)
})

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

onMounted(() => {
  const urlParams = new URLSearchParams(window.location.search)
  if (urlParams.get('dev') === '1') {
    devMode.value = true
  } else {
    devMode.value = localStorage.getItem(STORAGE_KEY_DEV) === '1'
  }

  const savedTab = localStorage.getItem(STORAGE_KEY_TAB) as ViewTab | null
  if (savedTab && ['run', 'review', 'assets'].includes(savedTab)) {
    activeTab.value = savedTab
  } else if (savedTab === 'debug' && devMode.value) {
    activeTab.value = 'debug'
  }

  const savedSessionId = localStorage.getItem(STORAGE_KEY_SESSION)
  if (savedSessionId) {
    workflowForm.value.sessionId = savedSessionId
  }

  const savedVideoUrl = localStorage.getItem(STORAGE_KEY_VIDEO_URL)
  if (savedVideoUrl) {
    finalVideoUrl.value = savedVideoUrl
    pushRecentFinalVideoUrl(savedVideoUrl)
  }
})

const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

const canSubmit = computed(() => {
  return (
    workflowForm.value.topic.trim().length > 0 &&
    selectedSteps.value.length > 0 &&
    !loading.value
  )
})

const providerStatsText = computed(() => {
  if (!samplesSummary.value?.provider_stats) {
    return ''
  }
  return stringifyPretty(samplesSummary.value.provider_stats)
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

function formatElapsedTime(totalSec: number): string {
  const normalizedSec = Math.max(0, Math.floor(totalSec))
  const minutes = Math.floor(normalizedSec / 60)
  const seconds = normalizedSec % 60
  if (minutes <= 0) {
    return `${seconds} 秒`
  }
  return `${minutes} 分 ${seconds} 秒`
}

const workflowRunStatusMessage = computed(() => {
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
  return '请先在 Run 页签执行一次 workflow，然后回到 Review 查看选图和结果。'
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
  const total = queue.length
  if (total === 0) {
    return {
      text: '候选图生成中',
      percent: 0,
    }
  }

  const currentIndex = Math.max(queue.indexOf(sceneRefreshingId.value), 0)
  const currentSceneId = sceneRefreshingId.value || queue[currentIndex] || ''
  const currentPlaceholder = reviewPlaceholders.value.find(
    (item) => item.scene_id === currentSceneId,
  )
  const currentSceneTitle = currentPlaceholder?.scene_title || currentSceneId
  const completedCount = reviewPlaceholders.value.filter(
    (item) => queue.includes(item.scene_id) && ['done', 'failed'].includes(item.state),
  ).length

  return {
    text: `候选图生成中：${currentIndex + 1}/${total}${
      currentSceneTitle ? ` · ${currentSceneTitle}` : ''
    }`,
    percent: Math.max(
      5,
      Math.min(100, Math.round((completedCount / total) * 100)),
    ),
  }
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
  finalVideoUrl.value = extractFinalVideoUrl(data)
  if (finalVideoUrl.value) {
    pushRecentFinalVideoUrl(finalVideoUrl.value)
    localStorage.setItem(STORAGE_KEY_VIDEO_URL, finalVideoUrl.value)
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
}

function buildReviewPlaceholdersFromStoryboard(data: WorkflowRunResponse): ReviewPlaceholderItem[] {
  const storyboard = data.outputs?.storyboard as Record<string, unknown> | undefined
  const scenesValue = storyboard?.scenes
  const scenes = Array.isArray(scenesValue) ? scenesValue : []

  const imageReview = data.outputs?.image_review as Record<string, unknown> | undefined
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

async function selectSample(sampleId: string) {
  selectedSampleId.value = sampleId
  samplesErrorMessage.value = ''

  try {
    await fetchSampleDetail(sampleId)
    await fetchSampleNotesText(selectedSampleDetail.value?.assets?.notes)
  } catch (error) {
    samplesErrorMessage.value =
      error instanceof Error ? error.message : 'Failed to load sample detail'
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

function handleManualRender() {
  if (!currentWorkflowResponse.value) return
  renderFinalVideoIfReady(currentWorkflowResponse.value)
}

async function refreshImageReviewScene(sceneId: string, signal?: AbortSignal, qualityTierOverride?: string) {
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

async function enhanceImageReviewScene(sceneId: string) {
  if (!sceneId || refreshingImageReview.value || sceneRefreshingId.value) {
    return
  }

  errorMessage.value = ''
  imageReviewRefreshAbortController = new AbortController()

  try {
    await refreshImageReviewScene(sceneId, imageReviewRefreshAbortController.signal, 'cinematic')
    if (workflowForm.value.renderMode === 'auto' && currentWorkflowResponse.value) {
      void renderFinalVideoIfReady(currentWorkflowResponse.value)
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    const message = error instanceof Error ? error.message : '场景增强失败'
    errorMessage.value = message
  } finally {
    sceneRefreshingId.value = ''
    imageReviewRefreshAbortController = null
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

  errorMessage.value = '已取消剩余候选图生成。'
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

  reviewAutoRefreshFiredOnce = true
  clearImageReviewAutoRefreshTimer()
  imageReviewAutoRefreshTimer = window.setTimeout(() => {
    if (refreshingImageReview.value) return
    void refreshImageReview()
  }, 1200)
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

    if (status === 'processing') {
      continue
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
  reviewAutoRefreshFiredOnce = false
  clearImageReviewAutoRefreshTimer()
  finalVideoText.value = ''
  finalVideoUrl.value = ''
  finalVideoRendering.value = false
  finalVideoRenderInFlight.value = false
  stepSummaries.value = []
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

  // ✅ 点击 Run 立刻给 UI 反馈（跨 tab 都能感知）
  loading.value = true
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
  }
}
</script>

<template>
  <main class="page">
    <section class="card">
      <h1>Jinsie Multimodal Frontend</h1>
      <p class="desc">
        输入一个主题，系统按默认参数或可选配置生成故事、分镜、旁白、字幕与视频渲染计划。
      </p>
      <div class="tabs-bar">
        <button
          class="tab-btn"
          :class="{ active: activeTab === 'run' }"
          @click="activeTab = 'run'"
        >
          Run
        </button>

        <button
          class="tab-btn"
          :class="{ active: activeTab === 'review' }"
          @click="activeTab = 'review'"
        >
          Review
        </button>

        <button
          class="tab-btn"
          :class="{ active: activeTab === 'assets' }"
          @click="activeTab = 'assets'"
        >
          Assets
        </button>

        <button
          v-if="devMode"
          class="tab-btn"
          :class="{ active: activeTab === 'debug' }"
          @click="activeTab = 'debug'"
        >
          Debug
        </button>

        <button
          class="tab-btn dev-mode-toggle"
          :class="{ active: devMode }"
          :title="devMode ? '关闭开发者模式' : '开启开发者模式'"
          @click="toggleDevMode"
        >
          ⚙
        </button>
      </div>
      <section v-if="activeTab === 'run'">
        <section class="recent-videos">
          <h2 class="section-title">Recent Videos</h2>

          <div v-if="recentFinalVideoUrls.length > 0" class="recent-videos-row">
            <video
              v-for="(url, idx) in recentFinalVideoUrls"
              :key="`${url}-${idx}`"
              class="recent-video-item"
              :src="url"
              controls
              playsinline
            />
          </div>

          <div v-else class="recent-videos-empty">
            <div class="recent-videos-empty-title">还没有生成过视频</div>
            <div class="recent-videos-empty-desc">
              在下方选择配音模式与参数，然后点击 <strong>Run Workflow</strong> 生成第一条视频。
            </div>
            <div class="example-topics-row">
              <span class="example-topics-label">试试：</span>
              <button
                v-for="topic in EXAMPLE_TOPICS"
                :key="topic"
                class="example-topic-btn"
                @click="setExampleTopic(topic)"
              >{{ topic }}</button>
            </div>
          </div>
        </section>

        <WorkflowRunPanel
          :loading="loading"
          :can-submit="canSubmit"
          :error-message="errorMessage"
          :form-state="workflowForm"
          :selected-steps="selectedSteps"
          :step-options="STEP_OPTIONS"
          @update:form-state="onUpdateFormState"
          @update:selected-steps="onUpdateSelectedSteps"
          @run="runWorkflow"
        />
      </section>
      <section v-if="activeTab === 'review'">
        <template v-if="hasReviewContent || workflowIsProcessing || refreshingImageReview || finalVideoRenderInFlight">
          <section class="result-panel final-video-hero">
            <div class="render-mode-switch">
              <span class="label">Render Mode:</span>
              <span class="value">{{ workflowForm.renderMode }}</span>
            </div>   
            <FinalVideoPanel
              :final-video-url="finalVideoUrl"
              :final-video-text="finalVideoText"
              :workflow-response="currentWorkflowResponse"
              :render-in-flight="finalVideoRenderInFlight"
              :loading="workflowIsProcessing || refreshingImageReview || finalVideoRenderInFlight"
              :error-message="errorMessage"
              :workflow-status-message="workflowRunStatusMessage"
              :workflow-status-progress="workflowStatusProgress"
              @render="renderFinalVideoIfReady(currentWorkflowResponse || {})"
              :show-render-button="workflowForm.renderMode === 'auto'"
            />
            <!-- Manual 主操作按钮 -->
            <div
              v-if="workflowForm.renderMode === 'manual'"
              class="manual-render-wrapper"
            >
              <button
                @click="handleManualRender"
                class="manual-render-primary"
                :disabled="!isWorkflowReadyForRender"
              >
                🎬 Generate Final Video
              </button>

              <div
                v-if="!isWorkflowReadyForRender"
                class="manual-hint"
              >
                等待候选图与音频生成完成…
              </div>
            </div>
            <div v-if="finalVideoAudioEnabled === false" class="silent-badge">
              🔇 无声模式
            </div>
          </section>

          <!-- 有内容才显示选图和结果；没内容但在跑时，只显示 FinalVideoPanel 占位 -->
          <template v-if="hasReviewContent">
            <InteractiveImageReview
              :items="imageReviewItems"
              :placeholders="reviewPlaceholders"
              :api-base-url="apiBaseUrl"
              :loading="loading || refreshingImageReview"
              :selecting-scene-id="selectingSceneId || sceneRefreshingId"
              :progress-text="reviewRefreshProgress.text"
              :progress-percent="reviewRefreshProgress.percent"
              :can-cancel="refreshingImageReview"
              @select-asset="({ sceneId, assetRef }) => selectImageAsset(sceneId, assetRef)"
              @retry-scene="retryImageReviewScene"
              @enhance-scene="enhanceImageReviewScene"
              @cancel-refresh="cancelImageReviewRefresh"
            />
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

        <p v-else class="empty-state">
          {{ reviewEmptyStateText }}
        </p>
      </section>
      <section v-if="activeTab === 'assets'">
        <SampleAssetsPanel
          :samples-loading="samplesLoading"
          :samples-error-message="samplesErrorMessage"
          :samples-summary="samplesSummary"
          :provider-stats-text="providerStatsText"
          :kling-samples="klingSamples"
          :selected-sample-id="selectedSampleId"
          :selected-sample-detail="selectedSampleDetail"
          :selected-sample-notes-text="selectedSampleNotesText"
          :selected-sample-notes-loading="selectedSampleNotesLoading"
          :api-base-url="apiBaseUrl"
          @refresh="loadSampleAssets"
          @select-sample="selectSample"
        />
        <section
          v-if="mockAudioIndexUrl || mockAudioSceneGroups.length > 0 || mockAudioDirectoryText"
          class="result-panel"
        >
          <h2 class="section-title">Mock Audio Assets</h2>

          <div v-if="mockAudioIndexUrl" class="mock-audio-link-row">
            <span class="mock-audio-label">Directory Index</span>
            <a
              class="asset-link"
              :href="`${apiBaseUrl}${mockAudioIndexUrl}`"
              target="_blank"
              rel="noreferrer"
            >
              Open index.json
            </a>
            <code>{{ mockAudioIndexUrl }}</code>
          </div>

          <div v-if="mockAudioSceneGroups.length > 0" class="mock-audio-scenes">
            <article
              v-for="group in mockAudioSceneGroups"
              :key="group.scene_id || 'unknown-scene'"
              class="mock-audio-scene-card"
            >
              <div class="mock-audio-scene-head">
                <strong>{{ group.scene_id || 'unknown-scene' }}</strong>
                <span>{{ (group.assets || []).length }} asset(s)</span>
              </div>

              <ul class="mock-audio-asset-list">
                <li
                  v-for="asset in group.assets || []"
                  :key="asset.asset_id || asset.segment_id || asset.file_name"
                  class="mock-audio-asset-item"
                >
                  <div class="mock-audio-asset-main">
                    <code>{{ asset.file_name || '-' }}</code>
                    <span class="mock-audio-meta">
                      {{ asset.speaker || '-' }} · {{ asset.duration_estimate_sec ?? 0 }}s
                    </span>
                  </div>

                  <a
                    v-if="asset.public_url"
                    class="asset-link"
                    :href="`${apiBaseUrl}${asset.public_url}`"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open asset path
                  </a>
                </li>
              </ul>
            </article>
          </div>

          <details v-if="mockAudioDirectoryText" class="mock-audio-details">
            <summary>Directory Manifest JSON</summary>
            <pre class="light-result compact-result">{{ mockAudioDirectoryText }}</pre>
          </details>
        </section>
      </section>
      <section v-if="activeTab === 'debug'">
        <p v-if="!hasDebugContent" class="empty-state">
          请先运行一次 workflow，生成 Steps Summary 和 Raw JSON 调试信息。
        </p>

        <template v-else>
          <section class="summary-panel diag-header-panel">
            <div class="diag-header-row">
              <h2 class="section-title">Run Diagnostics</h2>
              <button class="copy-diag-btn" @click="copyDiagnosticsJson">
                {{ diagCopied ? '✓ Copied' : 'Copy JSON' }}
              </button>
            </div>
            <div class="diagnostics-grid">
              <div class="diagnostics-item">
                <span class="diagnostics-label">run_id</span>
                <strong>{{ currentWorkflowResponse?.run_id || '—' }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">session_id</span>
                <strong>{{ currentWorkflowResponse?.session_id || '—' }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">Provider</span>
                <strong>{{ (currentWorkflowResponse?.outputs?.image_assets as any)?.provider || '—' }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">Status</span>
                <strong>{{ currentWorkflowResponse?.status || '—' }}</strong>
              </div>
              <div v-if="errorMessage" class="diagnostics-item diagnostics-item--error">
                <span class="diagnostics-label">Error</span>
                <strong>{{ errorMessage }}</strong>
              </div>
            </div>
          </section>

          <section v-if="storyDiagnostics" class="summary-panel">
            <h2 class="section-title">Story Diagnostics</h2>

            <div class="diagnostics-grid">
              <div class="diagnostics-item">
                <span class="diagnostics-label">Title</span>
                <strong>{{ storyDiagnostics.title }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">Source</span>
                <strong>{{ storyDiagnostics.generationSource }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">LLM provider</span>
                <strong :class="storyDiagnostics.providerUsed === 'fallback' ? 'warn-text' : ''">
                  {{ storyDiagnostics.providerUsed }}
                </strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">Fallback reason</span>
                <strong>{{ storyDiagnostics.fallbackReason }}</strong>
              </div>
              <div class="diagnostics-item">
                <span class="diagnostics-label">Character count</span>
                <strong>{{ storyDiagnostics.characterCount }}</strong>
              </div>
            </div>
          </section>

          <section v-if="stepSummaries.length > 0" class="summary-panel">
            <h2 class="section-title">Steps Summary</h2>

            <article v-for="item in stepSummaries" :key="item.name" class="summary-item">
              <div class="summary-head">
                <strong>{{ item.name }}</strong>
                <span class="summary-status">{{ item.status }}</span>
              </div>
              <pre class="summary-preview">{{ item.preview }}</pre>
            </article>
          </section>

          <section v-if="resultText" class="debug-panel">
            <h2 class="section-title">Raw JSON</h2>
            <pre class="result">{{ resultText }}</pre>
          </section>
        </template>
      </section>
    </section>
  </main>
</template>

<style scoped>
.page {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: #f7f8fa;
  padding: 24px;
}

.card {
  width: 100%;
  max-width: 960px;
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
.tabs-bar {
  display: flex;
  gap: 12px;
  margin: 0 0 24px;
  flex-wrap: wrap;
}

.empty-state {
  margin: 20px 0 0;
  padding: 20px;
  border: 1px dashed #d1d5db;
  border-radius: 14px;
  background: #f8fafc;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.7;
}

.recent-videos {
  margin: 0 0 18px;
}

.recent-videos-row {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding: 6px 2px;
  scroll-snap-type: x mandatory;
}

.recent-video-item {
  flex: 0 0 auto;
  width: 280px;
  height: 180px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #000000;
  scroll-snap-align: start;
}

.recent-videos-empty {
  border: 1px dashed #d1d5db;
  border-radius: 14px;
  background: #f8fafc;
  padding: 16px;
  color: #6b7280;
  line-height: 1.6;
}

.recent-videos-empty-title {
  font-weight: 700;
  color: #111827;
  margin-bottom: 6px;
}

.recent-videos-empty-desc strong {
  color: #111827;
}

.example-topics-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.example-topics-label {
  font-size: 13px;
  color: #9ca3af;
}

.example-topic-btn {
  border: 1px solid #e5e7eb;
  background: #ffffff;
  color: #374151;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.example-topic-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
  background: #f5f3ff;
}

.tab-btn {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #111827;
  border-radius: 999px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.tab-btn.active {
  background: #111827;
  color: #ffffff;
  border-color: #111827;
}

.dev-mode-toggle {
  margin-left: auto;
  font-size: 16px;
  padding: 10px 12px;
  color: #9ca3af;
  border-color: #e5e7eb;
}

.dev-mode-toggle.active {
  background: #f5f3ff;
  color: #6366f1;
  border-color: #6366f1;
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
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #374151;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.copy-diag-btn:hover {
  border-color: #6366f1;
  color: #6366f1;
}

.diagnostics-item--error strong {
  color: #dc2626;
}

.warn-text {
  color: #d97706;
}

.hint {
  margin: 12px 0 0;
  color: #dc2626;
  font-size: 13px;
}

.summary-panel,
.debug-panel {
  margin-top: 24px;
}

.summary-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.summary-status {
  color: #2563eb;
  font-size: 13px;
  font-weight: 600;
}

.diagnostics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.diagnostics-item {
  padding: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f8fafc;
}

.diagnostics-label {
  display: block;
  margin-bottom: 6px;
  color: #6b7280;
  font-size: 12px;
  font-weight: 600;
}

.diagnostics-item strong {
  color: #111827;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.summary-preview,
.light-result {
  margin: 12px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.6;
  color: #1f2937;
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  line-height: 1.4;
  color: #111827;
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
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
}

.detail-text {
  color: #111827;
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
  color: #2563eb;
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
  border: 1px solid #e5e7eb;
  background: #ffffff;
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
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #f8fafc;
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

.notes-preview-block {
  margin-top: 10px;
}

.notes-preview {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #111827;
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
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #f9fafb;
}

.mock-audio-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.mock-audio-scenes {
  display: grid;
  gap: 14px;
}

.mock-audio-scene-card {
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 16px;
  background: #ffffff;
}

.mock-audio-scene-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  color: #111827;
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
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.mock-audio-asset-main {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.mock-audio-meta {
  font-size: 13px;
  color: #6b7280;
}

.mock-audio-details {
  margin-top: 16px;
}

.mock-audio-details summary {
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  color: #111827;
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
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  border: 1px solid #e5e7eb;
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
