<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InspirationItem, InspirationKind } from '../data/inspirationLibrary'
import { INSPIRATION_ITEMS, KIND_META } from '../data/inspirationLibrary'

type FilterValue = 'all' | InspirationKind

const FILTERS: Array<{ value: FilterValue; label: string }> = [
  { value: 'all',       label: '全部' },
  { value: 'package',   label: '完整套餐' },
  { value: 'character', label: '角色形象' },
  { value: 'style',     label: '画面风格' },
  { value: 'template',  label: '故事模板' },
]

const emit = defineEmits<{
  (e: 'apply', item: InspirationItem): void
}>()

const activeFilter = ref<FilterValue>('all')
const activeItem = ref<InspirationItem | null>(null)

interface SectionGroup {
  kind: InspirationKind
  items: InspirationItem[]
}

// `package` first so it renders as the hero section.
const groupedItems = computed<SectionGroup[]>(() => {
  const kinds: InspirationKind[] = ['package', 'character', 'style', 'template']
  return kinds
    .filter((kind) => activeFilter.value === 'all' || activeFilter.value === kind)
    .map((kind) => ({
      kind,
      items: INSPIRATION_ITEMS.filter((item) => item.kind === kind),
    }))
})

function openDetail(item: InspirationItem) {
  activeItem.value = item
}

function closeDetail() {
  activeItem.value = null
}

function applyAndClose(item: InspirationItem) {
  emit('apply', item)
  closeDetail()
}

function kindLabel(kind: InspirationKind): string {
  return KIND_META[kind].label
}

function ctaLabel(kind: InspirationKind): string {
  if (kind === 'package')   return '一键应用套餐'
  if (kind === 'character') return '用此角色创作'
  if (kind === 'style')     return '用此风格创作'
  return '用此模板创作'
}

function padIndex(n: number): string {
  return String(n + 1).padStart(2, '0')
}

/* Spotlight cursor effect — writes the live mouse position (relative
   to the card) into two CSS custom properties on the card itself.
   The CSS uses them as the centre of a radial gradient overlay so
   the card appears "lit" by a soft gold glow that follows the
   cursor. Linear / Vercel landing-page signature move. */
function onCardMouseMove(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement | null
  if (!el) return
  const rect = el.getBoundingClientRect()
  const x = ((event.clientX - rect.left) / rect.width) * 100
  const y = ((event.clientY - rect.top) / rect.height) * 100
  el.style.setProperty('--spot-x', `${x}%`)
  el.style.setProperty('--spot-y', `${y}%`)
  // Fade the spotlight in on first move so the card doesn't pop on
  // re-entry; CSS handles the actual transition.
  el.style.setProperty('--spot-opacity', '1')
}
function onCardMouseLeave(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement | null
  if (!el) return
  el.style.setProperty('--spot-opacity', '0')
}
</script>

<template>
  <section class="inspiration-panel">
    <header class="inspiration-head">
      <div class="kicker">
        <span class="kicker-line"></span>
        <span class="kicker-text">INSPIRATION · 灵感参考</span>
      </div>
      <h2 class="inspiration-title">挑一个起点，3 秒进入创作</h2>
      <p class="inspiration-desc">
        每张卡片是一组预设的创作配置——点击"用此创作"，跳回创作页并自动填入对应角色、画风或故事模板，
        把"从零填表"的 5 分钟压缩到一次点击。
      </p>
    </header>

    <nav class="inspiration-filter" aria-label="灵感分类">
      <button
        v-for="filter in FILTERS"
        :key="filter.value"
        type="button"
        class="filter-pill"
        :class="{ active: activeFilter === filter.value }"
        @click="activeFilter = filter.value"
      >
        {{ filter.label }}
      </button>
    </nav>

    <div class="inspiration-sections">
      <section
        v-for="group in groupedItems"
        :key="group.kind"
        class="inspiration-section"
      >
        <div v-if="activeFilter === 'all'" class="section-header">
          <div class="section-icon-badge" aria-hidden="true">
            <span class="section-icon-glyph">{{ KIND_META[group.kind].icon }}</span>
          </div>
          <div class="section-header-text">
            <div class="section-header-top">
              <div class="section-title-block">
                <span class="section-eyebrow-mini">
                  {{ KIND_META[group.kind].eyebrow }}
                </span>
                <h3 class="section-title">{{ KIND_META[group.kind].label }}</h3>
              </div>
              <span class="section-count">{{ group.items.length }} 个</span>
            </div>
            <p class="section-desc">{{ KIND_META[group.kind].description }}</p>
          </div>
        </div>

        <ul class="inspiration-grid">
          <li
            v-for="(item, index) in group.items"
            :key="item.id"
            class="inspiration-card"
            :class="{ 'inspiration-card--package': item.kind === 'package' }"
            tabindex="0"
            :style="{ '--card-stagger': `${index * 60}ms` }"
            @click="openDetail(item)"
            @keydown.enter="openDetail(item)"
            @keydown.space.prevent="openDetail(item)"
            @mousemove="onCardMouseMove($event)"
            @mouseleave="onCardMouseLeave($event)"
          >
            <div class="card-head">
              <span class="card-eyebrow">
                {{ KIND_META[item.kind].eyebrow }} · {{ padIndex(index) }}
              </span>
              <span class="card-head-right">
                <span v-if="item.kind === 'package'" class="card-pill">一键就绪</span>
                <span class="card-icon" aria-hidden="true">{{ item.icon }}</span>
              </span>
            </div>

            <div class="card-body">
              <h3 class="card-title">{{ item.title }}</h3>
              <p class="card-subtitle">{{ item.subtitle }}</p>
            </div>

            <dl class="card-preview">
              <div
                v-for="row in item.preview"
                :key="row.label"
                class="preview-row"
              >
                <dt class="preview-label">{{ row.label }}</dt>
                <dd class="preview-value">{{ row.value }}</dd>
              </div>
            </dl>

            <div class="card-foot">
              <ul class="card-tags">
                <li v-for="tag in item.tags" :key="tag" class="card-tag">{{ tag }}</li>
              </ul>
              <span class="card-cta-pill" aria-hidden="true">
                查看详情 <span class="card-cta-arrow">→</span>
              </span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <Teleport to="body">
      <div
        v-if="activeItem"
        class="modal-backdrop detail-backdrop"
        role="dialog"
        aria-modal="true"
        :aria-label="activeItem.title"
        @click.self="closeDetail"
      >
        <section class="detail-modal">
          <button
            type="button"
            class="detail-close"
            aria-label="关闭详情"
            @click="closeDetail"
          >×</button>

          <header class="detail-head">
            <span class="detail-eyebrow">
              {{ KIND_META[activeItem.kind].eyebrow }} · {{ kindLabel(activeItem.kind) }}
            </span>
            <div class="detail-head-row">
              <h3 class="detail-title">{{ activeItem.title }}</h3>
              <span class="detail-icon" aria-hidden="true">{{ activeItem.icon }}</span>
            </div>
            <p class="detail-subtitle">{{ activeItem.subtitle }}</p>
          </header>

          <div class="detail-body">
            <p class="detail-description">{{ activeItem.description }}</p>

            <div class="detail-block">
              <span class="detail-block-label">自动填入</span>
              <dl class="detail-preview">
                <div
                  v-for="row in activeItem.preview"
                  :key="row.label"
                  class="preview-row preview-row-large"
                >
                  <dt class="preview-label">{{ row.label }}</dt>
                  <dd class="preview-value">{{ row.value }}</dd>
                </div>
              </dl>
            </div>

            <details class="detail-block detail-block-collapsible">
              <summary class="detail-block-summary">
                完整字段（开发者视图）
              </summary>
              <ul class="prefill-raw-list">
                <li
                  v-for="(value, key) in activeItem.prefill"
                  :key="String(key)"
                  class="prefill-raw-row"
                >
                  <code class="prefill-raw-key">{{ key }}</code>
                  <span class="prefill-raw-value">{{ String(value) }}</span>
                </li>
              </ul>
            </details>

            <div class="detail-tags-block">
              <span class="detail-block-label">标签</span>
              <ul class="detail-tags">
                <li v-for="tag in activeItem.tags" :key="tag" class="detail-tag">{{ tag }}</li>
              </ul>
            </div>
          </div>

          <footer class="detail-foot">
            <button type="button" class="detail-cancel" @click="closeDetail">关闭</button>
            <button
              type="button"
              class="detail-apply"
              @click="applyAndClose(activeItem)"
            >
              {{ ctaLabel(activeItem.kind) }} →
            </button>
          </footer>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
.inspiration-panel {
  padding: 0;
}

/* ── Header ─────────────────────────────────────────── */

.inspiration-head {
  margin-bottom: 28px;
}

.kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.kicker-line {
  width: 28px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--border-arc),
    transparent
  );
}
.kicker-text {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--arc-300);
}

.inspiration-title {
  margin: 4px 0 10px;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--text-primary);
}

.inspiration-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text-secondary);
}

/* ── Filter pills ───────────────────────────────────── */

.inspiration-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 28px;
}
.filter-pill {
  height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition:
    background 0.15s ease,
    border-color 0.15s ease,
    color 0.15s ease;
}
.filter-pill:hover {
  border-color: var(--border-arc);
  color: var(--text-primary);
}
.filter-pill.active {
  background: color-mix(in srgb, var(--arc-300) 16%, transparent);
  border-color: var(--arc-300);
  color: var(--arc-300);
}

/* ── Sections ───────────────────────────────────────── */

.inspiration-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* Section container — subtle glass frame that "grounds" the section
   header so it doesn't read as floating white text on the page bg.
   Wraps both the title block and the card grid; cards inside still
   have their own surface treatment, so there's a clear two-level
   hierarchy: section frame (outer, very faint) → cards (inner, more
   defined). */
.inspiration-section {
  padding: 28px 24px 30px;
  border-radius: 18px;
  border: 1px solid var(--border-subtle);
  background:
    linear-gradient(180deg, var(--surface-overlay-soft), transparent 30%),
    var(--surface-overlay-soft);
}

/* Section header — left-aligned "collection page chapter head".
   Gold circular icon badge anchors the left edge; title block lives
   on the right with an English eyebrow above the Chinese title, plus
   a count chip floating right. Reads as a real "section header" not a
   floating label. */
.section-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 24px;
}

/* The icon badge — circular, gold-bordered, holds a single Unicode
   glyph per kind (◆ / ✦ / ❖). Adds visible decoration without going
   childish; matches the abstract glyph style used by the studio
   sidebar tabs. */
.section-icon-badge {
  flex: 0 0 auto;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background:
    radial-gradient(
      circle at 30% 25%,
      color-mix(in srgb, var(--arc-300) 22%, transparent),
      transparent 65%
    ),
    var(--surface-overlay-soft);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 14%, transparent),
    0 0 18px color-mix(in srgb, var(--arc-300) 12%, transparent);
}
.section-icon-glyph {
  font-size: 1.125rem;
  color: var(--arc-300);
  line-height: 1;
}

.section-header-text {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 1px;
}
.section-header-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}
.section-title-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.section-eyebrow-mini {
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: var(--arc-300);
  opacity: 0.85;
}
.section-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.005em;
  color: var(--text-primary);
  line-height: 1.25;
}
.section-count {
  flex: 0 0 auto;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-subtle);
  background: var(--surface-overlay-soft);
  margin-top: 12px;
}
.section-desc {
  margin: 4px 0 0;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--text-muted);
}

/* ── Card grid ──────────────────────────────────────── */

.inspiration-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
}

@media (max-width: 1180px) {
  .inspiration-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 880px) {
  .inspiration-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 540px) {
  .inspiration-grid { grid-template-columns: 1fr; }
}

/* Card — text-led. Uses theme tokens so dark + pearl both work. The
   value sold by the card is the *preview rows*, not a decorative
   cover, so the surface stays calm and lets typography lead.
   ── Two interaction polishes layered on top ──
   1. Stagger entrance: each card fades + lifts in 60ms after the
      previous one, driven by the inline `--card-stagger` style set
      in the template (v-for index × 60). Single-shot animation;
      doesn't re-fire on filter switch.
   2. Spotlight cursor: a radial gold gradient pseudo-element follows
      the mouse, centred on the live --spot-x / --spot-y the script
      writes on mousemove. Reads as a soft "card under a torch"
      effect — premium without being noisy. */
.inspiration-card {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 20px 20px 18px;
  border-radius: 16px;
  border: 1px solid var(--border-glass);
  background:
    linear-gradient(180deg, var(--surface-overlay-soft), transparent 70%),
    var(--bg-elevated);
  cursor: pointer;
  overflow: hidden;
  transition:
    transform 0.2s ease,
    border-color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
  /* Local custom props with defaults — keeps the CSS valid even when
     the mousemove handler hasn't fired yet (i.e. before the cursor
     enters the card). */
  --spot-x: 50%;
  --spot-y: 50%;
  --spot-opacity: 0;
  --card-stagger: 0ms;
  animation: card-enter 0.55s cubic-bezier(0.2, 0.8, 0.2, 1) both;
  animation-delay: var(--card-stagger);
}
/* Spotlight overlay — sits above the card surface but below the
   content (z-index 0 on this layer, content is z-index auto/1).
   Opacity is driven from JS via --spot-opacity so hover state
   doesn't flicker on tiny mouse moves outside the card. */
.inspiration-card::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(
    280px circle at var(--spot-x) var(--spot-y),
    color-mix(in srgb, var(--arc-300) 22%, transparent) 0%,
    transparent 60%
  );
  opacity: var(--spot-opacity);
  pointer-events: none;
  transition: opacity 0.25s ease;
  z-index: 0;
}
/* Content stacks above the spotlight overlay. */
.inspiration-card > * {
  position: relative;
  z-index: 1;
}
@keyframes card-enter {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
/* Respect reduced-motion users — skip stagger + spotlight transition. */
@media (prefers-reduced-motion: reduce) {
  .inspiration-card {
    animation: none;
  }
  .inspiration-card::after {
    transition: none;
  }
}
/* Thin gold accent line at top — same design language as landing-page
   eyebrows. Adapts to both themes via the arc token. */
.inspiration-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 20px;
  right: 20px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    var(--border-arc),
    transparent
  );
  opacity: 0.7;
  pointer-events: none;
  transition: opacity 0.2s ease;
}
.inspiration-card:hover,
.inspiration-card:focus-visible {
  transform: translateY(-2px);
  border-color: var(--border-arc);
  background:
    linear-gradient(180deg, var(--surface-overlay-mid), transparent 70%),
    var(--bg-float);
  box-shadow:
    0 16px 36px var(--surface-overlay-strong),
    0 0 0 1px color-mix(in srgb, var(--arc-300) 8%, transparent);
  outline: none;
}
.inspiration-card:hover::before,
.inspiration-card:focus-visible::before {
  opacity: 1;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}
.card-eyebrow {
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: var(--arc-300);
}
.card-icon {
  font-size: 1.125rem;
  line-height: 1;
  opacity: 0.65;
  flex: 0 0 auto;
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.inspiration-card:hover .card-icon {
  opacity: 0.95;
  transform: scale(1.1);
}

/* Right cluster in the card head — pill + icon stacked horizontally so
   the pill sits next to the icon, not under the eyebrow. */
.card-head-right {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}

/* "一键就绪" tag on package cards. Tiny pill, gold tint, doesn't
   compete with the title — it's a value-prop badge, not a CTA. */
.card-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-400) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--arc-300) 35%, transparent);
  color: var(--arc-200);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  white-space: nowrap;
}

/* Package cards get a slightly more saturated border / shadow than
   character/style/template cards — they're the headline kind. The
   spotlight hover effect from `.inspiration-card::before` still works
   on top of this, so hover still feels premium. */
.inspiration-card--package {
  border-color: color-mix(in srgb, var(--arc-300) 38%, var(--border-glass));
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.28),
              inset 0 0 0 1px color-mix(in srgb, var(--arc-300) 14%, transparent);
}
.inspiration-card--package:hover,
.inspiration-card--package:focus-visible {
  border-color: color-mix(in srgb, var(--arc-300) 55%, var(--border-glass));
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.34),
              inset 0 0 0 1px color-mix(in srgb, var(--arc-300) 22%, transparent);
}

.card-body {
  margin-bottom: 16px;
}
.card-title {
  margin: 0 0 5px;
  font-size: 1.0625rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.005em;
  line-height: 1.3;
}
.card-subtitle {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Preview rows — the hero content. Shows what the click will configure,
   in human-readable form. This is the actual value of the card. */
.card-preview {
  margin: 0 0 16px;
  padding: 14px 0;
  border-top: 1px solid var(--border-subtle);
  border-bottom: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.preview-row {
  display: grid;
  grid-template-columns: 4.5em 1fr;
  gap: 12px;
  align-items: baseline;
  font-size: 0.75rem;
  line-height: 1.5;
}
.preview-label {
  margin: 0;
  font-size: 0.6875rem;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  white-space: nowrap;
}
.preview-value {
  margin: 0;
  color: var(--text-secondary);
  font-weight: 500;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-foot {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: auto;
}
.card-tags {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.card-tag {
  font-size: 0.625rem;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--surface-overlay-soft);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  letter-spacing: 0.02em;
}

/* Card CTA chip — affords "this card is clickable" with a real pill
   shape. Whole card remains clickable; this just makes the affordance
   unmistakable. Uses arc tokens so dark = bright gold, pearl = deep
   champagne — both read correctly against the card surface. */
.card-cta-pill {
  align-self: flex-end;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-300) 10%, transparent);
  color: var(--arc-300);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}
.card-cta-arrow {
  font-size: 0.875rem;
  line-height: 1;
  transition: transform 0.2s ease;
}
.inspiration-card:hover .card-cta-pill,
.inspiration-card:focus-visible .card-cta-pill {
  background: color-mix(in srgb, var(--arc-300) 22%, transparent);
  border-color: var(--arc-300);
}
.inspiration-card:hover .card-cta-arrow,
.inspiration-card:focus-visible .card-cta-arrow {
  transform: translateX(3px);
}

/* ── Detail modal ───────────────────────────────────── */

.detail-backdrop {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.detail-modal {
  position: relative;
  width: min(560px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  border-radius: 18px;
  border: 1px solid var(--border-arc);
  /* Frosted-glass surface: a translucent base (78% bg + 22% nothing)
     combined with the modal's own backdrop-filter means whatever is
     behind blurs into a soft wash of color through the modal — the
     "premium macOS sheet" effect. The gradient overlay on top gives
     a subtle inner highlight from the upper edge. */
  background:
    linear-gradient(180deg, var(--surface-overlay-soft), transparent 50%),
    color-mix(in srgb, var(--bg-elevated) 78%, transparent);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  box-shadow: 0 32px 72px var(--surface-overlay-strong);
}

.detail-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid var(--border-glass);
  background: var(--surface-overlay-soft);
  color: var(--text-primary);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.detail-close:hover {
  background: var(--surface-overlay-mid);
  border-color: var(--border-arc);
}

.detail-head {
  padding: 28px 28px 20px;
  border-bottom: 1px solid var(--border-subtle);
}
.detail-eyebrow {
  display: block;
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.26em;
  text-transform: uppercase;
  color: var(--arc-300);
  margin-bottom: 10px;
}
.detail-head-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 6px;
}
.detail-title {
  flex: 1 1 auto;
  margin: 0;
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.005em;
}
.detail-icon {
  flex: 0 0 auto;
  font-size: 1.25rem;
  opacity: 0.7;
}
.detail-subtitle {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
  line-height: 1.5;
}

.detail-body {
  padding: 22px 28px 8px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.detail-description {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.75;
  color: var(--text-secondary);
}

.detail-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.detail-block-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.detail-preview {
  margin: 0;
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--surface-overlay-soft);
  border: 1px solid var(--border-glass);
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.preview-row-large {
  grid-template-columns: 6em 1fr;
  font-size: 0.8125rem;
}
.preview-row-large .preview-label {
  font-size: 0.75rem;
}

.detail-block-collapsible {
  border-radius: 10px;
  background: var(--surface-overlay-soft);
  border: 1px solid var(--border-subtle);
  padding: 10px 14px;
}
.detail-block-summary {
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--arc-300);
  list-style: none;
  padding: 4px 0;
}
.detail-block-summary::-webkit-details-marker { display: none; }
.detail-block-summary::before {
  content: '▸';
  display: inline-block;
  margin-right: 6px;
  transition: transform 0.15s;
}
.detail-block-collapsible[open] .detail-block-summary::before {
  transform: rotate(90deg);
}
.prefill-raw-list {
  list-style: none;
  padding: 10px 0 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow: auto;
}
.prefill-raw-row {
  display: flex;
  gap: 10px;
  align-items: baseline;
  font-size: 0.75rem;
  line-height: 1.5;
}
.prefill-raw-key {
  flex: 0 0 auto;
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Consolas,
    monospace;
  font-size: 0.6875rem;
  color: var(--arc-300);
  background: color-mix(in srgb, var(--arc-300) 12%, transparent);
  border: 1px solid var(--border-subtle);
  padding: 1px 6px;
  border-radius: 4px;
}
.prefill-raw-value {
  flex: 1 1 auto;
  min-width: 0;
  color: var(--text-secondary);
  word-break: break-all;
}

.detail-tags-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-tags {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.detail-tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 0.75rem;
  background: var(--surface-overlay-soft);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.detail-foot {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 16px 28px 24px;
  border-top: 1px solid var(--border-subtle);
}
.detail-cancel,
.detail-apply {
  height: 40px;
  padding: 0 20px;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s,
    transform 0.1s;
}
.detail-cancel {
  border: 1px solid var(--border-glass);
  background: transparent;
  color: var(--text-secondary);
}
.detail-cancel:hover {
  border-color: var(--border-arc);
  color: var(--text-primary);
}
.detail-apply {
  border: 1px solid var(--arc-300);
  background: color-mix(in srgb, var(--arc-300) 16%, transparent);
  color: var(--arc-300);
}
.detail-apply:hover {
  background: color-mix(in srgb, var(--arc-300) 30%, transparent);
}
.detail-apply:active { transform: translateY(1px); }
</style>
