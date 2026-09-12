import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck } from 'lucide-react'
import type { ScanPhase } from '../types/scanner'

interface Props {
  score: number | null
  phase: ScanPhase
  detected: number
  protectedCount: number
  exposed: number
}

/** Large circular privacy score with animated count-up. */
export default function SecurityScore({
  score,
  phase,
  detected,
  protectedCount,
  exposed,
}: Props) {
  const [display, setDisplay] = useState(0)
  const complete = phase === 'complete' && score != null
  const target = score ?? 0

  useEffect(() => {
    if (!complete) {
      setDisplay(0)
      return
    }
    let raf = 0
    const start = performance.now()
    const dur = 900
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(Math.round(eased * target))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [complete, target])

  const R = 64
  const C = 2 * Math.PI * R
  const pct = complete ? display / 100 : 0
  const offset = C - pct * C

  return (
    <div className="glass-panel flex flex-col items-center gap-3 rounded-xl2 p-6">
      <span className="mono-label self-start">PRIVACY_SCORE</span>
      <div className="relative grid place-items-center">
        <svg width="160" height="160" viewBox="0 0 160 160" className="-rotate-90">
          <circle cx="80" cy="80" r={R} fill="none" stroke="#E5E7EB" strokeWidth="10" />
          <motion.circle
            cx="80"
            cy="80"
            r={R}
            fill="none"
            stroke="#10B981"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={C}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute flex flex-col items-center">
          {complete ? (
            <>
              <span className="text-4xl font-semibold text-cloak-ink">{display}</span>
              <span className="mono-label text-[9px]">/ 100</span>
            </>
          ) : (
            <span className="text-4xl font-semibold text-cloak-medgray">—</span>
          )}
        </div>
      </div>

      {complete && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="inline-flex items-center gap-2 rounded-full bg-state-safe/10 px-3 py-1.5 text-sm font-medium text-state-safe"
        >
          <ShieldCheck className="h-4 w-4" /> Safe to share
        </motion.div>
      )}

      <div className="mt-1 grid w-full grid-cols-3 gap-2 text-center">
        <Stat label="Detected" value={detected} tone="ink" />
        <Stat label="Protected" value={protectedCount} tone="safe" />
        <Stat label="Exposed" value={exposed} tone={exposed > 0 ? 'crit' : 'muted'} />
      </div>
    </div>
  )
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'ink' | 'safe' | 'crit' | 'muted'
}) {
  const color =
    tone === 'safe'
      ? 'text-state-safe'
      : tone === 'crit'
        ? 'text-state-crit'
        : tone === 'muted'
          ? 'text-cloak-medgray'
          : 'text-cloak-ink'
  return (
    <div className="rounded-xl2 border border-cloak-softgray bg-white/60 py-2">
      <div className={`text-xl font-semibold ${color}`}>{value}</div>
      <div className="mono-label text-[9px]">{label}</div>
    </div>
  )
}
