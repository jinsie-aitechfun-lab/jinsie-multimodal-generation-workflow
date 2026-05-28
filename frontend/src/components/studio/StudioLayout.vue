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
    <!-- Water drop ripples — glowing rings + center point -->
    <div class="water-layer" aria-hidden="true">
      <div class="drop" style="top:35%; left:20%;">
        <div class="dc"/>
        <div class="ring" style="--s:420px;--c:rgba(245,158,11,0.60);--dur:8s; animation-delay:0s;"/>
        <div class="ring" style="--s:360px;--c:rgba(245,158,11,0.42);--dur:8s; animation-delay:-2.7s;"/>
        <div class="ring" style="--s:290px;--c:rgba(249,115,22,0.28);--dur:8s; animation-delay:-5.4s;"/>
      </div>
      <div class="drop" style="top:58%; left:76%;">
        <div class="dc"/>
        <div class="ring" style="--s:480px;--c:rgba(249,115,22,0.55);--dur:9s; animation-delay:-1.8s;"/>
        <div class="ring" style="--s:410px;--c:rgba(249,115,22,0.38);--dur:9s; animation-delay:-4.8s;"/>
        <div class="ring" style="--s:330px;--c:rgba(245,158,11,0.24);--dur:9s; animation-delay:-7.5s;"/>
      </div>
      <div class="drop" style="top:20%; left:66%;">
        <div class="dc"/>
        <div class="ring" style="--s:350px;--c:rgba(251,191,36,0.55);--dur:7.5s;animation-delay:-0.9s;"/>
        <div class="ring" style="--s:290px;--c:rgba(251,191,36,0.38);--dur:7.5s;animation-delay:-3.4s;"/>
        <div class="ring" style="--s:220px;--c:rgba(245,158,11,0.24);--dur:7.5s;animation-delay:-6.0s;"/>
      </div>
      <div class="drop" style="top:76%; left:36%;">
        <div class="dc"/>
        <div class="ring" style="--s:390px;--c:rgba(245,158,11,0.52);--dur:8.5s;animation-delay:-4.0s;"/>
        <div class="ring" style="--s:330px;--c:rgba(245,158,11,0.36);--dur:8.5s;animation-delay:-7.0s;"/>
        <div class="ring" style="--s:260px;--c:rgba(249,115,22,0.22);--dur:8.5s;animation-delay:-1.5s;"/>
      </div>
    </div>

    <!-- Particle layer — three tiers of glowing orbs -->
    <div class="pt-layer" aria-hidden="true">
      <!-- Large glow orbs -->
      <div class="pt lg" style="left:8%;  top:68%;--dur:22s;--d:-4s; --dx:12px;"/>
      <div class="pt lg" style="left:87%; top:54%;--dur:28s;--d:-14s;--dx:-10px;"/>
      <div class="pt lg" style="left:44%; top:80%;--dur:20s;--d:-8s; --dx:8px;"/>
      <div class="pt lg" style="left:71%; top:24%;--dur:25s;--d:-18s;--dx:-6px;"/>
      <!-- Medium orbs -->
      <div class="pt md" style="left:18%; top:42%;--dur:17s;--d:-2s; --dx:6px;"/>
      <div class="pt md" style="left:61%; top:64%;--dur:21s;--d:-11s;--dx:-8px;"/>
      <div class="pt md" style="left:34%; top:57%;--dur:19s;--d:-6s; --dx:10px;"/>
      <div class="pt md" style="left:81%; top:77%;--dur:23s;--d:-16s;--dx:-5px;"/>
      <div class="pt md" style="left:26%; top:86%;--dur:15s;--d:-9s; --dx:4px;"/>
      <div class="pt md" style="left:54%; top:31%;--dur:26s;--d:-20s;--dx:-12px;"/>
      <div class="pt md" style="left:92%; top:38%;--dur:18s;--d:-7s; --dx:7px;"/>
      <div class="pt md" style="left:5%;  top:22%;--dur:24s;--d:-12s;--dx:-4px;"/>
      <!-- Tiny sparkles -->
      <div class="pt sm" style="left:13%; top:53%;--dur:12s;--d:-1s;"/>
      <div class="pt sm" style="left:39%; top:45%;--dur:14s;--d:-5s;"/>
      <div class="pt sm" style="left:67%; top:37%;--dur:11s;--d:-9s;"/>
      <div class="pt sm" style="left:83%; top:69%;--dur:16s;--d:-13s;"/>
      <div class="pt sm" style="left:23%; top:73%;--dur:13s;--d:-3s;"/>
      <div class="pt sm" style="left:57%; top:83%;--dur:15s;--d:-7s;"/>
      <div class="pt sm" style="left:4%;  top:48%;--dur:18s;--d:-11s;"/>
      <div class="pt sm" style="left:75%; top:89%;--dur:20s;--d:-15s;"/>
      <div class="pt sm" style="left:48%; top:17%;--dur:17s;--d:-8s;"/>
      <div class="pt sm" style="left:29%; top:28%;--dur:10s;--d:-6s;"/>
      <div class="pt sm" style="left:96%; top:60%;--dur:22s;--d:-10s;"/>
      <div class="pt sm" style="left:51%; top:51%;--dur:14s;--d:-4s;"/>
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
   Top bar — frosted glass
═══════════════════════════════════════════════ */
.topbar {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(9, 7, 3, 0.82);
  backdrop-filter: blur(28px) saturate(160%);
  -webkit-backdrop-filter: blur(28px) saturate(160%);
  flex-shrink: 0;
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
   Water drop ripples — glowing rings
═══════════════════════════════════════════════ */
.water-layer {
  position: fixed; inset: 0;
  z-index: 0; pointer-events: none; overflow: hidden;
}

.drop { position: absolute; }

/* Glowing center point — simulates the drop itself */
.dc {
  position: absolute;
  width: 7px; height: 7px;
  border-radius: 50%;
  top: -3.5px; left: -3.5px;
  background: rgba(251,191,36,0.95);
  box-shadow:
    0 0 6px  rgba(251,191,36,1),
    0 0 18px rgba(245,158,11,0.70),
    0 0 36px rgba(245,158,11,0.35),
    0 0 60px rgba(245,158,11,0.15);
  animation: dcPulse 2.8s ease-in-out infinite;
}

@keyframes dcPulse {
  0%,100% { opacity: 0.95; transform: scale(1);    }
  50%      { opacity: 0.40; transform: scale(0.65); }
}

/* Expanding ring — starts tiny, grows to full size, fades out */
.ring {
  position: absolute;
  width:  var(--s, 350px);
  height: var(--s, 350px);
  border-radius: 50%;
  border: 1.5px solid var(--c, rgba(245,158,11,0.50));
  box-shadow: 0 0 14px var(--c), 0 0 30px rgba(245,158,11,0.08);
  top:  calc(var(--s, 350px) / -2);
  left: calc(var(--s, 350px) / -2);
  transform: scale(0.04);
  opacity: 0;
  animation: waterRing var(--dur, 8s) cubic-bezier(0.08, 0.65, 0.28, 1) infinite;
}

@keyframes waterRing {
  0%   { transform: scale(0.04); opacity: 0;    }
  5%   {                          opacity: 0.95; }
  40%  {                          opacity: 0.40; }
  100% { transform: scale(1);     opacity: 0;    }
}

/* ═══════════════════════════════════════════════
   Particle system — three tiers of glowing orbs
═══════════════════════════════════════════════ */
.pt-layer {
  position: fixed; inset: 0;
  z-index: 0; pointer-events: none; overflow: hidden;
}

.pt {
  position: absolute;
  border-radius: 50%;
  animation-duration: var(--dur, 20s);
  animation-delay:    var(--d,  0s);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}

/* ── Large orbs: strong glow, slow drift ── */
.pt.lg {
  width: 6px; height: 6px;
  background: radial-gradient(circle, #fbbf24 0%, rgba(245,158,11,0.35) 65%, transparent 100%);
  box-shadow:
    0 0 8px  rgba(251,191,36,0.95),
    0 0 22px rgba(245,158,11,0.65),
    0 0 45px rgba(245,158,11,0.30),
    0 0 80px rgba(245,158,11,0.10);
  animation-name: ptRise;
}

/* ── Medium orbs: moderate glow ── */
.pt.md {
  width: 3.5px; height: 3.5px;
  background: radial-gradient(circle, #fde68a 0%, rgba(245,158,11,0.45) 60%, transparent 100%);
  box-shadow:
    0 0 5px  rgba(253,230,138,0.95),
    0 0 14px rgba(245,158,11,0.55),
    0 0 28px rgba(245,158,11,0.22);
  animation-name: ptRise;
}

/* ── Tiny sparkles: twinkle in place ── */
.pt.sm {
  width: 2px; height: 2px;
  background: #fde68a;
  box-shadow:
    0 0 3px  rgba(253,230,138,1),
    0 0 9px  rgba(251,191,36,0.80),
    0 0 18px rgba(245,158,11,0.40);
  animation-name: ptTwinkle;
}

@keyframes ptRise {
  0%   { transform: translateY(0)     translateX(0);              opacity: 0; }
  8%   {                                                           opacity: 1; }
  50%  { transform: translateY(-45px) translateX(var(--dx, 6px)); opacity: 0.85; }
  92%  {                                                           opacity: 0.30; }
  100% { transform: translateY(-90px) translateX(0);              opacity: 0; }
}

@keyframes ptTwinkle {
  0%,100% { opacity: 0;    transform: scale(0.5); }
  25%, 75% { opacity: 1;   transform: scale(1.8);
    box-shadow: 0 0 5px rgba(253,230,138,1), 0 0 14px rgba(251,191,36,0.85), 0 0 28px rgba(245,158,11,0.50); }
  50%      { opacity: 0.55; transform: scale(1.2); }
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
