import type {
  Detection,
  ScanImageInput,
  ScanResult,
  ScannerEngine,
  SensitiveType,
  Severity,
} from '../types/scanner'
import { TYPE_META } from './typeMeta'

// ---------------------------------------------------------------------------
// Real scanning engine — talks to the FastAPI backend at VITE_CLOAK_API_URL
// (default http://localhost:8000) and maps its response to the frontend's
// ScanResult contract. Implements the same `ScannerEngine` interface as the
// MockScanner, so it is a drop-in replacement (see scannerFactory.ts).
//
// Backend contract (POST /api/scan) differs from the UI's ScanResult:
//   - bbox is pixel-space [x, y, w, h]; UI wants normalized 0..1 {x,y,w,h}.
//   - confidence is 0..1; UI wants 0..100.
//   - type names are a superset; unknown types collapse to 'CUSTOM'.
// ---------------------------------------------------------------------------

const API_URL =
  (import.meta as { env?: Record<string, string> }).env?.VITE_CLOAK_API_URL ??
  'http://localhost:8000'

interface ApiDetection {
  type: string
  text: string
  confidence: number // 0..1
  severity: string
  bbox: [number, number, number, number] // pixels [x, y, w, h]
  status: string
  verification_passed: boolean
  attempts: number
}

interface ApiResponse {
  success: boolean
  processing_time_ms: number
  privacy_score: number
  summary: { total_detections: number; critical_count: number; protected_count: number }
  detections: ApiDetection[]
  protected_image: string | null
}

export interface OcrToken {
  text: string
  /** pixel-space [x, y, width, height] */
  bbox: [number, number, number, number]
}

/** Maps a backend type string onto a frontend SensitiveType. */
function toSensitiveType(t: string): SensitiveType {
  const known: SensitiveType[] = [
    'AADHAAR', 'CREDIT_CARD', 'DEBIT_CARD', 'API_KEY', 'PASSWORD', 'EMAIL',
    'PHONE', 'IP_ADDRESS', 'JWT_TOKEN', 'ACCESS_TOKEN', 'EMPLOYEE_ID',
    'ADDRESS', 'CUSTOM',
  ]
  return (known as string[]).includes(t) ? (t as SensitiveType) : 'CUSTOM'
}

function toSeverity(s: string): Severity {
  return (['low', 'medium', 'high', 'critical'].includes(s) ? s : 'medium') as Severity
}

function rid(): string {
  return 'DET-' + Math.random().toString(36).slice(2, 8).toUpperCase()
}

function scanId(): string {
  const now = new Date()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `IC-${now.getFullYear()}-${m}${d}`
}

export interface RealScanOptions {
  /** OCR tokens with pixel bboxes; enables precise spatial redaction. */
  tokens?: OcrToken[]
  /** Raw text to scan when no tokens are available. */
  text?: string
}

export class RealScanner implements ScannerEngine {
  constructor(private readonly baseUrl: string = API_URL) {}

  async scanImage(input: ScanImageInput, extra?: RealScanOptions): Promise<ScanResult> {
    const enabledTypes = input.enabledTypes.map(String)
    const body: Record<string, unknown> = {
      mode: 'frosted',
      enabled_types: enabledTypes,
      image_base64: input.src,
      image_width: input.width,
      image_height: input.height,
    }
    if (extra?.tokens) body.tokens = extra.tokens
    if (extra?.text) body.text = extra.text

    const res = await fetch(`${this.baseUrl}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`Scan API error ${res.status}`)
    const data = (await res.json()) as ApiResponse

    const W = input.width || 1
    const H = input.height || 1

    const detections: Detection[] = data.detections
      .map((d) => {
        const type = toSensitiveType(d.type)
        const [x, y, w, h] = d.bbox
        return {
          id: rid(),
          detectedType: type,
          boundingBox: {
            x: w > 0 ? x / W : 0,
            y: h > 0 ? y / H : 0,
            width: w / W,
            height: h / H,
          },
          confidence: Math.round(d.confidence * 1000) / 10, // 0..1 -> 0..100
          maskedValue: d.text,
          severity: TYPE_META[type]?.severity ?? toSeverity(d.severity),
          protected: d.status === 'protected',
        }
      })
      // keep only enabled types the UI knows how to render
      .filter((d) => input.enabledTypes.includes(d.detectedType))

    return {
      scanId: scanId(),
      detections,
      privacyScore: data.privacy_score,
      latencyMs: Math.round(data.processing_time_ms),
      timestamp: Date.now(),
    }
  }
}
