// Generates a fake "screenshot" (a mock account settings page) entirely on a
// canvas, containing plausible-but-fake sensitive data. Used by Demo Mode so no
// external asset is needed and no real PII is ever shipped.
//
// The generator is the single source of truth for where each sensitive value
// lives: as it draws a sensitive value it records the exact pixel box, then
// returns those boxes (normalized 0..1) alongside the image. The scanner uses
// them directly so redaction always lands on the real characters.

import type { SensitiveRegion, SensitiveType } from '../types/scanner'

export interface SampleScreenshot {
  src: string
  width: number
  height: number
  regions: SensitiveRegion[]
}

interface SensitiveSpec {
  type: SensitiveType
  text: string
  confidence: number
}

const W = 1000
const H = 640

export function generateSampleScreenshot(): SampleScreenshot {
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return { src: '', width: W, height: H, regions: [] }

  const regions: SensitiveRegion[] = []

  // ---- chrome / background -------------------------------------------------
  ctx.fillStyle = '#F8FAFC'
  ctx.fillRect(0, 0, W, H)
  ctx.fillStyle = '#FFFFFF'
  ctx.fillRect(0, 0, W, 56)
  ctx.strokeStyle = '#E5E7EB'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, 56.5)
  ctx.lineTo(W, 56.5)
  ctx.stroke()
  const lights = ['#F87171', '#FBBF24', '#34D399']
  lights.forEach((c, i) => {
    ctx.fillStyle = c
    ctx.beginPath()
    ctx.arc(28 + i * 22, 28, 6, 0, Math.PI * 2)
    ctx.fill()
  })
  ctx.fillStyle = '#111827'
  ctx.font = '600 16px "Space Grotesk", sans-serif'
  ctx.textBaseline = 'alphabetic'
  ctx.fillText('Account & Billing', 100, 33)

  // ---- helpers -------------------------------------------------------------
  const label = (t: string, x: number, y: number) => {
    ctx.fillStyle = '#6B7280'
    ctx.font = '500 13px "JetBrains Mono", monospace'
    ctx.fillText(t.toUpperCase(), x, y)
  }

  // Draws a value and, when a spec is provided, records its exact box so the
  // scanner can blur precisely that text. `font` controls the drawn glyphs; the
  // measured width + an approximate cap-height derive the box.
  const value = (
    t: string,
    x: number,
    baselineY: number,
    font: string,
    fontPx: number,
    spec?: SensitiveSpec,
  ) => {
    ctx.fillStyle = '#111827'
    ctx.font = font
    ctx.fillText(t, x, baselineY)

    if (spec) {
      const width = ctx.measureText(t).width
      // A generous vertical band around the glyphs (ascenders/descenders + pad).
      const top = baselineY - fontPx
      const height = fontPx * 1.5
      const padX = 6
      const padY = 3
      regions.push({
        detectedType: spec.type,
        text: spec.text,
        confidence: spec.confidence,
        boundingBox: {
          x: Math.max(0, (x - padX) / W),
          y: Math.max(0, (top - padY) / H),
          width: Math.min(1, (width + padX * 2) / W),
          height: Math.min(1, (height + padY * 2) / H),
        },
      })
    }
  }

  const drawCard = (x: number, y: number, w: number, h: number) => {
    ctx.fillStyle = '#FFFFFF'
    ctx.strokeStyle = '#E5E7EB'
    ctx.lineWidth = 1
    roundRect(ctx, x, y, w, h, 14)
    ctx.fill()
    ctx.stroke()
  }

  const SANS = '500 20px "Space Grotesk", sans-serif'
  const MONO = '500 18px "JetBrains Mono", monospace'
  const ADDR = '500 17px "Space Grotesk", sans-serif'

  // ---- card 1: identity ----------------------------------------------------
  drawCard(40, 84, 440, 200)
  label('Aadhaar Number', 64, 120)
  value('4829 1736 4928', 64, 150, SANS, 20, {
    type: 'AADHAAR',
    text: '4829 1736 4928',
    confidence: 98.7,
  })
  label('Phone', 64, 196)
  value('+91 98765 43210', 64, 226, SANS, 20, {
    type: 'PHONE',
    text: '+91 98765 43210',
    confidence: 97.0,
  })

  // ---- card 2: card --------------------------------------------------------
  drawCard(520, 84, 440, 200)
  label('Credit Card', 544, 120)
  value('4539 8842 1067 4821', 544, 150, SANS, 20, {
    type: 'CREDIT_CARD',
    text: '4539 8842 1067 4821',
    confidence: 97.4,
  })
  label('CVV / Expiry', 544, 196)
  value('123  09 / 29', 544, 226, SANS, 20, {
    type: 'CREDIT_CARD',
    text: '123 09/29',
    confidence: 96.2,
  })

  // ---- card 3: credentials -------------------------------------------------
  drawCard(40, 300, 920, 150)
  label('API Key (production)', 64, 336)
  value('sk-live-9fJ2Kd8sLpQw3nZx7Ab1Cd4Ef6Gh0Ij', 64, 366, MONO, 18, {
    type: 'API_KEY',
    text: 'sk-live-9fJ2Kd8sLpQw3nZx7Ab1Cd4Ef6Gh0Ij',
    confidence: 96.1,
  })
  label('Access Token', 64, 404)
  value('ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8', 64, 434, MONO, 18, {
    type: 'ACCESS_TOKEN',
    text: 'ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8',
    confidence: 95.3,
  })

  // ---- card 4: contact -----------------------------------------------------
  drawCard(40, 466, 440, 140)
  label('Email', 64, 502)
  value('rahul.sharma@example.com', 64, 532, SANS, 20, {
    type: 'EMAIL',
    text: 'rahul.sharma@example.com',
    confidence: 99.2,
  })
  label('Password', 64, 572)
  value('Sunsh1ne@2026!', 64, 596, SANS, 20, {
    type: 'PASSWORD',
    text: 'Sunsh1ne@2026!',
    confidence: 95.9,
  })

  // ---- card 5: address -----------------------------------------------------
  drawCard(520, 466, 440, 140)
  label('Billing Address', 544, 502)
  value('221B Baker Street, Bandra West,', 544, 530, ADDR, 17, {
    type: 'ADDRESS',
    text: '221B Baker Street, Bandra West, Mumbai 400050',
    confidence: 92.3,
  })
  value('Mumbai 400050', 544, 554, ADDR, 17, {
    type: 'ADDRESS',
    text: 'Mumbai 400050',
    confidence: 92.3,
  })
  label('Support Email', 544, 588)
  value('support@cloakbank.example', 544, 612, ADDR, 17, {
    type: 'EMAIL',
    text: 'support@cloakbank.example',
    confidence: 98.4,
  })

  return { src: canvas.toDataURL('image/png'), width: W, height: H, regions }
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}
