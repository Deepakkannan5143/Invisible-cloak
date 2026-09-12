import type {
  Detection,
  ScanImageInput,
  ScanResult,
  ScannerEngine,
  SensitiveRegion,
  SensitiveType,
  Severity,
} from '../types/scanner'
import { TYPE_META } from './typeMeta'

// ---------------------------------------------------------------------------
// Mock scanning engine.
//
// This simulates a privacy-detection backend. It returns realistic, plausible
// detections with normalized bounding boxes so the UI can render redaction
// overlays over any uploaded image. Swap `MockScanner` for a real implementation
// of `ScannerEngine` to connect to an actual detection service.
// ---------------------------------------------------------------------------

const SEVERITY_WEIGHT: Record<Severity, number> = {
  low: 4,
  medium: 8,
  high: 14,
  critical: 20,
}

function rid(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 8).toUpperCase()}`
}

function scanId(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `IC-${y}-${m}${d}`
}

function maskedFor(type: SensitiveType): string {
  switch (type) {
    case 'AADHAAR':
      return 'XXXX XXXX ' + (4000 + Math.floor(Math.random() * 5999))
    case 'CREDIT_CARD':
    case 'DEBIT_CARD':
      return 'XXXX XXXX XXXX ' + (1000 + Math.floor(Math.random() * 8999))
    case 'API_KEY':
      return 'sk-••••••••••••' + Math.random().toString(36).slice(2, 6)
    case 'PASSWORD':
      return '••••••••••'
    case 'EMAIL': {
      const names = ['a', 'user', 'dev', 'j.doe', 'team']
      return names[Math.floor(Math.random() * names.length)] + '•••@•••.com'
    }
    case 'PHONE':
      return '+91 •••••' + (10000 + Math.floor(Math.random() * 89999))
    case 'IP_ADDRESS':
      return '•••.•••.•.' + Math.floor(Math.random() * 255)
    case 'JWT_TOKEN':
      return 'eyJ••••.••••••.••••'
    case 'ACCESS_TOKEN':
      return 'ghp_••••••••••••'
    case 'EMPLOYEE_ID':
      return 'EMP-••••'
    case 'ADDRESS':
      return '••• •••••• Street, •••'
    case 'CUSTOM':
      return '••••••••'
  }
}

// Plausible detection templates. Bounding boxes are normalized (0..1) and
// laid out so they read like content on a real screenshot.
interface Template {
  type: SensitiveType
  box: { x: number; y: number; width: number; height: number }
  confidence: number
}

const TEMPLATES: Template[] = [
  { type: 'AADHAAR', box: { x: 0.08, y: 0.16, width: 0.34, height: 0.055 }, confidence: 98.7 },
  { type: 'CREDIT_CARD', box: { x: 0.52, y: 0.24, width: 0.38, height: 0.06 }, confidence: 97.4 },
  { type: 'API_KEY', box: { x: 0.1, y: 0.42, width: 0.5, height: 0.05 }, confidence: 96.1 },
  { type: 'API_KEY', box: { x: 0.1, y: 0.5, width: 0.44, height: 0.05 }, confidence: 94.8 },
  { type: 'PASSWORD', box: { x: 0.58, y: 0.5, width: 0.3, height: 0.05 }, confidence: 95.9 },
  { type: 'EMAIL', box: { x: 0.09, y: 0.66, width: 0.32, height: 0.05 }, confidence: 99.2 },
  { type: 'EMAIL', box: { x: 0.55, y: 0.66, width: 0.3, height: 0.05 }, confidence: 98.4 },
  { type: 'PHONE', box: { x: 0.1, y: 0.8, width: 0.26, height: 0.05 }, confidence: 97.0 },
  { type: 'ADDRESS', box: { x: 0.5, y: 0.8, width: 0.4, height: 0.06 }, confidence: 92.3 },
]

function buildDetections(enabled: SensitiveType[]): Detection[] {
  const active = TEMPLATES.filter((t) => enabled.includes(t.type))
  return active.map((t) => ({
    id: rid('DET'),
    detectedType: t.type,
    boundingBox: t.box,
    confidence: Math.round(t.confidence * 10) / 10,
    maskedValue: maskedFor(t.type),
    severity: TYPE_META[t.type].severity,
    protected: false,
  }))
}

/**
 * Masks a concrete sensitive value, preserving its shape so the report reads
 * naturally (e.g. keeps the last 4 digits of a card, the email host initial).
 * The full raw value is never surfaced.
 */
function maskText(type: SensitiveType, raw: string): string {
  const digits = raw.replace(/\D/g, '')
  switch (type) {
    case 'AADHAAR':
      return 'XXXX XXXX ' + (digits.slice(-4) || 'XXXX')
    case 'CREDIT_CARD':
    case 'DEBIT_CARD':
      return 'XXXX XXXX XXXX ' + (digits.slice(-4) || 'XXXX')
    case 'PHONE':
      return '+•• •••••' + (digits.slice(-5) || '•••••')
    case 'API_KEY':
      return raw.slice(0, 3) + '-••••••••••••'
    case 'ACCESS_TOKEN':
      return raw.slice(0, 4) + '••••••••••••'
    case 'JWT_TOKEN':
      return 'eyJ••••.••••••.••••'
    case 'PASSWORD':
      return '•'.repeat(Math.min(12, Math.max(8, raw.length)))
    case 'EMAIL': {
      const [user = '', host = ''] = raw.split('@')
      return (user.slice(0, 1) || '•') + '•••@' + (host.slice(0, 1) || '•') + '••.•••'
    }
    case 'ADDRESS':
      return (raw.split(/[, ]/)[0] || '•••') + ' •••••••, •••'
    default:
      return maskedFor(type)
  }
}

/** Builds detections directly from exact regions (demo / real backend). */
function buildFromRegions(
  regions: SensitiveRegion[],
  enabled: SensitiveType[],
): Detection[] {
  return regions
    .filter((r) => enabled.includes(r.detectedType))
    .map((r) => ({
      id: rid('DET'),
      detectedType: r.detectedType,
      boundingBox: r.boundingBox,
      confidence: Math.round(r.confidence * 10) / 10,
      maskedValue: maskText(r.detectedType, r.text),
      severity: TYPE_META[r.detectedType].severity,
      protected: false,
    }))
}

function computeScore(detections: Detection[]): number {
  if (detections.length === 0) return 100
  // Every detection that gets cloaked keeps the score high; the model reports a
  // confident residual-risk figure. With all items protected we land in the high 90s.
  const totalRisk = detections.reduce(
    (sum, d) => sum + SEVERITY_WEIGHT[d.severity],
    0,
  )
  const residual = Math.max(2, Math.round(totalRisk * 0.06))
  return Math.min(99, 100 - residual)
}

import { RealScanner } from './realScanner'

export class MockScanner implements ScannerEngine {
  async scanImage(input: ScanImageInput): Promise<ScanResult> {
    // Prefer exact regions (from the demo generator or a real vision backend);
    // fall back to heuristic templates for arbitrary uploaded images.
    const detections =
      input.regions && input.regions.length > 0
        ? buildFromRegions(input.regions, input.enabledTypes)
        : buildDetections(input.enabledTypes)
    // simulate compute latency (not the animation timing — that's UI driven)
    const latencyMs = 120 + Math.floor(Math.random() * 80)
    return {
      scanId: scanId(),
      detections,
      privacyScore: computeScore(detections),
      latencyMs,
      timestamp: Date.now(),
    }
  }
}

export const scanner: ScannerEngine = new MockScanner()

// Select the active engine from Vite env. MockScanner stays the default so the
// app and Demo Mode work with no backend running; set VITE_USE_REAL_BACKEND=true
// (and optionally VITE_CLOAK_API_URL) to route scans to the FastAPI backend.
const env = (import.meta as { env?: Record<string, string> }).env ?? {}
const useReal = String(env.VITE_USE_REAL_BACKEND ?? '').toLowerCase() === 'true'
export const activeScanner: ScannerEngine = useReal
  ? new RealScanner(env.VITE_CLOAK_API_URL)
  : scanner

/**
 * Convenience wrapper used by hooks/components.
 *
 * Delegates to the engine chosen above (Mock by default, Real when
 * VITE_USE_REAL_BACKEND=true). Existing imports of `scanImage` from
 * './mockScanner' continue to work unchanged.
 */
export function scanImage(input: ScanImageInput): Promise<ScanResult> {
  return activeScanner.scanImage(input)
}
