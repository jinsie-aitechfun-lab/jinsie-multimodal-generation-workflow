<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import InteractiveImageReview from './components/InteractiveImageReview.vue'
import WorkflowResultsPanel from './components/WorkflowResultsPanel.vue'
import WorkflowRunPanel from './components/WorkflowRunPanel.vue'
type StepName =
  | 'story'
  | 'storyboard'
  | 'image_prompts'
  | 'image_assets'
  | 'video_prompts'
  | 'dialogue_script'
  | 'narration'
  | 'subtitles'
  | 'render_plan'

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
  video_prompts?: Record<string, unknown>
  timestamp?: string
}

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

const STEP_OPTIONS: Array<{ label: string; value: StepName }> = [
  { label: 'Story', value: 'story' },
  { label: 'Storyboard', value: 'storyboard' },
  { label: 'Image Prompts', value: 'image_prompts' },
  { label: 'Image Assets', value: 'image_assets' },
  { label: 'Video Prompts', value: 'video_prompts' },
  { label: 'Dialogue Script', value: 'dialogue_script' },
  { label: 'Narration', value: 'narration' },
  { label: 'Subtitles', value: 'subtitles' },
  { label: 'Render Plan', value: 'render_plan' },
]

const DEFAULT_STEPS: StepName[] = [
  'story',
  'storyboard',
  'image_prompts',
  'image_assets',
  'video_prompts',
  'dialogue_script',
  'narration',
  'subtitles',
  'render_plan',
]

const loading = ref(false)
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

const structuredCharactersEnabled = ref(true)

const primaryCharacterDisplayName = ref('小兔子')
const primaryCharacterSpecies = ref('rabbit')
const primaryCharacterVisualTraits = ref('long upright ears, white fur, red scarf')
const primaryCharacterForbiddenTraits = ref('cat ears, turtle shell')

const secondaryCharacterDisplayName = ref('小乌龟')
const secondaryCharacterSpecies = ref('turtle')
const secondaryCharacterVisualTraits = ref('round shell, short legs, green shell')
const secondaryCharacterForbiddenTraits = ref('rabbit ears, cat ears')

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

const topic = ref('写一个关于小猫冒险的故事')
const sessionId = ref('demo-session-001')
const audience = ref('children')
const tone = ref('warm')
const visualStyle = ref('storybook')
const characterStyle = ref('animal')
const voiceStyle = ref('warm_female')
const voiceoverEnabled = ref(false)
const voiceMode = ref('single')
const narratorVoiceStyle = ref('warm_female')
const motherVoiceStyle = ref('warm_female')
const childVoiceStyle = ref('gentle_child')
const durationSec = ref(60)
const language = ref('zh-CN')
const subtitleEnabled = ref(true)
const videoProvider = ref('mock')
const outputMode = ref('full_video')

const selectedSteps = ref<StepName[]>([...DEFAULT_STEPS])
const stepSummaries = ref<Array<{ name: string; status: string; preview: string }>>(
  []
)
const currentWorkflowResponse = ref<WorkflowRunResponse | null>(null)
const currentWorkflowPayload = ref<WorkflowRunPayload | null>(null)
const selectingSceneId = ref('')
const apiBaseUrl =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ||
  'http://127.0.0.1:8004'

const canSubmit = computed(() => {
  return topic.value.trim().length > 0 && selectedSteps.value.length > 0 && !loading.value
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

function hasAssetLink(path?: string): boolean {
  return Boolean(path && path.trim())
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

function isVideoAsset(path?: string): boolean {
  if (!path) {
    return false
  }

  const value = path.toLowerCase()
  return value.endsWith('.mp4') || value.endsWith('.webm') || value.endsWith('.mov')
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
    ? audioOutput!.scene_asset_map || []
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
  extractMockAudioState(data)
  stepSummaries.value = buildStepSummaries(data)
  characterCandidatesText.value = extractCharacterCandidatesText(data)
  characterManifestText.value = extractCharacterManifestText(data)
  resultText.value = stringifyPretty(data)
  currentWorkflowResponse.value = data
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
        : videoProvider.value,
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
async function runWorkflow() {
  resultText.value = ''
  currentWorkflowResponse.value = null
  currentWorkflowPayload.value = null
  storyText.value = ''
  storyboardText.value = ''
  currentWorkflowResponse.value = null
  currentWorkflowPayload.value = null
  imagePromptsText.value = ''
  imageAssetsText.value = ''
  imageReviewText.value = ''
  videoPromptsText.value = ''
  characterCandidatesText.value = ''
  characterManifestText.value = ''
  narrationText.value = ''
  subtitlesText.value = ''
  renderPlanText.value = ''

  mockAudioIndexUrl.value = ''
  mockAudioSceneGroups.value = []
  mockAudioDirectoryText.value = ''
  stepSummaries.value = []

  const structuredCharacters: StructuredCharacterInput[] = structuredCharactersEnabled.value
    ? [
        {
          display_name: primaryCharacterDisplayName.value.trim(),
          species: primaryCharacterSpecies.value.trim(),
          role_type: 'primary',
          visual_traits: primaryCharacterVisualTraits.value.trim(),
          forbidden_traits: primaryCharacterForbiddenTraits.value.trim(),
        },
        ...(secondaryCharacterDisplayName.value.trim()
          ? [
              {
                display_name: secondaryCharacterDisplayName.value.trim(),
                species: secondaryCharacterSpecies.value.trim(),
                role_type: 'secondary' as const,
                visual_traits: secondaryCharacterVisualTraits.value.trim(),
                forbidden_traits: secondaryCharacterForbiddenTraits.value.trim(),
              },
            ]
          : []),
      ]
    : []

  const payload = {
    workflow_id: 'storybook-demo',
    session_id: sessionId.value.trim() || 'demo-session-001',
    input: {
      topic: topic.value.trim(),
      audience: audience.value,
      tone: tone.value,
      visual_style: visualStyle.value,
      character_style: characterStyle.value,
      structured_characters_enabled: structuredCharactersEnabled.value,
      characters: structuredCharacters,
      voice_style: voiceStyle.value,
      voiceover_enabled: voiceoverEnabled.value,
      voice_mode: voiceMode.value,
      speaker_profiles: {
        narrator: narratorVoiceStyle.value,
        mother: motherVoiceStyle.value,
        child: childVoiceStyle.value,
      },
      duration_sec: durationSec.value,
      language: language.value,
      subtitle_enabled: subtitleEnabled.value,
      video_provider: videoProvider.value,
      output_mode: outputMode.value,
    },
    steps: selectedSteps.value.map((name) => ({ name })),
  }
  currentWorkflowPayload.value = payload as WorkflowRunPayload

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
      sessionId.value = data.session_id
    }

    applyWorkflowResponse(data)

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
            <section class="samples-panel">
        <div class="samples-panel-head">
          <div>
            <h2 class="section-title">Real Sample Assets</h2>
            <p class="samples-desc">
              展示项目四当前已归档的真实可灵样片，总览 / 列表 / 详情三层查询已接入。
            </p>
          </div>

          <button class="secondary-btn" :disabled="samplesLoading" @click="loadSampleAssets">
            {{ samplesLoading ? 'Loading...' : 'Refresh Samples' }}
          </button>
        </div>

        <p v-if="samplesErrorMessage" class="error">
          样例资产加载失败：{{ samplesErrorMessage }}
        </p>

        <div v-if="samplesSummary" class="samples-summary-grid">
          <div class="samples-metric">
            <span class="metric-label">Providers</span>
            <strong class="metric-value">
              {{ (samplesSummary.providers || []).join(', ') || '-' }}
            </strong>
          </div>

          <div class="samples-metric">
            <span class="metric-label">Total Samples</span>
            <strong class="metric-value">
              {{ samplesSummary.total_sample_count ?? 0 }}
            </strong>
          </div>

          <div class="samples-metric samples-metric-wide">
            <span class="metric-label">Provider Stats</span>
            <pre class="light-result compact-result">{{ providerStatsText }}</pre>
          </div>
        </div>

        <div class="samples-layout">
          <section class="samples-list-panel">
            <h3 class="subsection-title">Kling Sample List</h3>

            <p v-if="klingSamples.length === 0" class="hint">
              当前没有可展示的样片记录。
            </p>

            <button
              v-for="sample in klingSamples"
              :key="sample.sample_id || sample.scene_id"
              class="sample-list-item"
              :class="{ active: sample.sample_id === selectedSampleId }"
              @click="selectSample(sample.sample_id || '')"
            >
              <strong>{{ sample.sample_id || 'unknown-sample' }}</strong>
              <span>scene_id: {{ sample.scene_id || '-' }}</span>
              <span>status: {{ sample.status || '-' }}</span>
            </button>
          </section>

          <section class="sample-detail-panel">
            <h3 class="subsection-title">Sample Detail</h3>

            <div v-if="selectedSampleDetail" class="sample-detail-content">
              <div class="detail-row">
                <span class="detail-label">sample_id</span>
                <code>{{ selectedSampleDetail.sample_id || '-' }}</code>
              </div>

              <div class="detail-row">
                <span class="detail-label">scene_id</span>
                <code>{{ selectedSampleDetail.scene_id || '-' }}</code>
              </div>

              <div class="detail-row">
                <span class="detail-label">generated_scene_id</span>
                <code>{{ selectedSampleDetail.generated_scene_id || '-' }}</code>
              </div>

              <div class="detail-row">
                <span class="detail-label">status</span>
                <code>{{ selectedSampleDetail.status || '-' }}</code>
              </div>

              <div class="detail-block">
                <span class="detail-label">notes</span>
                <p class="detail-text">{{ selectedSampleDetail.notes || '-' }}</p>
                <a
                  v-if="hasAssetLink(selectedSampleDetail.assets?.notes)"
                  class="asset-link"
                  :href="toAssetHref(selectedSampleDetail.assets?.notes)"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open notes file
                </a>

                <div class="notes-preview-block">
                  <span class="detail-label">notes preview</span>
                  <p v-if="selectedSampleNotesLoading" class="detail-text">Loading notes...</p>
                  <pre v-else class="notes-preview">{{ selectedSampleNotesText || '-' }}</pre>
                </div>
              </div>

              <div class="detail-block">
                <span class="detail-label">clean_video</span>
                <code>{{ selectedSampleDetail.assets?.clean_video || '-' }}</code>
                <a
                  v-if="hasAssetLink(selectedSampleDetail.assets?.clean_video)"
                  class="asset-link"
                  :href="toAssetHref(selectedSampleDetail.assets?.clean_video)"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open clean video
                </a>
                <video
                  v-if="isVideoAsset(selectedSampleDetail.assets?.clean_video)"
                  class="asset-video"
                  controls
                  preload="metadata"
                  :src="toAssetHref(selectedSampleDetail.assets?.clean_video)"
                />
              </div>

              <div class="detail-block">
                <span class="detail-label">watermarked_video</span>
                <code>{{ selectedSampleDetail.assets?.watermarked_video || '-' }}</code>
                <a
                  v-if="hasAssetLink(selectedSampleDetail.assets?.watermarked_video)"
                  class="asset-link"
                  :href="toAssetHref(selectedSampleDetail.assets?.watermarked_video)"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open watermarked video
                </a>
              </div>

              <div class="detail-block">
                <span class="detail-label">input_screenshot</span>
                <code>{{ selectedSampleDetail.assets?.input_screenshot || '-' }}</code>
                <a
                  v-if="isImageAsset(selectedSampleDetail.assets?.input_screenshot)"
                  class="asset-image-link"
                  :href="toAssetHref(selectedSampleDetail.assets?.input_screenshot)"
                  target="_blank"
                  rel="noreferrer"
                >
                  <img
                    class="asset-image asset-image-thumbnail"
                    :src="toAssetHref(selectedSampleDetail.assets?.input_screenshot)"
                    alt="input screenshot preview"
                  />
                </a>
              </div>

              <div class="detail-block">
                <span class="detail-label">result_screenshots</span>
                <ul class="asset-list asset-grid-list">
                  <li
                    v-for="path in selectedSampleDetail.assets?.result_screenshots || []"
                    :key="path"
                    class="asset-list-item"
                  >
                    <code>{{ path }}</code>
                    <a
                      v-if="isImageAsset(path)"
                      class="asset-image-link"
                      :href="toAssetHref(path)"
                      target="_blank"
                      rel="noreferrer"
                    >
                      <img
                        class="asset-image asset-image-thumbnail"
                        :src="toAssetHref(path)"
                        :alt="path"
                      />
                    </a>
                  </li>
                </ul>
              </div>
            </div>

            <p v-else class="hint">请选择左侧样片查看详情。</p>
          </section>
        </div>
      </section>
      <WorkflowRunPanel
        :loading="loading"
        :can-submit="canSubmit"
        :error-message="errorMessage"
        :session-id="sessionId"
        :topic="topic"
        :audience="audience"
        :tone="tone"
        :visual-style="visualStyle"
        :character-style="characterStyle"
        :voice-style="voiceStyle"
        :voiceover-enabled="voiceoverEnabled"
        :voice-mode="voiceMode"
        :narrator-voice-style="narratorVoiceStyle"
        :mother-voice-style="motherVoiceStyle"
        :child-voice-style="childVoiceStyle"
        :duration-sec="durationSec"
        :language="language"
        :subtitle-enabled="subtitleEnabled"
        :video-provider="videoProvider"
        :output-mode="outputMode"
        :structured-characters-enabled="structuredCharactersEnabled"
        :primary-character-display-name="primaryCharacterDisplayName"
        :primary-character-species="primaryCharacterSpecies"
        :primary-character-visual-traits="primaryCharacterVisualTraits"
        :primary-character-forbidden-traits="primaryCharacterForbiddenTraits"
        :secondary-character-display-name="secondaryCharacterDisplayName"
        :secondary-character-species="secondaryCharacterSpecies"
        :secondary-character-visual-traits="secondaryCharacterVisualTraits"
        :secondary-character-forbidden-traits="secondaryCharacterForbiddenTraits"
        :selected-steps="selectedSteps"
        :step-options="STEP_OPTIONS"
        @update:sessionId="sessionId = $event"
        @update:topic="topic = $event"
        @update:audience="audience = $event"
        @update:tone="tone = $event"
        @update:visualStyle="visualStyle = $event"
        @update:characterStyle="characterStyle = $event"
        @update:voiceStyle="voiceStyle = $event"
        @update:voiceoverEnabled="voiceoverEnabled = $event"
        @update:voiceMode="voiceMode = $event"
        @update:narratorVoiceStyle="narratorVoiceStyle = $event"
        @update:motherVoiceStyle="motherVoiceStyle = $event"
        @update:childVoiceStyle="childVoiceStyle = $event"
        @update:durationSec="durationSec = $event"
        @update:language="language = $event"
        @update:subtitleEnabled="subtitleEnabled = $event"
        @update:videoProvider="videoProvider = $event"
        @update:outputMode="outputMode = $event"
        @update:structuredCharactersEnabled="structuredCharactersEnabled = $event"
        @update:primaryCharacterDisplayName="primaryCharacterDisplayName = $event"
        @update:primaryCharacterSpecies="primaryCharacterSpecies = $event"
        @update:primaryCharacterVisualTraits="primaryCharacterVisualTraits = $event"
        @update:primaryCharacterForbiddenTraits="primaryCharacterForbiddenTraits = $event"
        @update:secondaryCharacterDisplayName="secondaryCharacterDisplayName = $event"
        @update:secondaryCharacterSpecies="secondaryCharacterSpecies = $event"
        @update:secondaryCharacterVisualTraits="secondaryCharacterVisualTraits = $event"
        @update:secondaryCharacterForbiddenTraits="secondaryCharacterForbiddenTraits = $event"
        @update:selectedSteps="selectedSteps = $event"
        @run="runWorkflow"
      />
      <InteractiveImageReview
        :items="imageReviewSelectedAssets"
        :api-base-url="apiBaseUrl"
        :loading="loading"
        :selecting-scene-id="selectingSceneId"
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

.label {
  display: block;
  margin-bottom: 8px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
}

.textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 15px;
  line-height: 1.5;
  resize: vertical;
  background: #ffffff;
  color: #111827;
}

.textarea:focus,
.input:focus,
.textarea:focus {
  outline: none;
  border-color: #111827;
}

.config-panel,
.steps-panel,
.story-panel,
.result-panel,
.summary-item {
  margin-top: 20px;
  padding: 16px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.field {
  display: block;
}

.field span,
.checkbox-field span {
  display: block;
  margin-bottom: 8px;
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 28px;
}

.checkbox-field span {
  margin-bottom: 0;
  font-weight: 500;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.step-option {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #111827;
  font-size: 14px;
}

.hint {
  margin: 12px 0 0;
  color: #dc2626;
  font-size: 13px;
}

.btn {
  margin-top: 16px;
  border: none;
  border-radius: 10px;
  padding: 12px 18px;
  font-size: 15px;
  cursor: pointer;
  background: #111827;
  color: #ffffff;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.error {
  margin-top: 16px;
  color: #dc2626;
  font-size: 14px;
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

.story-text {
  margin: 0;
  color: #1f2937;
  font-size: 15px;
  line-height: 1.8;
  white-space: pre-wrap;
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

.samples-panel {
  margin: 24px 0;
  padding: 20px;
  border-radius: 16px;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
}

.samples-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.samples-desc {
  color: #4b5563;
  font-size: 14px;
  line-height: 1.6;
}

.secondary-btn {
  border: 1px solid #d1d5db;
  background: #ffffff;
  color: #111827;
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 14px;
  white-space: nowrap;
}

.secondary-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.samples-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.samples-metric {
  padding: 14px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  text-align: left;
}

.samples-metric-wide {
  grid-column: 1 / -1;
}

.metric-label {
  display: block;
  margin-bottom: 8px;
  color: #6b7280;
  font-size: 13px;
  font-weight: 600;
}

.metric-value {
  color: #111827;
  font-size: 18px;
}

.samples-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
}

.samples-list-panel,
.sample-detail-panel {
  padding: 16px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.subsection-title {
  margin: 0 0 12px;
  color: #111827;
  font-size: 18px;
  text-align: left;
}

.sample-list-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  text-align: left;
  border: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #111827;
  border-radius: 12px;
  padding: 12px;
  margin-bottom: 10px;
  cursor: pointer;
}

.sample-list-item.active {
  border-color: #111827;
  background: #eef2ff;
}

.sample-detail-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  text-align: left;
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

@media (max-width: 900px) {
  .samples-panel-head {
    flex-direction: column;
    align-items: stretch;
  }

  .samples-summary-grid {
    grid-template-columns: 1fr;
  }

  .samples-layout {
    grid-template-columns: 1fr;
  }
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

@media (max-width: 768px) {
  .mock-audio-asset-item,
  .mock-audio-scene-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>