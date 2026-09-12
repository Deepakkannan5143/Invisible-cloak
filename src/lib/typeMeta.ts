import type { SensitiveType, Severity, TypeMeta } from '../types/scanner'

export const TYPE_META: Record<SensitiveType, TypeMeta> = {
  AADHAAR: {
    type: 'AADHAAR',
    label: 'Aadhaar',
    description: '12-digit Indian national identity numbers.',
    severity: 'critical',
  },
  CREDIT_CARD: {
    type: 'CREDIT_CARD',
    label: 'Credit Card',
    description: 'Payment card numbers and PAN sequences.',
    severity: 'critical',
  },
  DEBIT_CARD: {
    type: 'DEBIT_CARD',
    label: 'Debit Card',
    description: 'Bank card numbers linked to accounts.',
    severity: 'critical',
  },
  API_KEY: {
    type: 'API_KEY',
    label: 'API Key',
    description: 'Secret keys granting programmatic access.',
    severity: 'high',
  },
  PASSWORD: {
    type: 'PASSWORD',
    label: 'Password',
    description: 'Credentials in fields, logs or configs.',
    severity: 'high',
  },
  EMAIL: {
    type: 'EMAIL',
    label: 'Email',
    description: 'Personal and corporate email addresses.',
    severity: 'medium',
  },
  PHONE: {
    type: 'PHONE',
    label: 'Phone Number',
    description: 'Mobile and landline contact numbers.',
    severity: 'medium',
  },
  IP_ADDRESS: {
    type: 'IP_ADDRESS',
    label: 'IP Address',
    description: 'Network addresses that expose infra.',
    severity: 'low',
  },
  JWT_TOKEN: {
    type: 'JWT_TOKEN',
    label: 'JWT Token',
    description: 'Signed session and auth tokens.',
    severity: 'high',
  },
  ACCESS_TOKEN: {
    type: 'ACCESS_TOKEN',
    label: 'Access Token',
    description: 'OAuth and bearer access credentials.',
    severity: 'high',
  },
  EMPLOYEE_ID: {
    type: 'EMPLOYEE_ID',
    label: 'Employee ID',
    description: 'Internal staff identifiers.',
    severity: 'low',
  },
  ADDRESS: {
    type: 'ADDRESS',
    label: 'Address',
    description: 'Physical and postal addresses.',
    severity: 'medium',
  },
  CUSTOM: {
    type: 'CUSTOM',
    label: 'Custom Pattern',
    description: 'User-defined sensitive patterns.',
    severity: 'medium',
  },
}

export const SEVERITY_COLOR: Record<Severity, string> = {
  low: '#9CA3AF',
  medium: '#F59E0B',
  high: '#F97316',
  critical: '#EF4444',
}

export const DEFAULT_ENABLED: SensitiveType[] = [
  'AADHAAR',
  'CREDIT_CARD',
  'DEBIT_CARD',
  'API_KEY',
  'ACCESS_TOKEN',
  'JWT_TOKEN',
  'PASSWORD',
  'EMAIL',
  'PHONE',
  'ADDRESS',
]

/** Types exposed as user-facing toggles in Protection Settings. */
export const TOGGLEABLE_TYPES: SensitiveType[] = [
  'AADHAAR',
  'CREDIT_CARD',
  'API_KEY',
  'PASSWORD',
  'EMAIL',
  'PHONE',
  'ADDRESS',
  'CUSTOM',
]

/** All types shown in the "Supported Data Types" grid. */
export const SHOWCASE_TYPES: SensitiveType[] = [
  'AADHAAR',
  'CREDIT_CARD',
  'DEBIT_CARD',
  'API_KEY',
  'PASSWORD',
  'EMAIL',
  'PHONE',
  'IP_ADDRESS',
  'JWT_TOKEN',
  'ACCESS_TOKEN',
  'EMPLOYEE_ID',
  'CUSTOM',
]
