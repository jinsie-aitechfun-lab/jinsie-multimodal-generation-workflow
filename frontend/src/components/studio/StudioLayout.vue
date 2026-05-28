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
    <!-- Water ripple layer -->
    <div class="ripple-layer" aria-hidden="true">
      <div class="ripple ripple-1" />
      <div class="ripple ripple-2" />
      <div class="ripple ripple-3" />
      <div class="ripple ripple-4" />
      <div class="ripple ripple-5" />
    </div>

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
                  <stop offset="0%" stop-color="#f59e0b"/>
                  <stop offset="100%" stop-color="#fb923c"/>
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

  // Pure fade — no translate, no scale
  animate(container, {
    opacity: [0, 1],
    duration: 340,
    easing: 'easeOutCubic',
  })

  // Stagger-fade each glass-card inside, no scale/translate
  const cards = container.querySelectorAll<HTMLElement>('.glass-card, .glass-card-vivid')
  if (cards.length) {
    animate(Array.from(cards), {
      opacity: [0, 1],
      duration: 420,
      delay: (_el: HTMLElement, i: number) => i * 45,
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
/* ── Root shell — transparent so the body background-image gradient shows through ── */
.s-root {
  position: relative;
  min-height: 100vh;
  background: transparent;
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

/* Top-left gold orb */
.orb-cyan {
  width: 900px;
  height: 700px;
  top: -260px;
  left: -180px;
  background: radial-gradient(ellipse at center,
    rgba(245,158,11,0.36) 0%,
    rgba(180,80,10,0.14) 42%,
    transparent 65%
  );
  filter: blur(40px);
  animation: driftCyan 16s ease-in-out infinite;
}

/* Bottom-right ember orb */
.orb-violet {
  width: 800px;
  height: 650px;
  bottom: -200px;
  right: -160px;
  background: radial-gradient(ellipse at center,
    rgba(249,115,22,0.30) 0%,
    rgba(180,60,10,0.12) 42%,
    transparent 65%
  );
  filter: blur(44px);
  animation: driftViolet 20s ease-in-out infinite;
}

/* Roaming amber — creates warm glow in the middle */
.orb-rose {
  width: 520px;
  height: 400px;
  top: 30%;
  left: 40%;
  background: radial-gradient(ellipse at center,
    rgba(251,191,36,0.14) 0%,
    transparent 60%
  );
  filter: blur(70px);
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
  z-index: 1;
  pointer-events: none;
  background-image: radial-gradient(circle, rgba(245,158,11,0.22) 1px, transparent 1px);
  background-size: 38px 38px;
  -webkit-mask-image: radial-gradient(ellipse 75% 70% at 50% 35%, black 15%, transparent 85%);
  mask-image: radial-gradient(ellipse 75% 70% at 50% 35%, black 15%, transparent 85%);
}

/* ═══════════════════════════════════════════════
   Top bar — frosted glass with metallic sheen
═══════════════════════════════════════════════ */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background:
    /* metallic diagonal sheen sweep */
    linear-gradient(
      118deg,
      transparent 0%,
      rgba(255,220,100,0.04) 38%,
      rgba(255,255,255,0.07) 50%,
      rgba(255,220,100,0.03) 62%,
      transparent 100%
    ),
    rgba(9, 7, 3, 0.82);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  flex-shrink: 0;
}

/* Animated metallic sheen that slowly sweeps across */
.topbar::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(
    118deg,
    transparent 0%,
    transparent 30%,
    rgba(255,230,120,0.06) 50%,
    transparent 70%,
    transparent 100%
  );
  background-size: 200% 100%;
  animation: metalSheen 8s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

/* Gold glow line at bottom of header */
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
    rgba(245, 158, 11, 0.60) 28%,
    rgba(251, 146, 60, 0.55) 72%,
    transparent 100%
  );
  z-index: 1;
}

@keyframes metalSheen {
  0%   { background-position: -100% 0; }
  50%  { background-position:  200% 0; }
  100% { background-position: -100% 0; }
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
  position: relative;
  z-index: 2;
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
  filter: drop-shadow(0 0 8px rgba(245, 158, 11, 0.60));
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
  background: linear-gradient(110deg, #f59e0b 0%, #fb923c 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.brand-tag {
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(245, 158, 11, 0.75);
  border: 1px solid rgba(245, 158, 11, 0.30);
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
    rgba(245, 158, 11, 0.18) 0%,
    rgba(249, 115, 22, 0.13) 100%
  );
  border-color: rgba(245, 158, 11, 0.38);
  box-shadow:
    0 0 22px rgba(245, 158, 11, 0.22),
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
  background: linear-gradient(90deg, #f59e0b, #fb923c);
  border-radius: 1px;
  opacity: 0.85;
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
  color: rgba(245, 158, 11, 0.85);
  border: 1px solid rgba(245, 158, 11, 0.28);
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

/* ═══════════════════════════════════════════════
   Water ripple layer
═══════════════════════════════════════════════ */
.ripple-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.ripple {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(245,158,11,0.12);
  animation: rippleExpand 8s ease-out infinite;
  transform: translate(-50%, -50%) scale(0);
  opacity: 0;
}

/* Different origin points for each ring */
.ripple-1 { top: 18%;  left: 22%;  width: 600px; height: 600px; animation-delay: 0s;    animation-duration: 9s; }
.ripple-2 { top: 70%;  left: 75%;  width: 500px; height: 500px; animation-delay: 2.5s;  animation-duration: 8s; border-color: rgba(249,115,22,0.10); }
.ripple-3 { top: 45%;  left: 55%;  width: 700px; height: 700px; animation-delay: 5s;    animation-duration: 11s; }
.ripple-4 { top: 82%;  left: 18%;  width: 450px; height: 450px; animation-delay: 1.2s;  animation-duration: 7s; border-color: rgba(251,191,36,0.08); }
.ripple-5 { top: 12%;  left: 78%;  width: 550px; height: 550px; animation-delay: 3.8s;  animation-duration: 10s; }

@keyframes rippleExpand {
  0%   { transform: translate(-50%, -50%) scale(0.05); opacity: 0; }
  12%  { opacity: 1; }
  100% { transform: translate(-50%, -50%) scale(1);    opacity: 0; }
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
