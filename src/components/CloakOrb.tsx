import { motion } from 'framer-motion'
import { Shield } from 'lucide-react'
import type { ScanPhase } from '../types/scanner'
import { useReducedMotion } from '../hooks/useReducedMotion'

interface Props {
  phase: ScanPhase
  progress?: number
  size?: number
}

function statusText(phase: ScanPhase): string {
  switch (phase) {
    case 'idle':
      return 'READY TO PROTECT'
    case 'complete':
      return 'PROTECTED'
    case 'uploading':
      return 'RECEIVING'
    default:
      return 'SCANNING...'
  }
}

function accent(phase: ScanPhase): string {
  if (phase === 'complete') return '#10B981'
  if (phase === 'idle') return '#9CA3AF'
  return '#06B6D4'
}

/**
 * The central Privacy Scanner Orb / Cloak Core — a translucent glass sphere with
 * flowing rings, a rotating dotted ring and a liquid surface. Reacts to phase.
 */
export default function CloakOrb({ phase, progress = 0, size = 320 }: Props) {
  const reduced = useReducedMotion()
  const color = accent(phase)
  const scanning = phase !== 'idle' && phase !== 'complete'

  return (
    <div
      className="relative"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Cloak core status: ${statusText(phase)}`}
    >
      {/* soft outer glow */}
      <div
        className="absolute inset-0 rounded-full blur-2xl transition-colors duration-700"
        style={{ background: `${color}22` }}
      />

      {/* rotating dotted ring */}
      <motion.div
        className="absolute inset-2 rounded-full"
        style={{
          background: `conic-gradient(from 0deg, transparent 0 8deg, ${color}44 8deg 10deg, transparent 10deg 20deg)`,
          maskImage:
            'radial-gradient(circle, transparent 62%, black 63%, black 66%, transparent 67%)',
          WebkitMaskImage:
            'radial-gradient(circle, transparent 62%, black 63%, black 66%, transparent 67%)',
        }}
        animate={reduced ? {} : { rotate: 360 }}
        transition={{ duration: 24, ease: 'linear', repeat: Infinity }}
      />

      {/* flowing rings */}
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="absolute rounded-full border"
          style={{
            inset: 12 + i * 20,
            borderColor: `${color}${i === 0 ? '55' : '22'}`,
          }}
          animate={
            reduced || !scanning
              ? {}
              : { scale: [1, 1.03, 1], opacity: [0.5, 0.9, 0.5] }
          }
          transition={{ duration: 3 + i, ease: 'easeInOut', repeat: Infinity }}
        />
      ))}

      {/* glass sphere */}
      <div
        className="absolute inset-[18%] overflow-hidden rounded-full border border-white/60 shadow-glass backdrop-blur-md"
        style={{
          background:
            'radial-gradient(circle at 35% 28%, rgba(255,255,255,0.9), rgba(255,255,255,0.35) 45%, rgba(226,232,240,0.5) 100%)',
        }}
      >
        {/* liquid surface */}
        <svg
          className="absolute inset-0 h-full w-full"
          viewBox="0 0 200 200"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="orb-liquid" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={`${color}55`} />
              <stop offset="100%" stopColor={`${color}18`} />
            </linearGradient>
          </defs>
          <path fill="url(#orb-liquid)">
            {!reduced && (
              <animate
                attributeName="d"
                dur="6s"
                repeatCount="indefinite"
                values="
                  M0,120 C50,100 90,140 130,120 C170,105 190,130 200,120 L200,200 L0,200 Z;
                  M0,125 C50,145 90,105 130,130 C170,150 190,110 200,125 L200,200 L0,200 Z;
                  M0,120 C50,100 90,140 130,120 C170,105 190,130 200,120 L200,200 L0,200 Z"
              />
            )}
            {reduced && (
              <animate attributeName="opacity" values="0.8;0.8" dur="1s" />
            )}
          </path>
        </svg>

        {/* highlight */}
        <div className="absolute left-[18%] top-[14%] h-8 w-16 rounded-full bg-white/70 blur-md" />

        {/* center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <Shield
            className="mb-1 h-7 w-7"
            style={{ color }}
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <span className="font-mono text-sm font-semibold tracking-[0.28em] text-cloak-ink">
            CLOAK
          </span>
          <span
            className="led-text mt-1 text-[10px] font-medium"
            style={{ color }}
          >
            {statusText(phase)}
          </span>
          {scanning && (
            <span className="mono-label mt-1 text-[10px]" style={{ color }}>
              {Math.round(progress)}%
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
