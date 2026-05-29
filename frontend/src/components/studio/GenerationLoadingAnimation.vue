<template>
  <div class="gen-loading">
    <div class="gen-loading-art" aria-hidden="true">
      <svg viewBox="0 0 120 120" class="gen-loading-svg">
        <!-- Outer dashed ring — slow CW rotation -->
        <g class="ring-outer">
          <circle
            cx="60" cy="60" r="54"
            fill="none"
            stroke="currentColor"
            stroke-width="1.1"
            stroke-opacity="0.20"
            stroke-dasharray="5 9"
          />
        </g>

        <!-- Middle short arc — slow CCW rotation -->
        <g class="ring-mid">
          <path
            d="M 22 60 A 38 38 0 0 1 98 60"
            fill="none"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-opacity="0.58"
            stroke-linecap="round"
          />
        </g>

        <!-- Inner dotted ring — very slow CW rotation -->
        <g class="ring-inner">
          <circle
            cx="60" cy="60" r="26"
            fill="none"
            stroke="currentColor"
            stroke-width="0.9"
            stroke-opacity="0.24"
            stroke-dasharray="1.5 4"
          />
        </g>

        <!-- 4 cardinal dots — staggered pulse -->
        <circle class="dot dot-a" cx="60" cy="20" r="2.2" />
        <circle class="dot dot-b" cx="100" cy="60" r="1.7" />
        <circle class="dot dot-c" cx="60" cy="100" r="2.2" />
        <circle class="dot dot-d" cx="20" cy="60" r="1.7" />

        <!-- Center play-frame — breathing -->
        <g class="center">
          <rect
            x="48" y="51" width="24" height="18" rx="3"
            fill="none" stroke="currentColor"
            stroke-width="1.3" stroke-opacity="0.62"
          />
          <path
            d="M 56.5 56 L 64 60 L 56.5 64 Z"
            fill="currentColor" fill-opacity="0.82"
          />
        </g>
      </svg>
    </div>

    <div v-if="title" class="gen-loading-title">{{ title }}</div>
    <p v-if="description" class="gen-loading-desc">{{ description }}</p>
    <div v-if="status" class="gen-loading-status">
      <span class="gen-loading-status-dot" aria-hidden="true"></span>
      <span class="gen-loading-status-text">{{ status }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
  description?: string
  status?: string
}>()
</script>

<style scoped>
.gen-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 14px;
  color: var(--arc-300);
}

.gen-loading-art {
  width: 96px;
  height: 96px;
  filter: drop-shadow(
    0 0 14px color-mix(in srgb, var(--arc-300) 24%, transparent)
  );
}

.gen-loading-svg {
  width: 100%;
  height: 100%;
  display: block;
  color: var(--arc-300);
}

/* Three concentric rings, each rotating around the SVG view-box centre.
   `transform-box: view-box` keeps the rotation origin stable across
   browsers. Speeds are deliberately slow → "thinking" feel, not "loading". */
.ring-outer,
.ring-mid,
.ring-inner,
.center {
  transform-box: view-box;
  transform-origin: 60px 60px;
}

.ring-outer { animation: gen-spin-cw  12s linear infinite; }
.ring-mid   { animation: gen-spin-ccw  8s linear infinite; }
.ring-inner { animation: gen-spin-cw  18s linear infinite; }
.center     { animation: gen-breathe 2.8s ease-in-out infinite; }

.dot {
  fill: currentColor;
  fill-opacity: 0.78;
  animation: gen-dot-pulse 2.4s ease-in-out infinite;
}
.dot-a { animation-delay: 0s;   }
.dot-b { animation-delay: 0.6s; }
.dot-c { animation-delay: 1.2s; }
.dot-d { animation-delay: 1.8s; }

.gen-loading-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
}

.gen-loading-desc {
  margin: 0;
  max-width: 320px;
  font-size: 0.8125rem;
  line-height: 1.6;
  color: var(--text-muted);
}

.gen-loading-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--border-arc);
  background: color-mix(in srgb, var(--arc-400) 8%, transparent);
  color: var(--arc-300);
  font-size: 0.75rem;
  font-weight: 500;
  letter-spacing: 0.02em;
}

.gen-loading-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: currentColor;
  animation: gen-dot-pulse 1.6s ease-in-out infinite;
}

@keyframes gen-spin-cw  { to { transform: rotate(360deg);  } }
@keyframes gen-spin-ccw { to { transform: rotate(-360deg); } }

@keyframes gen-dot-pulse {
  0%, 100% { opacity: 0.30; transform: scale(0.82); }
  50%      { opacity: 1;    transform: scale(1.12); }
}

@keyframes gen-breathe {
  0%, 100% { transform: scale(1);    opacity: 0.78; }
  50%      { transform: scale(1.05); opacity: 1;    }
}

@media (prefers-reduced-motion: reduce) {
  .ring-outer, .ring-mid, .ring-inner,
  .center, .dot, .gen-loading-status-dot {
    animation: none;
  }
}
</style>
