import { motion } from 'framer-motion'
import { useReducedMotion } from '../hooks/useReducedMotion'

const SERVICES = [
  { label: 'DETECTION ENGINE', status: 'ONLINE' },
  { label: 'PATTERN ANALYZER', status: 'ONLINE' },
  { label: 'IMAGE PROCESSOR', status: 'ONLINE' },
  { label: 'REDACTION ENGINE', status: 'ONLINE' },
  { label: 'PRIVACY CHECK', status: 'PASSED' },
]

function dots(label: string) {
  const total = 34
  const fill = Math.max(0, total - label.length)
  return '.'.repeat(fill)
}

/** Technical LED "CLOAK ENGINE" status readout. */
export default function SystemStatus() {
  const reduced = useReducedMotion()
  return (
    <div className="glass-panel rounded-xl2 p-6">
      <div className="flex items-center justify-between">
        <span className="mono-label">CLOAK_ENGINE</span>
        <div className="flex items-center gap-1" aria-hidden="true">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-state-safe"
              animate={reduced ? {} : { opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </div>

      <div className="mt-4 space-y-1.5">
        {SERVICES.map((s) => (
          <div key={s.label} className="flex items-baseline font-mono text-[11px]">
            <span className="text-cloak-ink">{s.label}</span>
            <span className="mx-1 flex-1 overflow-hidden whitespace-nowrap text-cloak-medgray">
              {dots(s.label)}
            </span>
            <span className="font-semibold text-state-safe">{s.status}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 border-t border-cloak-softgray/70 pt-3">
        <span className="mono-label text-[10px]">SCAN_LATENCY: 142ms</span>
        <span className="mono-label text-[10px]">PRIVACY_LAYER: ENABLED</span>
      </div>
    </div>
  )
}
