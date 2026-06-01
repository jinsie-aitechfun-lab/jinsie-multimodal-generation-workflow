<template>
  <div class="landing">
    <!-- Decorative starfield + soft glow drift behind everything.
         Three layers: ambient radial wash, two big blurred glows,
         and a sparse twinkle field. -->
    <div class="landing-bg" aria-hidden="true">
      <div class="bg-ambient"></div>
      <div class="bg-glow bg-glow-a"></div>
      <div class="bg-glow bg-glow-b"></div>
      <div class="bg-grid"></div>
      <div class="bg-stars">
        <span
          v-for="i in 36"
          :key="i"
          :style="starStyle(i)"
        ></span>
      </div>
    </div>

    <!-- Top-right utility cluster: ThemeSwitcher (pinned to viewport
         top-right via :deep override) + lightweight "进入 Studio" CTA.
         Identity tag stays minimal — no login system, no avatar. -->
    <div class="landing-topbar" aria-label="顶部导航">
      <button
        type="button"
        class="landing-enter-studio"
        @click="goStudio"
      >
        <span class="landing-enter-studio-text">Enter Studio</span>
        <span class="landing-enter-studio-arrow" aria-hidden="true">→</span>
      </button>
    </div>
    <ThemeSwitcher class="landing-theme-switcher" />

    <!-- ── Hero ── -->
    <header class="landing-hero">
      <div class="hero-tag">
        <span class="hero-tag-dot" aria-hidden="true"></span>
        AI Story-to-Video Creative Workspace
      </div>
      <h1 class="hero-title">
        <span class="hero-title-brand">Jinsie</span>
        <span class="hero-title-rest">AI Video Studio</span>
      </h1>
      <p class="hero-subtitle">
        把故事灵感转化为绘本风视频作品
      </p>

      <div class="hero-cta-row">
        <button type="button" class="hero-primary" @click="goStudio">
          <span class="hero-primary-icon" aria-hidden="true">✦</span>
          Start Creating
        </button>
        <button
          type="button"
          class="hero-secondary"
          @click="scrollTo('workflow')"
        >
          View Workflow
        </button>
      </div>

      <!-- Tiny orbital ornament to suggest "AI workflow" without filling
           the page with a heavy hero illustration -->
      <div class="hero-orbit" aria-hidden="true">
        <div class="orbit-ring orbit-ring-1"></div>
        <div class="orbit-ring orbit-ring-2"></div>
        <div class="orbit-ring orbit-ring-3"></div>
        <div class="orbit-center">
          <svg viewBox="0 0 32 32" width="22" height="22" fill="none">
            <rect x="6" y="9" width="20" height="14" rx="3"
              stroke="currentColor" stroke-width="1.4" stroke-opacity="0.7"/>
            <path d="M14 13 L20 16 L14 19 Z" fill="currentColor" fill-opacity="0.78"/>
          </svg>
        </div>
        <span class="orbit-dot orbit-dot-1"></span>
        <span class="orbit-dot orbit-dot-2"></span>
        <span class="orbit-dot orbit-dot-3"></span>
      </div>
    </header>

    <!-- ── Workflow Showcase ── -->
    <section id="workflow" class="landing-section workflow-section">
      <h2 class="section-eyebrow">
        <span class="eyebrow-line"></span>
        Workflow
        <span class="eyebrow-line"></span>
      </h2>
      <h3 class="section-title">完整 Story-to-Video 创作链路</h3>

      <ol class="workflow-rail">
        <template v-for="(step, idx) in workflowSteps" :key="step.id">
          <li class="workflow-node">
            <div class="workflow-node-orb">
              <span class="workflow-node-num">{{ String(idx + 1).padStart(2, '0') }}</span>
            </div>
            <div class="workflow-node-body">
              <div class="workflow-node-title">{{ step.title }}</div>
              <div class="workflow-node-desc">{{ step.desc }}</div>
            </div>
          </li>
          <li
            v-if="idx < workflowSteps.length - 1"
            class="workflow-link"
            aria-hidden="true"
          ></li>
        </template>
      </ol>
    </section>

    <!-- ── Cases ── -->
    <section class="landing-section cases-section">
      <h2 class="section-eyebrow">
        <span class="eyebrow-line"></span>
        Showcase
        <span class="eyebrow-line"></span>
      </h2>
      <h3 class="section-title">已生成案例</h3>

      <div class="case-grid">
        <article
          v-for="caseItem in caseList"
          :key="caseItem.id"
          class="case-card"
        >
          <!-- Illustrated thumbnail — pure CSS so it works without backend
               connectivity and stays themed across light/dark. -->
          <div :class="['case-thumb', `case-thumb--${caseItem.tone}`]" aria-hidden="true">
            <div class="case-thumb-sky"></div>
            <div class="case-thumb-sun"></div>
            <div class="case-thumb-hill case-thumb-hill-back"></div>
            <div class="case-thumb-hill case-thumb-hill-front"></div>
            <div class="case-thumb-play">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none">
                <circle cx="12" cy="12" r="11" stroke="currentColor" stroke-opacity="0.5"/>
                <path d="M10 8 L17 12 L10 16 Z" fill="currentColor" fill-opacity="0.86"/>
              </svg>
            </div>
          </div>

          <div class="case-meta">
            <div class="case-title">{{ caseItem.title }}</div>
            <div class="case-tag-row">
              <span
                v-for="tag in caseItem.tags"
                :key="tag"
                class="case-tag"
              >{{ tag }}</span>
            </div>
            <button
              type="button"
              class="case-cta"
              @click="goStudio"
            >
              进入工作台 →
            </button>
          </div>
        </article>
      </div>
    </section>

    <!-- ── Footer banner ── -->
    <footer class="landing-foot">
      <div class="foot-content">
        <div class="foot-copy">开始创作你的故事视频</div>
        <button type="button" class="foot-cta" @click="goStudio">
          进入 Studio
          <span class="foot-cta-arrow">→</span>
        </button>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import ThemeSwitcher from '../studio/ThemeSwitcher.vue'

const router = useRouter()

function goStudio() {
  router.push('/studio')
}

function scrollTo(id: string) {
  if (typeof document === 'undefined') return
  const el = document.getElementById(id)
  if (el && 'scrollIntoView' in el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// Workflow nodes — same six-stage chain as the Studio timeline, kept in
// sync at the label level. Internal step ids are server-side keys but only
// label/desc surface in the UI.
const workflowSteps = [
  { id: 'story',      title: '故事生成', desc: '根据主题生成儿童故事' },
  { id: 'storyboard', title: '分镜设计', desc: '拆解镜头与叙事节奏' },
  { id: 'images',     title: '画面生成', desc: '生成候选图并支持审核' },
  { id: 'voice',      title: '配音旁白', desc: '生成旁白音频' },
  { id: 'subtitles',  title: '字幕生成', desc: '生成时间轴字幕' },
  { id: 'video',      title: '视频合成', desc: '输出最终绘本风视频' },
]

// Static showcase cards — illustrated thumbnails so the page works in any
// environment (no backend hits, no real path leaks). Titles + tags match
// the storybook tone of the Studio.
const caseList = [
  {
    id: 'forest',
    title: '森林里的小伙伴',
    tags: ['绘本风', '亲子故事'],
    tone: 'forest',
  },
  {
    id: 'ocean',
    title: '小蝌蚪的冒险',
    tags: ['儿童故事', 'AI Workflow'],
    tone: 'ocean',
  },
  {
    id: 'dawn',
    title: '清晨的旅行',
    tags: ['温暖治愈', '绘本风'],
    tone: 'dawn',
  },
]

// Pseudo-random but stable star positions (deterministic so SSR / HMR
// don't shuffle the field on every reload).
function starStyle(i: number) {
  const golden = 0.61803398875
  const left = ((i * golden * 100) % 100)
  const top = ((i * 17 + 9) % 88)
  const size = 1 + ((i * 7) % 3)
  const delay = ((i * 13) % 7) * 0.4
  return {
    left: `${left}%`,
    top: `${top}%`,
    width: `${size}px`,
    height: `${size}px`,
    animationDelay: `${delay}s`,
  }
}
</script>

<style scoped>
.landing {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
  color: var(--text-primary);
  /* Use the same token-driven page background as Studio.
     - Dark themes (gold/blue/purple) get their warm "deep space" radial
       wash from style.css.
     - Pearl Dawn gets a light pearl + ice-blue gradient — text colour
       (also token-driven) stays readable on light bg, no more grey fog. */
  background-color: var(--page-bg-color, #09090b);
  background-image: var(--page-bg-image, none);
  background-repeat: no-repeat;
  background-attachment: fixed;
}

/* Top-right utility cluster — sits left of the ThemeSwitcher. */
.landing-topbar {
  position: fixed;
  top: 22px;
  right: 156px;       /* leaves space for the ThemeSwitcher pill (~120px wide) */
  z-index: 9998;
  display: inline-flex;
  align-items: center;
  gap: 12px;
}

.landing-enter-studio {
  appearance: none;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 10%, rgba(10, 8, 4, 0.72));
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  color: rgba(255, 245, 220, 0.94);
  padding: 8px 16px;
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: inherit;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 18%, transparent),
    0 8px 22px rgba(0, 0, 0, 0.28);
  transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s;
}
.landing-enter-studio:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 52%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 26%, transparent),
    0 10px 28px rgba(0, 0, 0, 0.32),
    0 0 22px color-mix(in srgb, var(--arc-300) 20%, transparent);
}
.landing-enter-studio-arrow {
  transition: transform 0.18s;
}
.landing-enter-studio:hover .landing-enter-studio-arrow {
  transform: translateX(2px);
}

/* Pin the ThemeSwitcher to the top-right of the landing page (overrides
   the shared component's default bottom-right placement). Scoped :deep
   keeps every other consumer of <ThemeSwitcher /> unchanged. */
:deep(.landing-theme-switcher.ts-root),
:deep(.landing-theme-switcher .ts-root) {
  top: 22px;
  bottom: auto;
  right: 24px;
}

/* Flip the popover panel so it opens DOWNWARD from the trigger — the
   shared ThemeSwitcher defaults to opening upward (bottom: 100% + 12px),
   which goes off-screen when the trigger is anchored to the top.
   Without this override, clicks "look" unresponsive because the panel
   renders above the viewport. */
:deep(.landing-theme-switcher .ts-panel),
:deep(.landing-theme-switcher ~ .ts-panel),
:deep(.ts-root .ts-panel) {
  bottom: auto;
  top: calc(100% + 12px);
}
:deep(.landing-theme-switcher .ts-panel::after),
:deep(.landing-theme-switcher ~ .ts-panel::after),
:deep(.ts-root .ts-panel::after) {
  top: auto;
  bottom: 100%;
  border-top: 0;
  border-bottom: 7px solid var(--glass-bg-light, rgba(20,16,8,0.94));
  filter: drop-shadow(0 -1px 1px rgba(0,0,0,0.30));
}

/* ── Background — soft glows + starfield ── */
.landing-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

/* Slow ambient drift — keeps the page feeling "alive" without animating
   anything users actually look at. */
.bg-ambient {
  position: absolute;
  inset: -20%;
  background:
    radial-gradient(
      circle at 30% 22%,
      color-mix(in srgb, var(--arc-400) 8%, transparent) 0%,
      transparent 40%
    ),
    radial-gradient(
      circle at 78% 78%,
      color-mix(in srgb, var(--arc-300) 6%, transparent) 0%,
      transparent 42%
    );
  filter: blur(40px);
  animation: landing-ambient 22s ease-in-out infinite;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(
      to right,
      color-mix(in srgb, var(--arc-300) 5%, transparent) 1px,
      transparent 1px
    ),
    linear-gradient(
      to bottom,
      color-mix(in srgb, var(--arc-300) 5%, transparent) 1px,
      transparent 1px
    );
  background-size: 64px 64px;
  mask-image: radial-gradient(
    ellipse 70% 60% at 50% 40%,
    rgba(0, 0, 0, 0.5),
    transparent 75%
  );
  -webkit-mask-image: radial-gradient(
    ellipse 70% 60% at 50% 40%,
    rgba(0, 0, 0, 0.5),
    transparent 75%
  );
  opacity: 0.55;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.62;
}
.bg-glow-a {
  top: -12%;
  left: -10%;
  width: 580px;
  height: 580px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--arc-400) 44%, transparent) 0%,
    transparent 65%
  );
  animation: landing-glow-a 18s ease-in-out infinite;
}
.bg-glow-b {
  bottom: -18%;
  right: -12%;
  width: 680px;
  height: 680px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--prism-400, #fb923c) 30%, transparent) 0%,
    transparent 65%
  );
  opacity: 0.38;
  animation: landing-glow-b 24s ease-in-out infinite;
}

.bg-stars span {
  position: absolute;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 78%, transparent);
  box-shadow: 0 0 6px color-mix(in srgb, var(--arc-300) 38%, transparent);
  animation: landing-twinkle 4.4s ease-in-out infinite;
}

@keyframes landing-twinkle {
  0%, 100% { opacity: 0.30; transform: scale(0.85); }
  50%      { opacity: 1;    transform: scale(1.15); }
}
@keyframes landing-ambient {
  0%, 100% { transform: translate(0, 0)    scale(1);    }
  50%      { transform: translate(2%, -2%) scale(1.06); }
}
@keyframes landing-glow-a {
  0%, 100% { transform: translate(0, 0); }
  50%      { transform: translate(4%, 3%); }
}
@keyframes landing-glow-b {
  0%, 100% { transform: translate(0, 0); }
  50%      { transform: translate(-4%, -3%); }
}

/* ── Hero ── */
.landing-hero {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 96px 24px 64px;
  max-width: 1080px;
  margin: 0 auto;
}

.hero-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 8%, transparent);
  color: var(--arc-300);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.06em;
}
.hero-tag-dot {
  width: 6px; height: 6px;
  border-radius: 999px;
  background: currentColor;
  box-shadow: 0 0 6px color-mix(in srgb, currentColor 60%, transparent);
  animation: landing-pulse 2s ease-in-out infinite;
}

@keyframes landing-pulse {
  0%, 100% { opacity: 0.55; transform: scale(0.85); }
  50%      { opacity: 1;    transform: scale(1.15); }
}

.hero-title {
  margin: 24px 0 14px;
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.15;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.hero-title-brand {
  background: linear-gradient(
    135deg,
    color-mix(in srgb, var(--arc-200) 92%, transparent) 0%,
    var(--arc-300) 50%,
    var(--arc-400) 100%
  );
  -webkit-background-clip: text;
          background-clip: text;
  color: transparent;
  font-weight: 800;
  letter-spacing: 0.03em;
}
.hero-title-rest {
  color: var(--text-primary);
  font-weight: 600;
  font-size: 0.65em;
  letter-spacing: 0.1em;
}

.hero-subtitle {
  margin: 0 auto 40px;
  max-width: 520px;
  font-size: 1.0625rem;
  color: var(--text-secondary);
  line-height: 1.65;
  letter-spacing: 0.02em;
}

.hero-cta-row {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.hero-primary {
  appearance: none;
  border: 1px solid var(--border-arc);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 18%, rgba(20, 14, 6, 0.92)) 0%,
    rgba(10, 8, 4, 0.96) 100%
  );
  color: rgba(255, 245, 220, 0.96);
  padding: 13px 28px;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 22%, transparent),
    0 12px 28px rgba(0, 0, 0, 0.30),
    0 0 18px color-mix(in srgb, var(--arc-300) 14%, transparent);
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
}
.hero-primary:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 28%, transparent),
    0 16px 34px rgba(0, 0, 0, 0.38),
    0 0 26px color-mix(in srgb, var(--arc-300) 22%, transparent);
}
.hero-primary-icon {
  color: var(--arc-300);
  font-size: 0.85em;
}

.hero-secondary {
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--text-muted) 35%, transparent);
  background: transparent;
  color: var(--text-secondary);
  padding: 11px 22px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.hero-secondary:hover {
  border-color: color-mix(in srgb, var(--arc-300) 42%, transparent);
  color: var(--arc-300);
  background: color-mix(in srgb, var(--arc-400) 4%, transparent);
}

/* ── Orbit ornament ── */
.hero-orbit {
  position: relative;
  width: 220px;
  height: 220px;
  margin: 56px auto 8px;
  color: var(--arc-300);
}

.orbit-ring {
  position: absolute;
  inset: 0;
  border: 1px dashed color-mix(in srgb, var(--arc-300) 26%, transparent);
  border-radius: 999px;
  animation: orbit-spin 22s linear infinite;
}
.orbit-ring-2 {
  inset: 26px;
  border-style: solid;
  border-color: color-mix(in srgb, var(--arc-300) 18%, transparent);
  animation-duration: 14s;
  animation-direction: reverse;
}
.orbit-ring-3 {
  inset: 52px;
  border-color: color-mix(in srgb, var(--arc-300) 14%, transparent);
  border-style: dashed;
  animation-duration: 30s;
}

.orbit-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--arc-300);
  filter: drop-shadow(0 0 16px color-mix(in srgb, var(--arc-300) 30%, transparent));
}

.orbit-dot {
  position: absolute;
  width: 8px; height: 8px;
  border-radius: 999px;
  background: var(--arc-300);
  box-shadow: 0 0 10px color-mix(in srgb, var(--arc-300) 60%, transparent);
}
.orbit-dot-1 { top: 4px;    left: calc(50% - 4px); }
.orbit-dot-2 { right: 22px; top: calc(50% - 4px); }
.orbit-dot-3 { bottom: 32px; left: 38px; }

@keyframes orbit-spin {
  to { transform: rotate(360deg); }
}

/* ── Sections (Workflow + Cases) ── */
.landing-section {
  position: relative;
  z-index: 1;
  padding: 56px 24px 72px;
  max-width: 1100px;
  margin: 0 auto;
}

.section-eyebrow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--arc-300) 80%, transparent);
  margin: 0 0 14px;
}
.eyebrow-line {
  width: 36px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--arc-300) 60%, transparent),
    transparent
  );
}

.section-title {
  text-align: center;
  font-size: clamp(1.4rem, 2.4vw, 1.875rem);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 44px;
  letter-spacing: 0.04em;
}

/* ── Workflow Rail ── */
.workflow-rail {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: stretch;
  gap: 0;
  justify-content: center;
}

.workflow-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  flex: 0 0 140px;
  max-width: 160px;
  padding: 16px 8px;
  text-align: center;
  transition: transform 0.2s ease;
}
.workflow-node:hover {
  transform: translateY(-2px);
}

.workflow-node-orb {
  position: relative;
  width: 48px;
  height: 48px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 8%, rgba(8, 7, 5, 0.6));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--arc-300);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 18%, transparent),
    0 0 12px color-mix(in srgb, var(--arc-300) 14%, transparent);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.workflow-node:hover .workflow-node-orb {
  border-color: color-mix(in srgb, var(--arc-300) 52%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 28%, transparent),
    0 0 22px color-mix(in srgb, var(--arc-300) 26%, transparent);
}

.workflow-node-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.workflow-node-desc {
  margin-top: 4px;
  font-size: 0.6875rem;
  color: var(--text-muted);
  line-height: 1.5;
  letter-spacing: 0.01em;
}

.workflow-link {
  flex: 0 0 36px;
  height: 1px;
  margin-top: 38px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--arc-300) 36%, transparent),
    color-mix(in srgb, var(--arc-300) 12%, transparent)
  );
  list-style: none;
}

/* ── Case cards ── */
.case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 20px;
  max-width: 960px;
  margin: 0 auto;
}

.case-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid var(--border-glass);
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  overflow: hidden;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 8%, transparent),
    0 10px 26px rgba(0, 0, 0, 0.28);
  transition: transform 0.22s, border-color 0.22s, box-shadow 0.22s;
}
/* Soft top hairline highlight — same trick the Studio work card uses. */
.case-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 14px;
  right: 14px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--arc-200) 38%, transparent),
    transparent
  );
  pointer-events: none;
}
.case-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--arc-300) 42%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 14%, transparent),
    0 22px 46px rgba(0, 0, 0, 0.40),
    0 0 28px color-mix(in srgb, var(--arc-300) 18%, transparent);
}

.case-thumb {
  position: relative;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 14%, #14110a) 0%,
    rgba(8, 7, 5, 0.94) 100%
  );
}
.case-thumb-sky {
  position: absolute;
  inset: 0 0 42% 0;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 18%, transparent),
    color-mix(in srgb, var(--arc-400) 6%, transparent)
  );
}
.case-thumb-sun {
  position: absolute;
  top: 22%;
  left: 70%;
  width: 18px;
  height: 18px;
  border-radius: 999px;
  background: var(--arc-300);
  box-shadow:
    0 0 16px color-mix(in srgb, var(--arc-300) 60%, transparent),
    0 0 0 4px color-mix(in srgb, var(--arc-300) 18%, transparent);
}
.case-thumb-hill {
  position: absolute;
  bottom: 24%;
  border-radius: 50% 50% 0 0;
}
.case-thumb-hill-back {
  left: -8%;
  width: 78%;
  height: 28%;
  background: color-mix(in srgb, var(--arc-400) 22%, #1a1810);
}
.case-thumb-hill-front {
  right: -10%;
  width: 88%;
  height: 34%;
  background: color-mix(in srgb, var(--arc-400) 30%, #12110a);
}
.case-thumb-play {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 245, 220, 0.85);
  opacity: 0.86;
  filter: drop-shadow(0 0 8px rgba(0, 0, 0, 0.5));
}

/* Tone variants nudge the hill / sun for variety without re-coding the
   whole illustration per card. */
.case-thumb--ocean .case-thumb-sky {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--prism-400, #fb923c) 16%, transparent),
    color-mix(in srgb, var(--arc-400) 6%, transparent)
  );
}
.case-thumb--ocean .case-thumb-hill-front {
  background: color-mix(in srgb, var(--prism-400, #fb923c) 22%, #100c10);
}
.case-thumb--dawn .case-thumb-sun {
  left: 22%;
  background: color-mix(in srgb, var(--arc-200) 90%, transparent);
}

.case-meta {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.case-title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}
.case-tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.case-tag {
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--arc-300) 32%, transparent);
  background: color-mix(in srgb, var(--arc-400) 5%, transparent);
  color: color-mix(in srgb, var(--arc-300) 90%, transparent);
  font-size: 0.6875rem;
  letter-spacing: 0.02em;
}
.case-cta {
  margin-top: 2px;
  align-self: flex-start;
  appearance: none;
  border: none;
  background: transparent;
  color: var(--arc-300);
  font-size: 0.8125rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  padding: 0;
  cursor: pointer;
  transition: color 0.18s, transform 0.18s;
}
.case-cta:hover {
  color: var(--arc-200);
  transform: translateX(2px);
}

/* ── Footer ── */
.landing-foot {
  position: relative;
  z-index: 1;
  padding: 48px 24px 72px;
}
.foot-content {
  position: relative;
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  padding: 36px 28px;
  border-radius: 18px;
  border: 1px solid var(--border-glass);
  background: var(--glass-bg);
  backdrop-filter: blur(22px) saturate(150%);
  -webkit-backdrop-filter: blur(22px) saturate(150%);
  text-align: center;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 10%, transparent),
    0 16px 38px rgba(0, 0, 0, 0.28);
  overflow: hidden;
}
.foot-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 18px;
  right: 18px;
  height: 1px;
  background: linear-gradient(
    90deg,
    transparent,
    color-mix(in srgb, var(--arc-200) 40%, transparent),
    transparent
  );
  pointer-events: none;
}
.foot-copy {
  font-size: 1.0625rem;
  color: var(--text-primary);
  letter-spacing: 0.04em;
}
.foot-cta {
  appearance: none;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 10%, rgba(12, 9, 4, 0.92));
  color: rgba(255, 245, 220, 0.96);
  padding: 11px 22px;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s;
}
.foot-cta:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  box-shadow: 0 0 22px color-mix(in srgb, var(--arc-300) 22%, transparent);
}
.foot-cta-arrow {
  transition: transform 0.18s;
}
.foot-cta:hover .foot-cta-arrow {
  transform: translateX(2px);
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .bg-stars span,
  .bg-ambient,
  .bg-glow,
  .hero-tag-dot,
  .orbit-ring {
    animation: none;
  }
}

/* Pearl Dawn pearl-only theme overrides have been moved to a separate
   non-scoped <style> block below — see comment there. Vue's scoped CSS
   was silently dropping the `:global(:root[data-theme=pearl]) .landing X`
   pattern, leaving the page stuck on its dark visuals. */

/* (placeholder rule kept so the diff stays small) */
.landing-pearl-marker__do-not-use {
  display: none;
}

</style>

<style>
/* ═══════════════════════════════════════════════════════════
   珍珠晨光 · Pearl Dawn — Landing Page light-theme overrides.
   Lives in a NON-scoped <style> block because Vue 3 scoped CSS
   silently drops :global(:root[data-theme=pearl]) .landing X
   patterns. Selectors here are plain CSS and target the real
   DOM classes; specificity is enough to win over base rules.
   Dark themes (gold/blue/purple) are untouched.
═══════════════════════════════════════════════════════════ */
/* Background decorative layers — gentler on a light surface */
:root[data-theme="pearl"] .landing .bg-glow-a {
  background: radial-gradient(
    circle,
    rgba(214, 179, 90, 0.30) 0%,
    transparent 62%
  );
  opacity: 0.50;
}
:root[data-theme="pearl"] .landing .bg-glow-b {
  background: radial-gradient(
    circle,
    rgba(150, 192, 220, 0.34) 0%,
    transparent 62%
  );
  opacity: 0.56;
}
:root[data-theme="pearl"] .landing .bg-ambient {
  background:
    radial-gradient(circle at 30% 22%, rgba(214,179,90,0.10) 0%, transparent 42%),
    radial-gradient(circle at 78% 78%, rgba(140,180,220,0.12) 0%, transparent 44%);
}
:root[data-theme="pearl"] .landing .bg-grid {
  background-image:
    linear-gradient(to right,  rgba(184,132,62,0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(184,132,62,0.06) 1px, transparent 1px);
  opacity: 0.42;
}
:root[data-theme="pearl"] .landing .bg-stars span {
  background: rgba(184, 132, 62, 0.28);
  box-shadow: 0 0 4px rgba(184, 132, 62, 0.18);
}

/* Top-right Enter Studio — pearl glass pill */
:root[data-theme="pearl"] .landing .landing-enter-studio {
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.78) 0%,
    rgba(248, 232, 198, 0.72) 100%
  );
  color: #5a3f15;
  border-color: rgba(190, 148, 54, 0.36);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 8px 22px rgba(140, 100, 40, 0.14);
}
:root[data-theme="pearl"] .landing .landing-enter-studio:hover {
  border-color: rgba(190, 148, 54, 0.58);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 12px 28px rgba(140, 100, 40, 0.20),
    0 0 22px rgba(214, 179, 90, 0.22);
}

/* Hero — text, tag chip, gradient text colour */
:root[data-theme="pearl"] .landing .hero-tag {
  background: rgba(255, 255, 255, 0.62);
  border-color: rgba(190, 148, 54, 0.30);
  color: #8b6722;
}
:root[data-theme="pearl"] .landing .hero-title-brand {
  background: linear-gradient(
    135deg,
    #b8843e 0%,
    #c89a55 50%,
    #d6b06a 100%
  );
  -webkit-background-clip: text;
          background-clip: text;
}
:root[data-theme="pearl"] .landing .hero-title-rest {
  color: #2F2D28;
}
:root[data-theme="pearl"] .landing .hero-subtitle {
  color: rgba(47, 45, 40, 0.68);
}

/* Hero primary CTA — deep champagne instead of black glass */
:root[data-theme="pearl"] .landing .hero-primary {
  background: linear-gradient(
    180deg,
    rgba(255, 252, 240, 0.96) 0%,
    rgba(232, 200, 130, 0.94) 100%
  );
  color: rgba(70, 48, 18, 0.96);
  border-color: rgba(190, 148, 54, 0.50);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    inset 0 -1px 0 rgba(184, 132, 62, 0.16),
    0 10px 26px rgba(140, 100, 40, 0.20),
    0 0 18px rgba(214, 179, 90, 0.14);
}
:root[data-theme="pearl"] .landing .hero-primary:hover {
  border-color: rgba(190, 148, 54, 0.66);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 14px 32px rgba(140, 100, 40, 0.26),
    0 0 26px rgba(214, 179, 90, 0.24);
}
:root[data-theme="pearl"] .landing .hero-primary-icon {
  color: #b8843e;
}

/* Hero secondary — light glass outline */
:root[data-theme="pearl"] .landing .hero-secondary {
  color: #5a3f15;
  background: rgba(255, 255, 255, 0.42);
  border-color: rgba(120, 100, 70, 0.28);
}
:root[data-theme="pearl"] .landing .hero-secondary:hover {
  border-color: rgba(190, 148, 54, 0.55);
  color: #8b6722;
  background: rgba(255, 255, 255, 0.62);
}

/* Orbit ornament — barely-there rings on pearl */
:root[data-theme="pearl"] .landing .orbit-ring {
  border-color: rgba(190, 148, 54, 0.24);
}
:root[data-theme="pearl"] .landing .orbit-ring-2 {
  border-color: rgba(190, 148, 54, 0.18);
}
:root[data-theme="pearl"] .landing .orbit-ring-3 {
  border-color: rgba(190, 148, 54, 0.14);
}
:root[data-theme="pearl"] .landing .orbit-center {
  color: #b8843e;
  filter: drop-shadow(0 0 14px rgba(214, 179, 90, 0.30));
}
:root[data-theme="pearl"] .landing .orbit-dot {
  background: #c89a55;
  box-shadow: 0 0 10px rgba(200, 154, 85, 0.55);
}

/* Section headings — warm dark on light */
:root[data-theme="pearl"] .landing .section-eyebrow {
  color: rgba(184, 132, 62, 0.92);
}
:root[data-theme="pearl"] .landing .eyebrow-line {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(184, 132, 62, 0.50),
    transparent
  );
}
:root[data-theme="pearl"] .landing .section-title {
  color: #2F2D28;
}

/* Workflow chain — light glass orbs + champagne links */
:root[data-theme="pearl"] .landing .workflow-node-orb {
  background: rgba(255, 255, 255, 0.78);
  border-color: rgba(190, 148, 54, 0.36);
  color: #8b6722;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.94),
    0 4px 14px rgba(140, 100, 40, 0.12);
}
:root[data-theme="pearl"] .landing .workflow-node:hover .workflow-node-orb {
  border-color: rgba(190, 148, 54, 0.62);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.96),
    0 6px 20px rgba(140, 100, 40, 0.20),
    0 0 18px rgba(214, 179, 90, 0.22);
}
:root[data-theme="pearl"] .landing .workflow-node-title {
  color: #2F2D28;
}
:root[data-theme="pearl"] .landing .workflow-node-desc {
  color: rgba(47, 45, 40, 0.62);
}
:root[data-theme="pearl"] .landing .workflow-link {
  background: linear-gradient(
    90deg,
    rgba(190, 148, 54, 0.46),
    rgba(190, 148, 54, 0.18)
  );
}

/* Case cards — pearl glass body. The .case-thumb video preview stays
   in its dark form (the inner illustrated landscape is its own composition
   and reads fine as a "video frame" on a light card). */
:root[data-theme="pearl"] .landing .case-card {
  background: rgba(255, 255, 255, 0.62);
  border-color: rgba(190, 150, 82, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 18px 44px rgba(120, 104, 72, 0.12);
}
:root[data-theme="pearl"] .landing .case-card::before {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(184, 132, 62, 0.40),
    transparent
  );
}
:root[data-theme="pearl"] .landing .case-card:hover {
  border-color: rgba(190, 148, 54, 0.44);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.98),
    0 24px 54px rgba(120, 104, 72, 0.20),
    0 0 26px rgba(214, 179, 90, 0.20);
}
:root[data-theme="pearl"] .landing .case-title {
  color: #2F2D28;
}
:root[data-theme="pearl"] .landing .case-tag {
  background: rgba(255, 255, 255, 0.66);
  border-color: rgba(190, 148, 54, 0.36);
  color: #8b6722;
}
:root[data-theme="pearl"] .landing .case-cta {
  color: #b8843e;
}
:root[data-theme="pearl"] .landing .case-cta:hover {
  color: #8b6722;
}

/* Footer CTA card — pearl glass per spec */
:root[data-theme="pearl"] .landing .foot-content {
  background: rgba(255, 255, 255, 0.58);
  border-color: rgba(190, 150, 82, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 20px 60px rgba(120, 104, 72, 0.12);
}
:root[data-theme="pearl"] .landing .foot-content::before {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(184, 132, 62, 0.42),
    transparent
  );
}
:root[data-theme="pearl"] .landing .foot-copy {
  color: #2F2D28;
}
:root[data-theme="pearl"] .landing .foot-cta {
  background: linear-gradient(
    180deg,
    rgba(255, 252, 240, 0.96) 0%,
    rgba(232, 200, 130, 0.94) 100%
  );
  color: rgba(70, 48, 18, 0.96);
  border-color: rgba(190, 148, 54, 0.50);
}
:root[data-theme="pearl"] .landing .foot-cta:hover {
  border-color: rgba(190, 148, 54, 0.66);
  box-shadow: 0 0 26px rgba(214, 179, 90, 0.26);
}

/* ThemeSwitcher dropdown — match pearl panel border for the down-flipped
   arrow added in the :deep override above. */
:root[data-theme="pearl"] .ts-root .ts-panel::after {
  border-bottom-color: rgba(255, 255, 255, 0.96);
}
</style>
