import { motion } from 'framer-motion'
import { ArrowRight, Play, Sparkles } from 'lucide-react'
import CloakOrb from './CloakOrb'
import type { ScanPhase } from '../types/scanner'

interface Props {
  phase: ScanPhase
  progress: number
  onProtect: () => void
  onDemo: () => void
}

const HIGHLIGHTS = ['Aadhaar', 'Cards', 'API Keys', 'Passwords', 'Personal Data']

export default function Hero({ phase, progress, onProtect, onDemo }: Props) {
  return (
    <section id="top" className="relative mx-auto max-w-7xl px-4 pb-10 pt-14 sm:px-6 sm:pt-20">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        {/* Copy */}
        <div>
          <motion.span
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="pill mb-6"
          >
            <Sparkles className="h-3.5 w-3.5 text-state-scan" aria-hidden="true" />
            CLOAK_PROTOCOL // ACTIVE
          </motion.span>

          <motion.h1
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.05 }}
            className="text-4xl font-semibold leading-[1.05] tracking-tight text-cloak-ink sm:text-5xl lg:text-6xl"
          >
            Your Screenshots.
            <br />
            Your{' '}
            <span className="relative inline-block">
              Secrets.
              <svg
                className="absolute -bottom-2 left-0 h-3 w-full"
                viewBox="0 0 200 12"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path
                  d="M2,8 C40,2 70,10 100,6 C130,2 160,10 198,5"
                  fill="none"
                  stroke="#06B6D4"
                  strokeWidth="3"
                  strokeLinecap="round"
                  opacity="0.55"
                >
                  <animate
                    attributeName="d"
                    dur="6s"
                    repeatCount="indefinite"
                    values="
                      M2,8 C40,2 70,10 100,6 C130,2 160,10 198,5;
                      M2,6 C40,10 70,3 100,7 C130,11 160,4 198,8;
                      M2,8 C40,2 70,10 100,6 C130,2 160,10 198,5"
                  />
                </path>
              </svg>
            </span>
            <br />
            Protected.
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="mt-6 max-w-lg text-lg text-cloak-muted"
          >
            Invisible Cloak automatically detects sensitive information before you
            share your screen — then hides it under a protective liquid membrane.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="mt-6 flex flex-wrap gap-2"
          >
            {HIGHLIGHTS.map((h) => (
              <span key={h} className="pill">
                {h}
              </span>
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-8 flex flex-wrap items-center gap-3"
          >
            <button className="btn-primary" onClick={onProtect}>
              Protect a Screenshot
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
            <button className="btn-ghost" onClick={onDemo}>
              <Play className="h-4 w-4 text-state-scan" aria-hidden="true" />
              Try Demo
            </button>
          </motion.div>

          <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2">
            <span className="mono-label">ENCRYPTION: ACTIVE</span>
            <span className="mono-label">DATA_EXPOSURE: 0%</span>
            <span className="mono-label">THREAT_LEVEL: LOW</span>
          </div>
        </div>

        {/* Orb */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex justify-center lg:justify-end"
        >
          <div className="relative">
            <CloakOrb phase={phase} progress={progress} size={360} />
            <div className="pointer-events-none absolute -bottom-2 left-1/2 -translate-x-1/2">
              <span className="pill">SCAN_NODE_07</span>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
