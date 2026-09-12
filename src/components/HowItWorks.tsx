import { motion } from 'framer-motion'
import { EyeOff, ScanSearch, Share2 } from 'lucide-react'

const CARDS = [
  {
    n: '01',
    title: 'Detect',
    icon: ScanSearch,
    body: 'AI identifies sensitive information using pattern recognition and intelligent detection across the whole image.',
  },
  {
    n: '02',
    title: 'Cloak',
    icon: EyeOff,
    body: 'Detected information is automatically blurred, masked, or redacted under a flowing protective membrane.',
  },
  {
    n: '03',
    title: 'Share',
    icon: Share2,
    body: 'Only the protected version leaves your device or workflow. The originals never surface.',
  },
]

const FLOW = ['SCREENSHOT', 'DETECT', 'CLOAK', 'SAFE']

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="mono-label">// HOW_IT_WORKS</span>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-cloak-ink sm:text-4xl">
          Privacy, before exposure.
        </h2>
        <p className="mt-3 text-cloak-muted">
          Three steps stand between your screenshot and an accidental leak.
        </p>
      </div>

      <div className="relative mt-12 grid gap-6 md:grid-cols-3">
        {CARDS.map((c, i) => (
          <motion.article
            key={c.n}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-80px' }}
            transition={{ delay: i * 0.12 }}
            className="group relative overflow-hidden rounded-xl2 border border-cloak-softgray bg-white/70 p-6 shadow-soft transition-all hover:-translate-y-1 hover:shadow-glass"
          >
            <span className="absolute right-4 top-4 font-mono text-4xl font-semibold text-cloak-lightgray transition-colors group-hover:text-state-scan/20">
              {c.n}
            </span>
            <span className="grid h-12 w-12 place-items-center rounded-xl2 bg-cloak-lightgray text-cloak-ink transition-colors group-hover:bg-state-scan/10 group-hover:text-state-scan">
              <c.icon className="h-6 w-6" strokeWidth={1.6} aria-hidden="true" />
            </span>
            <h3 className="mt-4 text-lg font-semibold text-cloak-ink">{c.title}</h3>
            <p className="mt-2 text-sm text-cloak-muted">{c.body}</p>
          </motion.article>
        ))}
      </div>

      {/* animated flow */}
      <div className="mt-10 flex flex-wrap items-center justify-center gap-2 sm:gap-4">
        {FLOW.map((step, i) => (
          <div key={step} className="flex items-center gap-2 sm:gap-4">
            <span
              className={`rounded-full border px-3 py-1.5 font-mono text-[11px] font-medium tracking-wide ${
                step === 'SAFE'
                  ? 'border-state-safe/40 bg-state-safe/10 text-state-safe'
                  : 'border-cloak-softgray bg-white/70 text-cloak-muted'
              }`}
            >
              {step}
            </span>
            {i < FLOW.length - 1 && (
              <svg width="36" height="10" viewBox="0 0 36 10" aria-hidden="true">
                <line
                  x1="0"
                  y1="5"
                  x2="30"
                  y2="5"
                  stroke="#9CA3AF"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                >
                  <animate
                    attributeName="stroke-dashoffset"
                    values="14;0"
                    dur="1s"
                    repeatCount="indefinite"
                  />
                </line>
                <path d="M30,1 L36,5 L30,9" fill="none" stroke="#9CA3AF" strokeWidth="1.5" />
              </svg>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
