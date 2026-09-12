import { motion } from 'framer-motion'
import type { ScanPhase } from '../types/scanner'

interface Props {
  phase: ScanPhase
  progress: number
}

const STEPS: { phase: ScanPhase; label: string }[] = [
  { phase: 'analyzing', label: 'ANALYZING PIXELS' },
  { phase: 'identifying', label: 'IDENTIFYING PATTERNS' },
  { phase: 'classifying', label: 'CLASSIFYING SENSITIVE DATA' },
  { phase: 'cloaking', label: 'APPLYING CLOAK' },
  { phase: 'complete', label: 'PROTECTION COMPLETE' },
]

const ORDER: ScanPhase[] = [
  'uploading',
  'analyzing',
  'identifying',
  'classifying',
  'cloaking',
  'complete',
]

/** Circular scan progress + live phase checklist. */
export default function Scanner({ phase, progress }: Props) {
  const R = 52
  const C = 2 * Math.PI * R
  const dash = C - (progress / 100) * C
  const currentIdx = ORDER.indexOf(phase)

  return (
    <div className="glass-panel flex flex-col items-center gap-5 rounded-xl2 p-6">
      <span className="mono-label self-start">SCAN_PROGRESS</span>

      <div className="relative grid place-items-center">
        <svg width="128" height="128" viewBox="0 0 128 128" className="-rotate-90">
          <circle cx="64" cy="64" r={R} fill="none" stroke="#E5E7EB" strokeWidth="8" />
          <motion.circle
            cx="64"
            cy="64"
            r={R}
            fill="none"
            stroke="#06B6D4"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={dash}
            transition={{ ease: 'linear' }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          <span className="font-mono text-2xl font-semibold text-cloak-ink">
            {Math.round(progress)}%
          </span>
          <span className="mono-label text-[9px]">SCAN</span>
        </div>
      </div>

      <ul className="w-full space-y-2" aria-live="polite">
        {STEPS.map((s) => {
          const idx = ORDER.indexOf(s.phase)
          const done = currentIdx > idx
          const active = phase === s.phase
          return (
            <li key={s.phase} className="flex items-center gap-3">
              <span
                className={`grid h-4 w-4 place-items-center rounded-full text-[9px] ${
                  done
                    ? 'bg-state-safe text-white'
                    : active
                      ? 'bg-state-scan text-white'
                      : 'bg-cloak-softgray text-transparent'
                }`}
              >
                {done ? '✓' : active ? '•' : ''}
              </span>
              <span
                className={`led-text text-[11px] ${
                  active
                    ? 'text-state-scan'
                    : done
                      ? 'text-cloak-ink'
                      : 'text-cloak-medgray'
                }`}
              >
                {s.label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
