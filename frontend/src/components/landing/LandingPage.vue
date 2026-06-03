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

    <!-- ── Hero ──
         Two-column on desktop: text + CTAs on the left, illustrated
         Story-to-Video scene on the right. Collapses to single column on
         narrow viewports (visual moves below text). -->
    <header class="landing-hero">
      <div class="hero-grid">
        <div class="hero-flow-bridge" aria-hidden="true">
          <svg class="hero-flow-svg" viewBox="0 0 520 220" preserveAspectRatio="none">
            <path class="hero-flow-path hero-flow-path-base" d="M 10 130 C 120 56, 252 46, 510 100" />
            <path class="hero-flow-path hero-flow-path-live" d="M 10 130 C 120 56, 252 46, 510 100" />
          </svg>
          <span class="hero-flow-spark hero-flow-spark-1"></span>
          <span class="hero-flow-spark hero-flow-spark-2"></span>
          <span class="hero-flow-spark hero-flow-spark-3"></span>
        </div>

        <!-- ── Left: brand + copy + CTAs ── -->
        <div class="hero-left">
          <div class="hero-badge" aria-label="Jinsie Creative Orbit">
            <div class="hero-badge-line"></div>
            <div class="hero-badge-top">JINSIE  ·  CREATIVE  ORBIT</div>
            <div class="hero-badge-sub">Story · Storyboard · Visuals · Voice · Video</div>
          </div>

          <h1 class="hero-title">
            <span class="hero-title-brand">Jinsie</span>
            <span class="hero-title-rest">AI Video Studio</span>
          </h1>
          <p class="hero-subtitle">
            把故事灵感转化为绘本风视频作品
          </p>
          <p class="hero-subtitle hero-subtitle-secondary">
            从故事构想到绘本分镜，再到配音与成片，让你的创意在温柔的光里被看见。
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

          <!-- ── Workflow icon strip ──
               Four inline-SVG icons + labels + arrows, replaces the old
               plain-text mini-flow. Single-color line icons via currentColor
               so they pick up the theme accent automatically. -->
          <nav class="hero-workflow-icons" aria-label="Story to video flow">
            <div class="hwi-item">
              <div class="hwi-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 18h6"/>
                  <path d="M10 21h4"/>
                  <path d="M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>
                </svg>
              </div>
              <div class="hwi-label">Story Idea</div>
            </div>
            <span class="hwi-arrow" aria-hidden="true">→</span>
            <div class="hwi-item">
              <div class="hwi-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 6.5C12 6.5 9 5 4 5v13c5 0 8 1.5 8 1.5"/>
                  <path d="M12 6.5C12 6.5 15 5 20 5v13c-5 0-8 1.5-8 1.5"/>
                  <path d="M12 6.5v13"/>
                </svg>
              </div>
              <div class="hwi-label">Picture-book<br/>Scenes</div>
            </div>
            <span class="hwi-arrow" aria-hidden="true">→</span>
            <div class="hwi-item">
              <div class="hwi-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round">
                  <line x1="6"  y1="9"  x2="6"  y2="15"/>
                  <line x1="10" y1="6"  x2="10" y2="18"/>
                  <line x1="14" y1="4"  x2="14" y2="20"/>
                  <line x1="18" y1="9"  x2="18" y2="15"/>
                </svg>
              </div>
              <div class="hwi-label">Voice</div>
            </div>
            <span class="hwi-arrow" aria-hidden="true">→</span>
            <div class="hwi-item">
              <div class="hwi-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="5" width="18" height="14" rx="2"/>
                  <path d="M10 9l5 3-5 3z" fill="currentColor" stroke="none"/>
                </svg>
              </div>
              <div class="hwi-label">Video</div>
            </div>
          </nav>

        </div>

        <!-- ── Right: Storybook illustration ──
             Transparent PNG asset containing ONLY the illustration (book +
             moon + storyboard cards + final video + dust). No baked-in
             brand text. Positioned absolutely so it can be large without
             pushing the left column. Soft radial glow behind grounds it
             into the page surface. -->
        <div
          class="hero-visual"
          ref="heroVisualRef"
          aria-hidden="true"
          @pointermove="onHeroPointerMove"
          @pointerleave="onHeroPointerLeave"
        >
          <!-- Two illustration variants: dark scene for dark themes,
               cream-paper scene for pearl. Same positioning; CSS toggles
               which one is visible based on the active theme. -->
          <img
            class="hero-storybook-art hero-storybook-art--dark"
            src="/hero/storybook-hero-transparent.png"
            alt=""
            aria-hidden="true"
            draggable="false"
          />
          <img
            class="hero-storybook-art hero-storybook-art--light"
            src="/hero/storybook-hero-transparent-white.png"
            alt=""
            aria-hidden="true"
            draggable="false"
          />
        </div>
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

    <!-- ── Cases / Showcase ──
         Cinematic story posters — each card is an illustrated thumbnail
         with the title overlaid on a soft gradient at the bottom. First
         card carries the REFERENCE ribbon (《小老鼠吃月亮》). Hover lifts
         the card and softly zooms the illustration. -->
    <section class="landing-section cases-section">
      <h2 class="section-eyebrow">
        <span class="eyebrow-line"></span>
        Showcase
        <span class="eyebrow-line"></span>
      </h2>
      <h3 class="section-title">案例展示</h3>

      <div class="case-grid">
        <article
          v-for="caseItem in caseList"
          :key="caseItem.id"
          :class="['case-card', `case-card--${caseItem.tone}`]"
          @click="goStudio"
        >
          <!-- Thumbnail surface — per-tone illustration -->
          <div :class="['case-poster', `case-poster--${caseItem.tone}`]" aria-hidden="true">
            <!-- MOON: night sky + crescent moon (bitten) + tiny mouse -->
            <svg
              v-if="caseItem.tone === 'moon'"
              viewBox="0 0 320 200"
              preserveAspectRatio="xMidYMid slice"
              class="case-svg"
            >
              <defs>
                <linearGradient :id="`case-${caseItem.id}-sky`" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.20"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0.02"/>
                </linearGradient>
                <radialGradient :id="`case-${caseItem.id}-moonglow`" cx="50%" cy="50%" r="50%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.45"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0"/>
                </radialGradient>
              </defs>
              <rect x="0" y="0" width="320" height="200" :fill="`url(#case-${caseItem.id}-sky)`"/>
              <!-- Stars -->
              <circle cx="40"  cy="36" r="1.2" fill="currentColor" fill-opacity="0.85"/>
              <circle cx="86"  cy="22" r="0.8" fill="currentColor" fill-opacity="0.7"/>
              <circle cx="260" cy="44" r="1.4" fill="currentColor" fill-opacity="0.9"/>
              <circle cx="290" cy="78" r="0.9" fill="currentColor" fill-opacity="0.75"/>
              <circle cx="120" cy="14" r="0.8" fill="currentColor" fill-opacity="0.6"/>
              <circle cx="200" cy="20" r="1.0" fill="currentColor" fill-opacity="0.7"/>
              <!-- Moon glow -->
              <circle cx="195" cy="78" r="60" :fill="`url(#case-${caseItem.id}-moonglow)`"/>
              <!-- Bitten crescent moon: full disc minus a smaller disc on the right -->
              <mask :id="`case-${caseItem.id}-bite`">
                <rect x="0" y="0" width="320" height="200" fill="white"/>
                <circle cx="220" cy="68" r="22" fill="black"/>
              </mask>
              <circle cx="195" cy="78" r="34" fill="currentColor" fill-opacity="0.95"
                      :mask="`url(#case-${caseItem.id}-bite)`"/>
              <!-- Tiny mouse silhouette on a hill -->
              <g transform="translate(110,148)" fill="currentColor" fill-opacity="0.9">
                <!-- Body -->
                <ellipse cx="0" cy="0" rx="8" ry="5"/>
                <!-- Head -->
                <circle cx="-7" cy="-3" r="3.5"/>
                <!-- Ears -->
                <circle cx="-9" cy="-7" r="2.2"/>
                <circle cx="-5" cy="-7" r="2.2"/>
                <!-- Tail -->
                <path d="M 8 0 Q 14 -2 16 3" stroke="currentColor" stroke-width="1.2" fill="none"/>
              </g>
              <!-- Foreground hill -->
              <path d="M 0 156 Q 60 134, 140 148 T 320 142 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.45"/>
            </svg>

            <!-- FOREST: layered hills + tree silhouettes + warm sun -->
            <svg
              v-else-if="caseItem.tone === 'forest'"
              viewBox="0 0 320 200"
              preserveAspectRatio="xMidYMid slice"
              class="case-svg"
            >
              <defs>
                <linearGradient :id="`case-${caseItem.id}-sky`" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.06"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0.20"/>
                </linearGradient>
                <radialGradient :id="`case-${caseItem.id}-sun`" cx="50%" cy="50%" r="50%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.85"/>
                  <stop offset="60%"  stop-color="currentColor" stop-opacity="0.30"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0"/>
                </radialGradient>
              </defs>
              <rect x="0" y="0" width="320" height="200" :fill="`url(#case-${caseItem.id}-sky)`"/>
              <!-- Sun -->
              <circle cx="240" cy="68" r="46" :fill="`url(#case-${caseItem.id}-sun)`"/>
              <circle cx="240" cy="68" r="14" fill="currentColor" fill-opacity="0.8"/>
              <!-- Back ridge -->
              <path d="M 0 120 Q 80 96, 160 110 T 320 100 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.22"/>
              <!-- Mid ridge with trees -->
              <path d="M 0 140 Q 60 124, 140 134 T 320 130 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.38"/>
              <g fill="currentColor" fill-opacity="0.55">
                <path d="M 50 138 L 55 128 L 60 138 Z"/>
                <path d="M 88 134 L 94 120 L 100 134 Z"/>
                <path d="M 220 132 L 226 116 L 232 132 Z"/>
                <path d="M 260 138 L 265 126 L 270 138 Z"/>
              </g>
              <!-- Front hill with darker tree silhouettes -->
              <path d="M 0 162 Q 80 144, 160 156 T 320 152 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.62"/>
              <g fill="currentColor" fill-opacity="0.85">
                <path d="M 30 162 L 38 142 L 46 162 Z"/>
                <path d="M 130 158 L 138 138 L 146 158 Z"/>
                <path d="M 180 160 L 188 144 L 196 160 Z"/>
                <path d="M 290 156 L 298 140 L 306 156 Z"/>
              </g>
            </svg>

            <!-- OCEAN: water surface + lily pad + tadpole -->
            <svg
              v-else-if="caseItem.tone === 'ocean'"
              viewBox="0 0 320 200"
              preserveAspectRatio="xMidYMid slice"
              class="case-svg"
            >
              <defs>
                <linearGradient :id="`case-${caseItem.id}-water`" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.06"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0.28"/>
                </linearGradient>
              </defs>
              <rect x="0" y="0" width="320" height="200" :fill="`url(#case-${caseItem.id}-water)`"/>
              <!-- Wave ripples -->
              <path d="M 0 60  Q 50 70, 100 60 T 200 60 T 320 60"
                    stroke="currentColor" stroke-width="1.2" stroke-opacity="0.35" fill="none"/>
              <path d="M 0 90  Q 50 100, 100 90 T 200 90 T 320 90"
                    stroke="currentColor" stroke-width="1.2" stroke-opacity="0.45" fill="none"/>
              <path d="M 0 124 Q 50 134, 100 124 T 200 124 T 320 124"
                    stroke="currentColor" stroke-width="1.2" stroke-opacity="0.55" fill="none"/>
              <path d="M 0 160 Q 50 170, 100 160 T 200 160 T 320 160"
                    stroke="currentColor" stroke-width="1.2" stroke-opacity="0.65" fill="none"/>
              <!-- Lily pad -->
              <ellipse cx="220" cy="88" rx="34" ry="10" fill="currentColor" fill-opacity="0.55"/>
              <path d="M 196 88 L 220 88" stroke="currentColor" stroke-width="0.8" stroke-opacity="0.8"/>
              <!-- Tiny lily flower -->
              <circle cx="210" cy="84" r="2.4" fill="currentColor" fill-opacity="0.85"/>
              <!-- Tadpole silhouette -->
              <g transform="translate(120,118)" fill="currentColor" fill-opacity="0.85">
                <ellipse cx="0" cy="0" rx="7" ry="4.5"/>
                <path d="M -7 0 Q -16 -2 -18 2 Q -14 4 -7 2 Z"/>
                <circle cx="3" cy="-1.5" r="0.8" fill="rgba(0,0,0,0.6)"/>
              </g>
              <!-- Bubble -->
              <circle cx="80"  cy="42" r="2" fill="currentColor" fill-opacity="0.8"/>
              <circle cx="100" cy="30" r="1.4" fill="currentColor" fill-opacity="0.7"/>
            </svg>

            <!-- Bottom gradient + title overlay -->
            <div class="case-overlay"></div>
            <div class="case-overlay-text">
              <div class="case-overlay-subtitle">{{ caseItem.subtitle }}</div>
              <div class="case-overlay-title">{{ caseItem.title }}</div>
            </div>

            <!-- Reference ribbon (top-right) -->
            <span
              v-if="caseItem.badge"
              class="case-ribbon"
            >{{ caseItem.badge }}</span>

            <!-- Play overlay on hover -->
            <div class="case-play">
              <svg viewBox="0 0 64 64">
                <circle cx="32" cy="32" r="28" fill="currentColor" fill-opacity="0.18"
                        stroke="currentColor" stroke-width="1.4" stroke-opacity="0.85"/>
                <path d="M 26 20 L 46 32 L 26 44 Z" fill="currentColor" fill-opacity="0.95"/>
              </svg>
            </div>
          </div>

          <div class="case-meta">
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
              @click.stop="goStudio"
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ThemeSwitcher from '../studio/ThemeSwitcher.vue'

const router = useRouter()

// Pointer-parallax on the hero illustration. Mousemove writes --px / --py
// CSS vars (range ~ -0.5..0.5) onto .hero-visual; the .hero-storybook-art
// uses those vars in its translate to drift a few pixels with the cursor.
// Respects prefers-reduced-motion via a media query that zeroes translate.
const heroVisualRef = ref<HTMLElement | null>(null)
function onHeroPointerMove(e: PointerEvent) {
  const el = heroVisualRef.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const px = (e.clientX - rect.left) / rect.width - 0.5
  const py = (e.clientY - rect.top) / rect.height - 0.5
  el.style.setProperty('--px', String(px))
  el.style.setProperty('--py', String(py))
}
function onHeroPointerLeave() {
  const el = heroVisualRef.value
  if (!el) return
  el.style.setProperty('--px', '0')
  el.style.setProperty('--py', '0')
}

// Landing → Studio entries are treated as a fresh "start creating" intent,
// so we land on the first tab (创作故事) regardless of what the user was
// looking at last. Direct refresh of /studio doesn't go through here, so
// the existing per-session tab persistence still resumes the last tab on
// reload.
const STUDIO_TAB_STORAGE_KEY = 'jinsie_active_tab'
const STUDIO_DEFAULT_TAB = 'run'

function goStudio() {
  try {
    localStorage.setItem(STUDIO_TAB_STORAGE_KEY, STUDIO_DEFAULT_TAB)
  } catch {
    /* localStorage unavailable — fall through; StudioView's default is also 'run' */
  }
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

// Cinematic poster cards. Each case has its own illustrated thumbnail
// (rendered inline as SVG, keyed off `tone`) so the showcase reads as a
// portfolio strip rather than placeholder color blocks. First entry is a
// fixed Reference Case (经典绘本《小老鼠吃月亮》) so the showcase opens with
// recognizable provenance.
type CaseTone = 'moon' | 'forest' | 'ocean'
type CaseItem = {
  id: string
  title: string
  subtitle: string
  tags: string[]
  tone: CaseTone
  badge?: string  // optional top-right ribbon (e.g. "REFERENCE")
}
const caseList: CaseItem[] = [
  {
    id: 'moon',
    title: '小老鼠吃月亮',
    subtitle: '改编自经典绘本',
    tags: ['经典绘本', 'Reference'],
    tone: 'moon',
    badge: 'REFERENCE',
  },
  {
    id: 'forest',
    title: '森林里的小伙伴',
    subtitle: '原创亲子故事',
    tags: ['绘本风', '亲子'],
    tone: 'forest',
  },
  {
    id: 'ocean',
    title: '小蝌蚪的冒险',
    subtitle: '池塘里的成长',
    tags: ['儿童故事', '成长'],
    tone: 'ocean',
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

/* Background glows — toned down (was 0.62/0.38) so the deep-space surface
   reads as CLEAN, not foggy. The poster scene is now the visual subject;
   the background should be quiet. */
.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.24;
}
.bg-glow-a {
  top: -14%;
  left: -10%;
  width: 520px;
  height: 520px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--arc-400) 24%, transparent) 0%,
    transparent 65%
  );
  animation: landing-glow-a 18s ease-in-out infinite;
}
.bg-glow-b {
  bottom: -18%;
  right: -12%;
  width: 600px;
  height: 600px;
  background: radial-gradient(
    circle,
    color-mix(in srgb, #6488b0 20%, transparent) 0%,
    transparent 65%
  );
  opacity: 0.16;
  animation: landing-glow-b 24s ease-in-out infinite;
}

.bg-stars span {
  position: absolute;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 78%, transparent);
  box-shadow: 0 0 6px color-mix(in srgb, var(--arc-300) 38%, transparent);
  /* Stacked animations: fast twinkle (4.4s) for the scale/opacity sparkle +
     very slow drift (38s) for a barely-perceptible vertical float. The drift
     gives the field a "starfield slowly passing by" feel without anyone
     consciously noticing motion. Different `animation-delay` per star is
     supplied inline via starStyle(). */
  animation:
    landing-twinkle 4.4s ease-in-out infinite,
    landing-star-drift 38s ease-in-out infinite;
}

@keyframes landing-twinkle {
  0%, 100% { opacity: 0.30; transform: scale(0.85); }
  50%      { opacity: 1;    transform: scale(1.15); }
}
@keyframes landing-star-drift {
  0%, 100% { translate: 0 0; }
  50%      { translate: 0 -10px; }
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

@keyframes hero-flow-drift {
  to { stroke-dashoffset: -198; }
}
@keyframes hero-flow-spark {
  0%, 100% { opacity: 0.18; transform: translate(0, 0) scale(0.78); }
  40%      { opacity: 0.95; transform: translate(8px, -5px) scale(1.08); }
  70%      { opacity: 0.46; transform: translate(18px, -2px) scale(0.92); }
}
@keyframes hero-caret-blink {
  0%, 45%  { opacity: 1; }
  46%, 100% { opacity: 0; }
}

/* ── Hero (two-column, viewport-height) ──
   Left column = brand badge + headline + subtitle + CTA row.
   Right column = illustrated Story-to-Video scene.
   Hero fills the full viewport so the workflow section below is NEVER
   visible in the first fold — the user sees a complete brand + scene
   composition before scrolling reveals the chain. On narrow viewports
   collapses to single column; visual moves below text. */
.landing-hero {
  position: relative;
  z-index: 1;
  /* Cap min-height so a short viewport (e.g. 700px tall laptop) doesn't
     produce a huge empty gap before the Workflow section. Previously the
     `min-height: 100vh` combined with `position: absolute` hero-visual
     left the section bloated when content was shorter than 100vh. */
  min-height: min(100vh, 780px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  /* 14vh top padding pulls left content down from the topbar so it
     doesn't feel like it's hanging too high. */
  padding: 14vh 32px 64px;
  margin: 0 auto;
  max-width: 1240px;
  box-sizing: border-box;
}

.hero-grid {
  width: 100%;
  display: grid;
  position: relative;
  /* Tilt the ratio slightly toward the visual column — it carries the
     scene weight and should feel like the "stage", while the left column
     reads as the title card. */
  grid-template-columns: minmax(0, 0.78fr) minmax(0, 1.22fr);
  /* Pull left text up to fill the empty top-left zone. Image stays
     vertically centered via its own absolute positioning. */
  align-items: start;
  padding-top: 4vh;
  gap: 56px;
}

.hero-left {
  position: relative;
  z-index: 3;
  text-align: left;
}

/* Thin story-to-studio motion path. It sits behind the content columns,
   tying the left idea card to the right preview without becoming a flowchart. */
.hero-flow-bridge {
  position: absolute;
  left: 30%;
  right: 15%;
  top: 50%;
  height: 220px;
  transform: translateY(-36%);
  pointer-events: none;
  z-index: 1;
  opacity: 0.86;
}
.hero-flow-svg {
  width: 100%;
  height: 100%;
  overflow: visible;
}
.hero-flow-path {
  fill: none;
  vector-effect: non-scaling-stroke;
  stroke-linecap: round;
}
.hero-flow-path-base {
  stroke: color-mix(in srgb, var(--arc-300) 30%, transparent);
  stroke-width: 1;
  stroke-dasharray: 2 10;
}
.hero-flow-path-live {
  stroke: color-mix(in srgb, var(--arc-200) 72%, transparent);
  stroke-width: 1.2;
  stroke-dasharray: 18 180;
  filter: drop-shadow(0 0 8px color-mix(in srgb, var(--arc-300) 48%, transparent));
  animation: hero-flow-drift 8.5s linear infinite;
}
.hero-flow-spark {
  position: absolute;
  width: 4px;
  height: 4px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--arc-200) 88%, transparent);
  box-shadow:
    0 0 10px color-mix(in srgb, var(--arc-300) 78%, transparent),
    0 0 22px color-mix(in srgb, var(--arc-400) 28%, transparent);
  animation: hero-flow-spark 7.6s ease-in-out infinite;
}
.hero-flow-spark-1 { left: 15%; top: 56%; animation-delay: 0s; }
.hero-flow-spark-2 { left: 44%; top: 34%; animation-delay: 1.6s; width: 3px; height: 3px; }
.hero-flow-spark-3 { left: 79%; top: 41%; animation-delay: 3.2s; width: 3px; height: 3px; }

/* ── Brand badge (replaces the old pill micro-label) ──
   Two-line typographic mark — feels like a wordmark caption, not a tag.
   No surrounding pill border. A faint horizontal hairline sits above it
   to anchor the block in the page composition. */
.hero-badge {
  display: inline-flex;
  flex-direction: column;
  /* Larger gap between badge top + sub lines for 轻奢呼吸感 */
  gap: 14px;
  margin-bottom: 36px;
  line-height: 1.4;
}
.hero-badge-line {
  width: 56px;
  height: 1px;
  background: linear-gradient(
    90deg,
    color-mix(in srgb, var(--arc-300) 78%, transparent),
    transparent
  );
  margin-bottom: 10px;
}
.hero-badge-top {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.34em;
  color: var(--arc-300);
  text-shadow: 0 0 12px color-mix(in srgb, var(--arc-300) 32%, transparent);
}
.hero-badge-sub {
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.18em;
  color: color-mix(in srgb, var(--text-muted) 92%, transparent);
}

/* Headline — left-aligned in the column. */
.hero-title {
  margin: 0 0 18px;
  font-size: clamp(2.6rem, 5.4vw, 4.2rem);
  font-weight: 700;
  letter-spacing: 0.02em;
  line-height: 1.08;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
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
  font-size: 0.58em;
  letter-spacing: 0.1em;
}

.hero-subtitle {
  margin: 0 0 36px;
  max-width: 480px;
  font-size: 1.0625rem;
  color: var(--text-secondary);
  line-height: 1.65;
  letter-spacing: 0.02em;
}

.hero-cta-row {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

/* ── Hero mini workflow line ──
   Light typography under the CTAs — reads as a brand caption, NOT a card.
   Uppercase, wide tracking, muted color; arrows in soft gold. */
/* ─ Hero subtitle: secondary line under the main subtitle ─
   Smaller + lighter weight + brighter (less muted) so it reads as
   relaxed brand copy that doesn't compete with the main title. */
.hero-subtitle-secondary {
  margin-top: -16px;
  margin-bottom: 40px;
  font-size: 0.8125rem;
  font-weight: 300;
  line-height: 1.85;
  letter-spacing: 0.04em;
  color: rgba(255, 245, 220, 0.62);
}

/* ═══════════════════════════════════════════════════════════════════
   ── Hero Storybook Illustration (atmosphere layer) ──
   The transparent PNG is treated as a BACKGROUND ATMOSPHERE layer, not
   a foreground main visual. It's pushed to the right, downsized, and
   covered with strong gradient fades on the left/bottom/right edges
   so it never competes with the left-column brand text. The page
   gradient + starfield + this image together form the right-side
   ambient mood, not a hard image rectangle.
═══════════════════════════════════════════════════════════════════ */
.hero-visual {
  position: absolute;
  /* Vertical center shifted slightly downward (was 50%) so the
     storyboard cards aren't crowding the topbar / page edge.
     right offset increased to -4vw to push illustration further from
     the left-column text. */
  top: 56%;
  right: -4vw;
  transform: translateY(-50%);
  width: min(62vw, 980px);
  height: 78vh;
  max-height: 860px;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 1;
  overflow: visible;
}

/* (No ::before fade overlay — the transparent PNG has empty left
   padding, so the image's bounding box doesn't cross into the left
   text column. Left-column text relies on z-index: 3 above the image
   z-index: 1 instead of a gradient mask.) */

/* Ensure left-column text + CTA always sit above the image */
.hero-left { position: relative; z-index: 3; }
.hero-flow-bridge { z-index: 2; }

.hero-storybook-art {
  width: 100%;
  height: auto;
  max-height: 76vh;
  object-fit: contain;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
  opacity: 0.86;
  /* The PNG carries a dark gradient fill at its bounding-box edges
     (it's not truly transparent). Four-way linear mask fades each edge
     into transparency so the rectangular frame disappears.
       · vertical:   top 10% + bottom 12% fade
       · horizontal: left 14% + right 6%  fade
     Combined via mask-composite:intersect → visible ONLY in inner area. */
  mask-image:
    linear-gradient(to bottom, transparent 0%, #000 18%, #000 82%, transparent 100%),
    linear-gradient(to right,  transparent 0%, #000 22%, #000 90%, transparent 100%);
  mask-composite: intersect;
  -webkit-mask-image:
    linear-gradient(to bottom, transparent 0%, #000 18%, #000 82%, transparent 100%),
    linear-gradient(to right,  transparent 0%, #000 22%, #000 90%, transparent 100%);
  -webkit-mask-composite: source-in;
  /* Very subtle composite: minimal slow zoom + tiny float + small
     pointer parallax. The image is atmosphere — motion must stay low. */
  animation:
    hero-art-zoom   22s ease-in-out infinite,
    hero-art-float  11s ease-in-out infinite;
  translate: calc(var(--px, 0) * -2px) calc(var(--py, 0) * -1.5px);
  transition: translate 0.5s cubic-bezier(0.22, 0.65, 0.3, 1);
  will-change: transform, translate;
}

/* Dark/light variants — MUST come after base `.hero-storybook-art {
   display: block }` to win on equal specificity. Default: show dark,
   hide light. Pearl theme block flips the pair. The variants share the
   same absolute position; only one renders at a time. */
.hero-storybook-art--dark  { display: block !important; }
.hero-storybook-art--light { display: none  !important; }

@keyframes hero-art-zoom {
  /* Atmosphere-only breath — barely perceptible. */
  0%, 100% { transform: scale(1);     }
  50%      { transform: scale(1.008); }
}
@keyframes hero-art-float {
  /* Tiny vertical drift via the `translate` property so it composes
     with the zoom transform without conflict. */
  0%, 100% { translate: calc(var(--px, 0) * -2px) calc(var(--py, 0) * -1.5px - 0px); }
  50%      { translate: calc(var(--px, 0) * -2px) calc(var(--py, 0) * -1.5px - 4px); }
}

/* ═══════════════════════════════════════════════════════════════════
   ── Workflow icon strip ──
   Replaces the old text-only mini-flow with 4 inline-SVG icons + labels.
   currentColor lets them inherit the theme accent. Stagger fade-in once
   on mount. */
.hero-workflow-icons {
  margin-top: 30px;
  display: inline-flex;
  align-items: flex-start;
  gap: 14px;
  flex-wrap: wrap;
}
.hwi-item {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  min-width: 62px;
  animation: hwi-fade-in 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) backwards;
}
/* Stagger — each .hwi-item is at nth-child positions 1, 3, 5, 7 */
.hero-workflow-icons .hwi-item:nth-child(1) { animation-delay: 0.40s; }
.hero-workflow-icons .hwi-item:nth-child(3) { animation-delay: 0.55s; }
.hero-workflow-icons .hwi-item:nth-child(5) { animation-delay: 0.70s; }
.hero-workflow-icons .hwi-item:nth-child(7) { animation-delay: 0.85s; }
.hwi-icon {
  width: 26px;
  height: 26px;
  color: var(--arc-300);
  display: flex;
  align-items: center;
  justify-content: center;
  filter: drop-shadow(0 0 6px color-mix(in srgb, var(--arc-300) 24%, transparent));
}
.hwi-icon svg { width: 100%; height: 100%; }
.hwi-label {
  font-size: 0.625rem;
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--text-secondary) 95%, transparent);
  text-align: center;
  line-height: 1.3;
  white-space: nowrap;
}
.hwi-arrow {
  color: color-mix(in srgb, var(--arc-300) 56%, transparent);
  font-size: 0.875rem;
  font-weight: 400;
  align-self: flex-start;
  margin-top: 4px;
}
@keyframes hwi-fade-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0);   }
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
  position: relative;
  overflow: hidden;
  box-shadow:
    /* Inner warm moonlight glow — matches the page's moon ambience */
    inset 0 0 22px color-mix(in srgb, var(--arc-300) 18%, transparent),
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 26%, transparent),
    0 12px 28px rgba(0, 0, 0, 0.30),
    0 0 18px color-mix(in srgb, var(--arc-300) 16%, transparent);
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
/* Subtle sheen sweep on hover — runs once per hover, never autoplays */
.hero-primary::after {
  content: '';
  position: absolute;
  top: 0; left: -60%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    100deg,
    transparent,
    color-mix(in srgb, var(--arc-200) 38%, transparent),
    transparent
  );
  transform: skewX(-18deg);
  transition: left 0.55s cubic-bezier(0.2, 0.8, 0.2, 1);
  pointer-events: none;
}
.hero-primary:hover {
  transform: translateY(-2px);
  border-color: color-mix(in srgb, var(--arc-300) 56%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 30%, transparent),
    0 18px 38px rgba(0, 0, 0, 0.42),
    0 0 32px color-mix(in srgb, var(--arc-300) 28%, transparent);
}
.hero-primary:hover::after {
  left: 120%;
}
.hero-primary-icon {
  color: var(--arc-300);
  font-size: 0.85em;
}

.hero-secondary {
  appearance: none;
  /* Unified rose-gold palette — replaces the previous dark-gray stroke
     with a light-gold border to match the rest of the page's accents. */
  border: 1px solid color-mix(in srgb, var(--arc-300) 38%, transparent);
  background: transparent;
  color: color-mix(in srgb, var(--arc-300) 92%, transparent);
  padding: 11px 22px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s, transform 0.18s;
}
.hero-secondary:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 42%, transparent);
  color: var(--arc-300);
  background: color-mix(in srgb, var(--arc-400) 4%, transparent);
}

/* (Hero illustration styles moved below — see Hero Art section) */



/* ── Hero responsive: collapse to single column on narrow viewports ── */
/* Single-column collapse — visual moves below text but keeps the same
   "video-frame-at-center" composition logic. min-height: 100vh remains
   so the workflow section below is still off-fold on first paint. */
/* Intermediate width — keep side-by-side layout but kill min-height so
   short viewports don't create empty space below the hero before the
   Workflow section. Image is shrunk so it doesn't overflow content. */
@media (max-width: 1200px) {
  .landing-hero {
    min-height: auto;
    padding: 96px 24px 72px;
    overflow: hidden;
  }
  .hero-visual {
    height: 70vh;
    max-height: 620px;
  }
}

@media (max-width: 960px) {
  .landing-hero {
    min-height: auto;
    padding: 96px 24px 56px;
    overflow: visible;
  }
  .hero-grid {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  .hero-left {
    text-align: center;
  }
  .hero-title {
    align-items: center;
  }
  .hero-cta-row {
    justify-content: center;
  }
  .hero-flow-bridge {
    display: none;
  }
  .hero-badge {
    align-self: center;
    align-items: center;
  }
  .hero-badge-line {
    align-self: center;
  }
  .hero-visual {
    /* On collapsed single-column layout, the visual moves below the
       text block, full-width, no longer absolute. */
    position: relative;
    top: auto; right: auto; bottom: auto;
    transform: none;
    width: 100%;
    max-width: 720px;
    height: auto;
    margin: 0 auto;
  }
  .hero-storybook-art {
    max-height: 60vh;
  }
}
@media (max-width: 600px) {
  .landing-hero { padding: 64px 20px 40px; }
  .hero-storybook-art {
    max-height: 48vh;
  }
}

/* ── Sections (Workflow + Cases) ── */
.landing-section {
  position: relative;
  z-index: 1;
  padding: 56px 24px 72px;
  max-width: 1100px;
  margin: 0 auto;
}
/* On narrow / scaled-down viewports, shrink the top gap so the
   Workflow section sits ~80-120px below the hero, not pushed far down. */
@media (max-width: 1200px) {
  .landing-section { padding-top: 40px; }
}
@media (max-width: 960px) {
  .landing-section { padding-top: 32px; }
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

/* ── Case Posters ──
   Cinematic story-poster cards. Each card has a per-tone SVG illustration
   inside a 16:10 surface, a gradient title overlay, optional REFERENCE
   ribbon, and a play-icon overlay revealed on hover. Whole card is clickable
   (routes to /studio) — meta-row "进入工作台 →" is purely affordance signal. */
.case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 22px;
  max-width: 1080px;
  margin: 0 auto;
}

.case-card {
  position: relative;
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  border: 1px solid var(--border-glass);
  background: var(--glass-bg);
  backdrop-filter: blur(20px) saturate(140%);
  -webkit-backdrop-filter: blur(20px) saturate(140%);
  overflow: hidden;
  cursor: pointer;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 10%, transparent),
    0 14px 32px rgba(0, 0, 0, 0.32);
  transition: transform 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
              border-color 0.22s,
              box-shadow 0.26s;
}
/* Top hairline highlight (matches studio card aesthetic) */
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
    color-mix(in srgb, var(--arc-200) 42%, transparent),
    transparent
  );
  pointer-events: none;
  z-index: 2;
}
.case-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 18%, transparent),
    0 28px 56px rgba(0, 0, 0, 0.46),
    0 0 36px color-mix(in srgb, var(--arc-300) 24%, transparent);
}

/* Poster thumbnail — fills card top, 16:10 cinematic ratio */
.case-poster {
  position: relative;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  color: var(--arc-300);
  /* Tone backdrop: deep night-ish base. Per-tone variants tint further. */
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 16%, #0a0805) 0%,
    rgba(6, 5, 3, 0.96) 100%
  );
}

/* Per-tone moodboard: shift backdrop to match each scene. */
.case-poster--moon {
  background: linear-gradient(
    180deg,
    #0c1226 0%,
    #050811 60%,
    #03060d 100%
  );
}
.case-poster--forest {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 22%, #1a1408) 0%,
    color-mix(in srgb, var(--arc-400) 8%, #0a0805) 100%
  );
}
.case-poster--ocean {
  background: linear-gradient(
    180deg,
    #0a1a24 0%,
    #061216 60%,
    #030a0d 100%
  );
}

.case-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  transition: transform 0.42s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.case-card:hover .case-svg {
  transform: scale(1.05);
}

/* Bottom overlay — fades dark to transparent for title legibility */
.case-overlay {
  position: absolute;
  inset: 50% 0 0 0;
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(0, 0, 0, 0.55) 60%,
    rgba(0, 0, 0, 0.85) 100%
  );
  pointer-events: none;
}
.case-overlay-text {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 14px;
  color: rgba(255, 245, 220, 0.96);
  pointer-events: none;
}
.case-overlay-subtitle {
  font-size: 0.6875rem;
  letter-spacing: 0.22em;
  font-weight: 600;
  color: color-mix(in srgb, var(--arc-300) 88%, transparent);
  margin-bottom: 4px;
  text-transform: uppercase;
}
.case-overlay-title {
  font-size: 1.0625rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
}

/* REFERENCE ribbon — top-right pill */
.case-ribbon {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.625rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  color: rgba(255, 245, 220, 0.96);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 50%, rgba(28, 20, 8, 0.78)) 0%,
    color-mix(in srgb, var(--arc-400) 32%, rgba(14, 10, 4, 0.86)) 100%
  );
  border: 1px solid color-mix(in srgb, var(--arc-300) 55%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 28%, transparent),
    0 4px 14px rgba(0, 0, 0, 0.4),
    0 0 16px color-mix(in srgb, var(--arc-300) 24%, transparent);
  z-index: 3;
}

/* Play overlay — fades in on hover */
.case-play {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 56px;
  height: 56px;
  transform: translate(-50%, -50%) scale(0.84);
  color: rgba(255, 245, 220, 0.95);
  opacity: 0;
  transition: opacity 0.26s ease, transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1);
  pointer-events: none;
  filter: drop-shadow(0 0 14px color-mix(in srgb, var(--arc-300) 55%, transparent));
  z-index: 2;
}
.case-play svg { width: 100%; height: 100%; }
.case-card:hover .case-play {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
}

/* Meta row beneath the poster — small chips + CTA */
.case-meta {
  padding: 14px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.case-tag-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.case-tag {
  padding: 2px 10px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--arc-300) 30%, transparent);
  background: color-mix(in srgb, var(--arc-400) 5%, transparent);
  color: color-mix(in srgb, var(--arc-300) 90%, transparent);
  font-size: 0.6875rem;
  letter-spacing: 0.04em;
  font-weight: 500;
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
  transform: translateX(3px);
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

/* ── Reduced motion ──
   Disable every decorative motion when the user has requested less motion.
   Layout stays intact; only animations are stopped. CTA hover still works
   (transitions on user-initiated interaction are kept). */
@media (prefers-reduced-motion: reduce) {
  .bg-stars span,
  .bg-ambient,
  .bg-glow,
  .hero-flow-path-live,
  .hero-flow-spark,
  .hwi-item,
  .hero-storybook-art {
    animation: none;
  }
  /* Zero out pointer parallax too */
  .hero-storybook-art {
    translate: 0 0 !important;
    transition: none !important;
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

/* Hero — brand badge (replaces the old micro-label pill) */
:root[data-theme="pearl"] .landing .hero-badge-line {
  background: linear-gradient(
    90deg,
    rgba(184, 132, 62, 0.78),
    transparent
  );
}
:root[data-theme="pearl"] .landing .hero-badge-top {
  color: #8b6722;
  text-shadow: 0 0 10px rgba(214, 179, 90, 0.32);
}
:root[data-theme="pearl"] .landing .hero-badge-sub {
  color: rgba(80, 58, 22, 0.60);
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

:root[data-theme="pearl"] .landing .hero-flow-path-base {
  stroke: rgba(184, 132, 62, 0.20);
}
:root[data-theme="pearl"] .landing .hero-flow-path-live {
  stroke: rgba(184, 132, 62, 0.48);
  filter: drop-shadow(0 0 7px rgba(142, 197, 255, 0.24));
}
:root[data-theme="pearl"] .landing .hero-flow-spark {
  background: rgba(184, 132, 62, 0.62);
  box-shadow:
    0 0 10px rgba(214, 179, 90, 0.42),
    0 0 20px rgba(142, 197, 255, 0.24);
}

/* ─ Storybook Poster — pearl ("morning fog studio") ─
   Watercolor-paper aesthetic: pearl background, warm cream moon (no
   bright halo planet), cream-parchment book, light gold dust, warm
   brown mouse + text. The whole right column should feel like an
   illustrated picture-book spread laid on a designer's desk. */
/* Pearl-theme: workflow icon strip */
:root[data-theme="pearl"] .landing .hwi-icon {
  color: #b8843e;
  filter: drop-shadow(0 0 6px rgba(214, 179, 90, 0.32));
}
:root[data-theme="pearl"] .landing .hwi-label {
  color: rgba(80, 58, 22, 0.78);
}
:root[data-theme="pearl"] .landing .hwi-arrow {
  color: rgba(190, 148, 54, 0.6);
}
:root[data-theme="pearl"] .landing .hero-subtitle-secondary {
  color: rgba(80, 58, 22, 0.62);
}

/* Pearl-theme: swap which illustration is visible. The dark variant is
   designed for deep-space backgrounds; the light variant is a separate
   cream/paper asset that already targets the pearl surface, so we don't
   apply brightness/contrast filters or opacity reduction. */
:root[data-theme="pearl"] .landing .hero-storybook-art--dark  { display: none  !important; }
:root[data-theme="pearl"] .landing .hero-storybook-art--light { display: block !important; }
/* Pearl: hero illustration as a soft paper-style background visual.
   Quieter than the gold dark theme — readable but not the focal element.
   A dedicated light-theme illustration may replace this later. */
:root[data-theme="pearl"] .landing .hero-storybook-art {
  filter: brightness(1.04) contrast(0.88) saturate(0.82);
  opacity: 0.55;
  mix-blend-mode: normal;
}
/* Very light cream wash — just enough to soften any rectangular edges
   into the pearl surface without obscuring the illustration. */
:root[data-theme="pearl"] .landing .hero-visual::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    rgba(255, 252, 244, 0.18) 0%,
    rgba(255, 252, 244, 0.22) 100%
  );
}
/* (Pearl ::before override removed — no fade overlay on either theme.) */



/* Case posters — pearl ("paper poster on a studio wall")
   Posters get lighter tone-specific backdrops so the warm-gold SVG ink
   reads on the page; ribbon + overlay text switch to warm brown tones. */
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
    0 0 26px rgba(214, 179, 90, 0.22);
}
/* Per-tone pearl poster backdrops — soft pastel scenes, warm gold ink. */
:root[data-theme="pearl"] .landing .case-poster {
  color: #8b6722;
}
:root[data-theme="pearl"] .landing .case-poster--moon {
  background: linear-gradient(
    180deg,
    #e9e7ee 0%,
    #d8d4e0 60%,
    #c8c3d2 100%
  );
}
:root[data-theme="pearl"] .landing .case-poster--forest {
  background: linear-gradient(
    180deg,
    #f4ecd8 0%,
    #e6d6b0 100%
  );
}
:root[data-theme="pearl"] .landing .case-poster--ocean {
  background: linear-gradient(
    180deg,
    #dbe9ee 0%,
    #c0d6df 100%
  );
}
/* On pearl, the bottom overlay must lighten (not darken) so it doesn't
   muddy the soft poster. Switch to a warm cream wash. */
:root[data-theme="pearl"] .landing .case-overlay {
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(70, 48, 18, 0.18) 60%,
    rgba(70, 48, 18, 0.50) 100%
  );
}
:root[data-theme="pearl"] .landing .case-overlay-subtitle {
  color: rgba(255, 245, 220, 0.92);
}
:root[data-theme="pearl"] .landing .case-overlay-title {
  color: rgba(255, 248, 232, 0.98);
}
/* REFERENCE ribbon on pearl: bright cream pill */
:root[data-theme="pearl"] .landing .case-ribbon {
  background: linear-gradient(
    180deg,
    rgba(255, 252, 240, 0.95) 0%,
    rgba(232, 200, 130, 0.90) 100%
  );
  color: #5a3f15;
  border-color: rgba(190, 148, 54, 0.55);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    0 4px 14px rgba(140, 100, 40, 0.18),
    0 0 16px rgba(214, 179, 90, 0.30);
}
:root[data-theme="pearl"] .landing .case-play {
  color: rgba(255, 252, 240, 0.98);
  filter: drop-shadow(0 0 12px rgba(140, 100, 40, 0.55));
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
