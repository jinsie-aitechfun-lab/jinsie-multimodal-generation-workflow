import { animate } from 'animejs'

export function enterCards(selector: string) {
  const els = document.querySelectorAll<HTMLElement>(selector)
  if (!els.length) return
  animate(Array.from(els), {
    opacity: [0, 1],
    translateY: [20, 0],
    duration: 480,
    delay: (_el: HTMLElement, i: number) => i * 60,
    easing: 'easeOutCubic',
  })
}

export function glowPulse(el: HTMLElement | null) {
  if (!el) return
  animate(el, {
    boxShadow: [
      '0 0 0px rgba(0,196,255,0)',
      '0 0 32px rgba(0,196,255,0.60)',
      '0 0 0px rgba(0,196,255,0)',
    ],
    duration: 900,
    easing: 'easeInOutSine',
  })
}

export function tabTransition(el: HTMLElement | null) {
  if (!el) return
  animate(el, {
    opacity: [0, 1],
    translateX: [-12, 0],
    duration: 320,
    easing: 'easeOutCubic',
  })
}

export function spinnerReveal(el: HTMLElement | null) {
  if (!el) return
  animate(el, {
    scale: [0.85, 1],
    opacity: [0, 1],
    duration: 400,
    easing: 'spring(1, 80, 12, 0)',
  })
}
