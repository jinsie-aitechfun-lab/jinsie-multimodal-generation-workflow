<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  storyText: string
  /** Raw JSON of the story step output (LLM text + title + provider
   *  metadata + fallback_reason etc). Shown in the "故事" section as
   *  the source-of-truth for what the story step actually produced. */
  storyOutputText: string
  storyboardText: string
  imagePromptsText: string
  imageAssetsText: string
  imageReviewText: string
  videoPromptsText: string
  narrationText: string
  subtitlesText: string
  renderPlanText: string
  characterCandidatesText: string
  characterManifestText: string
}>()

type SceneSummary = {
  id: string
  title: string
  description: string
}

type PromptSummary = {
  id: string
  prompt: string
}

function parseJson(text: string): unknown {
  if (!text.trim()) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

function stringifyValue(value: unknown): string {
  if (typeof value === 'string') return value
  if (value == null) return ''
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

/* Split a Kolors prompt string on its native separator (`; ` then `;`
   then `. `) so the wall-of-text becomes a scannable list. The pieces
   themselves are kept verbatim — the prompt sent to the model is
   still the original concatenated string; this is display-only.
   Filters out blanks introduced by trailing separators. */
function splitPromptFragments(prompt: string): string[] {
  if (!prompt) return []
  return prompt
    .split(/[;。](?:\s+|$)/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
}

/* Classify a fragment so different rule families get different visual
   weight. Negative constraints (must-avoid / do-not) get a softer
   warning tint; identity / role descriptors get a gold accent so the
   "who's this about" lines stand out. */
function promptFragmentClass(fragment: string): string {
  const f = fragment.toLowerCase()
  if (
    f.startsWith('must avoid') ||
    f.startsWith('do not') ||
    f.includes('forbidden') ||
    f.includes('不要')
  ) {
    return 'prompt-fragment--avoid'
  }
  if (
    f.startsWith('must keep') ||
    f.startsWith('character ') ||
    f.startsWith('required ') ||
    f.includes('identity lock') ||
    f.includes('身份锁') ||
    f.includes('character trait lock')
  ) {
    return 'prompt-fragment--anchor'
  }
  return ''
}

const hasDeveloperContent = computed(() => Boolean(
  props.storyOutputText ||
  props.storyText ||
  props.storyboardText ||
  props.imagePromptsText ||
  props.imageAssetsText ||
  props.imageReviewText ||
  props.videoPromptsText ||
  props.narrationText ||
  props.subtitlesText ||
  props.renderPlanText ||
  props.characterCandidatesText ||
  props.characterManifestText
))

const storyboardScenes = computed<SceneSummary[]>(() => {
  const parsed = parseJson(props.storyboardText)
  const record = parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : {}
  const scenesValue: unknown[] = Array.isArray(record.scenes)
    ? record.scenes
    : record.storyboard && typeof record.storyboard === 'object' && Array.isArray((record.storyboard as Record<string, unknown>).scenes)
      ? (record.storyboard as Record<string, unknown>).scenes as unknown[]
      : []

  return scenesValue.map((scene, index) => {
    const item = scene && typeof scene === 'object' ? scene as Record<string, unknown> : {}
    const fallbackId = `场景 ${String(index + 1).padStart(2, '0')}`
    const id = String(item.scene_id || item.id || fallbackId)
    const title = String(item.title || item.scene_title || item.stage || fallbackId)
    const description = String(
      item.narration ||
      item.voiceover ||
      item.description ||
      item.visual_description ||
      item.action ||
      ''
    )
    return { id, title, description }
  })
})

const imagePromptEntries = computed<PromptSummary[]>(() => {
  const parsed = parseJson(props.imagePromptsText)
  if (!parsed) return []

  const source = parsed && typeof parsed === 'object' && Array.isArray((parsed as Record<string, unknown>).prompts)
    ? (parsed as Record<string, unknown>).prompts
    : parsed

  if (Array.isArray(source)) {
    return source.map((entry, index) => {
      const item = entry && typeof entry === 'object' ? entry as Record<string, unknown> : {}
      return {
        id: String(item.scene_id || item.id || `场景 ${String(index + 1).padStart(2, '0')}`),
        prompt: stringifyValue(item.prompt || item.image_prompt || entry),
      }
    })
  }

  if (source && typeof source === 'object') {
    return Object.entries(source as Record<string, unknown>).map(([key, value]) => ({
      id: key,
      prompt: stringifyValue(
        value && typeof value === 'object'
          ? (value as Record<string, unknown>).prompt || (value as Record<string, unknown>).image_prompt || value
          : value
      ),
    }))
  }

  return []
})
</script>

<template>
  <section
    v-if="hasDeveloperContent"
    class="result-panel developer-results-panel"
  >
    <details>
      <summary>生成细节</summary>

      <section v-if="storyOutputText || storyText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">故事</summary>
          <p class="developer-explainer">
            LLM 第一步的产出——故事完整文本、自动生成的标题、所用 provider、是否走过 fallback 等元数据。后续所有分镜 / 角色 / 画面 prompt 都从这一步衍生。
          </p>
          <pre v-if="storyOutputText" class="light-result">{{ storyOutputText }}</pre>
          <pre v-else class="light-result">{{ storyText }}</pre>
        </details>
      </section>

      <section v-if="storyboardText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">分镜结构</summary>
          <p class="developer-explainer">
            把整个故事按场景拆解的结构化结果。每个场景包含场景标题、画面描述、镜头类型、转场方式、出场角色等元信息——后续画面 prompt 的生成依据。
          </p>
          <div v-if="storyboardScenes.length" class="scene-summary-list">
            <p class="developer-count-line">
              本次共生成 <strong>{{ storyboardScenes.length }}</strong> 个场景：
            </p>
            <article
              v-for="scene in storyboardScenes"
              :key="scene.id"
              class="scene-summary-card"
            >
              <strong>{{ scene.title }}</strong>
              <span>{{ scene.id }}</span>
              <p v-if="scene.description">{{ scene.description }}</p>
            </article>
          </div>
          <!-- Same raw-JSON pattern as the sibling sections below.
               Sits at the bottom of every section so every node of the
               pipeline reads the same way: 这是什么 → 这是数据. -->
          <pre class="light-result">{{ storyboardText }}</pre>
        </details>
      </section>

      <section v-if="imagePromptsText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">图片提示词</summary>
          <p class="developer-explainer">
            送给文生图模型（如 Kolors）的实际 prompt 文本，按场景一一对应。
            包含主体描述、视觉风格、角色身份锁、负面词等约束——决定每张候选图的样子。
          </p>
          <div v-if="imagePromptEntries.length" class="prompt-summary-list">
            <p class="developer-count-line">
              本次共生成 <strong>{{ imagePromptEntries.length }}</strong> 条 prompt，点击展开查看：
            </p>
            <details
              v-for="entry in imagePromptEntries"
              :key="entry.id"
              class="prompt-summary-item"
            >
              <summary>{{ entry.id }}</summary>
              <!-- Wall-of-text prompts (single line broken only by ';
                   ') are unreadable for a human even though they're
                   what Kolors wants. Split on the same separator and
                   render each rule on its own indented line —
                   semantics preserved (it's still the exact same
                   string concatenated by ';'), but scannable. -->
              <ul class="prompt-fragment-list">
                <li
                  v-for="(fragment, idx) in splitPromptFragments(entry.prompt)"
                  :key="idx"
                  class="prompt-fragment"
                  :class="promptFragmentClass(fragment)"
                >{{ fragment }}</li>
              </ul>
            </details>
          </div>
          <pre class="light-result">{{ imagePromptsText }}</pre>
        </details>
      </section>

      <!-- Pipeline-order siblings under 生成细节. Each is a self-
           contained section: title + one-line explainer + raw JSON.
           Same structure as 分镜结构/图片提示词 above (those just have
           an extra parsed view between explainer and raw), so the
           hierarchy reads as one consistent list of "workflow output
           nodes" instead of split into two awkward groups. -->

      <section v-if="characterCandidatesText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">角色候选</summary>
          <p class="developer-explainer">
            LLM 从主题文本里抽取出来的候选角色——名称、物种、是否主角。后续会沉淀为正式的「角色设定清单」。
          </p>
          <pre class="light-result">{{ characterCandidatesText }}</pre>
        </details>
      </section>

      <section v-if="characterManifestText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">角色设定清单</summary>
          <p class="developer-explainer">
            每个角色的视觉身份锁——必须保留的外观特征（must_keep）和必须避免的特征（must_avoid）。
            多角色场景下还携带跨角色的互斥约束（如「兔子不能有龟壳」），用于约束图像 prompt。
          </p>
          <pre class="light-result">{{ characterManifestText }}</pre>
        </details>
      </section>

      <section v-if="imageAssetsText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">图片素材</summary>
          <p class="developer-explainer">
            实际生成的候选图元数据——按场景分组，每场景两张 A/B 候选，包含文件路径、provider、是否被选中等信息。
          </p>
          <pre class="light-result">{{ imageAssetsText }}</pre>
        </details>
      </section>

      <section v-if="imageReviewText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">画面审核 / 素材选择</summary>
          <p class="developer-explainer">
            自动 selector 的打分结果 + 用户手动审核时的最终选择记录——每个场景最终选了 A 还是 B、是 auto 还是 manual。
          </p>
          <pre class="light-result">{{ imageReviewText }}</pre>
        </details>
      </section>

      <section v-if="narrationText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">旁白</summary>
          <p class="developer-explainer">
            送给 TTS 的旁白脚本——含完整文本、按场景切分的段落、每段的说话人和声线设定。
          </p>
          <pre class="light-result">{{ narrationText }}</pre>
        </details>
      </section>

      <section v-if="subtitlesText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">字幕</summary>
          <p class="developer-explainer">
            带时间轴的字幕条目——FFmpeg 合成时按这份时间轴把文字烧进视频。
          </p>
          <pre class="light-result">{{ subtitlesText }}</pre>
        </details>
      </section>

      <section v-if="videoPromptsText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">视频提示词</summary>
          <p class="developer-explainer">
            送给分镜视频 provider（如可灵 / 海螺）的 prompt 文本——v1 默认走绘本风，本节点只有在 v2 接入分镜视频 provider 时才会被消费。
          </p>
          <pre class="light-result">{{ videoPromptsText }}</pre>
        </details>
      </section>

      <section v-if="renderPlanText" class="developer-result-block">
        <details>
          <summary class="developer-subsummary">渲染计划</summary>
          <p class="developer-explainer">
            最终交给 FFmpeg 的合成方案——时间轴、转场、画面与音频的对齐关系。视频成片就是按这份计划渲染出来的。
          </p>
          <pre class="light-result">{{ renderPlanText }}</pre>
        </details>
      </section>
    </details>
  </section>
</template>

<style scoped>
.story-panel,
.result-panel {
  margin-top: 16px;
  padding: 18px 20px;
  border-radius: 14px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(150%);
  -webkit-backdrop-filter: blur(20px) saturate(150%);
  border: 1px solid rgba(245,158,11,0.12);
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), inset 0 1px 0 rgba(251,191,36,0.06);
}

.developer-results-panel summary {
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.developer-results-panel summary:hover {
  color: var(--arc-300);
}

.developer-result-block {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid rgba(245,158,11,0.08);
  /* Visual containment cue: a thin gold "tree-branch" rail on the
     left side shows that this block is a *child* of 生成细节, not a
     sibling. Without it the 3 inner sub-sections (分镜结构 / 图片
     提示词 / 开发者原始数据) read as same-level entries as 生成
     细节 itself, breaking the parent-child hierarchy on screen. */
  margin-left: 14px;
  padding-left: 16px;
  border-left: 2px solid color-mix(in srgb, var(--arc-300) 22%, transparent);
}

.developer-subsummary {
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}

.developer-subsummary:hover {
  color: var(--arc-300);
}

.scene-summary-list,
.prompt-summary-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
  /* Nested children of a sub-section (e.g. scene_01..scene_06 under
     图片提示词) need to read as deeper-nested than the sub-section
     itself. The sub-section already has its rail from the outer
     .developer-result-block; this adds a second smaller indent so
     the visual hierarchy goes: 生成细节 → 图片提示词 → scene_N. */
  margin-left: 10px;
  padding-left: 12px;
  border-left: 1px solid color-mix(in srgb, var(--arc-300) 14%, transparent);
}

.scene-summary-card,
.prompt-summary-item {
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--surface-overlay-strong);
  border: 1px solid rgba(245,158,11,0.08);
}

.scene-summary-card strong {
  display: block;
  color: var(--arc-300);
  font-size: 0.875rem;
  margin-bottom: 4px;
}

.scene-summary-card span {
  display: block;
  color: var(--text-muted);
  font-size: 0.75rem;
  margin-bottom: 6px;
}

.scene-summary-card p,
.prompt-summary-item p,
.developer-empty-copy {
  margin: 0;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* Explainer preamble — sits directly under the section's summary
   trigger, before any list. Tells the reader WHAT this thing is
   ("把整个故事按场景拆解的结构化结果...") so the section header
   alone isn't doing all the explanatory work. Styled as a soft
   info card, not as ordinary body text, so it reads as "meta /
   docs" rather than "content". */
.developer-explainer {
  margin: 12px 0 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: color-mix(in srgb, var(--arc-300) 6%, transparent);
  border-left: 2px solid color-mix(in srgb, var(--arc-300) 38%, transparent);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  line-height: 1.65;
}

/* Count line — "本次共生成 X 个场景" between the explainer and the
   list. Gives the user a "what to expect" preview before they start
   scrolling. */
.developer-count-line {
  margin: 6px 0 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}
.developer-count-line strong {
  color: var(--arc-300);
  font-weight: 700;
  margin: 0 2px;
}

.prompt-summary-item summary {
  color: var(--arc-300);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 700;
}

.prompt-summary-item p {
  margin-top: 8px;
}

/* Structured prompt view — each `;`-separated rule becomes a list
   item with its own bullet, indent and (when applicable) coloured
   tint based on classification: gold for identity/role anchors,
   muted red for "must avoid / do not" negative constraints. Plain
   rules stay in the default secondary text colour. */
.prompt-fragment-list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.prompt-fragment {
  position: relative;
  padding: 4px 0 4px 18px;
  font-size: 0.8125rem;
  line-height: 1.65;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  word-break: break-word;
}
.prompt-fragment::before {
  content: '◦';
  position: absolute;
  left: 4px;
  top: 4px;
  color: color-mix(in srgb, var(--arc-300) 55%, transparent);
  font-size: 0.75rem;
}
.prompt-fragment--anchor {
  color: color-mix(in srgb, var(--arc-200) 90%, var(--text-primary));
}
.prompt-fragment--anchor::before {
  content: '◆';
  color: var(--arc-300);
}
.prompt-fragment--avoid {
  color: color-mix(in srgb, #f87171 70%, var(--text-secondary));
}
.prompt-fragment--avoid::before {
  content: '⊘';
  color: #f87171;
}

.section-title {
  margin: 0 0 12px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.story-text {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
}

.light-result {
  margin: 8px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
  /* Cap each raw-JSON dump at ~6 lines worth (was unbounded — a
     full storyboard JSON could run 15+ screens, making it
     impossible to scroll back up to collapse the parent <details>).
     Internal scroll keeps the surrounding layout stable. */
  max-height: 360px;
  overflow: auto;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-overlay-soft);
  border: 1px solid var(--border-subtle);
}
/* Custom thin scrollbar so the boxed JSON doesn't feel "trapped" by
   the OS-default chunky scrollbar at this small surface. */
.light-result::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.light-result::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--arc-300) 32%, transparent);
  border-radius: 3px;
}
.light-result::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--arc-300) 56%, transparent);
}
.light-result::-webkit-scrollbar-track {
  background: transparent;
}
</style>
