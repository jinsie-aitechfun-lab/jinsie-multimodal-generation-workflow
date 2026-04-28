<script setup lang="ts">
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

export type WorkflowRunFormState = {
  sessionId: string
  topic: string
  audience: string
  tone: string
  visualStyle: string
  characterStyle: string
  voiceStyle: string
  voiceoverEnabled: boolean
  voiceMode: string
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
}

const props = defineProps<{
  loading: boolean
  canSubmit: boolean
  errorMessage: string
  formState: WorkflowRunFormState
  selectedSteps: StepName[]
  stepOptions: Array<{ label: string; value: StepName }>
}>()

const emit = defineEmits<{
  (e: 'update:formState', value: WorkflowRunFormState): void
  (e: 'update:selectedSteps', value: StepName[]): void
  (e: 'run'): void
}>()

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
    voiceoverEnabled: true,
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
    voiceoverEnabled: true,
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
    voiceoverEnabled: true,
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
    <label class="label" for="session-id">Session ID</label>
    <input
      id="session-id"
      :value="formState.sessionId"
      class="input"
      type="text"
      placeholder="请输入会话标识，例如 demo-session-001"
      @input="updateFormState('sessionId', ($event.target as HTMLInputElement).value)"
    />

    <label class="label" for="topic">Topic</label>
    <textarea
      id="topic"
      :value="formState.topic"
      class="textarea"
      rows="4"
      placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      @input="updateFormState('topic', ($event.target as HTMLTextAreaElement).value)"
    />

    <section class="config-panel">
      <h2 class="section-title">Generation Config</h2>

      <div class="config-grid">
        <label class="field">
          <span>Audience</span>
          <input
            :value="formState.audience"
            class="input"
            type="text"
            @input="updateFormState('audience', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Tone</span>
          <input
            :value="formState.tone"
            class="input"
            type="text"
            @input="updateFormState('tone', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Visual Style</span>
          <input
            :value="formState.visualStyle"
            class="input"
            type="text"
            @input="updateFormState('visualStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Character Style</span>
          <input
            :value="formState.characterStyle"
            class="input"
            type="text"
            @input="updateFormState('characterStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Voice Style</span>
          <input
            :value="formState.voiceStyle"
            class="input"
            type="text"
            @input="updateFormState('voiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="checkbox-field">
          <input
            :checked="formState.voiceoverEnabled"
            type="checkbox"
            @change="
              updateFormState(
                'voiceoverEnabled',
                ($event.target as HTMLInputElement).checked
              )
            "
          />
          <span>Enable Voiceover</span>
        </label>

        <label class="field">
          <span>Voice Mode</span>

          <select
            :value="formState.voiceMode"
            class="input"
            @change="updateVoiceMode(($event.target as HTMLSelectElement).value)"
          >
            <option value="single">single · 单人旁白</option>
            <option value="multi">multi · 亲子双人轮流</option>
            <option value="character">character · 角色配音</option>
          </select>

          <div class="quickStart">
            <div class="quickStartTitle">Quick Start · 快捷模板</div>
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
              <summary class="advancedSummary">Advanced · 调试</summary>
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
        </label>

        <label class="field">
          <span>
            {{
              formState.voiceMode === 'single'
                ? 'Narrator Voice · 单人旁白'
                : 'Narrator Voice · 旁白'
            }}
          </span>
          <input
            :value="formState.narratorVoiceStyle"
            class="input"
            type="text"
            @input="
              updateFormState('narratorVoiceStyle', ($event.target as HTMLInputElement).value)
            "
          />
        </label>

        <template v-if="formState.voiceMode === 'multi'">
          <label class="field">
            <span>Mother Voice · 妈妈配音</span>
            <input
              :value="formState.motherVoiceStyle"
              class="input"
              type="text"
              @input="
                updateFormState('motherVoiceStyle', ($event.target as HTMLInputElement).value)
              "
            />
          </label>

          <label class="field">
            <span>Child Voice · 宝宝配音</span>
            <input
              :value="formState.childVoiceStyle"
              class="input"
              type="text"
              @input="
                updateFormState('childVoiceStyle', ($event.target as HTMLInputElement).value)
              "
            />
          </label>
        </template>

        <template v-if="formState.voiceMode === 'character'">
          <label class="field">
            <span>Main Character Voice · 主角色配音</span>
            <input
              :value="formState.childVoiceStyle"
              class="input"
              type="text"
              @input="
                updateFormState('childVoiceStyle', ($event.target as HTMLInputElement).value)
              "
            />
          </label>

          <label class="field">
            <span>Secondary Character Voice · 次角色配音</span>
            <input
              :value="formState.motherVoiceStyle"
              class="input"
              type="text"
              @input="
                updateFormState('motherVoiceStyle', ($event.target as HTMLInputElement).value)
              "
            />
          </label>
        </template>

        <label class="field">
          <span>Duration (sec)</span>
          <input
            :value="formState.durationSec"
            class="input"
            type="number"
            min="15"
            max="300"
            @input="
              updateFormState(
                'durationSec',
                Number(($event.target as HTMLInputElement).value)
              )
            "
          />
        </label>

        <label class="field">
          <span>Language</span>
          <input
            :value="formState.language"
            class="input"
            type="text"
            @input="updateFormState('language', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Video Provider</span>
          <input
            :value="formState.videoProvider"
            class="input"
            type="text"
            @input="updateFormState('videoProvider', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Output Mode</span>
          <input
            :value="formState.outputMode"
            class="input"
            type="text"
            @input="updateFormState('outputMode', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="checkbox-field">
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
          <span>Enable Subtitles</span>
        </label>
      </div>
    </section>

    <section v-if="formState.voiceMode === 'character'" class="config-panel">
      <h2 class="section-title">Character Finalization</h2>

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
        <span>Enable Structured Characters</span>
      </label>

      <div v-if="formState.structuredCharactersEnabled" class="config-grid">
        <label class="field">
          <span>Primary Character Display Name</span>
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
          <span>Primary Character Species</span>
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
          <span>Primary Visual Traits</span>
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
          <span>Primary Forbidden Traits</span>
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
          <span>Secondary Character Display Name</span>
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
          <span>Secondary Character Species</span>
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
          <span>Secondary Visual Traits</span>
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
          <span>Secondary Forbidden Traits</span>
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

    <section class="steps-panel">
      <h2 class="section-title">Workflow Steps</h2>
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
    </section>

    <button class="btn" :disabled="!canSubmit" @click="emit('run')">
      {{ loading ? '请求中...' : 'Run Workflow' }}
    </button>

    <p v-if="errorMessage" class="error">请求失败：{{ errorMessage }}</p>
  </section>
</template>

<style scoped>
.workflow-run-panel {
  display: contents;
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

.input:focus,
.textarea:focus {
  outline: none;
  border-color: #111827;
}

.config-panel,
.steps-panel {
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
  gap: 10px;
}

.checkbox-field input {
  width: 16px;
  height: 16px;
}

.checkbox-field span {
  margin-bottom: 0;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.step-option {
  display: flex;
  align-items: center;
  gap: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  padding: 10px 12px;
  font-size: 14px;
  color: #111827;
}

.section-title {
  margin: 0 0 16px;
  color: #111827;
  font-size: 18px;
  text-align: left;
}

.btn {
  margin-top: 20px;
  border: none;
  border-radius: 12px;
  background: #111827;
  color: #ffffff;
  padding: 12px 18px;
  font-size: 15px;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin: 12px 0 0;
  color: #dc2626;
  font-size: 13px;
}

.error {
  margin-top: 16px;
  color: #dc2626;
  font-size: 14px;
}

/* Quick Start / Advanced (minimal UI, product-friendly) */
.quickStart {
  margin: 6px auto 0;
  max-width: 760px;
}

.quickStartTitle {
  text-align: left;
  margin: 2px 0 8px 0;
  color: #111827;
  font-size: 12px;
  font-weight: 600;
  opacity: 0.85;
}

.quickStartRow {
  display: grid;
  grid-template-columns: repeat(3, minmax(140px, 180px));
  gap: 10px;
  justify-content: center;
  margin: 0 0 10px 0;
}

.chipBtn {
  width: 100%;
  border: 1px solid rgba(0, 0, 0, 0.12);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
  background: #fff;
  white-space: nowrap;
  text-align: center;
  transition: background 120ms ease, border-color 120ms ease, color 120ms ease;
}

.chipBtn:hover {
  border-color: rgba(0, 0, 0, 0.22);
  background: rgba(17, 24, 39, 0.03);
}

.chipBtn.active {
  border-color: #111827;
  background: #111827;
  color: #ffffff;
}

.chipBtn.subtle {
  opacity: 0.85;
}

.advancedBox {
  max-width: 760px;
  margin-top: 6px;
  margin-left: auto;
  margin-right: auto;
  border: 1px dashed rgba(0, 0, 0, 0.18);
  border-radius: 12px;
  padding: 10px 10px;
  background: rgba(255, 255, 255, 0.7);
}

.advancedSummary {
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  color: #111827;
  opacity: 0.85;
  text-align: left;
}

.advancedBox:hover {
  border-color: rgba(0, 0, 0, 0.24);
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
  font-size: 12px;
  color: #111827;
  opacity: 0.7;
}
.warn {
  margin: 6px 0 0 0;
  padding: 10px 12px;
  border-radius: 12px;
  border: 1px solid rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.06);
  color: #991b1b;
  font-size: 12px;
  line-height: 1.4;
}
</style>