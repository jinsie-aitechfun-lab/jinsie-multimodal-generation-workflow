/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Deep space base
        space: {
          950: '#03050f',
          900: '#060b1a',
          850: '#090e21',
          800: '#0d1228',
          750: '#111730',
          700: '#161d3a',
          600: '#1e2847',
          500: '#263357',
        },
        // Cold accent — electric cyan/blue
        arc: {
          50:  '#e8f9ff',
          100: '#c2f0ff',
          200: '#85e1ff',
          300: '#38cdff',
          400: '#00b5f0',
          500: '#0099d4',
          600: '#007bb0',
          700: '#005f8e',
        },
        // Violet secondary
        prism: {
          300: '#c4b5fd',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
        },
        // Neon highlight
        pulse: {
          400: '#34d399',
          500: '#10b981',
        },
        // Warm danger
        flare: {
          400: '#f87171',
          500: '#ef4444',
        },
      },
      fontFamily: {
        studio: ['Inter', 'SF Pro Display', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
        '2xl': '40px',
        '3xl': '60px',
      },
      boxShadow: {
        glow:      '0 0 20px 0 rgba(0,181,240,0.25), 0 0 40px 0 rgba(0,181,240,0.10)',
        'glow-lg': '0 0 40px 0 rgba(0,181,240,0.35), 0 0 80px 0 rgba(0,181,240,0.15)',
        'glow-prism': '0 0 20px 0 rgba(139,92,246,0.30), 0 0 40px 0 rgba(139,92,246,0.12)',
        glass:     '0 8px 32px rgba(0,0,0,0.48), inset 0 1px 0 rgba(255,255,255,0.06)',
        'glass-lg':'0 16px 64px rgba(0,0,0,0.56), inset 0 1px 0 rgba(255,255,255,0.08)',
        float:     '0 24px 48px rgba(0,0,0,0.64), 0 0 0 1px rgba(0,181,240,0.08)',
      },
      backgroundImage: {
        'gradient-arc':     'linear-gradient(135deg, #00b5f0 0%, #8b5cf6 100%)',
        'gradient-deep':    'linear-gradient(180deg, #060b1a 0%, #03050f 100%)',
        'gradient-glass':   'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'gradient-border':  'linear-gradient(135deg, rgba(0,181,240,0.6) 0%, rgba(139,92,246,0.6) 100%)',
        'gradient-header':  'linear-gradient(90deg, rgba(0,181,240,0.08) 0%, rgba(139,92,246,0.06) 100%)',
        'noise':            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E\")",
      },
      animation: {
        'pulse-glow':   'pulseGlow 3s ease-in-out infinite',
        'float':        'float 6s ease-in-out infinite',
        'shimmer':      'shimmer 2.5s linear infinite',
        'slide-up':     'slideUp 0.3s cubic-bezier(0.16,1,0.3,1)',
        'fade-in':      'fadeIn 0.25s ease-out',
        'border-spin':  'borderSpin 4s linear infinite',
        'scan-line':    'scanLine 8s linear infinite',
      },
      keyframes: {
        pulseGlow: {
          '0%,100%': { boxShadow: '0 0 20px rgba(0,181,240,0.20)' },
          '50%':     { boxShadow: '0 0 40px rgba(0,181,240,0.50), 0 0 60px rgba(139,92,246,0.20)' },
        },
        float: {
          '0%,100%': { transform: 'translateY(0px)' },
          '50%':     { transform: 'translateY(-6px)' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        slideUp: {
          '0%':   { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        borderSpin: {
          '0%':   { backgroundPosition: '0% 50%' },
          '100%': { backgroundPosition: '400% 50%' },
        },
        scanLine: {
          '0%':   { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(400%)' },
        },
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
        '4xl': '2rem',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
}
