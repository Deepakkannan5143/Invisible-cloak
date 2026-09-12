import { useEffect, useState } from 'react'

/**
 * Drives a continuous 0..1 phase value using requestAnimationFrame, used for
 * ambient wave / ring animations. Pauses automatically under reduced motion.
 */
export function useCloakAnimation(speed = 1, enabled = true): number {
  const [phase, setPhase] = useState(0)

  useEffect(() => {
    if (!enabled) return
    let raf = 0
    let mounted = true
    const start = performance.now()
    const loop = (now: number) => {
      if (!mounted) return
      const t = ((now - start) / 1000) * speed
      setPhase(t % 1000)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      mounted = false
      cancelAnimationFrame(raf)
    }
  }, [speed, enabled])

  return phase
}
