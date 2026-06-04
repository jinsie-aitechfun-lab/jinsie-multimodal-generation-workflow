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
            从故事创意到视频成片的 AI 创作工作台
          </p>
          <p class="hero-subtitle hero-subtitle-secondary">
            当前版本以绘本风故事视频为示例，打通故事生成、分镜设计、画面审核、配音字幕与视频合成的完整工作流。
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
              <div class="hwi-label">Storyboard</div>
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
          @click="openShowcaseCase(caseItem)"
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

            <!-- TRAIN: night sky + stars + little train + distant hills -->
            <svg
              v-else-if="caseItem.tone === 'train'"
              viewBox="0 0 320 200"
              preserveAspectRatio="xMidYMid slice"
              class="case-svg"
            >
              <defs>
                <linearGradient :id="`case-${caseItem.id}-sky`" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%"   stop-color="currentColor" stop-opacity="0.22"/>
                  <stop offset="100%" stop-color="currentColor" stop-opacity="0.04"/>
                </linearGradient>
              </defs>
              <rect x="0" y="0" width="320" height="200" :fill="`url(#case-${caseItem.id}-sky)`"/>
              <!-- Stars scattered across the night sky -->
              <circle cx="40"  cy="30" r="1.2" fill="currentColor" fill-opacity="0.85"/>
              <circle cx="90"  cy="18" r="0.8" fill="currentColor" fill-opacity="0.70"/>
              <circle cx="160" cy="38" r="1.4" fill="currentColor" fill-opacity="0.92"/>
              <circle cx="220" cy="22" r="0.9" fill="currentColor" fill-opacity="0.75"/>
              <circle cx="260" cy="44" r="1.1" fill="currentColor" fill-opacity="0.85"/>
              <circle cx="295" cy="18" r="0.7" fill="currentColor" fill-opacity="0.60"/>
              <circle cx="120" cy="50" r="0.8" fill="currentColor" fill-opacity="0.70"/>
              <circle cx="200" cy="70" r="0.6" fill="currentColor" fill-opacity="0.55"/>
              <!-- Distant hill -->
              <path d="M 0 132 Q 80 110, 160 124 T 320 120 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.28"/>
              <!-- Near hill -->
              <path d="M 0 160 Q 80 146, 160 156 T 320 152 L 320 200 L 0 200 Z"
                    fill="currentColor" fill-opacity="0.50"/>
              <!-- Track line -->
              <line x1="0" y1="172" x2="320" y2="172"
                    stroke="currentColor" stroke-width="1" stroke-opacity="0.4"/>
              <!-- Train silhouette with lit cabin windows -->
              <g transform="translate(96,142)" fill="currentColor" fill-opacity="0.92">
                <!-- Engine body -->
                <rect x="0"  y="6"  width="52" height="14" rx="2"/>
                <!-- Cabin -->
                <rect x="44" y="0"  width="14" height="10" rx="1.5"/>
                <!-- Chimney -->
                <rect x="6"  y="0"  width="5"  height="6"/>
                <!-- Lit windows along the side -->
                <rect x="4"  y="10" width="4"  height="4" fill-opacity="0.55"/>
                <rect x="12" y="10" width="4"  height="4" fill-opacity="0.55"/>
                <rect x="20" y="10" width="4"  height="4" fill-opacity="0.55"/>
                <rect x="28" y="10" width="4"  height="4" fill-opacity="0.55"/>
                <rect x="36" y="10" width="4"  height="4" fill-opacity="0.55"/>
                <!-- Wheels -->
                <circle cx="6"  cy="22" r="3"/>
                <circle cx="18" cy="22" r="3"/>
                <circle cx="30" cy="22" r="3"/>
                <circle cx="46" cy="22" r="3"/>
              </g>
              <!-- Sparkle dust trailing behind the train -->
              <circle cx="80" cy="148" r="1"   fill="currentColor" fill-opacity="0.85"/>
              <circle cx="70" cy="143" r="0.7" fill="currentColor" fill-opacity="0.60"/>
              <circle cx="60" cy="151" r="0.8" fill="currentColor" fill-opacity="0.70"/>
              <circle cx="48" cy="146" r="0.6" fill="currentColor" fill-opacity="0.50"/>
              <circle cx="36" cy="152" r="0.5" fill="currentColor" fill-opacity="0.40"/>
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
            <div class="case-meta-info" aria-hidden="true">
              <span class="case-meta-duration">60s</span>
              <span class="case-meta-dot">·</span>
              <span>画面风格</span>
              <span class="case-meta-dot">·</span>
              <span>AI 生成</span>
            </div>
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

    <!-- ── Showcase video preview modal ──
         Renders only when a case with `videoSrc` is opened. Teleported to
         <body> so it sits above every Landing layer regardless of the
         stacking context of the card it was opened from. Decorative
         framing (kicker / title / desc / actions) is plain CSS; no extra
         dependencies. -->
    <Teleport to="body">
      <div
        v-if="activeShowcaseCase"
        class="showcase-modal-backdrop"
        @click="closeShowcaseCase"
      >
        <section
          class="showcase-modal"
          role="dialog"
          aria-modal="true"
          :aria-label="activeShowcaseCase.title"
          @click.stop
        >
          <button
            type="button"
            class="showcase-modal-close"
            aria-label="关闭预览"
            @click="closeShowcaseCase"
          >
            ×
          </button>

          <header class="showcase-modal-header">
            <div v-if="activeShowcaseCase.isReference" class="showcase-modal-kicker">
              Reference Showcase · 灵感样片
            </div>
            <h3 class="showcase-modal-title">{{ activeShowcaseCase.title }}</h3>
            <p class="showcase-modal-desc">
              {{ activeShowcaseCase.description }}
            </p>
          </header>

          <video
            v-if="activeShowcaseCase.videoSrc"
            ref="showcaseVideoRef"
            class="showcase-modal-video"
            :src="activeShowcaseCase.videoSrc"
            controls
            autoplay
            playsinline
            preload="metadata"
          />

          <div class="showcase-modal-actions">
            <button
              type="button"
              class="showcase-modal-primary"
              @click="onShowcaseModalEnterStudio"
            >
              进入 Studio
              <span aria-hidden="true">→</span>
            </button>
            <button
              type="button"
              class="showcase-modal-secondary"
              @click="closeShowcaseCase"
            >
              关闭
            </button>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
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

/* ── Showcase video preview modal ──
   Only cases that declare a `videoSrc` open a modal player when the
   card body is clicked; the other cards continue to navigate to the
   Studio so the existing "进入 Studio" flow stays intact. The "进入工作台"
   button on every card always goes to /studio (unchanged). */
const activeShowcaseCase = ref<CaseItem | null>(null)
const showcaseVideoRef = ref<HTMLVideoElement | null>(null)

function openShowcaseCase(item: CaseItem) {
  if (!item.videoSrc) {
    goStudio()
    return
  }
  activeShowcaseCase.value = item
}

function closeShowcaseCase() {
  const v = showcaseVideoRef.value
  if (v) {
    try {
      v.pause()
      v.currentTime = 0
    } catch {
      /* ignore — video element may already be detached */
    }
  }
  activeShowcaseCase.value = null
}

function onShowcaseModalEnterStudio() {
  closeShowcaseCase()
  goStudio()
}

function handleShowcaseKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && activeShowcaseCase.value) {
    closeShowcaseCase()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleShowcaseKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleShowcaseKeydown)
})

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
  { id: 'story',      title: '故事生成', desc: '根据主题生成故事内容' },
  { id: 'storyboard', title: '分镜设计', desc: '拆解镜头与叙事节奏' },
  { id: 'images',     title: '画面生成', desc: '生成候选图并支持审核' },
  { id: 'voice',      title: '配音旁白', desc: '生成旁白音频' },
  { id: 'subtitles',  title: '字幕生成', desc: '生成时间轴字幕' },
  { id: 'video',      title: '视频合成', desc: '输出最终成片视频' },
]

// Cinematic poster cards. Each case has its own illustrated thumbnail
// (rendered inline as SVG, keyed off `tone`) so the showcase reads as a
// portfolio strip rather than placeholder color blocks. First entry is a
// fixed Reference Case (经典绘本《小老鼠吃月亮》) so the showcase opens with
// recognizable provenance.
type CaseTone = 'moon' | 'forest' | 'ocean' | 'train'
type CaseItem = {
  id: string
  title: string
  subtitle: string
  tags: string[]
  tone: CaseTone
  badge?: string  // optional top-right ribbon (e.g. "REFERENCE")
  /** Optional video preview — when present, clicking the card body opens
      a modal player instead of navigating to /studio. Static file under
      `frontend/public/`; never bundled. */
  videoSrc?: string
  /** Long description shown inside the preview modal. */
  description?: string
  /** Marks the entry as a Reference Showcase (inspiration sample) so the
      modal renders the "灵感样片" kicker and Reference framing. */
  isReference?: boolean
}
const caseList: CaseItem[] = [
  {
    id: 'moon',
    title: '小老鼠吃月亮',
    subtitle: '原创亲子故事参考样片',
    tags: ['灵感样片', '亲子故事'],
    tone: 'moon',
    badge: 'REFERENCE',
    isReference: true,
    videoSrc: '/showcase/mouse-moon-reference.mp4',
    description:
      '《小老鼠吃月亮》是一支原创亲子故事参考样片，也是 Jinsie AI Video Studio 的产品灵感来源。该样片通过多工具手工流程完成，用于展示从故事脚本、分镜画面、配音字幕到视频成片的目标创作效果。',
  },
  {
    id: 'forest',
    title: '森林里的小伙伴',
    subtitle: '原创亲子故事',
    tags: ['插画风', '亲子'],
    tone: 'forest',
  },
  {
    id: 'ocean',
    title: '小蝌蚪的冒险',
    subtitle: '池塘里的成长',
    tags: ['原创故事', '成长'],
    tone: 'ocean',
  },
  {
    id: 'train',
    title: '星光小火车',
    subtitle: '奇幻旅程',
    tags: ['奇幻故事', '成长'],
    tone: 'train',
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
  /* Tighter vertical rhythm — sections now sit ~40–56px apart instead of
     the earlier ~72px gap. Page reads as a connected product flow rather
     than a long magazine spread. */
  padding: 40px 24px 48px;
  max-width: 1100px;
  margin: 0 auto;
}
@media (max-width: 1200px) {
  .landing-section { padding: 32px 24px 40px; }
}
@media (max-width: 960px) {
  .landing-section { padding: 28px 24px 36px; }
}
/* Section title block also gets a smaller bottom gap — reduces the empty
   space between the title and the rail/grid beneath. */
.landing .section-title { margin-bottom: 32px; }
/* Footer banner: pull closer to the cases grid. */
.landing-foot { padding: 24px 24px 56px; }

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
  /* Desktop: explicit 4-column layout so the showcase row reads as a
     complete portfolio strip on wide viewports instead of leaving a
     gap at the end. Cards collapse to 2×2 on tablet and 1 column on
     mobile via the media queries below. */
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 22px;
  max-width: 1080px;
  margin: 0 auto;
}
@media (max-width: 1100px) {
  .case-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .case-grid { grid-template-columns: 1fr; }
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
  transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1),
              border-color 0.18s,
              box-shadow 0.2s;
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
  /* Lighter lift (3px) + slightly brighter border. No extra arc-300
     glow ring — that was reading as a strong halo on the page; the
     subtle border + soft shadow expansion alone signals interactivity. */
  transform: translateY(-3px);
  border-color: color-mix(in srgb, var(--arc-300) 40%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 14%, transparent),
    0 22px 44px rgba(0, 0, 0, 0.38);
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
.case-poster--train {
  background: linear-gradient(
    180deg,
    #0d1428 0%,
    #060914 60%,
    #03060e 100%
  );
}

.case-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  /* Subtler poster zoom — 1.02 over 0.22s. Previous 1.05 / 0.42s
     was pushing the illustration noticeably out of frame on hover
     which read as motion-heavy on a quiet portfolio strip. */
  transition: transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.case-card:hover .case-svg {
  transform: scale(1.02);
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

/* Play overlay — fades in on hover. Both hover and focus-within are
   targeted so keyboard users see the affordance too. Transitions
   tightened to 0.2s to match the rest of the card hover. */
.case-play {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 56px;
  height: 56px;
  transform: translate(-50%, -50%) scale(0.88);
  color: rgba(255, 245, 220, 0.95);
  opacity: 0;
  transition: opacity 0.2s ease, transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1);
  pointer-events: none;
  filter: drop-shadow(0 0 12px color-mix(in srgb, var(--arc-300) 45%, transparent));
  z-index: 2;
}
.case-play svg { width: 100%; height: 100%; }
.case-card:hover .case-play,
.case-card:focus-within .case-play {
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

/* ── Footer ──
   Horizontal closing action bar — copy on the left, CTA on the right.
   Replaces the previous vertically-stacked card so the page ends on a
   slim, deliberate strip instead of a centred panel.
   Background is a very low-alpha glass surface; per-theme tones (pearl
   paper / dark gold gradient) come from the overrides below. Stacks
   vertically on narrow viewports via the media query at the bottom. */
.landing-foot {
  position: relative;
  z-index: 1;
  padding: 32px 24px 56px;
}
.foot-content {
  position: relative;
  max-width: 780px;
  margin: 0 auto;
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 28px;
  border-radius: 24px;
  border: 1px solid rgba(227, 174, 75, 0.13);
  background: linear-gradient(
    180deg,
    rgba(18, 14, 7, 0.38),
    rgba(8, 7, 5, 0.28)
  );
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
  text-align: left;
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 6%, transparent),
    0 16px 42px rgba(0, 0, 0, 0.24);
  overflow: hidden;
}
.foot-copy {
  flex: 1 1 auto;
  min-width: 0;
}
.foot-cta {
  flex: 0 0 auto;
}
/* On narrow viewports the row collapses to a centred stack so the
   button stays comfortably tappable and the copy doesn't get squeezed. */
@media (max-width: 640px) {
  .foot-content {
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: 16px;
    padding: 22px 24px 22px;
  }
  .foot-copy { flex: 0 0 auto; }
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
  /* Slightly slimmer than the previous 11/22 — keeps the button as the
     bar's focal point without making it visually heavy. */
  padding: 10px 20px;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  cursor: pointer;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: transform 0.18s, border-color 0.18s, box-shadow 0.18s, background 0.18s;
}
.foot-cta:hover {
  /* Soft hover only: 1px lift + brighter border + a touch warmer
     background. No external glow ring — keeps the closing bar quiet. */
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 56%, transparent);
  background: color-mix(in srgb, var(--arc-400) 16%, rgba(12, 9, 4, 0.92));
}
.foot-cta-arrow {
  transition: transform 0.18s;
}
.foot-cta:hover .foot-cta-arrow {
  transform: translateX(2px);
}

/* ── Case video meta line ──
   Small chip-style metadata under the poster (e.g. "60s · 绘本风 · AI 生成")
   that signals the cards are video works, not flat illustrations. Subtle
   on dark themes so the existing approved card composition is preserved. */
.case-meta-info {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.6875rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: color-mix(in srgb, var(--text-secondary) 80%, transparent);
  margin-bottom: 4px;
}
.case-meta-info .case-meta-duration {
  font-weight: 700;
  color: color-mix(in srgb, var(--arc-300) 92%, transparent);
  letter-spacing: 0.06em;
}
.case-meta-info .case-meta-dot {
  color: color-mix(in srgb, var(--text-muted) 60%, transparent);
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

/* ═══════════════════════════════════════════════════════════════════
   Showcase video preview modal — base (dark gold/blue/purple themes).
   Pearl-specific tones live in the non-scoped pearl block below.
   Layered via <Teleport to="body"> so z-index is unaffected by the
   landing page stacking context; backdrop sits at 99999.
═══════════════════════════════════════════════════════════════════ */
.showcase-modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: rgba(6, 5, 3, 0.72);
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  animation: showcase-modal-fade 0.22s ease-out;
}
@keyframes showcase-modal-fade {
  from { opacity: 0; }
  to   { opacity: 1; }
}
.showcase-modal {
  position: relative;
  width: min(720px, 100%);
  max-height: calc(100vh - 64px);
  overflow: auto;
  padding: 26px 28px 22px;
  border-radius: 20px;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 12%, rgba(14, 10, 4, 0.94)) 0%,
    rgba(8, 6, 3, 0.96) 100%
  );
  border: 1px solid color-mix(in srgb, var(--arc-300) 32%, transparent);
  box-shadow:
    inset 0 1px 0 color-mix(in srgb, var(--arc-200) 18%, transparent),
    0 32px 80px rgba(0, 0, 0, 0.62),
    0 0 32px color-mix(in srgb, var(--arc-300) 18%, transparent);
  color: rgba(255, 245, 220, 0.96);
}
.showcase-modal-close {
  position: absolute;
  top: 12px;
  right: 14px;
  width: 32px;
  height: 32px;
  border-radius: 999px;
  border: 1px solid color-mix(in srgb, var(--arc-300) 28%, transparent);
  background: rgba(0, 0, 0, 0.32);
  color: rgba(255, 245, 220, 0.86);
  font-size: 1.25rem;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.18s, border-color 0.18s, color 0.18s;
}
.showcase-modal-close:hover {
  background: rgba(0, 0, 0, 0.50);
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  color: var(--arc-200);
}
.showcase-modal-header {
  margin-bottom: 14px;
  padding-right: 36px; /* keep clear of the absolute close button */
}
.showcase-modal-kicker {
  font-size: 0.6875rem;
  font-weight: 700;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--arc-300) 88%, transparent);
  margin-bottom: 6px;
}
.showcase-modal-title {
  margin: 0 0 8px;
  font-size: 1.25rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: rgba(255, 248, 232, 0.98);
}
.showcase-modal-desc {
  margin: 0;
  font-size: 0.875rem;
  line-height: 1.7;
  color: rgba(255, 245, 220, 0.72);
}
.showcase-modal-video {
  display: block;
  width: 100%;
  margin: 16px 0 18px;
  border-radius: 12px;
  background: #000;
  aspect-ratio: 16 / 9;
  border: 1px solid color-mix(in srgb, var(--arc-300) 20%, transparent);
}
.showcase-modal-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.showcase-modal-primary {
  appearance: none;
  border: 1px solid var(--border-arc);
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--arc-400) 22%, rgba(20, 14, 6, 0.92)) 0%,
    rgba(10, 8, 4, 0.96) 100%
  );
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
.showcase-modal-primary:hover {
  transform: translateY(-1px);
  border-color: color-mix(in srgb, var(--arc-300) 56%, transparent);
  box-shadow: 0 0 22px color-mix(in srgb, var(--arc-300) 24%, transparent);
}
.showcase-modal-secondary {
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--arc-300) 28%, transparent);
  background: transparent;
  color: color-mix(in srgb, var(--arc-200) 80%, transparent);
  padding: 10px 18px;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: border-color 0.18s, color 0.18s, background 0.18s;
}
.showcase-modal-secondary:hover {
  border-color: color-mix(in srgb, var(--arc-300) 50%, transparent);
  color: var(--arc-200);
  background: color-mix(in srgb, var(--arc-400) 8%, transparent);
}
@media (max-width: 560px) {
  .showcase-modal-backdrop { padding: 16px; }
  .showcase-modal { padding: 22px 20px 18px; }
  .showcase-modal-title { font-size: 1.125rem; }
  .showcase-modal-actions { flex-direction: column; align-items: stretch; }
  .showcase-modal-primary,
  .showcase-modal-secondary { width: 100%; justify-content: center; text-align: center; }
}
@media (prefers-reduced-motion: reduce) {
  .showcase-modal-backdrop { animation: none; }
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

/* ─ Defensive reset against browser-extension CSS injection.
   At least one extension (observed: Caoliao / Monica / Immersive
   Translate on this user) injects styles targeting
   `:root[data-theme="pearl"]` directly — it sets `height: 52px` on
   html plus a dark linear-gradient background, which tile-paints
   horizontal sawtooth stripes across the viewport.
   Force the html element back to natural sizing and paint the same
   cream as `.landing`'s base colour, so:
     · the extension's height/background injections are overridden
     · the default body margin (8px) doesn't reveal a white canvas
       strip at the viewport edges. */
:root[data-theme="pearl"] {
  height: auto !important;
  background: #faf3e4 !important;
}

/* ─ Page surface — warm paper (left) + ice-morning mist (right) ─
   Restored asymmetric gradient. The previous uniform cream variant kept
   the brand half clean but left the illustration's blue sky orphaned —
   a clear vertical seam where blue clouds met cream paper. Now the
   right side of the page softly carries an ice-blue mist that picks up
   the same blue from the illustration, so the figure dissolves into the
   page instead of sitting on top of it. */
:root[data-theme="pearl"] .landing {
  /* Defensive token override scoped to .landing only. Lifts --text-
     primary into the clearly-brown range so any selector that falls
     through to the var (body colour, badge sub, etc) inherits the
     same warm caramel tier as the explicit overrides below. */
  --text-primary: #3A2F1E;
  --text-secondary: rgba(94, 76, 50, 0.78);
  --text-muted: rgba(94, 78, 52, 0.56);

  background-color: #faf3e4;
  background-image:
    /* Ice-blue morning mist — sized HUGE with falloff all the way to
       100% so it has no perceptible boundary. */
    radial-gradient(ellipse 90% 100% at 82% 30%, rgba(196, 220, 238, 0.42) 0%, transparent 100%),
    /* Warm cream halo — top-left. */
    radial-gradient(ellipse 70% 70% at 18% 18%, rgba(252, 240, 210, 0.50) 0%, transparent 100%),
    /* Soft warm wash at the bottom-center. */
    radial-gradient(ellipse 90% 60% at 48% 100%, rgba(247, 232, 196, 0.36) 0%, transparent 100%),
    /* Diagonal: warm cream (left) → soft ice mist (right). */
    linear-gradient(125deg, #fffaf0 0%, #f8f3e2 38%, #e9f2fb 100%);
  background-repeat: no-repeat;
  background-attachment: fixed;
}

/* Background decorative layers — gentler on a light surface. */
:root[data-theme="pearl"] .landing .bg-glow-a {
  background: radial-gradient(
    circle,
    rgba(238, 204, 130, 0.24) 0%,
    transparent 64%
  );
  opacity: 0.42;
}
:root[data-theme="pearl"] .landing .bg-glow-b {
  background: radial-gradient(
    circle,
    rgba(190, 218, 240, 0.30) 0%,
    transparent 64%
  );
  opacity: 0.40;
}
:root[data-theme="pearl"] .landing .bg-ambient {
  background:
    radial-gradient(circle at 30% 22%, rgba(214,179,90,0.06) 0%, transparent 42%),
    radial-gradient(circle at 78% 78%, rgba(170,200,224,0.08) 0%, transparent 44%);
}
:root[data-theme="pearl"] .landing .bg-grid {
  /* Hide the 1px gold grid on pearl. On a near-white surface the grid
     lines anti-alias unevenly and read as faint jagged hatching along
     the left margin. Dark themes keep their grid via the base rule. */
  display: none;
}
/* Force GPU compositing on the soft blur layers so their animated drift
   doesn't show micro-edge artifacts at low alpha. */
:root[data-theme="pearl"] .landing .bg-glow-a,
:root[data-theme="pearl"] .landing .bg-glow-b,
:root[data-theme="pearl"] .landing .bg-ambient {
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: transform;
}
/* Remove the starfield entirely on pearl. On a near-white paper surface
   the 1-3px dots + their box-shadow halo anti-alias as faint rectangles,
   and the deterministic golden-ratio layout puts several of them near
   the left edge in a near-vertical column — which read as a sawtooth
   strip running down the left margin. Dark themes still get the stars
   via the base rule; the new `.landing::after` morning-light drift now
   covers the "atmospheric motion" duty on pearl. */
:root[data-theme="pearl"] .landing .bg-stars,
:root[data-theme="pearl"] .landing .bg-stars span {
  display: none !important;
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
  /* Higher-grade champagne — less mustard, more brushed copper.
     text-shadow removed: dark-theme glow on a paper surface looks dirty. */
  color: #b9904f;
  text-shadow: none;
}
:root[data-theme="pearl"] .landing .hero-badge-sub {
  color: rgba(46, 43, 39, 0.62);
}
:root[data-theme="pearl"] .landing .hero-title-brand {
  background: linear-gradient(
    135deg,
    #b9904f 0%,
    #c49a58 55%,
    #d6b06a 100%
  );
  -webkit-background-clip: text;
          background-clip: text;
}
/* Tighter title block — "Jinsie" and "AI Video Studio" read as ONE brand
   wordmark on pearl instead of two visually disjoint lines. */
:root[data-theme="pearl"] .landing .hero-title {
  gap: 2px;
  margin-bottom: 22px;
}
:root[data-theme="pearl"] .landing .hero-title-rest {
  /* Hero "AI Video Studio" — lifted from the very dark #252119 to a
     visibly brown #3A2D1E. Still strong for the brand wordmark, but
     no longer reads as flat black against the cream paper. */
  color: #3A2D1E;
  text-shadow: none;
  font-size: 0.74em;
  font-weight: 700;
  letter-spacing: 0.04em;
}
:root[data-theme="pearl"] .landing .hero-subtitle {
  /* Warm dark brown @ 0.72. */
  color: rgba(58, 50, 38, 0.72);
  font-weight: 500;
}

/* Hero primary CTA — deeper champagne so it reads as the focal point on
   a pale paper page. Larger padding + font on pearl so it owns the first
   fold as the page's primary action. Cream ink on antique gold. */
:root[data-theme="pearl"] .landing .hero-primary {
  background: linear-gradient(180deg, #c89a55 0%, #a07332 100%);
  color: #fff7e2;
  border-color: rgba(120, 86, 30, 0.55);
  padding: 15px 32px;
  font-size: 1rem;
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.36),
    inset 0 -1px 0 rgba(80, 56, 18, 0.22),
    0 14px 30px rgba(120, 86, 30, 0.28);
}
:root[data-theme="pearl"] .landing .hero-primary:hover {
  border-color: rgba(120, 86, 30, 0.72);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.46),
    0 16px 34px rgba(120, 86, 30, 0.34),
    0 0 22px rgba(214, 170, 88, 0.30);
}
:root[data-theme="pearl"] .landing .hero-primary-icon {
  color: #fff3d0;
}

/* Hero secondary — soft paper outline, no dark glow */
:root[data-theme="pearl"] .landing .hero-secondary {
  color: #4a4032;
  background: rgba(255, 255, 255, 0.55);
  border-color: rgba(151, 132, 96, 0.25);
  box-shadow: none;
}
:root[data-theme="pearl"] .landing .hero-secondary:hover {
  border-color: rgba(177, 132, 57, 0.48);
  color: #6e4f1c;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: 0 6px 18px rgba(177, 132, 57, 0.10);
}

/* Hero flow bridge — pearl theme uses morning-gold light dust, not
   technology-blue scan lines. Keep the track low-contrast so it reads
   as sunlight crossing the paper surface. */
:root[data-theme="pearl"] .landing .hero-flow-bridge {
  left: 36%;
  right: 11%;
  top: 45%;
  transform: translateY(-44%);
}
:root[data-theme="pearl"] .landing .hero-flow-path-base {
  stroke: rgba(153, 111, 38, 0.50);
  stroke-width: 1.15;
}
:root[data-theme="pearl"] .landing .hero-flow-path-live {
  stroke: rgba(236, 184, 92, 0.58);
  stroke-width: 1.55;
  filter:
    drop-shadow(0 0 8px rgba(255, 236, 190, 0.36))
    drop-shadow(0 0 16px rgba(181, 138, 58, 0.32));
}
:root[data-theme="pearl"] .landing .hero-flow-spark {
  width: 4.5px;
  height: 4.5px;
  background: rgba(153, 111, 38, 0.62);
  box-shadow:
    0 0 10px rgba(255, 236, 190, 0.36),
    0 0 20px rgba(181, 138, 58, 0.34);
}

/* ─ Storybook Poster — pearl ("morning fog studio") ─
   Watercolor-paper aesthetic: pearl background, warm cream moon (no
   bright halo planet), cream-parchment book, light gold dust, warm
   brown mouse + text. The whole right column should feel like an
   illustrated picture-book spread laid on a designer's desk. */
/* Pearl-theme: workflow icon strip — caption tier. The dedicated Workflow
   section below carries the real pipeline; this strip is a brand hint.
   Colours are deepened so the strip stays readable on the cream surface
   without becoming visually heavy. */
:root[data-theme="pearl"] .landing .hero-workflow-icons {
  margin-top: 22px;
  gap: 10px;
  opacity: 1;
}
:root[data-theme="pearl"] .landing .hwi-icon {
  /* Sizes (width / height / font-size) inherit from base scoped CSS so
     the strip matches the dark theme exactly. Pearl only changes colour
     and removes the drop-shadow halo. */
  color: rgba(181, 138, 58, 0.76);
  filter: none;
  transition: color 0.18s;
}
:root[data-theme="pearl"] .landing .hwi-label {
  color: #6F6048;
  transition: color 0.18s;
}
:root[data-theme="pearl"] .landing .hwi-arrow {
  color: rgba(181, 138, 58, 0.42);
}
/* Hover: subtle champagne pop on the label + icon for the row item. */
:root[data-theme="pearl"] .landing .hwi-item:hover .hwi-icon {
  color: #b9803a;
}
:root[data-theme="pearl"] .landing .hwi-item:hover .hwi-label {
  color: #4a3f2a;
}
:root[data-theme="pearl"] .landing .hero-subtitle-secondary {
  color: rgba(58, 49, 38, 0.62);
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
/* Pearl: the cream-paper PNG already has feathered transparent edges on
   the left and right, so no horizontal mask is needed. Only add a soft
   top + bottom feather so the upper sky and lower book don't end on
   sharp horizontal cuts.
   Size inherits from base scoped `.hero-visual` (same as dark theme).
   Composite is explicitly reset (1-layer + default add / source-over)
   because the inherited `intersect` / `source-in` from base would
   drop a single-layer mask on WebKit. */
:root[data-theme="pearl"] .landing .hero-storybook-art {
  opacity: 0.90;
  mask-image:
    linear-gradient(to bottom, transparent 0%, #000 10%, #000 90%, transparent 100%) !important;
  mask-composite: add !important;
  mask-repeat: no-repeat !important;
  -webkit-mask-image:
    linear-gradient(to bottom, transparent 0%, #000 10%, #000 90%, transparent 100%) !important;
  -webkit-mask-composite: source-over !important;
  -webkit-mask-repeat: no-repeat !important;
}
/* Stage glow BEHIND the illustration — pure warm champagne halo. Stops
   extend to 100% so neither radial has a perceptible inner falloff edge
   (previous 68%/72% stops were producing a soft elliptical boundary). */
:root[data-theme="pearl"] .landing .hero-visual::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(ellipse 62% 56% at 58% 46%, rgba(255, 236, 188, 0.38) 0%, transparent 100%),
    radial-gradient(ellipse 46% 40% at 72% 64%, rgba(248, 220, 162, 0.22) 0%, transparent 100%);
  filter: blur(26px);
}
/* Bottom mist is minimal now — just a hint so the figure doesn't end on
   a hard rectangular edge. Previous wash was hiding the video cards. */
:root[data-theme="pearl"] .landing .hero-visual::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  background: linear-gradient(
    180deg,
    transparent 0%,
    transparent 82%,
    rgba(255, 252, 244, 0.06) 100%
  );
}
/* (Pearl ::before override removed — no fade overlay on either theme.) */



/* Case posters — pearl ("paper poster on a studio wall")
   Posters get lighter tone-specific backdrops so the warm-gold SVG ink
   reads on the page; ribbon + overlay text switch to warm brown tones. */
:root[data-theme="pearl"] .landing .case-card {
  background: rgba(255, 253, 248, 0.88);
  border-color: rgba(186, 151, 84, 0.16);
  border-radius: 22px;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.96),
    0 18px 42px rgba(120, 92, 48, 0.07);
}
:root[data-theme="pearl"] .landing .case-card::before {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(190, 150, 82, 0.32),
    transparent
  );
}
:root[data-theme="pearl"] .landing .case-card:hover {
  /* Softer pearl hover — no champagne glow ring, just a slightly
     warmer paper shadow expansion. */
  border-color: rgba(190, 150, 82, 0.22);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.98),
    0 18px 38px rgba(120, 92, 48, 0.08);
}
/* Per-tone pearl poster backdrops — clean watercolor scenes with a hint
   more saturation than v1 so they don't read as muddy beige. SVG "ink"
   inherits `currentColor`, so the per-tone color line below controls the
   illustration tint over each backdrop. */
:root[data-theme="pearl"] .landing .case-poster {
  color: #a07a35;
}

/* ── MOON poster — clean moonlight blue-gray ───────────────────────
   Backdrop is brighter (#F8F9F4 → #E7EEF3) and individual SVG shapes
   are pulled out of the muddy single-currentColor scheme by targeting
   them via their `fill-opacity` attribute (the existing differentiator
   inside the inline SVG). The moon disc becomes a clean silver-blue,
   the hill a soft cool blue, and the stars / mouse keep currentColor
   so the overall ink stays consistent. */
:root[data-theme="pearl"] .landing .case-poster--moon {
  /* Brighter top to bottom — top is near-white moonlight, bottom is a
     barely-tinted cool ice. Pulls the card away from the gray-blue
     range that read as "dusty". */
  background: linear-gradient(180deg, #FAFCFE 0%, #ECF1F6 55%, #DDE7EF 100%);
}
:root[data-theme="pearl"] .landing .case-poster--moon .case-svg {
  /* Calmer ink-blue — stars + sky tint follow this. Less saturated
     than #70849A so the moonlight surface reads cleaner. */
  color: #7B91A8;
}
/* Moon disc — clean pale silver, brighter than the earlier #8B9FB6. */
:root[data-theme="pearl"] .landing .case-poster--moon .case-svg circle[r="34"] {
  fill: #B7C5D6;
  fill-opacity: 1;
}
/* Hill — very soft cool blue-gray, brighter and more transparent. */
:root[data-theme="pearl"] .landing .case-poster--moon .case-svg path[fill-opacity="0.45"] {
  fill: #D8E1EA;
  fill-opacity: 0.9;
}
/* Mouse — slightly warmer / less gray so it reads as a silhouette
   without looking dusty against the brighter sky. */
:root[data-theme="pearl"] .landing .case-poster--moon .case-svg g[transform="translate(110,148)"] {
  fill: #5E708A;
  fill-opacity: 0.92;
}

/* ── FOREST poster — clean cream + sand champagne ──────────────────
   Replace the muddy tan with a brighter cream → sand backdrop and
   restage the ridge layers in distinct sand tones (back ridge palest,
   front hill deepest) so the depth reads without going brown. Sun
   core gets a saturated champagne pop. */
:root[data-theme="pearl"] .landing .case-poster--forest {
  /* Cream-sand backdrop — pulled toward whiter cream at the top and
     lighter sand at the bottom so it reads as "warm morning" instead
     of "old paper ochre". */
  background: linear-gradient(180deg, #FFFAE8 0%, #F8E9C2 55%, #EFDBA8 100%);
}
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg {
  /* Slightly cooler champagne — was #9F7A2E (a touch muddy). #A88234
     keeps the warmth but lifts saturation so the sky tint + back trees
     read as clean gold rather than tan. */
  color: #A88234;
}
/* Sun core — brighter champagne pop */
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg circle[r="14"] {
  fill: #C99A38;
  fill-opacity: 1;
}
/* Back ridge — palest cream */
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg path[fill-opacity="0.22"] {
  fill: #F4E3B6;
  fill-opacity: 0.72;
}
/* Mid ridge — soft sand */
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg path[fill-opacity="0.38"] {
  fill: #E2C988;
  fill-opacity: 0.86;
}
/* Front hill — lighter than before (#B59548 was reading earthy);
   #CBA862 sits in the warm sand tier and gives clearer separation
   from the cream sky without going brown. */
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg path[fill-opacity="0.62"] {
  fill: #CBA862;
  fill-opacity: 0.86;
}
/* Front trees group — kept dark for silhouette readability, but
   slightly warmer hue. */
:root[data-theme="pearl"] .landing .case-poster--forest .case-svg g[fill-opacity="0.85"] {
  fill: #8E6A26;
  fill-opacity: 0.92;
}

/* ── OCEAN poster — bright lake teal ───────────────────────────────
   Backdrop pushed brighter (#F1FBFC → #D8EEF4) so the water reads as
   morning lake rather than cold gray. Wave lines get a saturated teal
   via currentColor; lily pad and tadpole pulled out to a cleaner
   mid-teal. */
:root[data-theme="pearl"] .landing .case-poster--ocean {
  /* Clean lake-blue — top is near-white aqua, bottom is a clear cool
     cyan instead of the previous slightly-dusty #D8EEF4. */
  background: linear-gradient(180deg, #F5FCFD 0%, #E1F3F8 55%, #CFEAF3 100%);
}
:root[data-theme="pearl"] .landing .case-poster--ocean .case-svg {
  /* Slightly more saturated teal — sky tint + waves follow this. */
  color: #4F8AA0;
}
/* Lily pad — brighter teal so it floats clearly on the water */
:root[data-theme="pearl"] .landing .case-poster--ocean .case-svg ellipse[ry="10"] {
  fill: #76A8BA;
  fill-opacity: 0.82;
}
/* Tadpole silhouette — deep teal */
:root[data-theme="pearl"] .landing .case-poster--ocean .case-svg g[transform="translate(120,118)"] {
  fill: #437285;
  fill-opacity: 0.92;
}

/* ── TRAIN poster — soft cream night sky with warm gold star + train ─
   The 4th case ("星光小火车 / 奇幻旅程"). Background is a pale blue
   morning-light sky (lighter than the dark theme's night) so it sits
   alongside the other three pearl cards. Stars and the train silhouette
   are pulled to distinct warm-gold / brown tones so the card stays
   crisp instead of blending into a single muddy currentColor pass. */
:root[data-theme="pearl"] .landing .case-poster--train {
  /* Clear dawn sky — brighter pre-dawn cyan at the top, fades into a
     soft slate blue at the bottom. Replaces the dusty cream-gray
     palette so the night-train scene reads as "early morning" rather
     than "old book paper". */
  background: linear-gradient(180deg, #F4FAFD 0%, #DCE7F2 50%, #C5D5E5 100%);
}
:root[data-theme="pearl"] .landing .case-poster--train .case-svg {
  /* Brighter warm gold — drives sky tint stops + star + dust ambient. */
  color: #D8A845;
}
/* Big stars — pure clean champagne gold */
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="1.4"],
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="1.2"],
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="1.1"] {
  fill: #E2B048;
  fill-opacity: 1;
}
/* Small stars — softer gold sparkle */
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="0.9"],
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="0.8"],
:root[data-theme="pearl"] .landing .case-poster--train .case-svg circle[r="0.7"] {
  fill: #D8A845;
  fill-opacity: 0.82;
}
/* Distant hill — soft dusty blue, less brown so it sits behind the
   front hill as atmospheric depth. */
:root[data-theme="pearl"] .landing .case-poster--train .case-svg path[fill-opacity="0.28"] {
  fill: #A8B5C4;
  fill-opacity: 0.55;
}
/* Near hill — warm gold-brown sand, not the previous gray-brown. */
:root[data-theme="pearl"] .landing .case-poster--train .case-svg path[fill-opacity="0.50"] {
  fill: #8E6E3C;
  fill-opacity: 0.78;
}
/* Train silhouette — deep warm caramel brown. */
:root[data-theme="pearl"] .landing .case-poster--train .case-svg g[transform="translate(96,142)"] {
  fill: #5A4022;
  fill-opacity: 0.94;
}

/* On pearl, flip the overlay from a dark wash to a soft cream paper fade,
   and switch title/subtitle to dark brown ink so they read on light. */
:root[data-theme="pearl"] .landing .case-overlay {
  background: linear-gradient(
    180deg,
    transparent 0%,
    rgba(255, 253, 248, 0.34) 55%,
    rgba(255, 253, 248, 0.82) 100%
  );
}
:root[data-theme="pearl"] .landing .case-overlay-subtitle {
  /* Warm gray-brown — case subtitle ("改编自经典绘本" etc) */
  color: rgba(110, 88, 56, 0.78);
  text-shadow: none;
}
:root[data-theme="pearl"] .landing .case-overlay-title {
  /* Brown caramel — was #30281D which technically is warm but at that
     luminance the eye reads it as black ink. #4E3A1E lifts the value
     into a clearly-brown range while keeping >7:1 contrast on the
     cream card surface, so the card titles read as "warm illustrated
     headline" instead of "hard ink". */
  color: #4E3A1E;
  text-shadow: none;
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
/* Play badge — always faintly visible on pearl so each card reads as a
   playable video work, not a flat illustration. Strengthens on hover. */
:root[data-theme="pearl"] .landing .case-play {
  color: rgba(122, 90, 36, 0.50);
  filter: drop-shadow(0 0 8px rgba(238, 204, 130, 0.32));
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.92);
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}
:root[data-theme="pearl"] .landing .case-card:hover .case-play,
:root[data-theme="pearl"] .landing .case-card:focus-within .case-play {
  color: rgba(122, 90, 36, 0.82);
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
}
:root[data-theme="pearl"] .landing .case-meta {
  background: rgba(255, 253, 248, 0.94);
  border-top: 1px solid rgba(188, 158, 96, 0.12);
}
:root[data-theme="pearl"] .landing .case-tag {
  background: rgba(255, 248, 232, 0.58);
  border-color: rgba(190, 150, 82, 0.22);
  color: #7a5a24;
}
/* "进入工作台 →" — caramel-brown affordance link. Brighter than the
   chip text so it reads as a CTA, but still warm not black. */
:root[data-theme="pearl"] .landing .case-cta {
  color: #8A641F;
  font-weight: 600;
  letter-spacing: 0.06em;
}
:root[data-theme="pearl"] .landing .case-cta:hover {
  color: #6F4C12;
}

/* Footer CTA bar — final visual collapse. Background dropped to 0.34
   alpha so the page surface barely thickens here; border at 0.10 is
   almost invisible; shadow flat. The bar reads as the button + copy
   floating, with just enough surface to group them. */
:root[data-theme="pearl"] .landing .foot-content {
  background: rgba(255, 253, 248, 0.34);
  border-color: rgba(188, 151, 84, 0.10);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 12px 28px rgba(126, 94, 36, 0.035);
  backdrop-filter: blur(8px) saturate(140%);
  -webkit-backdrop-filter: blur(8px) saturate(140%);
}
:root[data-theme="pearl"] .landing .foot-content::before {
  /* Top hairline — softer on pearl so it doesn't read as a panel edge. */
  background: linear-gradient(
    90deg,
    transparent,
    rgba(188, 151, 84, 0.22),
    transparent
  );
}
:root[data-theme="pearl"] .landing .foot-copy {
  /* Foot CTA copy ("开始创作你的故事视频") — matches the new card-title
     warm-brown tier so the closing line doesn't feel like a black
     headline tucked under the bright section. */
  color: #3D2F1E;
}
:root[data-theme="pearl"] .landing .foot-cta {
  background: linear-gradient(180deg, #c89a55 0%, #a07332 100%);
  color: #FFF8E8;
  border-color: rgba(120, 86, 30, 0.50);
  /* Lighter shadow than before so the button looks like a slim
     champagne pill on a near-transparent bar instead of a heavy chip. */
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.34),
    0 8px 18px rgba(120, 86, 30, 0.18);
}
:root[data-theme="pearl"] .landing .foot-cta:hover {
  border-color: rgba(120, 86, 30, 0.66);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.42),
    0 10px 22px rgba(120, 86, 30, 0.24);
}

/* ── Section headers ── */
:root[data-theme="pearl"] .landing .section-eyebrow {
  color: #b9904f;
}
:root[data-theme="pearl"] .landing .eyebrow-line {
  background: linear-gradient(
    90deg,
    transparent,
    rgba(177, 132, 57, 0.40),
    transparent
  );
}
:root[data-theme="pearl"] .landing .section-title {
  /* Section headers (完整 Story-to-Video 创作链路 / 案例展示) — lifted
     into clearly-brown range (#3D2F1E) so they don't read as ink-black
     stripes between the bright Workflow / Showcase sections. */
  color: #3D2F1E;
  text-shadow: none;
}

/* ── Workflow rail — light paper circles with champagne ink. Sized up so
   the technical chain is a clear, readable strip — not a row of small
   faded dots. ── */
:root[data-theme="pearl"] .landing .workflow-node {
  /* 6 nodes × 148 + 5 links × 28 = 1028 < 1052 (section content width
     at max-width 1100 − 2×24px padding). Earlier 160/180 was overflowing
     by ~48px and forcing the last node to wrap onto a second row. */
  flex: 0 0 148px;
  max-width: 168px;
  padding: 12px 8px;
}
:root[data-theme="pearl"] .landing .workflow-node-orb {
  width: 56px;
  height: 56px;
  background: rgba(255, 252, 244, 0.82);
  border: 1.5px solid rgba(177, 132, 57, 0.38);
  color: #8a6a2a;
  font-size: 0.8125rem;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.95),
    0 8px 20px rgba(92, 76, 46, 0.08);
}
:root[data-theme="pearl"] .landing .workflow-node:hover .workflow-node-orb {
  border-color: rgba(177, 132, 57, 0.62);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.98),
    0 10px 22px rgba(92, 76, 46, 0.14),
    0 0 22px rgba(238, 204, 130, 0.34);
}
:root[data-theme="pearl"] .landing .workflow-node-title {
  color: #3A3124;
  font-size: 0.9375rem;
  font-weight: 600;
}
:root[data-theme="pearl"] .landing .workflow-node-desc {
  /* Warm gray-brown @ 0.58 — caption tier under the node title. */
  color: rgba(76, 64, 46, 0.58);
  font-size: 0.75rem;
}
:root[data-theme="pearl"] .landing .workflow-link {
  flex-basis: 28px;
  margin-top: 42px;
  height: 1.5px;
  background: linear-gradient(
    90deg,
    rgba(177, 132, 57, 0.55),
    rgba(177, 132, 57, 0.18)
  );
}

/* ThemeSwitcher dropdown — match pearl panel border for the down-flipped
   arrow added in the :deep override above. */
:root[data-theme="pearl"] .ts-root .ts-panel::after {
  border-bottom-color: rgba(255, 255, 255, 0.96);
}

/* Pearl: case meta line (60s · 画面风格 · AI 生成) — warm gray-brown
   so it reads as a quiet caption tier under the bigger card title. */
:root[data-theme="pearl"] .landing .case-meta-info {
  color: rgba(78, 65, 47, 0.56);
}
:root[data-theme="pearl"] .landing .case-meta-info .case-meta-duration {
  color: #8A641F;
}
:root[data-theme="pearl"] .landing .case-meta-info .case-meta-dot {
  color: rgba(78, 65, 47, 0.32);
}

/* ════════════════════════════════════════════════════════════════
   Pearl-only — soft morning air shimmer.
   This is intentionally NOT a sun orb, ring, radar circle or lens flare.
   It is a very subtle atmospheric layer: warm morning haze drifting over
   the right side of the hero and a tiny amount of gold dust shimmer.
═══════════════════════════════════════════════════════════════════ */
:root[data-theme="pearl"] .landing::after {
  content: none;
}

/* ════════════════════════════════════════════════════════════════
   Showcase video preview modal — pearl theme override.
   Paper-glass card with warm ink-brown typography, soft champagne
   accents on borders and the primary button.
═══════════════════════════════════════════════════════════════════ */
:root[data-theme="pearl"] .showcase-modal-backdrop {
  /* Lighter scrim — keeps the page visible behind the modal instead
     of going to near-black. */
  background: rgba(46, 38, 22, 0.46);
}
:root[data-theme="pearl"] .showcase-modal {
  background: linear-gradient(
    180deg,
    rgba(255, 252, 244, 0.96) 0%,
    rgba(252, 245, 230, 0.94) 100%
  );
  border-color: rgba(188, 151, 84, 0.32);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.94),
    0 28px 64px rgba(126, 94, 36, 0.20),
    0 0 28px rgba(238, 204, 130, 0.12);
  color: #3D2F1E;
}
:root[data-theme="pearl"] .showcase-modal-close {
  background: rgba(255, 253, 248, 0.78);
  border-color: rgba(188, 151, 84, 0.30);
  color: #8A641F;
}
:root[data-theme="pearl"] .showcase-modal-close:hover {
  background: rgba(255, 253, 248, 0.92);
  border-color: rgba(120, 86, 30, 0.56);
  color: #6F4C12;
}
:root[data-theme="pearl"] .showcase-modal-kicker {
  color: #8A641F;
}
:root[data-theme="pearl"] .showcase-modal-title {
  color: #2F271C;
}
:root[data-theme="pearl"] .showcase-modal-desc {
  color: rgba(76, 64, 46, 0.82);
}
:root[data-theme="pearl"] .showcase-modal-video {
  border-color: rgba(188, 151, 84, 0.22);
  background: #1a1410;
}
:root[data-theme="pearl"] .showcase-modal-primary {
  background: linear-gradient(180deg, #c89a55 0%, #a07332 100%);
  color: #FFF8E8;
  border-color: rgba(120, 86, 30, 0.50);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.34),
    0 10px 22px rgba(120, 86, 30, 0.20);
}
:root[data-theme="pearl"] .showcase-modal-primary:hover {
  border-color: rgba(120, 86, 30, 0.66);
  box-shadow:
    inset 0 1px 0 rgba(255, 248, 220, 0.42),
    0 12px 26px rgba(120, 86, 30, 0.26);
}
:root[data-theme="pearl"] .showcase-modal-secondary {
  border-color: rgba(151, 132, 96, 0.36);
  color: #6E5828;
  background: rgba(255, 253, 248, 0.36);
}
:root[data-theme="pearl"] .showcase-modal-secondary:hover {
  border-color: rgba(120, 86, 30, 0.56);
  color: #4F3A14;
  background: rgba(255, 253, 248, 0.62);
}
</style>
