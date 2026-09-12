import { motion } from 'framer-motion'
import type { Detection, ProtectionMode, ScanPhase } from '../types/scanner'
import DetectionOverlay from './DetectionOverlay'
import { phaseLabel } from '../hooks/useImageScanner'

interface Props {
  src: string
  phase: ScanPhase
  progress: number
  cloakProgress: number
  detections: Detection[]
  mode: ProtectionMode
}

/**
 * Large screenshot preview with the scanning beam (top→bottom) during analysis
 * and the detection/redaction overlay. This is the visual centrepiece.
 */
export default function ScreenshotPreview({
  src,
  phase,
  progress,
  cloakProgress,
  detections,
  mode,
}: Props) {
  const scanning =
    phase === 'analyzing' || phase === 'identifying' || phase === 'classifying'
  const showBoxes = scanning || phase === 'cloaking'

  return (
    <div className="relative overflow-hidden rounded-xl2 border border-cloak-softgray bg-cloak-lightgray shadow-glass">
      {/* top status bar */}
      <div className="flex items-center justify-between border-b border-cloak-softgray/70 bg-white/70 px-4 py-2 backdrop-blur">
        <span className="mono-label">SCREENSHOT_PREVIEW</span>
        <span
          className="led-text text-[11px]"
          style={{
            color:
              phase === 'complete'
                ? '#10B981'
                : phase === 'idle'
                  ? '#9CA3AF'
                  : '#06B6D4',
          }}
        >
          {phaseLabel(phase)}
        </span>
      </div>

      <div className="relative">
        <img
          src={src}
          alt="Uploaded screenshot being analyzed for sensitive information"
          className="block w-full select-none"
          draggable={false}
        />

        {/* scanning beam */}
        {scanning && (
          <motion.div
            className="pointer-events-none absolute inset-x-0 h-24"
            initial={{ top: '-10%' }}
            animate={{ top: ['-10%', '100%'] }}
            transition={{ duration: 2.4, ease: 'easeInOut', repeat: Infinity }}
          >
            <div className="h-full w-full bg-gradient-to-b from-transparent via-state-scan/25 to-transparent" />
            <div className="absolute inset-x-0 bottom-0 h-[2px] bg-state-scan/80 shadow-[0_0_18px_rgba(6,182,212,0.8)]" />
          </motion.div>
        )}

        {/* scanning grid tint */}
        {scanning && (
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                'linear-gradient(to right, rgba(6,182,212,0.15) 1px, transparent 1px), linear-gradient(to bottom, rgba(6,182,212,0.15) 1px, transparent 1px)',
              backgroundSize: '40px 40px',
            }}
          />
        )}

        <DetectionOverlay
          detections={detections}
          phase={phase}
          cloakProgress={cloakProgress}
          mode={mode}
          showBoxes={showBoxes}
        />

        {/* percentage badge */}
        {scanning && (
          <div className="absolute bottom-3 right-3">
            <span className="rounded-full bg-cloak-ink/85 px-3 py-1 font-mono text-xs font-semibold text-white">
              SCAN {Math.round(progress)}%
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
