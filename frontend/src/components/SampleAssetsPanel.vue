<script setup lang="ts">
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

const props = defineProps<{
  samplesLoading: boolean
  samplesErrorMessage: string
  samplesSummary: SamplesSummaryResponse | null
  providerStatsText: string
  klingSamples: KlingSample[]
  selectedSampleId: string
  selectedSampleDetail: KlingSample | null
  selectedSampleNotesText: string
  selectedSampleNotesLoading: boolean
  apiBaseUrl: string
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'select-sample', sampleId: string): void
}>()

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

  const normalizedBase = props.apiBaseUrl.replace(/\/+$/, '')
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

function resultScreenshotTitle(index: number): string {
  return `结果截图 ${String(index + 1).padStart(2, '0')}`
}

function providerDisplayName(provider?: string): string {
  if (!provider) return '-'
  if (provider.toLowerCase() === 'kling') return '可灵'
  return provider
}

function statusDisplayName(status?: string): string {
  if (!status) return '-'
  const normalized = status.toLowerCase()
  if (normalized === 'archived') return '已归档'
  if (normalized === 'ready') return '可用'
  if (normalized === 'failed') return '失败'
  return status
}

function latestSampleId(): string {
  const stats = props.samplesSummary?.provider_stats || {}
  const provider = (props.samplesSummary?.providers || [])[0]
  return (provider && stats[provider]?.latest_sample_id) || '-'
}

function availableSceneIds(): string {
  const stats = props.samplesSummary?.provider_stats || {}
  const provider = (props.samplesSummary?.providers || [])[0]
  return (provider && stats[provider]?.available_scene_ids?.join(', ')) || '-'
}
</script>

<template>
  <section class="samples-panel">
    <div class="samples-panel-head">
      <div>
        <h2 class="section-title">真实样片库</h2>
        <p class="samples-desc">
          沉淀真实样片素材，支持后续创作参考、风格复用与案例展示。
        </p>
      </div>

      <button class="secondary-btn" :disabled="samplesLoading" @click="emit('refresh')">
        {{ samplesLoading ? '刷新中...' : '刷新素材' }}
      </button>
    </div>

    <p v-if="samplesErrorMessage" class="error">
      样例资产加载失败：{{ samplesErrorMessage }}
    </p>

    <div v-if="samplesSummary" class="samples-summary-grid">
      <div class="samples-metric">
        <span class="metric-label">素材来源</span>
        <strong class="metric-value">
          {{ (samplesSummary.providers || []).map(providerDisplayName).join('、') || '-' }}
        </strong>
      </div>

      <div class="samples-metric">
        <span class="metric-label">样片总数</span>
        <strong class="metric-value">
          {{ samplesSummary.total_sample_count ?? 0 }}
        </strong>
      </div>

      <div class="samples-metric">
        <span class="metric-label">最近样片</span>
        <strong class="metric-value metric-value-small">
          {{ latestSampleId() }}
        </strong>
      </div>

      <div class="samples-metric">
        <span class="metric-label">覆盖场景</span>
        <strong class="metric-value metric-value-small">
          {{ availableSceneIds() }}
        </strong>
      </div>

      <div class="samples-metric samples-metric-wide developer-info">
        <details>
          <summary>开发者信息</summary>
          <pre class="light-result compact-result">{{ providerStatsText }}</pre>
        </details>
      </div>
    </div>

    <div class="samples-layout">
      <section class="samples-list-panel">
        <h3 class="subsection-title">样片列表</h3>

        <p v-if="klingSamples.length === 0" class="hint">
          当前没有可展示的样片记录。
        </p>

        <button
          v-for="sample in klingSamples"
          :key="sample.sample_id || sample.scene_id"
          class="sample-list-item"
          :class="{ active: sample.sample_id === selectedSampleId }"
          @click="emit('select-sample', sample.sample_id || '')"
        >
          <strong>{{ sample.sample_id || 'unknown-sample' }}</strong>
          <span>场景 ID：{{ sample.scene_id || '-' }}</span>
          <span>状态：{{ statusDisplayName(sample.status) }}</span>
        </button>
      </section>

      <section class="sample-detail-panel">
        <h3 class="subsection-title">样片详情</h3>

        <div v-if="selectedSampleDetail" class="sample-detail-content">
          <div class="detail-row">
            <span class="detail-label">样片 ID</span>
            <code>{{ selectedSampleDetail.sample_id || '-' }}</code>
          </div>

          <div class="detail-row">
            <span class="detail-label">场景 ID</span>
            <code>{{ selectedSampleDetail.scene_id || '-' }}</code>
          </div>

          <div class="detail-row">
            <span class="detail-label">生成场景 ID</span>
            <code>{{ selectedSampleDetail.generated_scene_id || '-' }}</code>
          </div>

          <div class="detail-row">
            <span class="detail-label">状态</span>
            <code>{{ statusDisplayName(selectedSampleDetail.status) }}</code>
          </div>

          <div class="detail-block">
            <span class="detail-label">备注</span>
            <p class="detail-text">{{ selectedSampleDetail.notes || '-' }}</p>
            <a
              v-if="hasAssetLink(selectedSampleDetail.assets?.notes)"
              class="asset-link"
              :href="toAssetHref(selectedSampleDetail.assets?.notes)"
              target="_blank"
              rel="noreferrer"
            >
              打开备注文件
            </a>

            <div class="notes-preview-block">
              <span class="detail-label">备注预览</span>
              <p v-if="selectedSampleNotesLoading" class="detail-text">备注加载中...</p>
              <pre v-else class="notes-preview">{{ selectedSampleNotesText || '-' }}</pre>
            </div>
          </div>

          <div class="detail-block">
            <span class="detail-label">无水印视频</span>
            <span v-if="isVideoAsset(selectedSampleDetail.assets?.clean_video)" class="asset-preview-label">视频预览</span>
            <video
              v-if="isVideoAsset(selectedSampleDetail.assets?.clean_video)"
              class="asset-video"
              controls
              preload="metadata"
              :src="toAssetHref(selectedSampleDetail.assets?.clean_video)"
            />
            <a
              v-if="hasAssetLink(selectedSampleDetail.assets?.clean_video)"
              class="asset-link"
              :href="toAssetHref(selectedSampleDetail.assets?.clean_video)"
              target="_blank"
              rel="noreferrer"
            >
              打开视频
            </a>
            <p v-else class="hint">暂无无水印视频。</p>
          </div>

          <div class="detail-block">
            <span class="detail-label">带水印视频</span>
            <span v-if="isVideoAsset(selectedSampleDetail.assets?.watermarked_video)" class="asset-preview-label">视频预览</span>
            <video
              v-if="isVideoAsset(selectedSampleDetail.assets?.watermarked_video)"
              class="asset-video"
              controls
              preload="metadata"
              :src="toAssetHref(selectedSampleDetail.assets?.watermarked_video)"
            />
            <a
              v-if="hasAssetLink(selectedSampleDetail.assets?.watermarked_video)"
              class="asset-link"
              :href="toAssetHref(selectedSampleDetail.assets?.watermarked_video)"
              target="_blank"
              rel="noreferrer"
            >
              打开视频
            </a>
            <p v-else class="hint">暂无带水印视频。</p>
          </div>

          <div class="detail-block">
            <span class="detail-label">输入截图</span>
            <span v-if="isImageAsset(selectedSampleDetail.assets?.input_screenshot)" class="asset-preview-label">图片预览</span>
            <img
              v-if="isImageAsset(selectedSampleDetail.assets?.input_screenshot)"
              class="asset-image asset-image-thumbnail"
              :src="toAssetHref(selectedSampleDetail.assets?.input_screenshot)"
              alt="输入截图预览"
            />
            <a
              v-if="hasAssetLink(selectedSampleDetail.assets?.input_screenshot)"
              class="asset-link"
              :href="toAssetHref(selectedSampleDetail.assets?.input_screenshot)"
              target="_blank"
              rel="noreferrer"
            >
              打开图片
            </a>
            <p v-else class="hint">暂无输入截图。</p>
          </div>

          <div class="detail-block">
            <span class="detail-label">结果截图</span>
            <ul class="asset-list asset-grid-list">
              <li
                v-for="(path, index) in selectedSampleDetail.assets?.result_screenshots || []"
                :key="path"
                class="asset-list-item"
              >
                <strong class="asset-card-title">{{ resultScreenshotTitle(index) }}</strong>
                <img
                  v-if="isImageAsset(path)"
                  class="asset-image asset-image-thumbnail"
                  :src="toAssetHref(path)"
                  :alt="resultScreenshotTitle(index)"
                />
                <a
                  v-if="hasAssetLink(path)"
                  class="asset-link"
                  :href="toAssetHref(path)"
                  target="_blank"
                  rel="noreferrer"
                >
                  打开图片
                </a>
              </li>
            </ul>
          </div>

          <div class="detail-block">
            <details class="asset-developer-info">
              <summary>开发者信息</summary>
              <div class="detail-row">
                <span class="detail-label">备注路径</span>
                <code>{{ selectedSampleDetail.assets?.notes || '-' }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">无水印视频路径</span>
                <code>{{ selectedSampleDetail.assets?.clean_video || '-' }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">带水印视频路径</span>
                <code>{{ selectedSampleDetail.assets?.watermarked_video || '-' }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">输入截图路径</span>
                <code>{{ selectedSampleDetail.assets?.input_screenshot || '-' }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">结果截图路径</span>
                <ul class="asset-list">
                  <li
                    v-for="path in selectedSampleDetail.assets?.result_screenshots || []"
                    :key="path"
                  >
                    <code>{{ path }}</code>
                  </li>
                </ul>
              </div>
            </details>
          </div>
        </div>

        <p v-else class="hint">请选择左侧样片查看详情。</p>
      </section>
    </div>
  </section>
</template>

<style scoped>
/* ── dark gold theme throughout ── */
.samples-panel {
  margin: 0;
  padding: 0;
}

.samples-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 4px;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.samples-desc {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

.secondary-btn {
  border: 1px solid rgba(245,158,11,0.30);
  background: rgba(245,158,11,0.08);
  color: var(--arc-300);
  border-radius: 8px;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  white-space: nowrap;
  transition: border-color 0.18s, background 0.18s;
}
.secondary-btn:hover  { border-color: rgba(245,158,11,0.55); background: rgba(245,158,11,0.14); }
.secondary-btn:disabled { opacity: 0.45; cursor: not-allowed; }

.samples-summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.samples-metric {
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--glass-bg);
  border: 1px solid rgba(245,158,11,0.10);
  text-align: left;
}

.samples-metric-wide { grid-column: 1 / -1; }

.metric-label {
  display: block;
  margin-bottom: 6px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.metric-value {
  color: var(--arc-300);
  font-size: 1.25rem;
  font-weight: 700;
}

.metric-value-small {
  display: block;
  font-size: 0.9rem;
  line-height: 1.45;
  word-break: break-word;
}

.developer-info {
  padding: 0;
  overflow: hidden;
}

.developer-info details {
  padding: 12px 16px;
}

.developer-info summary {
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  list-style-position: inside;
}

.developer-info summary:hover {
  color: var(--arc-300);
}

.samples-layout {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 14px;
}

.samples-list-panel,
.sample-detail-panel {
  padding: 16px;
  border-radius: 14px;
  background: var(--glass-bg);
  border: 1px solid rgba(245,158,11,0.10);
  box-shadow: 0 4px 16px rgba(0,0,0,0.30);
}

.subsection-title {
  margin: 0 0 12px;
  color: var(--text-primary);
  font-size: 0.9375rem;
  font-weight: 700;
}

.sample-list-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: left;
  border: 1px solid rgba(255,255,255,0.07);
  background: rgba(255,255,255,0.03);
  color: var(--text-secondary);
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  cursor: pointer;
  font-family: inherit;
  font-size: 13px;
  transition: border-color 0.18s, background 0.18s;
}
.sample-list-item:hover         { border-color: rgba(245,158,11,0.25); background: rgba(245,158,11,0.05); color: var(--text-primary); }
.sample-list-item.active        { border-color: rgba(245,158,11,0.45); background: rgba(245,158,11,0.10); color: var(--text-primary); }
.sample-list-item strong        { color: var(--arc-300); font-size: 13px; }

.sample-detail-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  text-align: left;
}

.detail-row,
.detail-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(245,158,11,0.07);
}
.detail-row:last-child,
.detail-block:last-child { border-bottom: none; }

.detail-label {
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-text {
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
}

code {
  color: var(--arc-200);
  font-size: 12px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  word-break: break-all;
}

.asset-list {
  margin: 0;
  padding-left: 16px;
}
.asset-list li { margin-bottom: 6px; }

.compact-result { margin: 0; max-height: 220px; overflow: auto; }

.light-result {
  margin: 6px 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.hint  { margin: 8px 0 0; color: var(--text-muted); font-size: 13px; }
.error { margin-top: 12px; color: #f87171; font-size: 13px; }

.asset-link {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  margin-top: 4px;
  color: var(--arc-300);
  font-size: 12px;
  font-weight: 600;
  text-decoration: none;
}
.asset-link:hover { text-decoration: underline; color: var(--arc-200); }

.asset-list-item { display: flex; flex-direction: column; gap: 4px; }

.asset-card-title {
  color: var(--arc-300);
  font-size: 13px;
  font-weight: 700;
}

.asset-preview-label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.asset-developer-info {
  width: 100%;
}

.asset-developer-info summary {
  color: var(--text-muted);
  cursor: pointer;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.asset-developer-info summary:hover {
  color: var(--arc-300);
}

.asset-developer-info .detail-row {
  margin-top: 10px;
}

.asset-image {
  display: block;
  width: 100%;
  max-width: 520px;
  border-radius: 10px;
  border: 1px solid rgba(245,158,11,0.15);
  margin-top: 8px;
}

.asset-video {
  display: block;
  width: 100%;
  max-width: 520px;
  border-radius: 10px;
  margin-top: 8px;
  background: #000;
}

.asset-image-link  { display: inline-block; width: fit-content; margin-top: 6px; }
.asset-image-thumbnail { max-width: 240px; max-height: 180px; object-fit: cover; cursor: pointer; border-radius: 8px; }

.asset-grid-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 10px;
  padding-left: 0;
  list-style: none;
}

.asset-grid-list .asset-list-item {
  padding: 10px;
  border: 1px solid rgba(245,158,11,0.10);
  border-radius: 10px;
  background: rgba(255,255,255,0.02);
}

.notes-preview-block { margin-top: 8px; }

.notes-preview {
  margin: 6px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(245,158,11,0.10);
  background: var(--surface-overlay-strong);
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 280px;
  overflow: auto;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

@media (max-width: 900px) {
  .samples-panel-head { flex-direction: column; }
  .samples-summary-grid { grid-template-columns: 1fr; }
  .samples-layout { grid-template-columns: 1fr; }
}
</style>
