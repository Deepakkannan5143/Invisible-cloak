import { memo } from 'react'
import Particles from './Particles'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Ambient background system:
 *  A. LiquidFlow — slow flowing translucent SVG waves
 *  B. Moving grid — subtle large-spaced technical grid
 *  C. Floating particles — canvas dots that connect
 *  D. Ambient light — soft blurred radial gradients that drift
 *
 * Everything is extremely subtle and sits behind the interface (fixed, -z).
 */
function LiquidBackground() {
  const reduced = useReducedMotion()

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-cloak-white"
    >
      {/* base wash */}
      <div className="absolute inset-0 bg-gradient-to-b from-white via-cloak-offwhite to-cloak-lightgray" />

      {/* D. Ambient light blobs */}
      <div
        className={`absolute -left-40 top-[-10%] h-[42rem] w-[42rem] rounded-full bg-state-scan/10 blur-3xl ${
          reduced ? '' : 'animate-float-y'
        }`}
      />
      <div
        className={`absolute right-[-15%] top-[20%] h-[38rem] w-[38rem] rounded-full bg-sky-200/25 blur-3xl ${
          reduced ? '' : 'animate-float-y'
        }`}
        style={{ animationDelay: '2s' }}
      />
      <div
        className={`absolute bottom-[-20%] left-[25%] h-[40rem] w-[40rem] rounded-full bg-slate-200/40 blur-3xl ${
          reduced ? '' : 'animate-float-y'
        }`}
        style={{ animationDelay: '4s' }}
      />

      {/* B. Moving grid */}
      <div
        className={`absolute inset-0 opacity-[0.5] ${reduced ? '' : 'animate-grid-pan'}`}
        style={{
          backgroundImage:
            'linear-gradient(to right, rgba(148,163,184,0.10) 1px, transparent 1px), linear-gradient(to bottom, rgba(148,163,184,0.10) 1px, transparent 1px)',
          backgroundSize: '80px 80px',
          maskImage:
            'radial-gradient(ellipse at 50% 30%, black 20%, transparent 75%)',
          WebkitMaskImage:
            'radial-gradient(ellipse at 50% 30%, black 20%, transparent 75%)',
        }}
      />

      {/* A. LiquidFlow waves */}
      <svg
        className="absolute inset-x-0 top-1/4 h-[60vh] w-full opacity-[0.55]"
        viewBox="0 0 1440 600"
        preserveAspectRatio="none"
      >
        <defs>
          <linearGradient id="wave1" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(6,182,212,0.10)" />
            <stop offset="50%" stopColor="rgba(148,163,184,0.14)" />
            <stop offset="100%" stopColor="rgba(6,182,212,0.06)" />
          </linearGradient>
          <linearGradient id="wave2" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(148,163,184,0.10)" />
            <stop offset="100%" stopColor="rgba(125,211,252,0.10)" />
          </linearGradient>
        </defs>

        <g style={{ filter: 'blur(2px)' }}>
          <path fill="url(#wave1)">
            <animate
              attributeName="d"
              dur="14s"
              repeatCount="indefinite"
              values="
                M0,300 C360,220 720,380 1080,300 C1260,260 1380,320 1440,300 L1440,600 L0,600 Z;
                M0,320 C360,400 720,240 1080,340 C1260,380 1380,280 1440,320 L1440,600 L0,600 Z;
                M0,300 C360,220 720,380 1080,300 C1260,260 1380,320 1440,300 L1440,600 L0,600 Z"
            />
          </path>
          <path fill="url(#wave2)">
            <animate
              attributeName="d"
              dur="18s"
              repeatCount="indefinite"
              values="
                M0,360 C400,300 680,420 1040,360 C1240,330 1360,390 1440,360 L1440,600 L0,600 Z;
                M0,340 C400,420 680,300 1040,380 C1240,410 1360,340 1440,360 L1440,600 L0,600 Z;
                M0,360 C400,300 680,420 1040,360 C1240,330 1360,390 1440,360 L1440,600 L0,600 Z"
            />
          </path>
        </g>
      </svg>

      {/* C. Floating particles */}
      <div className="absolute inset-0">
        <Particles count={44} />
      </div>

      {/* top fade so content reads cleanly */}
      <div className="absolute inset-x-0 top-0 h-32 bg-gradient-to-b from-white to-transparent" />
    </div>
  )
}

export default memo(LiquidBackground)
