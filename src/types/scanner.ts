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

/**
 * A sensitive region located inside an image, with its exact normalized box.
 * Produced by the demo screenshot generator (source of truth) or, in a real
 * deployment, by an OCR / vision backend. When supplied to the scanner these
 * regions are used verbatim so redaction always aligns with the real pixels.
 */
export interface SensitiveRegion {
  detectedType: SensitiveType
  /** The underlying (fake) text — used only to build a masked preview value. */
  text: string
  boundingBox: BoundingBox
  confidence: number
}

export interface ScanImageInput {
  /** Object URL or data URL for the image being scanned. */
  src: string
  width: number
  height: number
  /** Types the user has enabled for protection. */
  enabledTypes: SensitiveType[]
  /**
   * Optional exact regions for the image. When present the scanner uses these
   * instead of heuristic templates, guaranteeing every value is covered.
   */
  regions?: SensitiveRegion[]
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
