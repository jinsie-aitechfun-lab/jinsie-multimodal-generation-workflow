<template>
  <div class="s-root">
    <!-- Aurora orbs -->
    <div class="aurora" aria-hidden="true">
      <div class="orb orb-cyan" />
      <div class="orb orb-violet" />
      <div class="orb orb-rose" />
    </div>
    <!-- Dot grid -->
    <div class="dot-grid" aria-hidden="true" />

    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-inner">
        <!-- Brand -->
        <div class="brand">
          <div class="brand-hex" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <path d="M11 1.5L20.5 6.5V15.5L11 20.5L1.5 15.5V6.5Z"
                stroke="url(#hexG)" stroke-width="1.5" stroke-linejoin="round"/>
              <circle cx="11" cy="11" r="2.5" fill="url(#hexG)" opacity="0.9"/>
              <defs>
                <linearGradient id="hexG" x1="1.5" y1="1.5" x2="20.5" y2="20.5" gradientUnits="userSpaceOnUse">
                  <stop offset="0%" stop-color="#00c4ff"/>
                  <stop offset="100%" stop-color="#a855f7"/>
                </linearGradient>
              </defs>
            </svg>
          </div>
          <span class="brand-name">Jinsie<em class="brand-em"> AI</em> Studio</span>
          <span class="brand-tag">BETA</span>
        </div>

        <!-- Navigation -->
        <nav class="nav" role="tablist">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            role="tab"
            :class="['nav-item', { 'is-active': modelValue === tab.id }]"
            :aria-selected="modelValue === tab.id"
            @click="$emit('update:modelValue', tab.id)"
          >
            <span class="nav-icon" aria-hidden="true">{{ tab.icon }}</span>
            <span class="nav-label">{{ tab.label }}</span>
            <span v-if="tab.badge" class="nav-badge">{{ tab.badge }}</span>
          </button>
        </nav>

        <!-- Right actions -->
        <div class="topbar-right">
          <slot name="header-actions" />
          <button v-if="devMode" class="dev-btn" title="Dev mode" @click="$emit('toggle-dev')">
            ⚙
          </button>
        </div>
      </div>

      <!-- Progress sub-row -->
      <div v-if="$slots['progress']" class="topbar-progress">
        <slot name="progress" />
      </div>
    </header>

    <!-- Page content -->
    <main class="s-main" ref="mainRef">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { animate } from 'animejs'

const props = defineProps<{
  modelValue: string
  tabs: Array<{ id: string; label: string; icon: string; badge?: string }>
  devMode?: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', tab: string): void
  (e: 'toggle-dev'): void
}>()

const mainRef = ref<HTMLElement | null>(null)

function animateContentIn() {
  const container = mainRef.value
  if (!container) return

  // Fade + rise the entire content area
  animate(container, {
    opacity: [0, 1],
    translateY: [20, 0],
    duration: 420,
    easing: 'easeOutCubic',
  })

  // Stagger-animate each glass-card inside
  const cards = container.querySelectorAll<HTMLElement>('.glass-card, .glass-card-vivid')
  if (cards.length) {
    animate(Array.from(cards), {
      opacity: [0, 1],
      translateY: [28, 0],
      scale: [0.97, 1],
      duration: 500,
      delay: (_el: HTMLElement, i: number) => i * 55,
      easing: 'easeOutCubic',
    })
  }
}

// Animate nav items on first mount
onMounted(() => {
  animate('.nav-item', {
    opacity: [0, 1],
    translateY: [-6, 0],
    duration: 450,
    delay: (_el: HTMLElement, i: number) => 80 + i * 70,
    easing: 'easeOutCubic',
  })
  animate('.brand', {
    opacity: [0, 1],
    translateX: [-14, 0],
    duration: 480,
    easing: 'easeOutCubic',
  })
  // Initial content entrance
  setTimeout(animateContentIn, 150)
})

// Animate on tab change
watch(() => props.modelValue, () => {
  // Short delay so Vue can swap the content
  setTimeout(animateContentIn, 16)
})
</script>

<style scoped>
/* ── Root shell ── */
.s-root {
  position: relative;
  min-height: 100vh;
  background: #06091b;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
}

/* ═══════════════════════════════════════════════
   Aurora background
═══════════════════════════════════════════════ */
.aurora {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.orb {
  position: absolute;
  border-radius: 50%;
  will-change: transform;
}

/* Top-left cyan orb — the dominant light source */
.orb-cyan {
  width: 1000px;
  height: 750px;
  top: -280px;
  left: -200px;
  background: radial-gradient(ellipse at center,
    rgba(0,190,255,0.55) 0%,
    rgba(0,100,230,0.22) 40%,
    transparent 68%
  );
  filter: blur(50px);
  animation: driftCyan 16s ease-in-out infinite;
}

/* Bottom-right violet orb */
.orb-violet {
  width: 850px;
  height: 680px;
  bottom: -220px;
  right: -180px;
  background: radial-gradient(ellipse at center,
    rgba(140,60,255,0.52) 0%,
    rgba(80,20,210,0.18) 42%,
    transparent 68%
  );
  filter: blur(55px);
  animation: driftViolet 20s ease-in-out infinite;
}

/* Center-right rose accent */
.orb-rose {
  width: 580px;
  height: 440px;
  top: 28%;
  left: 42%;
  background: radial-gradient(ellipse at center,
    rgba(225,65,210,0.24) 0%,
    transparent 62%
  );
  filter: blur(80px);
  animation: driftRose 27s ease-in-out infinite;
}

@keyframes driftCyan {
  0%, 100% { transform: translate(0, 0) scale(1); }
  30%       { transform: translate(60px, -35px) scale(1.04); }
  65%       { transform: translate(-28px, 50px) scale(0.97); }
}
@keyframes driftViolet {
  0%, 100% { transform: translate(0, 0) scale(1); }
  38%       { transform: translate(-50px, -60px) scale(1.07); }
  72%       { transform: translate(38px, 30px) scale(0.94); }
}
@keyframes driftRose {
  0%, 100% { transform: translate(0, 0); }
  50%       { transform: translate(-70px, -45px); }
}

/* ── Dot grid overlay ── */
.dot-grid {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: radial-gradient(circle, rgba(0,196,255,0.22) 1px, transparent 1px);
  background-size: 38px 38px;
  -webkit-mask-image: radial-gradient(ellipse 70% 70% at 50% 40%, black 20%, transparent 88%);
  mask-image: radial-gradient(ellipse 70% 70% at 50% 40%, black 20%, transparent 88%);
}

/* ═══════════════════════════════════════════════
   Top bar
═══════════════════════════════════════════════ */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(6, 9, 27, 0.80);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  flex-shrink: 0;
}

/* Rainbow glow line at bottom of header */
.topbar::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 196, 255, 0.55) 28%,
    rgba(168, 85, 247, 0.55) 72%,
    transparent 100%
  );
}

.topbar-inner {
  display: flex;
  align-items: center;
  gap: 1rem;
  height: 58px;
  padding: 0 1.75rem;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

/* ── Brand ── */
.brand {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-shrink: 0;
  opacity: 0; /* animated in on mount */
}

.brand-hex {
  line-height: 0;
  filter: drop-shadow(0 0 8px rgba(0, 196, 255, 0.55));
  flex-shrink: 0;
}

.brand-name {
  font-size: 15px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.96);
  letter-spacing: -0.025em;
  white-space: nowrap;
}

.brand-em {
  font-style: normal;
  background: linear-gradient(110deg, #00c4ff 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-tag {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(0, 196, 255, 0.65);
  border: 1px solid rgba(0, 196, 255, 0.25);
  border-radius: 4px;
  padding: 1px 5px;
  flex-shrink: 0;
}

/* ── Navigation ── */
.nav {
  display: flex;
  align-items: center;
  gap: 3px;
  flex: 1;
  justify-content: center;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 20px;
  border-radius: 9px;
  font-size: 13.5px;
  font-weight: 500;
  font-family: inherit;
  color: rgba(255, 255, 255, 0.42);
  background: none;
  border: 1px solid transparent;
  cursor: pointer;
  transition: color 0.18s, background 0.18s, border-color 0.18s, box-shadow 0.22s;
  white-space: nowrap;
  user-select: none;
  opacity: 0; /* animated in on mount */
}

.nav-item:hover:not(.is-active) {
  color: rgba(255, 255, 255, 0.78);
  background: rgba(255, 255, 255, 0.055);
}

.nav-item.is-active {
  color: #ffffff;
  font-weight: 600;
  background: linear-gradient(140deg,
    rgba(0, 196, 255, 0.17) 0%,
    rgba(168, 85, 247, 0.13) 100%
  );
  border-color: rgba(0, 196, 255, 0.32);
  box-shadow:
    0 0 22px rgba(0, 196, 255, 0.20),
    inset 0 1px 0 rgba(255, 255, 255, 0.10);
}

/* Bottom indicator glow for active tab */
.nav-item.is-active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 25%;
  right: 25%;
  height: 2px;
  background: linear-gradient(90deg, #00c4ff, #a855f7);
  border-radius: 1px;
  opacity: 0.75;
}

.nav-icon {
  font-size: 11px;
  line-height: 1;
  opacity: 0.75;
}

.nav-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: rgba(0, 196, 255, 0.75);
  border: 1px solid rgba(0, 196, 255, 0.22);
  border-radius: 3px;
  padding: 0 4px;
  margin-left: 1px;
}

/* ── Right actions ── */
.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.dev-btn {
  padding: 5px 11px;
  border-radius: 6px;
  font-size: 12px;
  font-family: inherit;
  color: rgba(255, 255, 255, 0.42);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: color 0.18s, background 0.18s;
}

.dev-btn:hover {
  color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.08);
}

/* ── Progress slot ── */
.topbar-progress {
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding: 0 1.75rem 0.5rem;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
}

/* ── Main content ── */
.s-main {
  position: relative;
  z-index: 1;
  flex: 1;
  padding: 1.5rem 1.75rem;
  max-width: 1440px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .topbar-inner { padding: 0 1rem; height: 52px; }
  .s-main       { padding: 1rem; }
  .brand-name   { font-size: 13px; }
  .nav-item     { padding: 6px 12px; font-size: 12px; }
  .nav-icon     { display: none; }
}
</style>
