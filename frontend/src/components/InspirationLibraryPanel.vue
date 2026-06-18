<script setup lang="ts">
import { computed, ref } from 'vue'
import type { InspirationItem, InspirationKind } from '../data/inspirationLibrary'
import { INSPIRATION_ITEMS, KIND_META } from '../data/inspirationLibrary'

type FilterValue = 'all' | InspirationKind

const FILTERS: Array<{ value: FilterValue; label: string }> = [
  { value: 'all',       label: '全部' },
  { value: 'character', label: '角色形象' },
  { value: 'style',     label: '画面风格' },
  { value: 'template',  label: '故事模板' },
]

const emit = defineEmits<{
  (e: 'apply', item: InspirationItem): void
}>()

const activeFilter = ref<FilterValue>('all')
const activeItem = ref<InspirationItem | null>(null)

const filteredItems = computed<InspirationItem[]>(() => {
  if (activeFilter.value === 'all') return INSPIRATION_ITEMS
  return INSPIRATION_ITEMS.filter((item) => item.kind === activeFilter.value)
})

// When showing the "全部" view, group by kind so the page reads as
// three distinct curated rails instead of a flat mixed grid. Premium
// product feel: clear section eyebrows + per-section description.
const groupedItems = computed<Array<{ kind: InspirationKind; items: InspirationItem[] }>>(() => {
  if (activeFilter.value !== 'all') {
    return [{ kind: activeFilter.value as InspirationKind, items: filteredItems.value }]
  }
  const kinds: InspirationKind[] = ['character', 'style', 'template']
  return kinds.map((kind) => ({
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
        预设的角色形象、画面风格与故事模板。点击"用此创作"会跳回创作页并自动填好对应设定，
        你只需要轻微调整就能开始生成。
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
        <div v-if="activeFilter === 'all'" class="section-eyebrow-row">
          <span class="section-eyebrow">{{ KIND_META[group.kind].eyebrow }}</span>
          <span class="section-eyebrow-line"></span>
          <span class="section-eyebrow-meta">
            {{ KIND_META[group.kind].label }} · {{ KIND_META[group.kind].description }}
          </span>
        </div>

        <ul class="inspiration-grid">
          <li
            v-for="item in group.items"
            :key="item.id"
            class="inspiration-card"
            tabindex="0"
            @click="openDetail(item)"
            @keydown.enter="openDetail(item)"
            @keydown.space.prevent="openDetail(item)"
          >
            <div class="card-cover" :style="{ background: item.gradient }">
              <span class="card-icon" aria-hidden="true">{{ item.icon }}</span>
              <span class="card-kind-badge">{{ kindLabel(item.kind) }}</span>
            </div>
            <div class="card-body">
              <h3 class="card-title">{{ item.title }}</h3>
              <p class="card-subtitle">{{ item.subtitle }}</p>
              <ul class="card-tags">
                <li v-for="tag in item.tags" :key="tag" class="card-tag">{{ tag }}</li>
              </ul>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <Teleport to="body">
      <div
        v-if="activeItem"
        class="detail-backdrop"
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

          <header class="detail-head" :style="{ background: activeItem.gradient }">
            <span class="detail-cover-icon" aria-hidden="true">{{ activeItem.icon }}</span>
            <div class="detail-head-text">
              <span class="detail-kind-badge">{{ kindLabel(activeItem.kind) }}</span>
              <h3 class="detail-title">{{ activeItem.title }}</h3>
              <p class="detail-subtitle">{{ activeItem.subtitle }}</p>
            </div>
          </header>

          <div class="detail-body">
            <p class="detail-description">{{ activeItem.description }}</p>

            <div class="detail-tags-block">
              <span class="detail-tags-label">标签</span>
              <ul class="detail-tags">
                <li v-for="tag in activeItem.tags" :key="tag" class="detail-tag">{{ tag }}</li>
              </ul>
            </div>

            <div class="detail-prefill-block">
              <span class="detail-tags-label">将自动应用的设定</span>
              <ul class="prefill-list">
                <li
                  v-for="(value, key) in activeItem.prefill"
                  :key="String(key)"
                  class="prefill-row"
                >
                  <code class="prefill-key">{{ key }}</code>
                  <span class="prefill-value">{{ String(value) }}</span>
                </li>
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
              用此{{ kindLabel(activeItem.kind).slice(0, 2) }}创作 →
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
  margin-bottom: 24px;
}

.kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.kicker-line {
  width: 28px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--arc-300) 60%, transparent),
    transparent
  );
}
.kicker-text {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--arc-300) 88%, transparent);
}

.inspiration-title {
  margin: 4px 0 8px;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.01em;
  color: var(--text-primary);
}

.inspiration-desc {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--text-secondary);
}

/* ── Filter pills ───────────────────────────────────── */

.inspiration-filter {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
}
.filter-pill {
  height: 32px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--arc-300) 24%, transparent);
  background: color-mix(in srgb, var(--arc-400) 4%, rgba(8, 7, 5, 0.4));
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
  border-color: color-mix(in srgb, var(--arc-300) 52%, transparent);
  color: var(--text-primary);
}
.filter-pill.active {
  background: color-mix(in srgb, var(--arc-300) 18%, transparent);
  border-color: color-mix(in srgb, var(--arc-300) 60%, transparent);
  color: var(--arc-200);
}

/* ── Sections ───────────────────────────────────────── */

.inspiration-sections {
  display: flex;
  flex-direction: column;
  gap: 28px;
}

.section-eyebrow-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}
.section-eyebrow {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--arc-300) 80%, transparent);
}
.section-eyebrow-line {
  flex: 0 0 24px;
  height: 1px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--arc-300) 36%, transparent),
    transparent
  );
}
.section-eyebrow-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

/* ── Card grid ──────────────────────────────────────── */

.inspiration-grid {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 1100px) {
  .inspiration-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 820px) {
  .inspiration-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 520px) {
  .inspiration-grid { grid-template-columns: 1fr; }
}

/* Card — dark base with thin gold top-hairline, gold-tinted border on
   hover. Designed to read as "native to the dark-gold theme" rather
   than as bright sticker tiles. */
.inspiration-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--arc-300) 14%, transparent);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 4%, rgba(10, 8, 5, 0.62)),
    color-mix(in srgb, var(--arc-400) 2%, rgba(6, 5, 3, 0.55))
  );
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}
/* Thin gold accent line at the very top — defines the dark-gold theme
   identity even when the cover gradient is muted. */
.inspiration-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 12px;
  right: 12px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--arc-300) 36%, transparent),
    transparent
  );
  z-index: 2;
  pointer-events: none;
}
.inspiration-card:hover,
.inspiration-card:focus-visible {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--arc-300) 44%, transparent);
  box-shadow:
    0 14px 36px rgba(0, 0, 0, 0.42),
    0 0 0 1px color-mix(in srgb, var(--arc-300) 18%, transparent),
    0 0 22px color-mix(in srgb, var(--arc-300) 16%, transparent);
  outline: none;
}

.card-cover {
  position: relative;
  aspect-ratio: 16 / 10;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
/* Inner highlight + bottom shadow lift the dark cover off the card. */
.card-cover::after {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(
      circle at 28% 24%,
      color-mix(in srgb, var(--arc-300) 12%, transparent),
      transparent 58%
    ),
    linear-gradient(
      180deg,
      transparent 60%,
      rgba(0, 0, 0, 0.32) 100%
    );
  pointer-events: none;
}
.card-icon {
  font-size: 2.625rem;
  line-height: 1;
  opacity: 0.72;
  filter:
    drop-shadow(0 2px 8px rgba(0, 0, 0, 0.55))
    drop-shadow(0 0 18px color-mix(in srgb, var(--arc-300) 26%, transparent));
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.inspiration-card:hover .card-icon {
  opacity: 0.92;
  transform: scale(1.06);
}
.card-kind-badge {
  position: absolute;
  top: 10px;
  left: 10px;
  z-index: 1;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(8, 7, 5, 0.62);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid color-mix(in srgb, var(--arc-300) 22%, transparent);
  color: color-mix(in srgb, var(--arc-200) 88%, transparent);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.card-body {
  padding: 14px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}
.card-title {
  margin: 0;
  font-size: 0.9375rem;
  font-weight: 600;
  color: color-mix(in srgb, var(--arc-200) 92%, var(--text-primary));
  letter-spacing: 0.01em;
}
.card-subtitle {
  margin: 0;
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--text-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-tags {
  list-style: none;
  padding: 0;
  margin: 4px 0 0;
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.card-tag {
  font-size: 0.625rem;
  padding: 2px 7px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--arc-400) 10%, rgba(8, 7, 5, 0.45));
  border: 1px solid color-mix(in srgb, var(--arc-300) 14%, transparent);
  color: color-mix(in srgb, var(--arc-200) 70%, var(--text-secondary));
  letter-spacing: 0.02em;
}

/* ── Detail modal ───────────────────────────────────── */

.detail-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(4, 3, 2, 0.72);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.detail-modal {
  position: relative;
  width: min(540px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--arc-300) 22%, transparent);
  background: linear-gradient(
    180deg,
    rgba(22, 18, 10, 0.96),
    rgba(12, 10, 6, 0.96)
  );
  box-shadow: 0 32px 72px rgba(0, 0, 0, 0.6);
}

.detail-close {
  position: absolute;
  top: 14px;
  right: 14px;
  z-index: 2;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: none;
  background: rgba(8, 7, 5, 0.6);
  color: rgba(255, 255, 255, 0.85);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  transition: background 0.15s;
}
.detail-close:hover {
  background: rgba(8, 7, 5, 0.9);
  color: #fff;
}

.detail-head {
  position: relative;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 28px 28px 24px;
  overflow: hidden;
}
.detail-head::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle at 20% 20%,
    rgba(255, 255, 255, 0.18),
    transparent 60%
  );
  pointer-events: none;
}
.detail-cover-icon {
  font-size: 3.5rem;
  line-height: 1;
  flex: 0 0 auto;
  filter: drop-shadow(0 2px 10px rgba(0, 0, 0, 0.45));
}
.detail-head-text {
  flex: 1 1 auto;
  min-width: 0;
}
.detail-kind-badge {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(8, 7, 5, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.9);
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.detail-title {
  margin: 0 0 4px;
  font-size: 1.25rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.98);
  letter-spacing: 0.01em;
}
.detail-subtitle {
  margin: 0;
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.78);
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
  line-height: 1.7;
  color: var(--text-secondary);
}

.detail-tags-block,
.detail-prefill-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.detail-tags-label {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--text-muted);
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
  background: color-mix(in srgb, var(--arc-300) 14%, transparent);
  color: color-mix(in srgb, var(--arc-200) 80%, var(--text-secondary));
}

.prefill-list {
  list-style: none;
  padding: 12px 14px;
  margin: 0;
  border-radius: 8px;
  background: rgba(8, 7, 5, 0.45);
  border: 1px solid color-mix(in srgb, var(--arc-300) 14%, transparent);
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow: auto;
}
.prefill-row {
  display: flex;
  gap: 10px;
  align-items: baseline;
  font-size: 0.75rem;
  line-height: 1.5;
}
.prefill-key {
  flex: 0 0 auto;
  font-family:
    ui-monospace,
    SFMono-Regular,
    Menlo,
    Consolas,
    monospace;
  font-size: 0.6875rem;
  color: var(--arc-300);
  background: color-mix(in srgb, var(--arc-300) 14%, transparent);
  padding: 1px 6px;
  border-radius: 4px;
}
.prefill-value {
  flex: 1 1 auto;
  min-width: 0;
  color: var(--text-secondary);
  word-break: break-all;
}

.detail-foot {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 16px 28px 24px;
}
.detail-cancel,
.detail-apply {
  height: 38px;
  padding: 0 18px;
  border-radius: 8px;
  font-size: 0.8125rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition:
    background 0.15s,
    border-color 0.15s,
    transform 0.1s;
}
.detail-cancel {
  border: 1px solid color-mix(in srgb, var(--arc-300) 22%, transparent);
  background: transparent;
  color: var(--text-secondary);
}
.detail-cancel:hover {
  border-color: color-mix(in srgb, var(--arc-300) 48%, transparent);
  color: var(--text-primary);
}
.detail-apply {
  border: 1px solid color-mix(in srgb, var(--arc-300) 60%, transparent);
  background: color-mix(in srgb, var(--arc-300) 22%, transparent);
  color: var(--arc-200);
}
.detail-apply:hover {
  background: color-mix(in srgb, var(--arc-300) 38%, transparent);
  border-color: color-mix(in srgb, var(--arc-300) 90%, transparent);
}
.detail-apply:active { transform: translateY(1px); }
</style>
