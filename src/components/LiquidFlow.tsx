import { memo } from 'react'
import { useReducedMotion } from '../hooks/useReducedMotion'

/**
 * Reusable localized liquid-flow SVG. Renders slow translucent waves that can
 * be dropped inside any container (e.g. behind the upload zone or scanner) to
 * create the "protective liquid membrane" motif.
 */
function LiquidFlow({
  className = '',
  tint = 'rgba(6,182,212,0.14)',
  speed = 12,
}: {
  className?: string
  tint?: string
  speed?: number
}) {
  const reduced = useReducedMotion()
  const gid = `lf-${Math.round(speed)}`

  return (
    <svg
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
      viewBox="0 0 400 200"
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={tint} />
          <stop offset="60%" stopColor="rgba(148,163,184,0.10)" />
          <stop offset="100%" stopColor={tint} />
        </linearGradient>
      </defs>
      <g style={{ filter: 'blur(1px)' }}>
        <path fill={`url(#${gid})`}>
          {!reduced && (
            <animate
              attributeName="d"
              dur={`${speed}s`}
              repeatCount="indefinite"
              values="
                M0,120 C100,90 160,150 240,120 C320,95 360,140 400,120 L400,200 L0,200 Z;
                M0,130 C100,160 160,100 240,135 C320,160 360,110 400,130 L400,200 L0,200 Z;
                M0,120 C100,90 160,150 240,120 C320,95 360,140 400,120 L400,200 L0,200 Z"
            />
          )}
          {reduced && (
            <animate attributeName="opacity" values="1;1" dur="1s" />
          )}
          <animateTransform
            attributeName="transform"
            type="translate"
            values="0 0"
            dur="1s"
          />
        </path>
      </g>
    </svg>
  )
}

export default memo(LiquidFlow)
