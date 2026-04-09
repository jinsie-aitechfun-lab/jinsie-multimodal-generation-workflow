<script setup lang="ts">
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

const props = defineProps<{
  loading: boolean
  canSubmit: boolean
  errorMessage: string

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

  selectedSteps: StepName[]
  stepOptions: Array<{ label: string; value: StepName }>
}>()

const emit = defineEmits<{
  (e: 'update:sessionId', value: string): void
  (e: 'update:topic', value: string): void
  (e: 'update:audience', value: string): void
  (e: 'update:tone', value: string): void
  (e: 'update:visualStyle', value: string): void
  (e: 'update:characterStyle', value: string): void
  (e: 'update:voiceStyle', value: string): void
  (e: 'update:voiceoverEnabled', value: boolean): void
  (e: 'update:voiceMode', value: string): void
  (e: 'update:narratorVoiceStyle', value: string): void
  (e: 'update:motherVoiceStyle', value: string): void
  (e: 'update:childVoiceStyle', value: string): void
  (e: 'update:durationSec', value: number): void
  (e: 'update:language', value: string): void
  (e: 'update:subtitleEnabled', value: boolean): void
  (e: 'update:videoProvider', value: string): void
  (e: 'update:outputMode', value: string): void

  (e: 'update:structuredCharactersEnabled', value: boolean): void
  (e: 'update:primaryCharacterDisplayName', value: string): void
  (e: 'update:primaryCharacterSpecies', value: string): void
  (e: 'update:primaryCharacterVisualTraits', value: string): void
  (e: 'update:primaryCharacterForbiddenTraits', value: string): void
  (e: 'update:secondaryCharacterDisplayName', value: string): void
  (e: 'update:secondaryCharacterSpecies', value: string): void
  (e: 'update:secondaryCharacterVisualTraits', value: string): void
  (e: 'update:secondaryCharacterForbiddenTraits', value: string): void

  (e: 'update:selectedSteps', value: StepName[]): void
  (e: 'run'): void
}>()

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
</script>

<template>
  <section class="workflow-run-panel">
    <label class="label" for="session-id">Session ID</label>
    <input
      id="session-id"
      :value="sessionId"
      class="input"
      type="text"
      placeholder="请输入会话标识，例如 demo-session-001"
      @input="emit('update:sessionId', ($event.target as HTMLInputElement).value)"
    />

    <label class="label" for="topic">Topic</label>
    <textarea
      id="topic"
      :value="topic"
      class="textarea"
      rows="4"
      placeholder="请输入一个主题，例如：写一个关于小猫冒险的故事"
      @input="emit('update:topic', ($event.target as HTMLTextAreaElement).value)"
    />

    <section class="config-panel">
      <h2 class="section-title">Generation Config</h2>

      <div class="config-grid">
        <label class="field">
          <span>Audience</span>
          <input
            :value="audience"
            class="input"
            type="text"
            @input="emit('update:audience', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Tone</span>
          <input
            :value="tone"
            class="input"
            type="text"
            @input="emit('update:tone', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Visual Style</span>
          <input
            :value="visualStyle"
            class="input"
            type="text"
            @input="emit('update:visualStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Character Style</span>
          <input
            :value="characterStyle"
            class="input"
            type="text"
            @input="emit('update:characterStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Voice Style</span>
          <input
            :value="voiceStyle"
            class="input"
            type="text"
            @input="emit('update:voiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="checkbox-field">
          <input
            :checked="voiceoverEnabled"
            type="checkbox"
            @change="emit('update:voiceoverEnabled', ($event.target as HTMLInputElement).checked)"
          />
          <span>Enable Voiceover</span>
        </label>

        <label class="field">
          <span>Voice Mode</span>
          <select
            :value="voiceMode"
            class="input"
            @change="emit('update:voiceMode', ($event.target as HTMLSelectElement).value)"
          >
            <option value="single">single</option>
            <option value="multi">multi</option>
          </select>
        </label>

        <label class="field">
          <span>Narrator Voice</span>
          <input
            :value="narratorVoiceStyle"
            class="input"
            type="text"
            @input="emit('update:narratorVoiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label v-if="voiceMode === 'multi'" class="field">
          <span>Mother Voice</span>
          <input
            :value="motherVoiceStyle"
            class="input"
            type="text"
            @input="emit('update:motherVoiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label v-if="voiceMode === 'multi'" class="field">
          <span>Child Voice</span>
          <input
            :value="childVoiceStyle"
            class="input"
            type="text"
            @input="emit('update:childVoiceStyle', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Duration (sec)</span>
          <input
            :value="durationSec"
            class="input"
            type="number"
            min="15"
            max="300"
            @input="emit('update:durationSec', Number(($event.target as HTMLInputElement).value))"
          />
        </label>

        <label class="field">
          <span>Language</span>
          <input
            :value="language"
            class="input"
            type="text"
            @input="emit('update:language', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Video Provider</span>
          <input
            :value="videoProvider"
            class="input"
            type="text"
            @input="emit('update:videoProvider', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="field">
          <span>Output Mode</span>
          <input
            :value="outputMode"
            class="input"
            type="text"
            @input="emit('update:outputMode', ($event.target as HTMLInputElement).value)"
          />
        </label>

        <label class="checkbox-field">
          <input
            :checked="subtitleEnabled"
            type="checkbox"
            @change="emit('update:subtitleEnabled', ($event.target as HTMLInputElement).checked)"
          />
          <span>Enable Subtitles</span>
        </label>
      </div>
    </section>

    <section class="config-panel">
      <h2 class="section-title">Character Finalization</h2>

      <label class="checkbox-field">
        <input
          :checked="structuredCharactersEnabled"
          type="checkbox"
          @change="
            emit(
              'update:structuredCharactersEnabled',
              ($event.target as HTMLInputElement).checked
            )
          "
        />
        <span>Enable Structured Characters</span>
      </label>

      <div v-if="structuredCharactersEnabled" class="config-grid">
        <label class="field">
          <span>Primary Character Display Name</span>
          <input
            :value="primaryCharacterDisplayName"
            class="input"
            type="text"
            @input="
              emit(
                'update:primaryCharacterDisplayName',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Primary Character Species</span>
          <input
            :value="primaryCharacterSpecies"
            class="input"
            type="text"
            @input="
              emit(
                'update:primaryCharacterSpecies',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Primary Visual Traits</span>
          <textarea
            :value="primaryCharacterVisualTraits"
            class="textarea"
            rows="3"
            placeholder="例如：long upright ears, white fur, red scarf"
            @input="
              emit(
                'update:primaryCharacterVisualTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Primary Forbidden Traits</span>
          <textarea
            :value="primaryCharacterForbiddenTraits"
            class="textarea"
            rows="3"
            placeholder="例如：cat ears, turtle shell"
            @input="
              emit(
                'update:primaryCharacterForbiddenTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Secondary Character Display Name</span>
          <input
            :value="secondaryCharacterDisplayName"
            class="input"
            type="text"
            @input="
              emit(
                'update:secondaryCharacterDisplayName',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Secondary Character Species</span>
          <input
            :value="secondaryCharacterSpecies"
            class="input"
            type="text"
            @input="
              emit(
                'update:secondaryCharacterSpecies',
                ($event.target as HTMLInputElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Secondary Visual Traits</span>
          <textarea
            :value="secondaryCharacterVisualTraits"
            class="textarea"
            rows="3"
            placeholder="例如：round shell, short legs, green shell"
            @input="
              emit(
                'update:secondaryCharacterVisualTraits',
                ($event.target as HTMLTextAreaElement).value
              )
            "
          />
        </label>

        <label class="field">
          <span>Secondary Forbidden Traits</span>
          <textarea
            :value="secondaryCharacterForbiddenTraits"
            class="textarea"
            rows="3"
            placeholder="例如：rabbit ears, cat ears"
            @input="
              emit(
                'update:secondaryCharacterForbiddenTraits',
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
</style>