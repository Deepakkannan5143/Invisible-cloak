import {
  AtSign,
  CreditCard,
  Fingerprint,
  Globe,
  IdCard,
  KeyRound,
  Lock,
  type LucideIcon,
  MapPin,
  Phone,
  ShieldQuestion,
  Ticket,
  Wallet,
} from 'lucide-react'
import type { SensitiveType } from '../types/scanner'

export const TYPE_ICON: Record<SensitiveType, LucideIcon> = {
  AADHAAR: Fingerprint,
  CREDIT_CARD: CreditCard,
  DEBIT_CARD: Wallet,
  API_KEY: KeyRound,
  PASSWORD: Lock,
  EMAIL: AtSign,
  PHONE: Phone,
  IP_ADDRESS: Globe,
  JWT_TOKEN: Ticket,
  ACCESS_TOKEN: Ticket,
  EMPLOYEE_ID: IdCard,
  ADDRESS: MapPin,
  CUSTOM: ShieldQuestion,
}
