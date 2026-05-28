<script setup lang="ts">
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
}>()

const emit = defineEmits<{
  (e: 'update:formState', v: WorkflowRunFormState): void
  (e: 'update:selectedSteps', v: StepName[]): void
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

    <section class="config-panel">
      <h2 class="section-title">生成配置</h2>

      <div class="config-grid">
        <label class="field">
          <span>受众群体</span>
          <input
            :value="formState.audience"
            class="input"
            type="text"
            @input="updateFormState('audience', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>故事风格</span>
          <input
            :value="formState.tone"
            class="input"
            type="text"
            @input="updateFormState('tone', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>视觉风格</span>
          <input
            :value="formState.visualStyle"
            class="input"
            type="text"
            @input="updateFormState('visualStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>角色风格</span>
          <input
            :value="formState.characterStyle"
            class="input"
            type="text"
            @input="updateFormState('characterStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>配音风格</span>
          <input
            :value="formState.voiceStyle"
            class="input"
            type="text"
            @input="updateFormState('voiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <!-- ===== Render & Audio controls (UI-only layout) ===== -->
        <div class="render-audio-block">
          <div class="block-title">渲染 & 音频</div>

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
        </label>

        <label class="field">
          <span>
            旁白配音
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
            <span>妈妈配音</span>
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
            <span>宝宝配音</span>
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
            <span>主角配音</span>
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
            <span>配角配音</span>
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
          <span>视频时长（秒）</span>
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
          <span class="hint">推荐默认 120 秒；支持 60 / 120 / 180 秒。</span>
        </label>

        <label class="field">
          <span>语言</span>
          <input
            :value="formState.language"
            class="input"
            type="text"
            @input="updateFormState('language', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>视频模式</span>
          <select
            :value="formState.videoProvider"
            class="input"
            @change="updateFormState('videoProvider', ($event.target as HTMLSelectElement).value)"
          >
            <option value="mock">绘本视频模式</option>
            <option value="storybook">分镜播放模式</option>
          </select>
        </label>

        <label class="field">
          <span>输出模式</span>
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
          <span>启用字幕</span>
        </label>
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

    <section class="steps-panel">
      <h2 class="section-title">工作步骤</h2>
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

    <p v-if="errorMessage" class="error">请求失败：{{ errorMessage }}</p>

    <div class="stickyCtaBar">
      <button class="btn stickyCtaBtn" :disabled="!canSubmit" @click="emit('run')">
        {{ loading ? '生成中…' : '开始创作' }}
      </button>
    </div>
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

.config-panel,
.steps-panel {
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 0.875rem;
  background: var(--surface-overlay-mid);
  border: 1px solid var(--border-glass);
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

.stickyCtaBar {
  position: sticky;
  bottom: 16px;
  margin-top: 14px;
  padding: 0;
  background: transparent;
  z-index: 20;
}

.stickyCtaBtn {
  width: 100%;
  margin-top: 0;
}

.hint {
  margin: 10px 0 0;
  color: #f87171;
  font-size: 0.8125rem;
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
  margin: 6px auto 0;
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

.quickStartRow {
  display: grid;
  grid-template-columns: repeat(3, minmax(120px, 1fr));
  gap: 8px;
  margin: 0 0 10px;
}

.chipBtn {
  width: 100%;
  border: 1px solid var(--border-glass);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 0.75rem;
  cursor: pointer;
  background: var(--surface-overlay-soft);
  color: var(--text-secondary);
  white-space: nowrap;
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
</style>