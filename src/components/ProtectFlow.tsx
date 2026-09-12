import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useState,
} from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Play } from 'lucide-react'
import type { ProtectionMode, SensitiveRegion, SensitiveType } from '../types/scanner'
import { DEFAULT_ENABLED } from '../lib/typeMeta'
import { downloadDataUrl, dataUrlToBlob } from '../lib/imageProcessor'
import { generateSampleScreenshot } from '../lib/sampleScreenshot'
import { useImageScanner } from '../hooks/useImageScanner'
import { useReducedMotion } from '../hooks/useReducedMotion'
import { useToast } from '../hooks/useToast'
import UploadZone from './UploadZone'
import Scanner from './Scanner'
import ScreenshotPreview from './ScreenshotPreview'
import ProtectionReport from './ProtectionReport'
import SecurityScore from './SecurityScore'
import ScanTimeline from './ScanTimeline'
import BeforeAfterSlider from './BeforeAfterSlider'
import ProtectionSettings from './ProtectionSettings'
import ShareResult from './ShareResult'

export interface ProtectFlowHandle {
  runDemo: () => void
}

interface Props {
  onPhaseChange: (phase: import('../types/scanner').ScanPhase, progress: number) => void
}

const ProtectFlow = forwardRef<ProtectFlowHandle, Props>(function ProtectFlow(
  { onPhaseChange },
  ref,
) {
  const { state, run, reset } = useImageScanner()
  const reduced = useReducedMotion()
  const { push } = useToast()

  const [enabled, setEnabled] = useState<Set<SensitiveType>>(
    () => new Set(DEFAULT_ENABLED),
  )
  const [mode, setMode] = useState<ProtectionMode>('frosted')
  const [customPatterns, setCustomPatterns] = useState<string[]>([])

  // bubble phase/progress up to hero orb
  useEffect(() => {
    onPhaseChange(state.phase, state.progress)
  }, [state.phase, state.progress, onPhaseChange])

  const startScan = useCallback(
    (src: string, regions?: SensitiveRegion[]) => {
      const enabledTypes = [...enabled]
      run(src, { enabledTypes, mode, reducedMotion: reduced, regions, customPatterns }).catch(() => {
        push({ kind: 'error', title: 'Scan failed', description: 'Please try another image.' })
      })
    },
    [enabled, mode, reduced, run, push, customPatterns],
  )

  const handleImage = useCallback(
    (src: string) => {
      push({ kind: 'info', title: 'Screenshot received', description: 'Starting privacy scan…' })
      startScan(src)
    },
    [push, startScan],
  )

  const runDemo = useCallback(() => {
    const sample = generateSampleScreenshot()
    if (!sample.src) {
      push({ kind: 'error', title: 'Demo unavailable', description: 'Canvas not supported.' })
      return
    }
    push({ kind: 'info', title: 'Demo started', description: 'Loading a sample screenshot…' })
    // The demo generator knows the exact location of every sensitive value, so
    // pass those regions through — redaction then aligns perfectly.
    startScan(sample.src, sample.regions)
  }, [push, startScan])

  // expose runDemo to parent
  useImperativeHandle(ref, () => ({ runDemo }), [runDemo])

  const detections = state.result?.detections ?? []
  const total = detections.length
  const protectedCount = detections.filter((d) => d.protected).length
  const exposed = total - protectedCount
  const isComplete = state.phase === 'complete'
  const isBusy =
    state.phase !== 'idle' && state.phase !== 'complete' && state.phase !== 'uploading'
  const hasImage = state.imageSrc != null && state.phase !== 'idle'

  const handleDownload = useCallback(() => {
    if (!state.protectedSrc) return
    downloadDataUrl(state.protectedSrc, 'invisible-cloak-protected.png')
    push({
      kind: 'success',
      title: 'Protected screenshot generated successfully.',
      description: 'Download started.',
    })
  }, [state.protectedSrc, push])

  const handleCopy = useCallback(async () => {
    if (!state.protectedSrc) return
    try {
      const blob = await dataUrlToBlob(state.protectedSrc)
      if (navigator.clipboard && 'write' in navigator.clipboard && window.ClipboardItem) {
        await navigator.clipboard.write([new window.ClipboardItem({ [blob.type]: blob })])
        push({ kind: 'success', title: 'Copied to clipboard', description: 'Protected image ready to paste.' })
      } else {
        throw new Error('unsupported')
      }
    } catch {
      push({ kind: 'warn', title: 'Copy not supported', description: 'Use download instead.' })
    }
  }, [state.protectedSrc, push])

  const handleReset = useCallback(() => {
    reset()
    push({ kind: 'info', title: 'Ready for another screenshot' })
  }, [reset, push])

  const toggleType = useCallback((type: SensitiveType) => {
    setEnabled((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  const addPattern = useCallback(
    (p: string) => {
      setCustomPatterns((prev) => (prev.includes(p) ? prev : [...prev, p]))
      push({ kind: 'success', title: 'Custom pattern added', description: p })
    },
    [push],
  )

  return (
    <section id="protect" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-16 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="mono-label">// CLOAK_INTERFACE</span>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-cloak-ink sm:text-4xl">
          Protect a Screenshot
        </h2>
        <p className="mono-label mt-3 normal-case tracking-normal text-base text-cloak-muted">
          Drop an image. Cloak detects the rest.
        </p>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Left: upload / preview */}
        <div className="space-y-6">
          <AnimatePresence mode="wait">
            {!hasImage ? (
              <motion.div
                key="upload"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <UploadZone
                  onImage={handleImage}
                  onError={(m) => push({ kind: 'error', title: 'Upload error', description: m })}
                  onDemo={runDemo}
                />
              </motion.div>
            ) : (
              <motion.div
                key="preview"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-6"
              >
                <ScreenshotPreview
                  src={state.imageSrc!}
                  phase={state.phase}
                  progress={state.progress}
                  cloakProgress={state.cloakProgress}
                  detections={detections}
                  mode={mode}
                />

                {isComplete && state.protectedSrc && (
                  <BeforeAfterSlider
                    beforeSrc={state.imageSrc!}
                    afterSrc={state.protectedSrc}
                  />
                )}

                {isComplete && state.protectedSrc && (
                  <ShareResult
                    protectedSrc={state.protectedSrc}
                    itemsCloaked={protectedCount}
                    onDownload={handleDownload}
                    onCopy={handleCopy}
                    onReset={handleReset}
                  />
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Right: live panels */}
        <div className="space-y-6">
          {isBusy && <Scanner phase={state.phase} progress={state.progress} />}

          {(isBusy || isComplete) && (
            <SecurityScore
              score={isComplete ? (state.result?.privacyScore ?? null) : null}
              phase={state.phase}
              detected={total}
              protectedCount={protectedCount}
              exposed={exposed}
            />
          )}

          {isComplete && state.result && <ProtectionReport result={state.result} />}

          {hasImage && <ScanTimeline phase={state.phase} />}

          {!hasImage && (
            <>
              <div className="glass-panel rounded-xl2 p-6 text-center">
                <p className="text-sm text-cloak-muted">
                  Upload a screenshot or run the demo to watch the cloak in action.
                </p>
                <button className="btn-ghost mt-4" onClick={runDemo}>
                  <Play className="h-4 w-4 text-state-scan" /> Try Demo
                </button>
              </div>
              <ProtectionSettings
                enabled={enabled}
                onToggle={toggleType}
                mode={mode}
                onModeChange={setMode}
                customPatterns={customPatterns}
                onAddPattern={addPattern}
              />
            </>
          )}

          {hasImage && (
            <ProtectionSettings
              enabled={enabled}
              onToggle={toggleType}
              mode={mode}
              onModeChange={setMode}
              customPatterns={customPatterns}
              onAddPattern={addPattern}
            />
          )}
        </div>
      </div>
    </section>
  )
})

export default ProtectFlow
