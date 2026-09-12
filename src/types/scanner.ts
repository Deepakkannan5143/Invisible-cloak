// Core domain types for the Invisible Cloak scanning engine.
// The mock engine implements these interfaces so a real backend/API
// can be dropped in later without touching UI components.

export type SensitiveType =
  | 'AADHAAR'
  | 'CREDIT_CARD'
  | 'DEBIT_CARD'
  | 'API_KEY'
  | 'PASSWORD'
  | 'EMAIL'
  | 'PHONE'
  | 'IP_ADDRESS'
  | 'JWT_TOKEN'
  | 'ACCESS_TOKEN'
  | 'EMPLOYEE_ID'
  | 'ADDRESS'
  | 'CUSTOM'

export type Severity = 'low' | 'medium' | 'high' | 'critical'

export type ProtectionMode = 'blur' | 'pixelate' | 'redact' | 'frosted'

/** Normalized bounding box: values are fractions (0..1) of image size. */
export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Detection {
  id: string
  detectedType: SensitiveType
  boundingBox: BoundingBox
  confidence: number // 0..100
  maskedValue: string
  severity: Severity
  protected: boolean
}

export interface ScanResult {
  scanId: string
  detections: Detection[]
  privacyScore: number // 0..100
  latencyMs: number
  timestamp: number
}

export interface ScanImageInput {
  /** Object URL or data URL for the image being scanned. */
  src: string
  width: number
  height: number
  /** Types the user has enabled for protection. */
  enabledTypes: SensitiveType[]
}

/** The contract any scanner (mock or real) must fulfil. */
export interface ScannerEngine {
  scanImage(input: ScanImageInput): Promise<ScanResult>
}

export type ScanPhase =
  | 'idle'
  | 'uploading'
  | 'analyzing'
  | 'identifying'
  | 'classifying'
  | 'cloaking'
  | 'complete'

export interface TypeMeta {
  type: SensitiveType
  label: string
  description: string
  severity: Severity
}
