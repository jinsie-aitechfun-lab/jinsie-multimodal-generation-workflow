<template>
  <div class="studio-root">
    <!-- Ambient background layers -->
    <div class="studio-bg-layers" aria-hidden="true">
      <div class="studio-bg-radial studio-bg-radial--arc" />
      <div class="studio-bg-radial studio-bg-radial--prism" />
      <div class="studio-bg-radial studio-bg-radial--rose" />
      <div class="studio-bg-radial studio-bg-radial--deep" />
      <div class="studio-bg-grid" />
    </div>

    <!-- Main layout -->
    <div class="studio-shell">
      <!-- Header -->
      <header class="studio-header glass-card border-gradient" style="border-radius:0;">
        <div class="studio-header__inner">
          <!-- Brand -->
          <div class="studio-brand">
            <span class="studio-brand__icon" aria-hidden="true">⬡</span>
            <span class="studio-brand__name">Jinsie<span class="studio-brand__accent"> AI Studio</span></span>
            <span class="badge badge-arc" style="font-size:0.6rem;padding:0.15rem 0.5rem;">BETA</span>
          </div>

          <!-- Tab bar (center) -->
          <nav class="studio-tabs" role="tablist">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              role="tab"
              :aria-selected="modelValue === tab.id"
              :class="['studio-tab', { active: modelValue === tab.id }]"
              @click="$emit('update:modelValue', tab.id)"
            >
              <span class="studio-tab__icon" aria-hidden="true">{{ tab.icon }}</span>
              {{ tab.label }}
              <span v-if="tab.badge" class="badge badge-arc" style="font-size:0.55rem;padding:0.1rem 0.4rem;margin-left:2px;">{{ tab.badge }}</span>
            </button>
          </nav>

          <!-- Actions (right) -->
          <div class="studio-header__actions">
            <slot name="header-actions" />
            <button
              v-if="devMode"
              class="btn-ghost"
              style="font-size:0.75rem;padding:0.375rem 0.75rem;"
              @click="$emit('toggle-dev')"
            >
              <span aria-hidden="true">⚙</span> Dev
            </button>
          </div>
        </div>

        <!-- Sub-header progress slot -->
        <div v-if="$slots['progress']" class="studio-header__progress">
          <slot name="progress" />
        </div>
      </header>

      <!-- Content area -->
      <main class="studio-content" role="main">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  tabs: Array<{ id: string; label: string; icon: string; badge?: string }>
  devMode?: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', tab: string): void
  (e: 'toggle-dev'): void
}>()
</script>

<style scoped>
.studio-root {
  position: relative;
  min-height: 100vh;
  background: var(--bg-void);
  overflow-x: hidden;
}

/* ── Ambient layers ── */
.studio-bg-layers {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
.studio-bg-radial {
  position: absolute;
  border-radius: 50%;
}
.studio-bg-radial--arc {
  width: 1400px; height: 900px;
  top: -350px; left: -250px;
  background: radial-gradient(ellipse, rgba(0,196,255,0.36) 0%, rgba(0,100,220,0.12) 50%, transparent 70%);
  filter: blur(90px);
  animation: float 10s ease-in-out infinite;
}
.studio-bg-radial--prism {
  width: 1100px; height: 800px;
  bottom: -200px; right: -200px;
  background: radial-gradient(ellipse, rgba(157,110,248,0.32) 0%, rgba(100,40,220,0.10) 50%, transparent 70%);
  filter: blur(100px);
  animation: float 13s ease-in-out infinite reverse;
}
.studio-bg-radial--rose {
  width: 700px; height: 500px;
  top: 35%; left: 35%;
  background: radial-gradient(ellipse, rgba(236,72,153,0.14) 0%, transparent 65%);
  filter: blur(120px);
  animation: float 18s ease-in-out infinite;
}
.studio-bg-radial--deep {
  width: 1000px; height: 500px;
  bottom: -100px; left: 50%;
  transform: translateX(-50%);
  background: radial-gradient(ellipse, rgba(0,60,200,0.22) 0%, transparent 65%);
  filter: blur(80px);
}
.studio-bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(0,196,255,0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,196,255,0.055) 1px, transparent 1px);
  background-size: 52px 52px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 30%, transparent 100%);
}

/* ── Shell ── */
.studio-shell {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ── Header ── */
.studio-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: linear-gradient(180deg, rgba(10,16,36,0.96) 0%, rgba(8,12,28,0.92) 100%);
  backdrop-filter: blur(32px);
  -webkit-backdrop-filter: blur(32px);
  border-radius: 0 !important;
  flex-shrink: 0;
  border: none !important;
  border-bottom: 1px solid transparent !important;
  box-shadow:
    0 1px 0 0 rgba(0,196,255,0.15),
    0 4px 32px rgba(0,0,0,0.40);
}
.studio-header::before { display: none; }
.studio-header::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(0,196,255,0.50) 25%,
    rgba(157,110,248,0.50) 75%,
    transparent 100%
  );
  pointer-events: none;
}

.studio-header__inner {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0 1.5rem;
  height: 56px;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

.studio-header__progress {
  border-top: 1px solid rgba(255,255,255,0.04);
  padding: 0 1.5rem 0.5rem;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

/* ── Brand ── */
.studio-brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}
.studio-brand__icon {
  font-size: 1.25rem;
  background: linear-gradient(135deg, var(--arc-400), var(--prism-500));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}
.studio-brand__name {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  white-space: nowrap;
}
.studio-brand__accent {
  background: linear-gradient(90deg, var(--arc-400), var(--prism-400));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── Tabs ── */
.studio-tabs {
  display: flex;
  align-items: center;
  gap: 0.125rem;
  flex: 1;
  justify-content: center;
}

/* ── Header actions ── */
.studio-header__actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

/* ── Content ── */
.studio-content {
  flex: 1;
  padding: 1.5rem;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

@media (max-width: 768px) {
  .studio-header__inner { padding: 0 1rem; }
  .studio-content { padding: 1rem; }
  .studio-brand__name { font-size: 0.875rem; }
  .studio-tabs { gap: 0; }
  .studio-tab { padding: 0.5rem 0.75rem; font-size: 0.75rem; }
}
</style>
