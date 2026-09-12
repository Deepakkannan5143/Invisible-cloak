import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'

const STATS = [
  { value: 12, suffix: '+', label: 'Data types detected' },
  { value: 98, suffix: '%', label: 'Detection confidence' },
  { value: 142, suffix: 'ms', label: 'Avg scan latency' },
  { value: 0, suffix: '%', label: 'Data leaves device' },
]

function useCountUp(target: number, active: boolean) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    if (!active) return
    let raf = 0
    const start = performance.now()
    const dur = 1200
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur)
      const eased = 1 - Math.pow(1 - t, 3)
      setVal(Math.round(eased * target))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, active])
  return val
}

function StatItem({
  value,
  suffix,
  label,
  active,
}: {
  value: number
  suffix: string
  label: string
  active: boolean
}) {
  const n = useCountUp(value, active)
  return (
    <div className="text-center">
      <div className="text-4xl font-semibold text-cloak-ink sm:text-5xl">
        {n}
        <span className="text-state-scan">{suffix}</span>
      </div>
      <div className="mono-label mt-2 text-[10px]">{label}</div>
    </div>
  )
}

/** Animated statistics band. */
export default function Statistics() {
  const [active, setActive] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Activate immediately if the band is already within the viewport on mount.
    const rect = el.getBoundingClientRect()
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      setActive(true)
      return
    }

    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setActive(true)
          obs.disconnect()
        }
      },
      { threshold: 0.15 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6">
      <motion.div
        ref={ref}
        className="glass-panel grid grid-cols-2 gap-8 rounded-xl3 p-10 lg:grid-cols-4"
      >
        {STATS.map((s) => (
          <StatItem key={s.label} {...s} active={active} />
        ))}
      </motion.div>
    </section>
  )
}
