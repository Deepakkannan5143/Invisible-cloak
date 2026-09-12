import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import type { Detection, ProtectionMode, ScanPhase } from '../types/scanner'
import { TYPE_META, SEVERITY_COLOR } from '../lib/typeMeta'

interface Props {
  detections: Detection[]
  phase: ScanPhase
  cloakProgress: number
  mode: ProtectionMode
  showBoxes: boolean
}

/**
 * Renders animated bounding boxes + redaction regions over a screenshot.
 * Positioned absolutely using the detection's normalized bounding box.
 * As `cloakProgress` (0..1) sweeps left→right, boxes flip to a protected badge
 * and the underlying region gets the chosen redaction effect.
 */
export default function DetectionOverlay({
  detections,
  phase,
  cloakProgress,
  mode,
  showBoxes,
}: Props) {
  return (
    <div className="pointer-events-none absolute inset-0">
      {detections.map((d, i) => {
        const meta = TYPE_META[d.detectedType]
        const color = SEVERITY_COLOR[d.severity]
        const isProtected = d.protected
        const style: React.CSSProperties = {
          left: `${d.boundingBox.x * 100}%`,
          top: `${d.boundingBox.y * 100}%`,
          width: `${d.boundingBox.width * 100}%`,
          height: `${d.boundingBox.height * 100}%`,
        }

        return (
          <motion.div
            key={d.id}
            className="absolute"
            style={style}
            initial={{ opacity: 0 }}
            animate={{ opacity: showBoxes || isProtected ? 1 : 0 }}
            transition={{ delay: i * 0.06, duration: 0.3 }}
          >
            {/* redaction region */}
            <RedactionRegion active={isProtected} mode={mode} />

            {/* bounding box */}
            {!isProtected ? (
              <div
                className="absolute inset-0 rounded-md"
                style={{
                  border: `1.5px dashed ${color}`,
                  boxShadow: `0 0 0 3px ${color}14`,
                }}
              >
                <span
                  className="animate-pulse-soft absolute -top-6 left-0 whitespace-nowrap rounded-md px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide text-white"
                  style={{ backgroundColor: color }}
                >
                  {meta.label.toUpperCase()} • {d.confidence.toFixed(1)}%
                </span>
              </div>
            ) : (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: 'spring', stiffness: 320, damping: 22 }}
                className="absolute inset-0 rounded-md ring-1 ring-state-safe/70"
              >
                <span className="absolute -top-6 left-0 inline-flex items-center gap-1 whitespace-nowrap rounded-md bg-state-safe px-1.5 py-0.5 font-mono text-[10px] font-medium text-white">
                  <Check className="h-3 w-3" /> CLOAKED
                </span>
              </motion.div>
            )}
          </motion.div>
        )
      })}

      {/* cloak wave membrane sweeping across */}
      {phase === 'cloaking' && cloakProgress < 1 && (
        <div
          className="absolute inset-y-0 w-24"
          style={{ left: `calc(${cloakProgress * 100}% - 3rem)` }}
        >
          <div className="h-full w-full bg-gradient-to-r from-transparent via-state-scan/25 to-transparent backdrop-blur-[2px]" />
          <div className="absolute inset-y-0 right-0 w-[2px] bg-state-scan/70 shadow-[0_0_20px_rgba(6,182,212,0.7)]" />
        </div>
      )}
    </div>
  )
}

function RedactionRegion({ active, mode }: { active: boolean; mode: ProtectionMode }) {
  if (!active) return null

  // Each mode obscures the pixels *behind* the overlay (the screenshot value)
  // using backdrop-filter, so the real value stays in the image but is
  // unreadable. A strong blur radius is used so characters cannot be recovered.
  const base = 'absolute inset-0 rounded-md overflow-hidden'
  if (mode === 'redact') {
    return (
      <div
        className={base}
        style={{
          backdropFilter: 'blur(9px)',
          WebkitBackdropFilter: 'blur(9px)',
          background: 'rgba(17,24,39,0.82)',
        }}
      />
    )
  }
  if (mode === 'pixelate') {
    return (
      <div
        className={base}
        style={{
          backdropFilter: 'blur(6px) contrast(0.85)',
          WebkitBackdropFilter: 'blur(6px) contrast(0.85)',
          backgroundImage:
            'repeating-conic-gradient(rgba(148,163,184,0.55) 0% 25%, rgba(203,213,225,0.55) 0% 50%)',
          backgroundSize: '9px 9px',
        }}
      />
    )
  }
  if (mode === 'frosted') {
    return (
      <div
        className={base}
        style={{
          background: 'rgba(255,255,255,0.5)',
          backdropFilter: 'blur(10px) saturate(1.1)',
          WebkitBackdropFilter: 'blur(10px) saturate(1.1)',
          border: '1px solid rgba(255,255,255,0.7)',
        }}
      />
    )
  }
  // blur
  return (
    <div
      className={base}
      style={{
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        background: 'rgba(226,232,240,0.28)',
      }}
    />
  )
}
