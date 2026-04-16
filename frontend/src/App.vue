<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import InteractiveImageReview from './components/InteractiveImageReview.vue'
import WorkflowResultsPanel from './components/WorkflowResultsPanel.vue'
import WorkflowRunPanel, {
  type WorkflowRunFormState,
} from './components/WorkflowRunPanel.vue'
import SampleAssetsPanel from './components/SampleAssetsPanel.vue'
import FinalVideoPanel from './components/FinalVideoPanel.vue'
type StepName =
  | 'story'
  | 'storyboard'
  | 'image_prompts'
  | 'image_assets'
  | 'video_prompts'
  | 'dialogue_script'
  | 'audio_segments'
  | 'narration'
  | 'subtitles'
  | 'render_plan'
  | 'final_video'

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
  state: 'waiting' | 'refreshing' | 'done'
}

const DEFAULT_WORKFLOW_FORM: WorkflowRunFormState = {
  sessionId: 'demo-session-001',
  topic: '写一个关于小猫冒险的故事',
  audience: 'children',
  tone: 'warm',
  visualStyle: 'storybook',
  characterStyle: 'animal',
  voiceStyle: 'warm_female',
  voiceoverEnabled: true,
  voiceMode: 'single',
  narratorVoiceStyle: 'warm_female',
  motherVoiceStyle: 'warm_female',
  childVoiceStyle: 'gentle_child',
  durationSec: 60,
  language: 'zh-CN',
  subtitleEnabled: true,
  videoProvider: 'mock',
  outputMode: 'full_video',

  structuredCharactersEnabled: true,
  primaryCharacterDisplayName: '小兔子',
  primaryCharacterSpecies: 'rabbit',
  primaryCharacterVisualTraits: 'long upright ears, white fur, red scarf',
  primaryCharacterForbiddenTraits: 'cat ears, turtle shell',
  secondaryCharacterDisplayName: '小乌龟',
  secondaryCharacterSpecies: 'turtle',
  secondaryCharacterVisualTraits: 'round shell, short legs, green shell',
  secondaryCharacterForbiddenTraits: 'rabbit ears, cat ears',
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

const loading = ref(false)
const finalVideoRenderInFlight = ref(false)
const errorMessage = ref('')
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
const finalVideoRendering = ref(false)
const workflowForm = ref<WorkflowRunFormState>({ ...DEFAULT_WORKFLOW_FORM })
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
let reviewAutoRefreshFiredOnce = false
let imageReviewAutoRefreshTimer: number | null = null
type ViewTab = 'run' | 'review' | 'assets' | 'debug'
const activeTab = ref<ViewTab>('run')

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

const hasDebugContent = computed(() => {
  return Boolean(stepSummaries.value.length > 0 || resultText.value)
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
  finalVideoUrl.value = extractFinalVideoUrl(data)
  extractMockAudioState(data)
  stepSummaries.value = buildStepSummaries(data)
  characterCandidatesText.value = extractCharacterCandidatesText(data)
  characterManifestText.value = extractCharacterManifestText(data)
  resultText.value = stringifyPretty(data)
  currentWorkflowResponse.value = data
  syncReviewPlaceholders(data)
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

function markPlaceholderState(sceneId: string, state: 'waiting' | 'refreshing' | 'done') {
  reviewPlaceholders.value = reviewPlaceholders.value.map((item) =>
    item.scene_id === sceneId ? { ...item, state } : item,
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
  if (audioItems.length === 0) return

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

async function refreshImageReviewScene(sceneId: string) {
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
    workflow_input: currentWorkflowPayload.value.input,
    image_review: imageReview && typeof imageReview === 'object' ? imageReview : {},
    video_provider:
      typeof currentWorkflowPayload.value.input?.video_provider === 'string'
        ? currentWorkflowPayload.value.input.video_provider
        : workflowForm.value.videoProvider,
  }

  const response = await fetch(`${apiBaseUrl}/v1/image-review/refresh-scene`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
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
  errorMessage.value = ''

  try {
    for (const sceneId of sceneRefreshQueue.value) {
      await refreshImageReviewScene(sceneId)
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '候选图分场景刷新失败'
  } finally {
    sceneRefreshingId.value = ''
    sceneRefreshQueue.value = []
    refreshingImageReview.value = false
  }
}
async function runWorkflow() {
  clearImageReviewAutoRefreshTimer()
  resultText.value = ''
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
  finalVideoRendering.value = false
  finalVideoRenderInFlight.value = false
  stepSummaries.value = []

  const form = workflowForm.value

  const structuredCharacters: StructuredCharacterInput[] = form.structuredCharactersEnabled
    ? [
        {
          display_name: form.primaryCharacterDisplayName.trim(),
          species: form.primaryCharacterSpecies.trim(),
          role_type: 'primary',
          visual_traits: form.primaryCharacterVisualTraits.trim(),
          forbidden_traits: form.primaryCharacterForbiddenTraits.trim(),
        },
        ...(form.secondaryCharacterDisplayName.trim()
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

  const payload = {
    workflow_id: 'storybook-demo',
    session_id: form.sessionId.trim() || 'demo-session-001',
    input: {
      topic: form.topic.trim(),
      audience: form.audience,
      tone: form.tone,
      visual_style: form.visualStyle,
      character_style: form.characterStyle,
      structured_characters_enabled: form.structuredCharactersEnabled,
      characters: structuredCharacters,
      voice_style: form.voiceStyle,
      voiceover_enabled: form.voiceoverEnabled,
      voice_mode: form.voiceMode,
      speaker_profiles: {
        narrator: form.narratorVoiceStyle,
        mother: form.motherVoiceStyle,
        child: form.childVoiceStyle,
      },
      duration_sec: form.durationSec,
      language: form.language,
      subtitle_enabled: form.subtitleEnabled,
      video_provider: form.videoProvider,
      output_mode: form.outputMode,
    },
    steps: selectedSteps.value.map((name) => ({ name })),
  }
  currentWorkflowPayload.value = payload as WorkflowRunPayload

  // ✅ 点击 Run 立刻给 UI 反馈（跨 tab 都能感知）
  loading.value = true
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

    if (reviewWaitingState.value === 'deferred_pending' && !reviewAutoRefreshFiredOnce) {
      reviewAutoRefreshFiredOnce = true
      clearImageReviewAutoRefreshTimer()
      imageReviewAutoRefreshTimer = window.setTimeout(() => {
        // 二次保护：如果此时已经在刷新，则不再触发
        if (refreshingImageReview.value) return
        void refreshImageReview()
      }, 1200)
    }

  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Request failed'
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  void loadSampleAssets()
})
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
          class="tab-btn"
          :class="{ active: activeTab === 'debug' }"
          @click="activeTab = 'debug'"
        >
          Debug
        </button>
      </div>
      <section v-if="activeTab === 'run'">
         <FinalVideoPanel
          :final-video-url="finalVideoUrl"
          :final-video-text="finalVideoText"
          :workflow-response="currentWorkflowResponse"
          :render-in-flight="finalVideoRenderInFlight"
          @render="renderFinalVideoIfReady(currentWorkflowResponse || {})"
          :loading="loading || refreshingImageReview || finalVideoRenderInFlight"
        />

        <WorkflowRunPanel
          :loading="loading"
          :can-submit="canSubmit"
          :error-message="errorMessage"
          :form-state="workflowForm"
          :selected-steps="selectedSteps"
          :step-options="STEP_OPTIONS"
          @update:form-state="workflowForm = $event"
          @update:selected-steps="selectedSteps = $event"
          @run="runWorkflow"
        />
      </section>
      <section v-if="activeTab === 'review'">
        <template v-if="hasReviewContent || loading || refreshingImageReview || finalVideoRenderInFlight">
  <section class="result-panel final-video-hero">
    <FinalVideoPanel
      :final-video-url="finalVideoUrl"
      :final-video-text="finalVideoText"
      :workflow-response="currentWorkflowResponse"
      :render-in-flight="finalVideoRenderInFlight"
      :loading="loading || refreshingImageReview || finalVideoRenderInFlight"
      @render="renderFinalVideoIfReady(currentWorkflowResponse || {})"
    />
  </section>

  <!-- 有内容才显示选图和结果；没内容但在跑时，只显示 FinalVideoPanel 占位 -->
  <template v-if="hasReviewContent">
    <InteractiveImageReview
      :items="imageReviewItems"
      :placeholders="reviewPlaceholders"
      :api-base-url="apiBaseUrl"
      :loading="loading || refreshingImageReview"
      :selecting-scene-id="selectingSceneId || sceneRefreshingId"
      @select-asset="({ sceneId, assetRef }) => selectImageAsset(sceneId, assetRef)"
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
          请先在 Run 页签执行一次 workflow，然后回到 Review 查看选图和结果。
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