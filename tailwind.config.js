/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cloak: {
          white: '#FFFFFF',
          offwhite: '#FAFAFA',
          lightgray: '#F3F4F6',
          softgray: '#E5E7EB',
          medgray: '#9CA3AF',
          ink: '#111827',
          muted: '#6B7280',
        },
        state: {
          scan: '#06B6D4',
          safe: '#10B981',
          warn: '#F59E0B',
          crit: '#EF4444',
        },
      },
      fontFamily: {
        sans: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      borderRadius: {
        xl2: '18px',
        xl3: '24px',
      },
      boxShadow: {
        soft: '0 1px 2px rgba(17,24,39,0.04), 0 8px 24px rgba(17,24,39,0.06)',
        glass: '0 8px 40px rgba(17,24,39,0.08)',
        glow: '0 0 0 1px rgba(6,182,212,0.15), 0 0 30px rgba(6,182,212,0.15)',
      },
      keyframes: {
        'grid-pan': {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '80px 80px' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        'spin-slow': {
          to: { transform: 'rotate(360deg)' },
        },
        'float-y': {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'draw-check': {
          to: { strokeDashoffset: '0' },
        },
      },
      animation: {
        'grid-pan': 'grid-pan 24s linear infinite',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'spin-slow': 'spin-slow 18s linear infinite',
        'float-y': 'float-y 6s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
