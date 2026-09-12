import { motion } from 'framer-motion'
import { useReducedMotion } from '../hooks/useReducedMotion'

const NODES = ['Detection', 'Classification', 'Redaction', 'Verification', 'Export']

/** Futuristic circular privacy-network visualization with orbiting nodes. */
export default function SecurityVisualization() {
  const reduced = useReducedMotion()
  const size = 320
  const center = size / 2
  const radius = 120

  return (
    <div className="glass-panel flex flex-col items-center rounded-xl2 p-6">
      <span className="mono-label self-start">PRIVACY_NETWORK // LIVE</span>

      <div className="relative mt-4" style={{ width: size, height: size }}>
        <svg
          className="absolute inset-0"
          viewBox={`0 0 ${size} ${size}`}
          aria-hidden="true"
        >
          {NODES.map((_, i) => {
            const angle = (i / NODES.length) * Math.PI * 2 - Math.PI / 2
            const x = center + radius * Math.cos(angle)
            const y = center + radius * Math.sin(angle)
            return (
              <line
                key={i}
                x1={center}
                y1={center}
                x2={x}
                y2={y}
                stroke="#CBD5E1"
                strokeWidth="1"
                strokeDasharray="3 4"
              >
                {!reduced && (
                  <animate
                    attributeName="stroke-dashoffset"
                    values="14;0"
                    dur="1.4s"
                    repeatCount="indefinite"
                  />
                )}
              </line>
            )
          })}
          {/* traveling particle */}
          {!reduced && (
            <circle r="3" fill="#06B6D4">
              <animateMotion
                dur="4s"
                repeatCount="indefinite"
                path={`M${center},${center} L${center},${center - radius}`}
              />
            </circle>
          )}
        </svg>

        {/* center core */}
        <div className="absolute left-1/2 top-1/2 grid h-24 w-24 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-state-scan/30 bg-white/80 text-center shadow-glass backdrop-blur">
          <span className="font-mono text-[11px] font-semibold tracking-wide text-cloak-ink">
            CLOAK
            <br />
            ENGINE
          </span>
        </div>

        {/* orbit nodes */}
        {NODES.map((label, i) => {
          const angle = (i / NODES.length) * Math.PI * 2 - Math.PI / 2
          const x = center + radius * Math.cos(angle)
          const y = center + radius * Math.sin(angle)
          return (
            <motion.div
              key={label}
              className="absolute -translate-x-1/2 -translate-y-1/2"
              style={{ left: x, top: y }}
              animate={reduced ? {} : { scale: [1, 1.08, 1] }}
              transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.3 }}
            >
              <span className="whitespace-nowrap rounded-full border border-cloak-softgray bg-white px-2.5 py-1 font-mono text-[10px] font-medium text-cloak-ink shadow-soft">
                {label}
              </span>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
