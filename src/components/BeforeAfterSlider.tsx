import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { MoveHorizontal } from 'lucide-react'

interface Props {
  beforeSrc: string
  afterSrc: string
}

/** Interactive before/after comparison slider (mouse + touch + keyboard). */
export default function BeforeAfterSlider({ beforeSrc, afterSrc }: Props) {
  const [pos, setPos] = useState(50)
  const [ripple, setRipple] = useState(false)
  const [containerWidth, setContainerWidth] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const dragging = useRef(false)

  // Track container width so the clipped BEFORE image can span the full width
  // and stay perfectly aligned with the AFTER image behind it.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const update = () => setContainerWidth(el.clientWidth)
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const updateFromClientX = useCallback((clientX: number) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const p = ((clientX - rect.left) / rect.width) * 100
    setPos(Math.max(0, Math.min(100, p)))
  }, [])

  const onPointerDown = (e: React.PointerEvent) => {
    dragging.current = true
    setRipple(true)
    updateFromClientX(e.clientX)
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragging.current) return
    updateFromClientX(e.clientX)
  }
  const onPointerUp = () => {
    dragging.current = false
    setTimeout(() => setRipple(false), 400)
  }

  return (
    <div className="glass-panel rounded-xl2 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="mono-label">BEFORE / AFTER CLOAK</span>
        <span className="mono-label text-[10px]">DRAG TO COMPARE</span>
      </div>
      <div
        ref={containerRef}
        className="relative aspect-[16/10] w-full touch-none select-none overflow-hidden rounded-xl2 border border-cloak-softgray"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        {/* after (full) */}
        <img
          src={afterSrc}
          alt="Protected screenshot with sensitive data cloaked"
          className="absolute inset-0 h-full w-full object-cover"
          draggable={false}
        />
        <span className="absolute right-3 top-3 rounded-full bg-state-safe px-2 py-1 font-mono text-[10px] font-medium text-white">
          AFTER CLOAK
        </span>

        {/* before (clipped) */}
        <div
          className="absolute inset-0 overflow-hidden"
          style={{ width: `${pos}%` }}
        >
          <img
            src={beforeSrc}
            alt="Original screenshot before protection"
            className="absolute inset-0 h-full object-cover"
            style={{ width: containerWidth || '100%', maxWidth: 'none' }}
            draggable={false}
          />
          <span className="absolute left-3 top-3 rounded-full bg-cloak-ink px-2 py-1 font-mono text-[10px] font-medium text-white">
            BEFORE
          </span>
        </div>

        {/* divider + handle */}
        <div
          className="absolute inset-y-0 z-10 w-0.5 bg-white shadow-[0_0_12px_rgba(6,182,212,0.6)]"
          style={{ left: `${pos}%` }}
        >
          {ripple && (
            <span className="absolute left-1/2 top-1/2 h-16 w-16 -translate-x-1/2 -translate-y-1/2 animate-ping rounded-full bg-state-scan/20" />
          )}
          <button
            type="button"
            role="slider"
            aria-label="Comparison slider position"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(pos)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowLeft') setPos((p) => Math.max(0, p - 4))
              if (e.key === 'ArrowRight') setPos((p) => Math.min(100, p + 4))
            }}
            className="absolute left-1/2 top-1/2 grid h-10 w-10 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full border border-cloak-softgray bg-white text-cloak-ink shadow-glass focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan"
          >
            <motion.span whileTap={{ scale: 0.9 }}>
              <MoveHorizontal className="h-4 w-4 text-state-scan" />
            </motion.span>
          </button>
        </div>
      </div>
    </div>
  )
}
