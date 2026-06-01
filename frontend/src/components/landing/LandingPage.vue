<template>
  <div class="landing">
    <!-- Decorative starfield + soft glow drift behind everything -->
    <div class="landing-bg" aria-hidden="true">
      <div class="bg-glow bg-glow-a"></div>
      <div class="bg-glow bg-glow-b"></div>
      <div class="bg-stars">
        <span
          v-for="i in 22"
          :key="i"
          :style="starStyle(i)"
        ></span>
      </div>
    </div>

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
        <div class="foot-copy">Start creating your story video.</div>
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
  background: var(--page-bg-color, #09090b);
}

/* ── Background — soft glows + starfield ── */
.landing-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: none;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.55;
}
.bg-glow-a {
  top: -10%;
  left: -8%;
  width: 520px;
  height: 520px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--arc-400) 38%, transparent) 0%,
    transparent 65%
  );
}
.bg-glow-b {
  bottom: -15%;
  right: -10%;
  width: 620px;
  height: 620px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--prism-400, #fb923c) 26%, transparent) 0%,
    transparent 65%
  );
  opacity: 0.32;
}

.bg-stars span {
  position: absolute;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 72%, transparent);
  box-shadow: 0 0 6px color-mix(in srgb, var(--arc-300) 32%, transparent);
  animation: landing-twinkle 4.4s ease-in-out infinite;
}

@keyframes landing-twinkle {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50%      { opacity: 1;    transform: scale(1.1); }
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
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid var(--border-glass);
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  overflow: hidden;
  transition: transform 0.22s, border-color 0.22s, box-shadow 0.22s;
}
.case-card:hover {
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--arc-300) 38%, transparent);
  box-shadow:
    0 18px 40px rgba(0, 0, 0, 0.35),
    0 0 24px color-mix(in srgb, var(--arc-300) 14%, transparent);
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
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
  padding: 32px 28px;
  border-radius: 18px;
  border: 1px solid var(--border-glass);
  background: var(--glass-bg);
  text-align: center;
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
  .hero-tag-dot,
  .orbit-ring {
    animation: none;
  }
}
</style>
