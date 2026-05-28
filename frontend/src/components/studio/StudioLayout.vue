<template>
  <div class="s-root" :data-theme="currentTheme">
    <!-- ── Aurora orbs ── -->
    <div class="aurora" aria-hidden="true">
      <div class="orb orb-a" />
      <div class="orb orb-b" />
      <div class="orb orb-c" />
    </div>
    <!-- ── Dot grid ── -->
    <div class="dot-grid" aria-hidden="true" />

    <!-- ── Water drop ripples ── -->
    <div class="water-layer" aria-hidden="true">
      <div class="drop" style="top:35%; left:20%;">
        <div class="dc"/>
        <div class="ring" :style="`--s:420px;--c:${tc(0.60)};--dur:8s;animation-delay:0s;`"/>
        <div class="ring" :style="`--s:360px;--c:${tc(0.42)};--dur:8s;animation-delay:-2.7s;`"/>
        <div class="ring" :style="`--s:290px;--c:${tc(0.28,'b')};--dur:8s;animation-delay:-5.4s;`"/>
      </div>
      <div class="drop" style="top:58%; left:76%;">
        <div class="dc"/>
        <div class="ring" :style="`--s:480px;--c:${tc(0.55,'b')};--dur:9s;animation-delay:-1.8s;`"/>
        <div class="ring" :style="`--s:410px;--c:${tc(0.38,'b')};--dur:9s;animation-delay:-4.8s;`"/>
        <div class="ring" :style="`--s:330px;--c:${tc(0.24)};--dur:9s;animation-delay:-7.5s;`"/>
      </div>
      <div class="drop" style="top:20%; left:66%;">
        <div class="dc"/>
        <div class="ring" :style="`--s:350px;--c:${tc(0.55,'c')};--dur:7.5s;animation-delay:-0.9s;`"/>
        <div class="ring" :style="`--s:290px;--c:${tc(0.38,'c')};--dur:7.5s;animation-delay:-3.4s;`"/>
        <div class="ring" :style="`--s:220px;--c:${tc(0.24)};--dur:7.5s;animation-delay:-6.0s;`"/>
      </div>
      <div class="drop" style="top:76%; left:36%;">
        <div class="dc"/>
        <div class="ring" :style="`--s:390px;--c:${tc(0.52)};--dur:8.5s;animation-delay:-4.0s;`"/>
        <div class="ring" :style="`--s:330px;--c:${tc(0.36)};--dur:8.5s;animation-delay:-7.0s;`"/>
        <div class="ring" :style="`--s:260px;--c:${tc(0.22,'b')};--dur:8.5s;animation-delay:-1.5s;`"/>
      </div>
    </div>

    <!-- ── Particle layer ── -->
    <div class="pt-layer" aria-hidden="true">
      <div class="pt lg" style="left:8%;  top:68%;--dur:22s;--d:-4s; --dx:12px;"/>
      <div class="pt lg" style="left:87%; top:54%;--dur:28s;--d:-14s;--dx:-10px;"/>
      <div class="pt lg" style="left:44%; top:80%;--dur:20s;--d:-8s; --dx:8px;"/>
      <div class="pt lg" style="left:71%; top:24%;--dur:25s;--d:-18s;--dx:-6px;"/>
      <div class="pt md" style="left:18%; top:42%;--dur:17s;--d:-2s; --dx:6px;"/>
      <div class="pt md" style="left:61%; top:64%;--dur:21s;--d:-11s;--dx:-8px;"/>
      <div class="pt md" style="left:34%; top:57%;--dur:19s;--d:-6s; --dx:10px;"/>
      <div class="pt md" style="left:81%; top:77%;--dur:23s;--d:-16s;--dx:-5px;"/>
      <div class="pt md" style="left:26%; top:86%;--dur:15s;--d:-9s; --dx:4px;"/>
      <div class="pt md" style="left:54%; top:31%;--dur:26s;--d:-20s;--dx:-12px;"/>
      <div class="pt md" style="left:92%; top:38%;--dur:18s;--d:-7s; --dx:7px;"/>
      <div class="pt md" style="left:5%;  top:22%;--dur:24s;--d:-12s;--dx:-4px;"/>
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

    <!-- ═══════════════════════════════════
         LEFT SIDEBAR
    ═══════════════════════════════════ -->
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sb-brand" aria-label="Jinsie AI Studio">
        <div class="sb-brand-hex">
          <svg width="28" height="28" viewBox="0 0 22 22" fill="none">
            <path d="M11 1.5L20.5 6.5V15.5L11 20.5L1.5 15.5V6.5Z"
              stroke="url(#sbHexG)" stroke-width="1.5" stroke-linejoin="round"/>
            <circle cx="11" cy="11" r="2.5" fill="url(#sbHexG)" opacity="0.9"/>
            <defs>
              <linearGradient id="sbHexG" x1="1.5" y1="1.5" x2="20.5" y2="20.5" gradientUnits="userSpaceOnUse">
                <stop offset="0%" :stop-color="themeAccentA"/>
                <stop offset="100%" :stop-color="themeAccentB"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span class="sb-brand-dot"/>
      </div>

      <!-- Navigation -->
      <nav class="sb-nav" role="tablist">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          role="tab"
          :class="['sb-item', { 'is-active': modelValue === tab.id }]"
          :aria-selected="modelValue === tab.id"
          @click="$emit('update:modelValue', tab.id)"
        >
          <span class="sb-icon" aria-hidden="true">{{ tab.icon }}</span>
          <span class="sb-label">{{ tab.label }}</span>
          <span v-if="tab.badge" class="sb-badge">{{ tab.badge }}</span>
        </button>
      </nav>

      <!-- Footer: header-actions slot + dev toggle -->
      <div class="sb-footer">
        <slot name="header-actions"/>
        <button v-if="devMode" class="sb-dev-btn" title="Dev mode" @click="$emit('toggle-dev')">⚙</button>
      </div>
    </aside>

    <!-- Floating theme switcher — fixed to viewport top-right -->
    <ThemeSwitcher/>

    <!-- ═══════════════════════════════════
         CONTENT AREA
    ═══════════════════════════════════ -->
    <div class="s-content">
      <!-- Progress bar slot -->
      <div v-if="$slots['progress']" class="s-progress">
        <slot name="progress"/>
      </div>

      <!-- Main content -->
      <main class="s-main" ref="mainRef">
        <slot/>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { animate } from 'animejs'
import ThemeSwitcher from './ThemeSwitcher.vue'
import { useTheme } from '../../composables/useTheme'

const props = defineProps<{
  modelValue: string
  tabs: Array<{ id: string; label: string; icon: string; badge?: string }>
  devMode?: boolean
}>()

defineEmits<{
  (e: 'update:modelValue', tab: string): void
  (e: 'toggle-dev'): void
}>()

// ── Theme (shared composable) ────────────────────
const { theme: currentTheme, themeMeta } = useTheme()

// Accent helpers for inline-styled SVG / dynamic styles
function tc(opacity: number, variant: 'a' | 'b' | 'c' = 'a'): string {
  const arr = themeMeta.value.swatches
  // Convert hex swatch to "r,g,b" for use in rgba()
  const hex = variant === 'a' ? arr[0] : variant === 'b' ? arr[1] : arr[2]
  const rgb = hexToRgb(hex)
  return `rgba(${rgb},${opacity})`
}

function hexToRgb(hex: string): string {
  const m = hex.replace('#', '').match(/.{2}/g)
  if (!m || m.length < 3) return '255,255,255'
  return `${parseInt(m[0], 16)},${parseInt(m[1], 16)},${parseInt(m[2], 16)}`
}

const themeAccentA = computed(() => themeMeta.value.swatches[0])
const themeAccentB = computed(() => themeMeta.value.swatches[1])

// ── Content animation ────────────────────────────
const mainRef = ref<HTMLElement | null>(null)

function animateContentIn() {
  const container = mainRef.value
  if (!container) return
  animate(container, { opacity: [0, 1], duration: 340, easing: 'easeOutCubic' })
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

onMounted(() => {
  animate('.sb-item', {
    opacity: [0, 1],
    translateX: [-10, 0],
    duration: 420,
    delay: (_el: HTMLElement, i: number) => 80 + i * 60,
    easing: 'easeOutCubic',
  })
  animate('.sb-brand', {
    opacity: [0, 1],
    translateY: [-8, 0],
    duration: 400,
    easing: 'easeOutCubic',
  })
  setTimeout(animateContentIn, 150)
})

watch(() => props.modelValue, () => {
  setTimeout(animateContentIn, 16)
})
</script>

<style scoped>
/* ══════════════════════════════════════════════════
   Root — row layout so sidebar + content sit side-by-side
══════════════════════════════════════════════════ */
.s-root {
  position: relative;
  min-height: 100vh;
  background: transparent;
  overflow-x: hidden;
  display: flex;
  flex-direction: row;
}

/* ══════════════════════════════════════════════════
   Aurora
══════════════════════════════════════════════════ */
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

.orb-a {
  width: 900px; height: 700px;
  top: -260px; left: -180px;
  background: radial-gradient(ellipse at center,
    var(--orb-a1, rgba(245,158,11,0.36)) 0%,
    var(--orb-a2, rgba(180,80,10,0.14)) 42%,
    transparent 65%
  );
  filter: blur(40px);
  animation: driftA 16s ease-in-out infinite;
}

.orb-b {
  width: 800px; height: 650px;
  bottom: -200px; right: -160px;
  background: radial-gradient(ellipse at center,
    var(--orb-b1, rgba(249,115,22,0.30)) 0%,
    var(--orb-b2, rgba(180,60,10,0.12)) 42%,
    transparent 65%
  );
  filter: blur(44px);
  animation: driftB 20s ease-in-out infinite;
}

.orb-c {
  width: 520px; height: 400px;
  top: 30%; left: 40%;
  background: radial-gradient(ellipse at center,
    var(--orb-c1, rgba(251,191,36,0.14)) 0%,
    transparent 60%
  );
  filter: blur(70px);
  animation: driftC 27s ease-in-out infinite;
}

@keyframes driftA {
  0%,100% { transform: translate(0,0) scale(1); }
  30%      { transform: translate(60px,-35px) scale(1.04); }
  65%      { transform: translate(-28px,50px) scale(0.97); }
}
@keyframes driftB {
  0%,100% { transform: translate(0,0) scale(1); }
  38%      { transform: translate(-50px,-60px) scale(1.07); }
  72%      { transform: translate(38px,30px) scale(0.94); }
}
@keyframes driftC {
  0%,100% { transform: translate(0,0); }
  50%      { transform: translate(-70px,-45px); }
}

/* ── Dot grid ── */
.dot-grid {
  position: fixed; inset: 0;
  z-index: 1; pointer-events: none;
  background-image: radial-gradient(circle, var(--dot-color, rgba(245,158,11,0.20)) 1px, transparent 1px);
  background-size: 38px 38px;
  -webkit-mask-image: radial-gradient(ellipse 75% 70% at 50% 35%, black 15%, transparent 85%);
  mask-image:         radial-gradient(ellipse 75% 70% at 50% 35%, black 15%, transparent 85%);
}

/* ══════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════ */
.sidebar {
  position: fixed;
  left: 0; top: 0; bottom: 0;
  width: 88px;
  z-index: 50;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px 0 16px;
  gap: 0;

  background: var(--sidebar-bg, rgba(7,5,2,0.88));
  backdrop-filter: blur(28px) saturate(150%);
  -webkit-backdrop-filter: blur(28px) saturate(150%);
  border-right: 1px solid var(--sidebar-border, rgba(245,158,11,0.10));
  box-shadow: var(--sidebar-shadow, 4px 0 32px rgba(0,0,0,0.55)), inset -1px 0 0 var(--sidebar-border, rgba(245,158,11,0.06));
}

/* ── Brand ── */
.sb-brand {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 28px;
  opacity: 0;
}

.sb-brand-hex {
  line-height: 0;
  filter: drop-shadow(0 0 10px var(--brand-glow, rgba(245,158,11,0.65)));
}

.sb-brand-dot {
  display: block;
  width: 18px;
  height: 2px;
  border-radius: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-a, rgba(245,158,11,0.6)), transparent);
}

/* ── Nav ── */
.sb-nav {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
  width: 100%;
  padding: 0 8px;
}

.sb-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  width: 72px;
  padding: 10px 6px;
  border-radius: 14px;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s cubic-bezier(0.16,1,0.3,1);
  opacity: 0;
}

.sb-item:hover:not(.is-active) {
  background: var(--item-hover-bg, rgba(245,158,11,0.07));
  border-color: var(--item-hover-border, rgba(245,158,11,0.18));
}

.sb-item.is-active {
  background: var(--item-active-bg, rgba(245,158,11,0.14));
  border-color: var(--item-active-border, rgba(245,158,11,0.38));
  box-shadow:
    0 0 20px var(--item-glow, rgba(245,158,11,0.18)),
    inset 0 1px 0 rgba(255,255,255,0.08);
}

/* Active indicator bar */
.sb-item.is-active::before {
  content: '';
  position: absolute;
  left: -9px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  border-radius: 0 2px 2px 0;
  background: var(--accent-a, rgba(245,158,11,0.8));
  box-shadow: 0 0 8px var(--accent-a, rgba(245,158,11,0.6));
}

.sb-icon {
  font-size: 17px;
  line-height: 1;
  color: rgba(255,255,255,0.42);
  transition: color 0.18s;
}
.sb-item:hover:not(.is-active) .sb-icon { color: rgba(255,255,255,0.70); }
.sb-item.is-active .sb-icon             { color: var(--arc-300, #fbbf24); }

.sb-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: rgba(255,255,255,0.38);
  white-space: nowrap;
  transition: color 0.18s;
}
.sb-item:hover:not(.is-active) .sb-label { color: rgba(255,255,255,0.65); }
.sb-item.is-active .sb-label             { color: var(--arc-300, #fbbf24); }

.sb-badge {
  position: absolute;
  top: 6px; right: 6px;
  font-size: 8px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: var(--arc-300, #fbbf24);
  border: 1px solid var(--item-active-border, rgba(245,158,11,0.30));
  border-radius: 3px;
  padding: 0 3px;
}

/* ── Footer ── */
.sb-footer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  width: 100%;
  border-top: 1px solid var(--sidebar-border, rgba(245,158,11,0.08));
}

.sb-dev-btn {
  width: 36px; height: 36px;
  border-radius: 10px;
  font-size: 14px;
  font-family: inherit;
  color: rgba(255,255,255,0.35);
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color 0.18s, background 0.18s;
}
.sb-dev-btn:hover { color: rgba(255,255,255,0.65); background: rgba(255,255,255,0.08); }

/* ══════════════════════════════════════════════════
   CONTENT AREA
══════════════════════════════════════════════════ */
.s-content {
  margin-left: 88px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  position: relative;
  z-index: 1;
}

/* Progress bar — sticky top strip with glass background */
.s-progress {
  position: sticky;
  top: 0;
  z-index: 40;
  padding: 0.45rem 1.75rem 0.35rem;
  background: var(--sidebar-bg, rgba(9,7,3,0.82));
  backdrop-filter: blur(24px) saturate(150%);
  -webkit-backdrop-filter: blur(24px) saturate(150%);
  border-bottom: 1px solid var(--sidebar-border, rgba(245,158,11,0.10));
  flex-shrink: 0;
}

/* Main content */
.s-main {
  flex: 1;
  padding: 1.5rem 1.75rem;
  max-width: 1440px;
  width: 100%;
  box-sizing: border-box;
}

/* ══════════════════════════════════════════════════
   Water drop ripples
══════════════════════════════════════════════════ */
.water-layer { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.drop { position: absolute; }

.dc {
  position: absolute;
  width: 7px; height: 7px;
  border-radius: 50%;
  top: -3.5px; left: -3.5px;
  background: var(--dc-color, rgba(251,191,36,0.95));
  box-shadow:
    0 0 6px  var(--dc-color, rgba(251,191,36,1)),
    0 0 18px var(--accent-a, rgba(245,158,11,0.70)),
    0 0 36px var(--accent-a, rgba(245,158,11,0.35)),
    0 0 60px var(--accent-a, rgba(245,158,11,0.15));
  animation: dcPulse 2.8s ease-in-out infinite;
}
@keyframes dcPulse {
  0%,100% { opacity: 0.95; transform: scale(1); }
  50%      { opacity: 0.40; transform: scale(0.65); }
}

.ring {
  position: absolute;
  width: var(--s,350px); height: var(--s,350px);
  border-radius: 50%;
  border: 1.5px solid var(--c, rgba(245,158,11,0.50));
  box-shadow: 0 0 14px var(--c), 0 0 30px rgba(0,0,0,0.04);
  top: calc(var(--s,350px) / -2);
  left: calc(var(--s,350px) / -2);
  transform: scale(0.04);
  opacity: 0;
  animation: waterRing var(--dur,8s) cubic-bezier(0.08,0.65,0.28,1) infinite;
}
@keyframes waterRing {
  0%   { transform: scale(0.04); opacity: 0; }
  5%   { opacity: 0.95; }
  40%  { opacity: 0.40; }
  100% { transform: scale(1); opacity: 0; }
}

/* ══════════════════════════════════════════════════
   Particles
══════════════════════════════════════════════════ */
.pt-layer { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
.pt {
  position: absolute;
  border-radius: 50%;
  animation-duration: var(--dur,20s);
  animation-delay: var(--d,0s);
  animation-timing-function: ease-in-out;
  animation-iteration-count: infinite;
}
.pt.lg {
  width: 6px; height: 6px;
  background: radial-gradient(circle, var(--pt-a,#fbbf24) 0%, rgba(245,158,11,0.35) 65%, transparent 100%);
  box-shadow:
    0 0 8px  var(--pt-glow-a, rgba(251,191,36,0.95)),
    0 0 22px var(--accent-a,  rgba(245,158,11,0.65)),
    0 0 45px var(--accent-a,  rgba(245,158,11,0.30)),
    0 0 80px var(--accent-a,  rgba(245,158,11,0.10));
  animation-name: ptRise;
}
.pt.md {
  width: 3.5px; height: 3.5px;
  background: radial-gradient(circle, var(--pt-b,#fde68a) 0%, rgba(245,158,11,0.45) 60%, transparent 100%);
  box-shadow:
    0 0 5px  var(--pt-glow-b, rgba(253,230,138,0.95)),
    0 0 14px var(--accent-a,  rgba(245,158,11,0.55)),
    0 0 28px var(--accent-a,  rgba(245,158,11,0.22));
  animation-name: ptRise;
}
.pt.sm {
  width: 2px; height: 2px;
  background: var(--pt-c, #fde68a);
  box-shadow:
    0 0 3px  var(--pt-glow-c, rgba(253,230,138,1)),
    0 0 9px  var(--accent-c,  rgba(251,191,36,0.80)),
    0 0 18px var(--accent-a,  rgba(245,158,11,0.40));
  animation-name: ptTwinkle;
}
@keyframes ptRise {
  0%   { transform: translateY(0) translateX(0); opacity: 0; }
  8%   { opacity: 1; }
  50%  { transform: translateY(-45px) translateX(var(--dx,6px)); opacity: 0.85; }
  92%  { opacity: 0.30; }
  100% { transform: translateY(-90px) translateX(0); opacity: 0; }
}
@keyframes ptTwinkle {
  0%,100% { opacity: 0; transform: scale(0.5); }
  25%,75%  { opacity: 1; transform: scale(1.8); }
  50%      { opacity: 0.55; transform: scale(1.2); }
}

/* ══════════════════════════════════════════════════
   THEME OVERRIDES via data-theme (cascade into vars)
══════════════════════════════════════════════════ */

/* Blue theme */
.s-root[data-theme="blue"] {
  --accent-a:         rgba(14,165,233,0.65);
  --accent-c:         rgba(56,189,248,0.80);
  --accent-a-solid:   #0ea5e9;
  --brand-glow:       rgba(14,165,233,0.65);
  --sidebar-border:   rgba(14,165,233,0.10);
  --item-hover-bg:    rgba(14,165,233,0.07);
  --item-hover-border:rgba(14,165,233,0.20);
  --item-active-bg:   rgba(14,165,233,0.14);
  --item-active-border:rgba(14,165,233,0.40);
  --item-glow:        rgba(14,165,233,0.20);
  --orb-a1: rgba(14,165,233,0.36);
  --orb-a2: rgba(6,60,160,0.14);
  --orb-b1: rgba(99,102,241,0.28);
  --orb-b2: rgba(50,40,180,0.12);
  --orb-c1: rgba(56,189,248,0.12);
  --dot-color: rgba(14,165,233,0.18);
  --dc-color: rgba(56,189,248,0.95);
  --pt-a: #38bdf8;
  --pt-b: #bae6fd;
  --pt-c: #bae6fd;
  --pt-glow-a: rgba(56,189,248,0.95);
  --pt-glow-b: rgba(186,230,253,0.95);
  --pt-glow-c: rgba(186,230,253,1);
}

/* Purple theme */
.s-root[data-theme="purple"] {
  --accent-a:         rgba(168,85,247,0.65);
  --accent-c:         rgba(192,132,252,0.80);
  --accent-a-solid:   #a855f7;
  --brand-glow:       rgba(168,85,247,0.65);
  --sidebar-border:   rgba(168,85,247,0.10);
  --item-hover-bg:    rgba(168,85,247,0.07);
  --item-hover-border:rgba(168,85,247,0.22);
  --item-active-bg:   rgba(168,85,247,0.14);
  --item-active-border:rgba(168,85,247,0.40);
  --item-glow:        rgba(168,85,247,0.20);
  --orb-a1: rgba(168,85,247,0.36);
  --orb-a2: rgba(80,20,180,0.14);
  --orb-b1: rgba(244,63,94,0.28);
  --orb-b2: rgba(160,20,80,0.12);
  --orb-c1: rgba(192,132,252,0.14);
  --dot-color: rgba(168,85,247,0.18);
  --dc-color: rgba(192,132,252,0.95);
  --pt-a: #c084fc;
  --pt-b: #e9d5ff;
  --pt-c: #e9d5ff;
  --pt-glow-a: rgba(192,132,252,0.95);
  --pt-glow-b: rgba(233,213,255,0.95);
  --pt-glow-c: rgba(233,213,255,1);
}

/* ═══════════════════════════════════════════════
   珍珠晨光 · Pearl Dawn (light theme)
═══════════════════════════════════════════════ */
.s-root[data-theme="pearl"] {
  --accent-a:           rgba(200,154,85,0.72);
  --accent-c:           rgba(233,203,131,0.80);
  --accent-a-solid:     #c89a55;
  --brand-glow:         rgba(200,154,85,0.50);

  /* Bright white pearl sidebar */
  --sidebar-bg:         rgba(255,255,255,0.88);
  --sidebar-border:     rgba(200,154,85,0.18);
  --sidebar-shadow:     4px 0 28px rgba(100,90,60,0.10);

  --item-hover-bg:      rgba(200,154,85,0.10);
  --item-hover-border:  rgba(200,154,85,0.28);
  --item-active-bg:     rgba(255,238,200,0.55);
  --item-active-border: rgba(200,154,85,0.55);
  --item-glow:          rgba(200,154,85,0.22);

  /* Aurora orbs — brighter, more visible warm-cool blooms on pearl bg */
  --orb-a1: rgba(255,210,130,0.55);
  --orb-a2: rgba(220,170,80,0.18);
  --orb-b1: rgba(150,190,225,0.50);
  --orb-b2: rgba(90,150,200,0.18);
  --orb-c1: rgba(255,225,160,0.30);

  --dot-color:  rgba(200,154,85,0.16);
  --dc-color:   rgba(200,154,85,0.85);
  --pt-a:       #c89a55;
  --pt-b:       #e9cb83;
  --pt-c:       #d6b06a;
  --pt-glow-a:  rgba(200,154,85,0.80);
  --pt-glow-b:  rgba(233,203,131,0.80);
  --pt-glow-c:  rgba(200,154,85,0.95);
}

/* Sidebar nav items — dark icons/labels on white pearl */
.s-root[data-theme="pearl"] .sb-icon                                { color: rgba(60,66,76,0.55); }
.s-root[data-theme="pearl"] .sb-item:hover:not(.is-active) .sb-icon { color: rgba(60,66,76,0.85); }
.s-root[data-theme="pearl"] .sb-label                               { color: rgba(60,66,76,0.55); }
.s-root[data-theme="pearl"] .sb-item:hover:not(.is-active) .sb-label{ color: rgba(60,66,76,0.85); }
.s-root[data-theme="pearl"] .sb-item.is-active .sb-icon,
.s-root[data-theme="pearl"] .sb-item.is-active .sb-label            { color: #8b6722; }
.s-root[data-theme="pearl"] .sb-dev-btn                             { color: rgba(60,66,76,0.55); background: rgba(0,0,0,0.04); border-color: rgba(0,0,0,0.08); }
.s-root[data-theme="pearl"] .sb-dev-btn:hover                       { color: rgba(60,66,76,0.85); background: rgba(0,0,0,0.07); }

/* Soft white highlight on active item */
.s-root[data-theme="pearl"] .sb-item.is-active {
  box-shadow: 0 4px 18px var(--item-glow), inset 0 1px 0 rgba(255,255,255,0.85);
}

/* ═══════════════════════════════════════════════
   Pearl Dawn — drifting flowing light layer
   Below content but above page bg. Strong, visible bloom that
   slowly rotates → "morning light streaming through the room".
═══════════════════════════════════════════════ */
.s-root[data-theme="pearl"]::before {
  content: '';
  position: fixed;
  inset: -30%;
  z-index: 0;
  pointer-events: none;
  background:
    conic-gradient(
      from 0deg at 28% 32%,
      transparent 0deg,
      rgba(255, 198, 110, 0.50) 50deg,
      rgba(255, 222, 165, 0.28) 110deg,
      transparent 190deg,
      rgba(160, 205, 235, 0.42) 270deg,
      rgba(190, 220, 240, 0.20) 320deg,
      transparent 360deg
    );
  filter: blur(60px);
  animation: pearlFlow 26s linear infinite;
  will-change: transform;
  mix-blend-mode: normal;
}

.s-root[data-theme="pearl"]::after {
  content: '';
  position: fixed;
  inset: -20%;
  z-index: 0;
  pointer-events: none;
  background:
    conic-gradient(
      from 180deg at 75% 68%,
      transparent 0deg,
      rgba(255, 210, 140, 0.38) 70deg,
      transparent 170deg,
      rgba(195, 220, 235, 0.32) 250deg,
      rgba(255, 205, 145, 0.22) 320deg,
      transparent 360deg
    );
  filter: blur(70px);
  animation: pearlFlow 36s linear infinite reverse;
  will-change: transform;
}

@keyframes pearlFlow {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .sidebar    { width: 64px; }
  .s-content  { margin-left: 64px; }
  .sb-label   { display: none; }
  .sb-item    { padding: 10px 4px; }
  .s-main     { padding: 1rem; }
}
</style>
