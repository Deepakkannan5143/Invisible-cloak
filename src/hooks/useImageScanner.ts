import { useCallback, useRef, useState } from 'react'
import type {
  Detection,
  ProtectionMode,
  ScanPhase,
  ScanResult,
  SensitiveRegion,
  SensitiveType,
} from '../types/scanner'
import { scanImage } from '../lib/mockScanner'
import { loadImage, renderProtectedImage } from '../lib/imageProcessor'

export interface ScannerState {
  phase: ScanPhase
  progress: number // 0..100
  imageSrc: string | null
  imageDims: { width: number; height: number } | null
  result: ScanResult | null
  protectedSrc: string | null
  cloakProgress: number // 0..1 wave sweep progress
  error: string | null
}

const PHASE_SEQUENCE: { phase: ScanPhase; label: string; until: number }[] = [
  { phase: 'analyzing', label: 'ANALYZING PIXELS', until: 30 },
  { phase: 'identifying', label: 'IDENTIFYING PATTERNS', until: 55 },
  { phase: 'classifying', label: 'CLASSIFYING SENSITIVE DATA', until: 80 },
  { phase: 'cloaking', label: 'APPLYING CLOAK', until: 100 },
]

export function phaseLabel(phase: ScanPhase): string {
  switch (phase) {
    case 'idle':
      return 'READY TO PROTECT'
    case 'uploading':
      return 'RECEIVING IMAGE'
    case 'analyzing':
      return 'ANALYZING PIXELS'
    case 'identifying':
      return 'IDENTIFYING PATTERNS'
    case 'classifying':
      return 'CLASSIFYING SENSITIVE DATA'
    case 'cloaking':
      return 'APPLYING CLOAK'
    case 'complete':
      return 'PROTECTION COMPLETE'
  }
}

const initialState: ScannerState = {
  phase: 'idle',
  progress: 0,
  imageSrc: null,
  imageDims: null,
  result: null,
  protectedSrc: null,
  cloakProgress: 0,
  error: null,
}

interface RunOptions {
  enabledTypes: SensitiveType[]
  mode: ProtectionMode
  reducedMotion: boolean
  /** Optional exact regions (demo generator / real vision backend). */
  regions?: SensitiveRegion[]
}

export function useImageScanner() {
  const [state, setState] = useState<ScannerState>(initialState)
  const rafRef = useRef<number | null>(null)
  const timersRef = useRef<number[]>([])

  const cleanup = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    timersRef.current.forEach((t) => clearTimeout(t))
    timersRef.current = []
    rafRef.current = null
  }, [])

  const reset = useCallback(() => {
    cleanup()
    setState((s) => {
      if (s.imageSrc && s.imageSrc.startsWith('blob:')) URL.revokeObjectURL(s.imageSrc)
      return initialState
    })
  }, [cleanup])

  const run = useCallback(
    async (src: string, opts: RunOptions) => {
      cleanup()
      setState({ ...initialState, phase: 'uploading', imageSrc: src })

      let dims = { width: 1000, height: 640 }
      try {
        const img = await loadImage(src)
        dims = { width: img.width, height: img.height }
      } catch {
        // keep fallback dims
      }
      setState((s) => ({ ...s, imageDims: dims }))

      // kick off the (fast) detection compute in parallel with the animation
      const resultPromise = scanImage({
        src,
        width: dims.width,
        height: dims.height,
        enabledTypes: opts.enabledTypes,
        regions: opts.regions,
      })

      const scanDuration = opts.reducedMotion ? 600 : 2600
      const start = performance.now()

      await new Promise<void>((resolve) => {
        const tick = (now: number) => {
          const elapsed = now - start
          const progress = Math.min(100, (elapsed / scanDuration) * 100)
          const current =
            PHASE_SEQUENCE.find((p) => progress <= p.until) ??
            PHASE_SEQUENCE[PHASE_SEQUENCE.length - 1]
          setState((s) => ({ ...s, progress, phase: current.phase }))
          if (progress >= 100) {
            resolve()
            return
          }
          rafRef.current = requestAnimationFrame(tick)
        }
        rafRef.current = requestAnimationFrame(tick)
      })

      const result = await resultPromise

      // Build protected image (baked redactions) for download + after view.
      let protectedSrc: string | null = null
      try {
        protectedSrc = await renderProtectedImage(src, result.detections, opts.mode)
      } catch {
        protectedSrc = null
      }

      // Cloak wave sweep animation over the detections.
      const cloakDuration = opts.reducedMotion ? 400 : 1800
      const cloakStart = performance.now()
      const protectedDetections: Detection[] = result.detections.map((d) => ({
        ...d,
      }))

      await new Promise<void>((resolve) => {
        const tick = (now: number) => {
          const elapsed = now - cloakStart
          const cp = Math.min(1, elapsed / cloakDuration)
          // mark detections protected as the wave passes their center
          protectedDetections.forEach((d) => {
            const center = d.boundingBox.x + d.boundingBox.width / 2
            if (cp >= center) d.protected = true
          })
          setState((s) => ({
            ...s,
            cloakProgress: cp,
            result: s.result
              ? { ...s.result, detections: protectedDetections.map((d) => ({ ...d })) }
              : { ...result, detections: protectedDetections.map((d) => ({ ...d })) },
          }))
          if (cp >= 1) {
            resolve()
            return
          }
          rafRef.current = requestAnimationFrame(tick)
        }
        // seed result so overlay can render during the sweep
        setState((s) => ({ ...s, result: { ...result }, protectedSrc }))
        rafRef.current = requestAnimationFrame(tick)
      })

      const finalDetections = protectedDetections.map((d) => ({ ...d, protected: true }))
      setState((s) => ({
        ...s,
        phase: 'complete',
        progress: 100,
        cloakProgress: 1,
        protectedSrc,
        result: { ...result, detections: finalDetections },
      }))
    },
    [cleanup],
  )

  return { state, run, reset }
}
