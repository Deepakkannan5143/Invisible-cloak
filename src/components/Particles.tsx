import { useEffect, useRef } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

interface Node {
  x: number
  y: number
  vx: number
  vy: number
  r: number
  a: number
}

/**
 * Canvas particle field: tiny slow-drifting dots that occasionally connect with
 * thin lines. Uses a single canvas + requestAnimationFrame for performance.
 */
export default function Particles({ count = 42 }: { count?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const reduced = useReducedMotion()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let nodes: Node[] = []
    let raf = 0

    const resize = () => {
      width = canvas.clientWidth
      height = canvas.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const seed = () => {
      const n = reduced ? Math.min(count, 16) : count
      nodes = Array.from({ length: n }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        vx: (Math.random() - 0.5) * 0.15,
        vy: (Math.random() - 0.5) * 0.15,
        r: 0.6 + Math.random() * 1.6,
        a: 0.2 + Math.random() * 0.5,
      }))
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      // connections
      for (let i = 0; i < nodes.length; i++) {
        const p = nodes[i]
        for (let j = i + 1; j < nodes.length; j++) {
          const q = nodes[j]
          const dx = p.x - q.x
          const dy = p.y - q.y
          const dist = Math.hypot(dx, dy)
          if (dist < 130) {
            ctx.strokeStyle = `rgba(148,163,184,${(1 - dist / 130) * 0.12})`
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(p.x, p.y)
            ctx.lineTo(q.x, q.y)
            ctx.stroke()
          }
        }
      }
      // dots
      for (const p of nodes) {
        ctx.fillStyle = `rgba(100,116,139,${p.a})`
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fill()
      }
    }

    const step = () => {
      for (const p of nodes) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < -20) p.x = width + 20
        if (p.x > width + 20) p.x = -20
        if (p.y < -20) p.y = height + 20
        if (p.y > height + 20) p.y = -20
      }
      draw()
      raf = requestAnimationFrame(step)
    }

    resize()
    seed()

    if (reduced) {
      draw()
    } else {
      raf = requestAnimationFrame(step)
    }

    const onResize = () => {
      resize()
      seed()
      if (reduced) draw()
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
    }
  }, [count, reduced])

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  )
}
