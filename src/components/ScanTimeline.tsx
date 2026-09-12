import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import type { ScanPhase } from '../types/scanner'

interface Props {
  phase: ScanPhase
}

const STAGES = [
  { id: '01', label: 'Screenshot received', at: 0 },
  { id: '02', label: 'Image normalized', at: 1 },
  { id: '03', label: 'Sensitive patterns detected', at: 2 },
  { id: '04', label: 'Risk classified', at: 3 },
  { id: '05', label: 'Cloak applied', at: 4 },
  { id: '06', label: 'Verification complete', at: 5 },
]

const PHASE_STEP: Record<ScanPhase, number> = {
  idle: -1,
  uploading: 0,
  analyzing: 1,
  identifying: 2,
  classifying: 3,
  cloaking: 4,
  complete: 6,
}

/** Protection pipeline timeline; stages light up as scanning progresses. */
export default function ScanTimeline({ phase }: Props) {
  const step = PHASE_STEP[phase]

  return (
    <div className="glass-panel rounded-xl2 p-6">
      <span className="mono-label">PROTECTION_PIPELINE</span>
      <ol className="mt-4 space-y-0">
        {STAGES.map((s, i) => {
          const done = step > s.at
          const active = step === s.at || (phase === 'complete' && i === STAGES.length - 1)
          const reached = done || active
          return (
            <li key={s.id} className="flex gap-3">
              <div className="flex flex-col items-center">
                <motion.span
                  initial={false}
                  animate={{
                    backgroundColor: done
                      ? '#10B981'
                      : active
                        ? '#06B6D4'
                        : '#E5E7EB',
                    scale: active ? 1.1 : 1,
                  }}
                  className="grid h-7 w-7 place-items-center rounded-full font-mono text-[10px] font-semibold text-white"
                >
                  {done ? <Check className="h-3.5 w-3.5" /> : s.id}
                </motion.span>
                {i < STAGES.length - 1 && (
                  <span
                    className={`my-1 w-px flex-1 ${
                      done ? 'bg-state-safe' : 'bg-cloak-softgray'
                    }`}
                    style={{ minHeight: 22 }}
                  />
                )}
              </div>
              <div className="pb-4 pt-0.5">
                <span
                  className={`led-text text-[11px] ${
                    reached ? 'text-cloak-ink' : 'text-cloak-medgray'
                  }`}
                >
                  {s.id} — {s.label}
                </span>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
