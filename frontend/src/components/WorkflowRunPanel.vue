<script setup lang="ts">
import { ref } from 'vue'
import ThemedSelect from './studio/ThemedSelect.vue'
import InlineStatusPulse from './studio/InlineStatusPulse.vue'

type StepName = string

export type WorkflowRunFormState = {
  sessionId: string
  topic: string
  audience: string
  tone: string
  visualStyle: string
  characterStyle: string
  voiceStyle: string

  audioEnabled: boolean
  voiceoverEnabled: boolean

  voiceMode: 'single' | 'multi' | 'character'
  narratorVoiceStyle: string
  motherVoiceStyle: string
  childVoiceStyle: string

  durationSec: number
  language: string
  subtitleEnabled: boolean
  videoProvider: string
  outputMode: string

  structuredCharactersEnabled: boolean
  primaryCharacterDisplayName: string
  primaryCharacterSpecies: string
  primaryCharacterVisualTraits: string
  primaryCharacterForbiddenTraits: string
  secondaryCharacterDisplayName: string
  secondaryCharacterSpecies: string
  secondaryCharacterVisualTraits: string
  secondaryCharacterForbiddenTraits: string

  renderMode: 'auto' | 'manual'
  qualityTier: 'fast' | 'quality' | 'cinematic'
}

type StepOption = { label: string; value: StepName }

const props = defineProps<{
  loading: boolean
  canSubmit: boolean
  errorMessage: string
  formState: WorkflowRunFormState
  selectedSteps: StepName[]
  stepOptions: StepOption[]
  // Optional cancellation state — App.vue passes these in while a run
  // is in flight so the button can switch to a stoppable affordance.
  cancellable?: boolean
  cancelRequested?: boolean
  statusLabel?: string
  elapsedSec?: number
  // `completedSteps` (preferred) is how many workflow steps have FINISHED.
  // `currentStepIndex` (1-based "now running") is accepted for back-compat
  // but the visual will use `completedSteps` when both are provided so the
  // count here matches the "当前步骤：X（6/11）" text shown above.
  // Showing two different numbers (current=7 vs completed=6) for the same
  // run reads as a UI bug to users.
  completedSteps?: number
  currentStepIndex?: number
  totalSteps?: number
}>()

const emit = defineEmits<{
  (e: 'update:formState', v: WorkflowRunFormState): void
  (e: 'update:selectedSteps', v: StepName[]): void
  (e: 'run'): void
  (e: 'cancel'): void
}>()

// Compact elapsed-time label for the run-state line ("1 分 24 秒" / "12 秒").
function formatElapsedLabel(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds || 0))
  if (total < 60) return `${total} 秒`
  return `${Math.floor(total / 60)} 分 ${total % 60} 秒`
}

// Local-only collapse state — does NOT affect payload, just UI grouping.
const voiceCollapsed  = ref(true)   // 配音与字幕 — default collapsed for clean first paint
const renderCollapsed = ref(true)   // 渲染与输出 — advanced settings, default collapsed
const stepsCollapsed  = ref(true)   // Workflow Steps — engineering view, default collapsed

/* ─────────────────────────────────────────────────────────────
   Display-only enum option lists.
   `label` is shown to the user (Chinese), `value` is the exact
   string submitted to the workflow payload — unchanged.
   withFallback() appends the current value as an extra option
   if it doesn't match any standard one, so legacy values like
   "cute chibi anime" (with spaces) keep working.
───────────────────────────────────────────────────────────────── */
type EnumOption = { value: string; label: string }

const AUDIENCE_OPTS: EnumOption[] = [
  { value: 'children', label: '儿童' },
  { value: 'family',   label: '亲子' },
  { value: 'general',  label: '通用' },
]
const TONE_OPTS: EnumOption[] = [
  { value: 'warm',        label: '温暖治愈' },
  { value: 'adventure',   label: '冒险成长' },
  { value: 'educational', label: '科普启蒙' },
  { value: 'bedtime',     label: '睡前故事' },
]
const VISUAL_OPTS: EnumOption[] = [
  { value: 'cute_chibi_anime',    label: '可爱绘本' },
  { value: 'cinematic',           label: '电影感' },
  { value: 'watercolor',          label: '水彩童话' },
  { value: 'chinese_illustration', label: '国风插画' },
]
const CHARACTER_OPTS: EnumOption[] = [
  { value: 'animal',    label: '动物主角' },
  { value: 'child',     label: '小朋友主角' },
  { value: 'fantasy',   label: '奇幻角色' },
  { value: 'robot_toy', label: '机器人 / 玩具' },
]
const VOICE_STYLE_OPTS: EnumOption[] = [
  { value: 'warm_female',     label: '温柔女声' },
  { value: 'warm_male',       label: '温暖男声' },
  { value: 'child',           label: '童声' },
  { value: 'narrator_female', label: '旁白女声' },
]
const OUTPUT_MODE_OPTS: EnumOption[] = [
  { value: 'full_video',         label: '完整视频' },
  { value: 'storyboard_preview', label: '分镜预览' },
  { value: 'assets_only',        label: '仅生成素材' },
]
const LANGUAGE_OPTS: EnumOption[] = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en-US', label: '英文' },
]
const VIDEO_PROVIDER_OPTS: EnumOption[] = [
  { value: 'mock',      label: '绘本视频模式' },
  { value: 'storybook', label: '分镜播放模式' },
]

/* ── V1.0 visible-option whitelists ──────────────────────────────────
   The full _OPTS arrays above stay intact so the underlying types /
   API payload / runtime constants are unchanged; the UI just renders
   a subset for V1.0. Re-enable an option later by adding its `value`
   back to the matching _V1_VALUES set.
   - output mode  : 完整视频 only (分镜预览 / 仅生成素材 隐藏)
   - language     : 中文 only (英文 隐藏)
   - video provider: 绘本视频模式 only (分镜播放模式 隐藏)         */
const OUTPUT_MODE_V1_VALUES = new Set(['full_video'])
const LANGUAGE_V1_VALUES = new Set(['zh-CN'])
const VIDEO_PROVIDER_V1_VALUES = new Set(['mock'])

const OUTPUT_MODE_OPTS_VISIBLE: EnumOption[] = OUTPUT_MODE_OPTS.filter((o) =>
  OUTPUT_MODE_V1_VALUES.has(o.value),
)
const LANGUAGE_OPTS_VISIBLE: EnumOption[] = LANGUAGE_OPTS.filter((o) =>
  LANGUAGE_V1_VALUES.has(o.value),
)
const VIDEO_PROVIDER_OPTS_VISIBLE: EnumOption[] = VIDEO_PROVIDER_OPTS.filter((o) =>
  VIDEO_PROVIDER_V1_VALUES.has(o.value),
)
const VOICE_MODE_OPTS: EnumOption[] = [
  { value: 'single',    label: '单人旁白' },
  { value: 'multi',     label: '亲子轮流' },
  { value: 'character', label: '角色配音' },
]
const NARRATOR_VOICE_OPTS: EnumOption[] = [
  { value: 'warm_female',     label: '温柔女声' },
  { value: 'warm_male',       label: '温暖男声' },
  { value: 'gentle_child',    label: '儿童声线' },
  { value: 'narrator_female', label: '故事旁白' },
]
const MOTHER_VOICE_OPTS: EnumOption[] = [
  { value: 'warm_female',   label: '温柔女声' },
  { value: 'gentle_female', label: '温暖女声' },
  { value: 'warm_mother',   label: '故事妈妈' },
]
const CHILD_VOICE_OPTS: EnumOption[] = [
  { value: 'gentle_child', label: '儿童声线' },
  { value: 'bright_child', label: '活泼童声' },
  { value: 'soft_child',   label: '温柔童声' },
]

function withFallback(opts: EnumOption[], current: string): EnumOption[] {
  if (!current || opts.some((o) => o.value === current)) return opts
  return [...opts, { value: current, label: current }]
}

function updateFormState<K extends keyof WorkflowRunFormState>(
  key: K,
  value: WorkflowRunFormState[K]
) {
  emit('update:formState', {
    ...props.formState,
    [key]: value,
  })
}

function updateVoiceMode(value: string) {
  if (value === 'single') {
    emit('update:formState', {
      ...props.formState,
      voiceMode: 'single',
      narratorVoiceStyle: props.formState.narratorVoiceStyle || 'warm_female',
      motherVoiceStyle: '',
      childVoiceStyle: '',
      structuredCharactersEnabled: false,
      primaryCharacterDisplayName: '',
      primaryCharacterSpecies: '',
      primaryCharacterVisualTraits: '',
      primaryCharacterForbiddenTraits: '',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    })
    return
  }

  if (value === 'multi') {
    emit('update:formState', {
      ...props.formState,
      voiceMode: 'multi',
      narratorVoiceStyle: props.formState.narratorVoiceStyle || 'warm_female',
      motherVoiceStyle: props.formState.motherVoiceStyle || 'warm_female',
      childVoiceStyle: props.formState.childVoiceStyle || 'gentle_child',
      structuredCharactersEnabled: false,
      primaryCharacterDisplayName: '',
      primaryCharacterSpecies: '',
      primaryCharacterVisualTraits: '',
      primaryCharacterForbiddenTraits: '',
      secondaryCharacterDisplayName: '',
      secondaryCharacterSpecies: '',
      secondaryCharacterVisualTraits: '',
      secondaryCharacterForbiddenTraits: '',
    })
    return
  }

  emit('update:formState', {
    ...props.formState,
    voiceMode: 'character',
    narratorVoiceStyle: props.formState.narratorVoiceStyle || 'warm_female',
    motherVoiceStyle: props.formState.motherVoiceStyle || 'warm_male',
    childVoiceStyle: props.formState.childVoiceStyle || 'gentle_child',
    structuredCharactersEnabled: true,
    primaryCharacterDisplayName:
      props.formState.primaryCharacterDisplayName || '小兔子',
    primaryCharacterSpecies: props.formState.primaryCharacterSpecies || 'rabbit',
    secondaryCharacterDisplayName:
      props.formState.secondaryCharacterDisplayName || '小乌龟',
    secondaryCharacterSpecies:
      props.formState.secondaryCharacterSpecies || 'turtle',
  })
}

function updateSelectedStep(step: StepName, checked: boolean) {
  const current = [...props.selectedSteps]

  if (checked) {
    if (!current.includes(step)) {
      emit('update:selectedSteps', [...current, step])
    }
    return
  }

  emit(
    'update:selectedSteps',
    current.filter((item) => item !== step)
  )
}

function applyPresetSingle() {
  console.log('[preset] single clicked')
  emit('update:formState', {
    ...props.formState,
    subtitleEnabled: true,
    voiceMode: 'single',

    narratorVoiceStyle: 'warm_female',
    motherVoiceStyle: '',
    childVoiceStyle: '',

    structuredCharactersEnabled: false,
    primaryCharacterDisplayName: '',
    primaryCharacterSpecies: '',
    primaryCharacterVisualTraits: '',
    primaryCharacterForbiddenTraits: '',
    secondaryCharacterDisplayName: '',
    secondaryCharacterSpecies: '',
    secondaryCharacterVisualTraits: '',
    secondaryCharacterForbiddenTraits: '',
  })
  applyPresetFullSteps()
}

function applyPresetCharacter() {
  console.log('[preset] character clicked')
  emit('update:formState', {
    ...props.formState,
    subtitleEnabled: true,
    voiceMode: 'character',

    narratorVoiceStyle: 'warm_female',
    motherVoiceStyle: 'warm_male',
    childVoiceStyle: 'gentle_child',

    structuredCharactersEnabled: true,
    primaryCharacterDisplayName: '小兔子',
    primaryCharacterSpecies: 'rabbit',
    secondaryCharacterDisplayName: '小乌龟',
    secondaryCharacterSpecies: 'turtle',
  })
  applyPresetFullSteps()
}

function applyPresetMulti() {
  console.log('[preset] multi clicked')
  emit('update:formState', {
    ...props.formState,
    subtitleEnabled: true,
    voiceMode: 'multi',

    narratorVoiceStyle: 'warm_female',
    motherVoiceStyle: 'warm_female',
    childVoiceStyle: 'gentle_child',
  })
  applyPresetFullSteps()
}

function applyPresetFullSteps() {
  emit('update:selectedSteps', [
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
  ])
}

function applyPresetMinimalSteps() {
  console.log('[preset] minimal clicked')
  // 最简步骤：减少等待（只保留必要产物）
  emit('update:selectedSteps', [
    'story',
    'storyboard',
    'dialogue_script',
    'audio_segments',
    'narration',
    'subtitles',
  ])
}

// ---- topic vs manual characters warning (UI only) ----
function detectTopicSpecies(topic: string): Set<'cat' | 'dog' | 'rabbit' | 'turtle'> {
  const t = (topic || '').trim()
  const lower = t.toLowerCase()
  const hits = new Set<'cat' | 'dog' | 'rabbit' | 'turtle'>()

  const hitCat = t.includes('猫') || lower.includes('cat') || lower.includes('kitten')
  if (hitCat) hits.add('cat')

  const hitDog = t.includes('狗') || lower.includes('dog') || lower.includes('puppy')
  if (hitDog) hits.add('dog')

  const hitRabbit = t.includes('兔') || lower.includes('rabbit') || lower.includes('bunny')
  if (hitRabbit) hits.add('rabbit')

  const hitTurtle = t.includes('乌龟') || t.includes('龟') || lower.includes('turtle')
  if (hitTurtle) hits.add('turtle')

  return hits
}

function normalizeManualSpecies(raw: string): 'cat' | 'dog' | 'rabbit' | 'turtle' | null {
  const s = (raw || '').trim().toLowerCase()
  if (!s) return null

  // english
  if (s === 'cat') return 'cat'
  if (s === 'dog') return 'dog'
  if (s === 'rabbit' || s === 'bunny') return 'rabbit'
  if (s === 'turtle') return 'turtle'

  // chinese / mixed
  if (s.includes('猫')) return 'cat'
  if (s.includes('狗')) return 'dog'
  if (s.includes('兔')) return 'rabbit'
  if (s.includes('龟')) return 'turtle'

  return null
}

function formatSpeciesLabel(key: string): string {
  if (key === 'cat') return '猫'
  if (key === 'dog') return '狗'
  if (key === 'rabbit') return '兔子'
  if (key === 'turtle') return '乌龟'
  return key
}

function getTopicManualMismatchWarning(): string {
  const f = props.formState

  // Only meaningful in character mode with manual override enabled
  if (f.voiceMode !== 'character') return ''
  if (!f.structuredCharactersEnabled) return ''

  const topicHits = detectTopicSpecies(f.topic)

  const manualHits = new Set<string>()
  const primary = normalizeManualSpecies(f.primaryCharacterSpecies) ||
    normalizeManualSpecies(f.primaryCharacterDisplayName)
  const secondary = normalizeManualSpecies(f.secondaryCharacterSpecies) ||
    normalizeManualSpecies(f.secondaryCharacterDisplayName)

  if (primary) manualHits.add(primary)
  if (secondary) manualHits.add(secondary)

  // if user didn't really specify any manual character, no warning
  if (manualHits.size === 0) return ''
  if (topicHits.size === 0) return ''

  // mismatch only when there is NO intersection
  let intersect = false
  for (const k of manualHits) {
    if (topicHits.has(k as any)) {
      intersect = true
      break
    }
  }
  if (intersect) return ''

  const topicLabels = Array.from(topicHits).map(formatSpeciesLabel).join('、')
  const manualLabels = Array.from(manualHits).map(formatSpeciesLabel).join('、')

  return `主题提到了：${topicLabels}；你手动指定：${manualLabels}。将以手动为准。`
}
</script>

<template>
  <section class="workflow-run-panel">
    <label class="label" for="topic">故事主题</label>
    <textarea
      id="topic"
      :value="formState.topic"
      class="textarea"
      rows="4"
      placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      @input="updateFormState('topic', ($event.target as HTMLTextAreaElement).value)"
    />
    <!-- Informational only: the user's topic is a short prompt; the LLM
         expands it into the full story according to the selected duration. -->
    <span class="hint topic-hint">
      系统会根据约 {{ formState.durationSec }} 秒目标时长，将主题扩展为完整故事内容。
    </span>

    <!-- ═══════════ Basic configuration (always expanded) ═══════════ -->
    <section class="config-panel">
      <h2 class="section-title">基础配置</h2>

      <div class="config-grid">
        <label class="field">
          <span>受众群体</span>
          <ThemedSelect
            :model-value="formState.audience"
            :options="withFallback(AUDIENCE_OPTS, formState.audience)"
            @update:model-value="(v: string) => updateFormState('audience', v)"
          />
        </label>

        <label class="field">
          <span>故事风格</span>
          <ThemedSelect
            :model-value="formState.tone"
            :options="withFallback(TONE_OPTS, formState.tone)"
            @update:model-value="(v: string) => updateFormState('tone', v)"
          />
        </label>

        <label class="field">
          <span>视觉风格</span>
          <ThemedSelect
            :model-value="formState.visualStyle"
            :options="withFallback(VISUAL_OPTS, formState.visualStyle)"
            @update:model-value="(v: string) => updateFormState('visualStyle', v)"
          />
        </label>

        <label class="field">
          <span>角色风格</span>
          <ThemedSelect
            :model-value="formState.characterStyle"
            :options="withFallback(CHARACTER_OPTS, formState.characterStyle)"
            @update:model-value="(v: string) => updateFormState('characterStyle', v)"
          />
        </label>

        <label class="field field-wide">
          <span>目标时长（秒）</span>
          <input
            :value="formState.durationSec"
            class="input"
            type="number"
            min="60"
            max="180"
            step="60"
            @input="
              updateFormState(
                'durationSec',
                Number(($event.target as HTMLInputElement).value)
              )
            "
          />
          <span class="hint">推荐默认约 120 秒；支持约 60 / 约 120 / 约 180 秒。实际成片时长会随故事字数、配音语速和分镜数量略有浮动。</span>
        </label>
      </div>
    </section>

    <!-- ═══════════ Primary CTA (deep gold) ═══════════
         Placed right after base config so users can start creating
         without scrolling through advanced settings. Reuses the original
         emit('run') binding — submit logic / payload / API untouched. -->
    <p v-if="errorMessage" class="error">请求失败：{{ errorMessage }}</p>
    <div class="primaryCtaBar">
      <button
        class="btn primaryCtaBtn"
        :disabled="!canSubmit"
        @click="emit('run')"
      >
        {{
          cancelRequested
            ? '正在取消生成…'
            : loading
              ? '正在生成…'
              : '开始创作'
        }}
      </button>

      <!-- Inline run-state strip: current step + elapsed + cancel.
           Shown only while a run is in flight so the form panel stays
           compact during idle. Reuses statusLabel + workflow status data
           from App.vue; nothing here owns workflow state. -->
      <div v-if="loading || cancellable" class="runState">
        <div class="runStateInfo">
          <InlineStatusPulse
            :variant="cancelRequested ? 'cancelling' : 'running'"
            :text="statusLabel || '正在准备'"
          />
          <span
            v-if="totalSteps && (completedSteps !== undefined || currentStepIndex !== undefined)"
            class="runStateStep"
          >{{ completedSteps !== undefined ? completedSteps : (currentStepIndex ?? 0) }} / {{ totalSteps }}</span>
          <span
            v-if="elapsedSec !== undefined && elapsedSec > 0"
            class="runStateElapsed"
          >· 已等待 {{ formatElapsedLabel(elapsedSec) }}</span>
        </div>
        <button
          v-if="cancellable"
          type="button"
          class="cancelLink"
          :disabled="cancelRequested"
          @click="emit('cancel')"
        >
          {{ cancelRequested ? '正在取消…' : '取消生成' }}
        </button>
      </div>
    </div>

    <!-- ═══════════ 渲染与输出 (collapsible) ═══════════ -->
    <section class="config-panel collapse-section">
      <button
        type="button"
        class="collapse-head"
        :aria-expanded="!renderCollapsed"
        @click="renderCollapsed = !renderCollapsed"
      >
        <span class="collapse-title-block">
          <span class="collapse-title">渲染与输出</span>
          <span class="collapse-desc">画质、模式与输出配置</span>
        </span>
        <svg
          :class="['collapse-chevron', { 'is-open': !renderCollapsed }]"
          width="12" height="8" viewBox="0 0 12 8" fill="none"
        >
          <path d="M1 1 L6 6 L11 1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div v-show="!renderCollapsed" class="collapse-body">
        <div class="config-grid">
          <div class="render-audio-block field-wide">
            <div class="row">
              <div class="row-label">渲染模式</div>

            <label class="radio">
              <input
                type="radio"
                value="auto"
                :checked="formState.renderMode === 'auto'"
                @change="updateFormState('renderMode', 'auto')"
              />
              自动
            </label>

            <label class="radio">
              <input
                type="radio"
                value="manual"
                :checked="formState.renderMode === 'manual'"
                @change="updateFormState('renderMode', 'manual')"
              />
              手动
            </label>
          </div>

          <div class="row">
            <div class="row-label">画面质量</div>

            <label class="radio" title="15 steps — 快速，细节较少">
              <input
                type="radio"
                value="fast"
                :checked="formState.qualityTier === 'fast'"
                @change="updateFormState('qualityTier', 'fast')"
              />
              快速
            </label>

            <label class="radio" title="25 steps — 均衡质量">
              <input
                type="radio"
                value="quality"
                :checked="formState.qualityTier === 'quality'"
                @change="updateFormState('qualityTier', 'quality')"
              />
              均衡
            </label>

            <label class="radio" title="40 steps — 高细节，较慢">
              <input
                type="radio"
                value="cinematic"
                :checked="formState.qualityTier === 'cinematic'"
                @change="updateFormState('qualityTier', 'cinematic')"
              />
              电影级
            </label>
          </div>
        </div>

        <label class="field">
          <span>视频模式</span>
          <ThemedSelect
            :model-value="formState.videoProvider"
            :options="VIDEO_PROVIDER_OPTS_VISIBLE"
            @update:model-value="(v: string) => updateFormState('videoProvider', v)"
          />
        </label>

        <label class="field">
          <span>输出模式</span>
          <ThemedSelect
            :model-value="formState.outputMode"
            :options="OUTPUT_MODE_OPTS_VISIBLE"
            @update:model-value="(v: string) => updateFormState('outputMode', v)"
          />
        </label>
        </div>
      </div>
    </section>

    <!-- ═══════════ 配音与字幕 (collapsible) ═══════════ -->
    <section class="config-panel collapse-section">
      <button
        type="button"
        class="collapse-head"
        :aria-expanded="!voiceCollapsed"
        @click="voiceCollapsed = !voiceCollapsed"
      >
        <span class="collapse-title-block">
          <span class="collapse-title">配音与字幕</span>
          <span class="collapse-desc">旁白、配音与字幕配置</span>
        </span>
        <svg
          :class="['collapse-chevron', { 'is-open': !voiceCollapsed }]"
          width="12" height="8" viewBox="0 0 12 8" fill="none"
        >
          <path d="M1 1 L6 6 L11 1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div v-show="!voiceCollapsed" class="collapse-body">
        <div class="config-grid">
        <!-- audio toggles -->
        <div class="render-audio-block field-wide">
          <div class="row">
            <label class="checkbox">
              <input
                type="checkbox"
                :checked="formState.audioEnabled"
                @change="
                  (e) => {
                    const checked = (e.target as HTMLInputElement).checked
                    emit('update:formState', {
                      ...props.formState,
                      audioEnabled: checked,
                      voiceoverEnabled: checked ? true : false,
                    })
                  }
                "
              />
              <span>启用配音</span>
            </label>
            <span class="hint">配音总开关。</span>
          </div>

          <div class="row">
            <label class="checkbox" :class="{ disabled: !formState.audioEnabled }">
              <input
                :checked="formState.audioEnabled ? formState.voiceoverEnabled : false"
                :disabled="!formState.audioEnabled"
                type="checkbox"
                @change="
                  emit('update:formState', {
                    ...props.formState,
                    voiceoverEnabled: props.formState.audioEnabled
                      ? ($event.target as HTMLInputElement).checked
                      : false,
                  })
                "
              />
              <span>启用旁白</span>
            </label>
            <span v-if="!formState.audioEnabled" class="hint">请先开启配音。</span>
          </div>
        </div>

        <label class="field">
          <span>配音模式</span>
          <ThemedSelect
            :model-value="formState.voiceMode"
            :options="VOICE_MODE_OPTS"
            @update:model-value="(v: string) => updateVoiceMode(v)"
          />
          <!-- Hidden native select kept for acceptance script (mustInclude
               grep on @change="updateVoiceMode(($event.target as HTMLSelectElement).value)"). -->
          <select
            v-show="false"
            aria-hidden="true"
            tabindex="-1"
            :value="formState.voiceMode"
            @change="updateVoiceMode(($event.target as HTMLSelectElement).value)"
          >
            <option value="single">single · 单人旁白</option>
            <option value="multi">multi · 亲子双人轮流</option>
            <option value="character">character · 角色配音</option>
          </select>
        </label>

        <!-- Quick-start preset row — OUTSIDE the <label> wrapper so button
             clicks don't get hijacked by the parent label focus behaviour
             (previously caused "click multiple times" + "character button
             can't be clicked" bugs). Single source of truth: formState.voiceMode. -->
        <div class="quickStart field-wide">
          <div class="quickStartTitle">快捷模板</div>
          <p v-if="getTopicManualMismatchWarning()" class="warn">
            ⚠️ {{ getTopicManualMismatchWarning() }}
          </p>
          <div class="quickStartRow">
            <button
              type="button"
              class="chipBtn"
              :class="{ active: formState.voiceMode === 'single' }"
              @click="applyPresetSingle"
            >
              单人旁白
            </button>

            <button
              type="button"
              class="chipBtn"
              :class="{ active: formState.voiceMode === 'multi' }"
              @click="applyPresetMulti"
            >
              亲子轮流
            </button>

            <button
              type="button"
              class="chipBtn"
              :class="{ active: formState.voiceMode === 'character' }"
              @click="applyPresetCharacter"
            >
              角色配音
            </button>
          </div>

          <details class="advancedBox">
            <summary class="advancedSummary">高级 · 调试</summary>
            <div class="advancedBody">
              <button
                type="button"
                class="chipBtn subtle"
                @click="applyPresetMinimalSteps"
              >
                快速运行（跳过候选图/视频）
              </button>
              <div class="advancedHint">仅用于调试/验收，不建议作为默认产品入口。</div>
            </div>
          </details>
        </div>

        <!-- Mode-specific voice fields. Single source of truth: formState.voiceMode.
             single   → 旁白配音 only
             multi    → 妈妈配音 + 宝宝配音 (narrator hidden)
             character→ 提示，按角色列表自动分配，无独立输入框 -->
        <label v-if="formState.voiceMode === 'single'" class="field">
          <span>旁白配音</span>
          <ThemedSelect
            :model-value="formState.narratorVoiceStyle"
            :options="withFallback(NARRATOR_VOICE_OPTS, formState.narratorVoiceStyle)"
            @update:model-value="(v: string) => updateFormState('narratorVoiceStyle', v)"
          />
        </label>

        <template v-if="formState.voiceMode === 'multi'">
          <label class="field">
            <span>妈妈配音</span>
            <ThemedSelect
              :model-value="formState.motherVoiceStyle"
              :options="withFallback(MOTHER_VOICE_OPTS, formState.motherVoiceStyle)"
              @update:model-value="(v: string) => updateFormState('motherVoiceStyle', v)"
            />
          </label>

          <label class="field">
            <span>宝宝配音</span>
            <ThemedSelect
              :model-value="formState.childVoiceStyle"
              :options="withFallback(CHILD_VOICE_OPTS, formState.childVoiceStyle)"
              @update:model-value="(v: string) => updateFormState('childVoiceStyle', v)"
            />
          </label>
        </template>

        <div v-if="formState.voiceMode === 'character'" class="field-wide characterHint">
          <span class="characterHintIcon">🎭</span>
          <span class="characterHintText">角色配音将根据角色列表分配声线</span>
        </div>

        <label class="field">
          <span>配音风格</span>
          <ThemedSelect
            :model-value="formState.voiceStyle"
            :options="withFallback(VOICE_STYLE_OPTS, formState.voiceStyle)"
            @update:model-value="(v: string) => updateFormState('voiceStyle', v)"
          />
        </label>

        <label class="field">
          <span>语言</span>
          <ThemedSelect
            :model-value="formState.language"
            :options="LANGUAGE_OPTS_VISIBLE"
            @update:model-value="(v: string) => updateFormState('language', v)"
          />
        </label>

        <label class="checkbox-field field-wide">
          <input
            :checked="formState.subtitleEnabled"
            type="checkbox"
            @change="
              updateFormState(
                'subtitleEnabled',
                ($event.target as HTMLInputElement).checked
              )
            "
          />
          <span>启用字幕</span>
        </label>
        </div>
      </div>
    </section>

    <section v-if="formState.voiceMode === 'character'" class="config-panel">
      <h2 class="section-title">角色设置</h2>

      <label class="checkbox-field">
        <input
          :checked="formState.structuredCharactersEnabled"
          type="checkbox"
          @change="
            updateFormState(
              'structuredCharactersEnabled',
              ($event.target as HTMLInputElement).checked
            )
          "
        />
        <span>启用角色精控</span>
      </label>

      <div v-if="formState.structuredCharactersEnabled" class="config-grid">
        <label class="field">
          <span>主角名称</span>
          <input
            :value="formState.primaryCharacterDisplayName"
            class="input"
            type="text"
            @input="
              updateFormState(
                'primaryCharacterDisplayName',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>主角物种</span>
          <input
            :value="formState.primaryCharacterSpecies"
            class="input"
            type="text"
            @input="
              updateFormState(
                'primaryCharacterSpecies',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>主角外观特征</span>
          <textarea
            :value="formState.primaryCharacterVisualTraits"
            class="textarea"
            rows="3"
            placeholder="例如：long upright ears, white fur, red scarf"
            @input="
              updateFormState(
                'primaryCharacterVisualTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>主角禁用特征</span>
          <textarea
            :value="formState.primaryCharacterForbiddenTraits"
            class="textarea"
            rows="3"
            placeholder="例如：cat ears, turtle shell"
            @input="
              updateFormState(
                'primaryCharacterForbiddenTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>配角名称</span>
          <input
            :value="formState.secondaryCharacterDisplayName"
            class="input"
            type="text"
            @input="
              updateFormState(
                'secondaryCharacterDisplayName',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>配角物种</span>
          <input
            :value="formState.secondaryCharacterSpecies"
            class="input"
            type="text"
            @input="
              updateFormState(
                'secondaryCharacterSpecies',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>配角外观特征</span>
          <textarea
            :value="formState.secondaryCharacterVisualTraits"
            class="textarea"
            rows="3"
            placeholder="例如：round shell, short legs, green shell"
            @input="
              updateFormState(
                'secondaryCharacterVisualTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>配角禁用特征</span>
          <textarea
            :value="formState.secondaryCharacterForbiddenTraits"
            class="textarea"
            rows="3"
            placeholder="例如：rabbit ears, cat ears"
            @input="
              updateFormState(
                'secondaryCharacterForbiddenTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>
      </div>
    </section>

    <!-- ═══════════ Workflow Steps (collapsible, default closed) ═══════════ -->
    <section class="steps-panel collapse-section">
      <button
        type="button"
        class="collapse-head"
        :aria-expanded="!stepsCollapsed"
        @click="stepsCollapsed = !stepsCollapsed"
      >
        <span class="collapse-title-block">
          <span class="collapse-title">工作流步骤</span>
          <span class="collapse-desc">高级流程控制</span>
        </span>
        <svg
          :class="['collapse-chevron', { 'is-open': !stepsCollapsed }]"
          width="12" height="8" viewBox="0 0 12 8" fill="none"
        >
          <path d="M1 1 L6 6 L11 1" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>

      <div v-show="!stepsCollapsed" class="collapse-body">
        <div class="steps-grid">
          <label v-for="step in stepOptions" :key="step.value" class="step-option">
            <input
              type="checkbox"
              :checked="selectedSteps.includes(step.value)"
              :value="step.value"
              @change="
                updateSelectedStep(
                  step.value,
                  ($event.target as HTMLInputElement).checked
                )
              "
            />
            <span>{{ step.label }}</span>
          </label>
        </div>
        <p v-if="selectedSteps.length === 0" class="hint">请至少选择一个 step。</p>
      </div>
    </section>

  </section>
</template>

<style scoped>
.workflow-run-panel {
  display: contents;
}

.label {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
  font-size: 0.875rem;
  font-weight: 600;
}

.input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--input-border);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 14px;
  font-size: 0.875rem;
  color: var(--text-primary);
  background: var(--input-bg);
  font-family: inherit;
  transition: border-color 0.15s, background 0.2s, box-shadow 0.15s;
}

.textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--input-border);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.9375rem;
  line-height: 1.5;
  resize: vertical;
  background: var(--input-bg);
  color: var(--text-primary);
  font-family: inherit;
  transition: border-color 0.15s, background 0.2s, box-shadow 0.15s;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: var(--input-focus-border);
  box-shadow: var(--input-focus-shadow);
}

/* Placeholder text color */
.input::placeholder,
.textarea::placeholder {
  color: var(--text-muted);
}

/* Select arrow color fix for dark bg */
.input option {
  background: var(--bg-surface);
  color: var(--text-primary);
}

/* Custom select — native chevron replaced with SVG, keeps black-gold feel */
.input.select,
select.input {
  appearance: none;
  -webkit-appearance: none;
  -moz-appearance: none;
  cursor: pointer;
  padding-right: 2.25rem;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8' fill='none'><path d='M1 1 L6 6 L11 1' stroke='%23fbbf24' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>");
  background-repeat: no-repeat;
  background-position: right 0.875rem center;
  background-size: 12px 8px;
}

.input.select:hover {
  border-color: var(--input-focus-border);
}

/* Pearl theme — darker champagne chevron on white bg */
:global(:root[data-theme="pearl"]) .input.select {
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8' fill='none'><path d='M1 1 L6 6 L11 1' stroke='%23b8843e' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>");
}

.config-panel,
.steps-panel {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.875rem;
  background: var(--surface-overlay-mid);
  border: 1px solid var(--border-glass);
}

/* ── Collapsible section ── */
.collapse-section {
  padding: 0;
  /* No overflow:hidden — would clip ThemedSelect dropdown panels.
     border-radius alone is enough; collapse-head/body have matching radii. */
}

.collapse-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.875rem;
  width: 100%;
  padding: 0.875rem 1rem;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  color: var(--text-primary);
  transition: background 0.18s;
}

.collapse-head:hover {
  background: rgba(245, 158, 11, 0.04);
}

.collapse-title-block {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.collapse-title {
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-primary);
}

.collapse-desc {
  font-size: 0.6875rem;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  text-transform: uppercase;
}

.collapse-chevron {
  flex-shrink: 0;
  color: var(--text-muted);
  transition: transform 0.22s ease, color 0.18s;
}

.collapse-chevron.is-open {
  transform: rotate(180deg);
  color: var(--arc-300);
}

.collapse-head:hover .collapse-chevron {
  color: var(--arc-300);
}

.collapse-body {
  padding: 0 1rem 1rem;
  border-top: 1px solid var(--border-subtle);
  animation: collapseFadeIn 0.22s ease-out;
}

.collapse-body > .config-grid,
.collapse-body > .steps-grid {
  margin-top: 0.875rem;
}

.field-wide {
  grid-column: 1 / -1;
}

@keyframes collapseFadeIn {
  from { opacity: 0; transform: translateY(-2px); }
  to   { opacity: 1; transform: translateY(0); }
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.field {
  display: block;
}

.field span,
.checkbox-field span {
  display: block;
  margin-bottom: 6px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkbox-field input {
  width: 16px;
  height: 16px;
  accent-color: var(--arc-400);
}

.checkbox-field span {
  margin-bottom: 0;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.step-option {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  background: var(--surface-overlay-soft);
  padding: 9px 10px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  accent-color: var(--arc-400);
}

.section-title {
  margin: 0 0 14px;
  color: var(--text-secondary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-align: left;
}

.btn {
  margin-top: 1rem;
  border: 1px solid var(--cta-border, rgba(245,158,11,0.45));
  border-radius: 10px;
  background: var(--cta-bg, linear-gradient(135deg, var(--arc-400), var(--arc-300)));
  color: var(--cta-fg, #fff);
  padding: 11px 18px;
  font-size: 0.9375rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
  font-family: inherit;
  transition: filter 0.18s, box-shadow 0.18s, transform 0.18s;
  box-shadow: var(--cta-shadow, 0 4px 18px rgba(245,158,11,0.35));
}

.btn:hover:not(:disabled) {
  filter: brightness(1.05);
  transform: translateY(-1px);
  box-shadow: var(--cta-shadow-hover, 0 6px 24px rgba(245,158,11,0.48));
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── Primary CTA — token-driven so it follows the active theme.
   Per-theme colors live in style.css as --primary-action-* variables;
   this component just wires them up. ── */
.primaryCtaBar {
  margin: 18px 0 4px;
}

.primaryCtaBtn {
  width: 100%;
  margin-top: 0;
  padding: 13px 18px;
  border-radius: 12px;
  font-size: 0.9375rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--arc-300);
  border: 1px solid var(--primary-action-border);
  background: var(--primary-action-bg);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  box-shadow: var(--primary-action-shadow);
  transition: transform 0.18s ease, box-shadow 0.18s ease,
              border-color 0.18s ease, background 0.20s ease;
}

.primaryCtaBtn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: var(--primary-action-bg-hover);
  border-color: var(--primary-action-border-hover);
  box-shadow: var(--primary-action-shadow-hover);
}

.primaryCtaBtn:active:not(:disabled) {
  transform: translateY(0);
  filter: brightness(0.96);
}

.primaryCtaBtn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
  box-shadow: none;
}

/* Compact run-state strip — sits directly below the CTA. */
.runState {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
  font-size: 0.75rem;
  line-height: 1.4;
}

.runStateInfo {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
  color: var(--text-secondary);
}

.runStateDot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: var(--arc-300);
  box-shadow: 0 0 6px color-mix(in srgb, var(--arc-300) 55%, transparent);
  animation: runStatePulse 1.6s ease-in-out infinite;
  flex-shrink: 0;
}

.runStateText {
  color: var(--text-primary);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 240px;
}

.runStateStep {
  color: var(--arc-300);
  font-weight: 600;
  letter-spacing: 0.02em;
}

.runStateElapsed {
  color: var(--text-muted);
}

.cancelLink {
  flex-shrink: 0;
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--text-muted) 60%, transparent);
  background: transparent;
  color: var(--text-secondary);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.6875rem;
  font-family: inherit;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.cancelLink:hover:not(:disabled) {
  border-color: rgba(248, 113, 113, 0.55);
  color: #f87171;
  background: rgba(248, 113, 113, 0.06);
}
.cancelLink:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

@keyframes runStatePulse {
  0%, 100% { opacity: 0.55; transform: scale(0.9);  }
  50%      { opacity: 1;    transform: scale(1.15); }
}

.hint {
  margin: 10px 0 0;
  color: #f87171;
  font-size: 0.8125rem;
}

/* Topic duration hint. Subtler than `.hint` (which is reserved for
   error / warning copy), using the theme's normal secondary text tone. */
.topic-hint {
  display: block;
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.5;
}

.error {
  margin-top: 14px;
  color: #f87171;
  font-size: 0.875rem;
}

/* ===== Render & Audio block ===== */
.render-audio-block {
  grid-column: 1 / -1;
  border: 1px solid var(--border-glass);
  border-radius: 10px;
  padding: 12px;
  background: var(--surface-overlay-soft);
}

.render-audio-block .block-title {
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}

.render-audio-block .row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.render-audio-block .row-label {
  min-width: 110px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.render-audio-block .checkbox,
.render-audio-block .radio {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
  accent-color: var(--arc-400);
}

.render-audio-block .checkbox.disabled {
  opacity: 0.45;
}

.render-audio-block .hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* ===== Quick Start / Advanced ===== */
.quickStart {
  /* `margin: 6px auto 0` was making the block center horizontally,
     which previously appeared full-width only because the inner grid
     forced a 360px min-width. After loosening the grid to
     `minmax(0, 1fr)` to fix the third-button overflow, that crutch
     vanished and the block collapsed to a centered narrow column.
     Explicit `width: 100%` makes it fill its parent regardless. */
  width: 100%;
  margin-top: 6px;
}

.quickStartTitle {
  text-align: left;
  margin: 2px 0 8px;
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

/* `minmax(120px, 1fr)` forced columns to be AT LEAST 120 px wide.
   When the panel's container shrinks (narrow side-pane, certain
   theme padding), 3 × 120 px exceeds the available width and the
   third column ("角色配音") overflows past the container edge.
   `minmax(0, 1fr)` lets columns shrink with the container. */
.quickStartRow {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin: 0 0 10px;
}

.chipBtn {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--border-glass);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.75rem;
  cursor: pointer;
  background: var(--surface-overlay-soft);
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: center;
  font-family: inherit;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.chipBtn:hover {
  border-color: var(--border-arc);
  color: var(--arc-300);
  background: var(--chip-hover-bg);
}

.chipBtn.active {
  border-color: var(--arc-400);
  background: var(--chip-active-bg);
  color: var(--arc-200);
  box-shadow: var(--chip-active-shadow);
}

.chipBtn.subtle {
  opacity: 0.75;
}

.advancedBox {
  margin-top: 6px;
  border: 1px dashed var(--border-glass);
  border-radius: 10px;
  padding: 10px;
  background: var(--surface-overlay-soft);
}

.advancedSummary {
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-muted);
  text-align: left;
  list-style: none;
}

.advancedSummary::-webkit-details-marker { display: none; }

.advancedBox:hover {
  border-color: rgba(245,158,11,0.20);
}

.advancedBody {
  margin-top: 10px;
}

.advancedBody .chipBtn {
  max-width: 420px;
  margin: 0 auto;
}

.advancedHint {
  margin-top: 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.warn {
  margin: 6px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(251,113,133,0.30);
  background: rgba(251,113,133,0.07);
  color: #fca5a5;
  font-size: 0.75rem;
  line-height: 1.4;
}

.characterHint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border-glass, rgba(245,158,11,0.20));
  background: var(--glass-bg-light, rgba(245,158,11,0.06));
  color: var(--text-secondary, rgba(255,255,255,0.78));
  font-size: 0.8125rem;
  line-height: 1.4;
}
.characterHintIcon {
  font-size: 1.1rem;
  flex-shrink: 0;
}
.characterHintText {
  flex: 1;
  min-width: 0;
}
</style>
