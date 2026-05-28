<template>
  <div :class="['studio-card', `studio-card--${variant}`, { 'studio-card--hoverable': hoverable, 'studio-card--glow': glow }]">
    <div v-if="$slots.header" class="studio-card__header">
      <slot name="header" />
    </div>
    <div class="studio-card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="studio-card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'default' | 'elevated' | 'inset' | 'highlight'
  hoverable?: boolean
  glow?: boolean
}>(), {
  variant: 'default',
  hoverable: false,
  glow: false,
})
</script>

<style scoped>
.studio-card {
  position: relative;
  border-radius: 1rem;
  overflow: hidden;
  transition: transform 0.2s cubic-bezier(0.16,1,0.3,1),
              box-shadow 0.2s cubic-bezier(0.16,1,0.3,1),
              border-color 0.2s;
  animation: slideUp 0.3s cubic-bezier(0.16,1,0.3,1);
}

/* Variants */
.studio-card--default {
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--glass-border);
  box-shadow: var(--shadow-glass);
}
.studio-card--elevated {
  background: var(--glass-bg-light);
  backdrop-filter: blur(28px);
  -webkit-backdrop-filter: blur(28px);
  border: 1px solid rgba(255,255,255,0.10);
  box-shadow: var(--shadow-float);
}
.studio-card--inset {
  background: rgba(6,11,26,0.60);
  border: 1px solid rgba(255,255,255,0.05);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
}
.studio-card--highlight {
  background: rgba(245,158,11,0.06);
  border: 1px solid rgba(245,158,11,0.20);
  box-shadow: 0 0 20px rgba(245,158,11,0.10);
}

/* Modifiers */
.studio-card--hoverable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-float), 0 0 24px rgba(245,158,11,0.12);
  border-color: rgba(245,158,11,0.20);
}
.studio-card--glow {
  animation: pulseGlow 3s ease-in-out infinite;
}

/* Gradient border via pseudo */
.studio-card--highlight::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  padding: 1px;
  background: linear-gradient(135deg, rgba(245,158,11,0.42) 0%, rgba(249,115,22,0.30) 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  pointer-events: none;
}

/* Inner layout */
.studio-card__header {
  padding: 1rem 1.25rem 0.75rem;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.studio-card__body { padding: 1.25rem; }
.studio-card__footer {
  padding: 0.75rem 1.25rem 1rem;
  border-top: 1px solid rgba(255,255,255,0.05);
}
</style>
