// Generates a fake "screenshot" (a mock account settings page) entirely on a
// canvas, containing plausible-but-fake sensitive data. Used by Demo Mode so no
// external asset is needed and no real PII is ever shipped.

export function generateSampleScreenshot(): string {
  const W = 1000
  const H = 640
  const canvas = document.createElement('canvas')
  canvas.width = W
  canvas.height = H
  const ctx = canvas.getContext('2d')
  if (!ctx) return ''

  // window background
  ctx.fillStyle = '#F8FAFC'
  ctx.fillRect(0, 0, W, H)

  // top chrome bar
  ctx.fillStyle = '#FFFFFF'
  ctx.fillRect(0, 0, W, 56)
  ctx.strokeStyle = '#E5E7EB'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, 56.5)
  ctx.lineTo(W, 56.5)
  ctx.stroke()
  // traffic lights
  const lights = ['#F87171', '#FBBF24', '#34D399']
  lights.forEach((c, i) => {
    ctx.fillStyle = c
    ctx.beginPath()
    ctx.arc(28 + i * 22, 28, 6, 0, Math.PI * 2)
    ctx.fill()
  })
  ctx.fillStyle = '#111827'
  ctx.font = '600 16px "Space Grotesk", sans-serif'
  ctx.fillText('Account & Billing', 100, 33)

  const label = (t: string, x: number, y: number) => {
    ctx.fillStyle = '#6B7280'
    ctx.font = '500 13px "JetBrains Mono", monospace'
    ctx.fillText(t.toUpperCase(), x, y)
  }
  const value = (t: string, x: number, y: number) => {
    ctx.fillStyle = '#111827'
    ctx.font = '500 20px "Space Grotesk", sans-serif'
    ctx.fillText(t, x, y)
  }

  // card container
  const drawCard = (x: number, y: number, w: number, h: number) => {
    ctx.fillStyle = '#FFFFFF'
    ctx.strokeStyle = '#E5E7EB'
    ctx.lineWidth = 1
    roundRect(ctx, x, y, w, h, 14)
    ctx.fill()
    ctx.stroke()
  }

  drawCard(40, 84, 440, 200)
  label('Aadhaar Number', 64, 120)
  value('4829 1736 4928', 64, 150)
  label('Phone', 64, 196)
  value('+91 98765 43210', 64, 226)

  drawCard(520, 84, 440, 200)
  label('Credit Card', 544, 120)
  value('4539 8842 1067 4821', 544, 150)
  label('CVV / Expiry', 544, 196)
  value('•••  09 / 29', 544, 226)

  drawCard(40, 300, 920, 150)
  label('API Key (production)', 64, 336)
  ctx.fillStyle = '#111827'
  ctx.font = '500 18px "JetBrains Mono", monospace'
  ctx.fillText('sk-live-9fJ2Kd8sLpQw3nZx7Ab1Cd4Ef6Gh0Ij', 64, 366)
  label('Access Token', 64, 404)
  ctx.fillText('ghp_A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8', 64, 434)

  drawCard(40, 466, 440, 140)
  label('Email', 64, 502)
  value('rahul.sharma@example.com', 64, 532)
  label('Password', 64, 572)
  value('Sunsh1ne@2026!', 64, 596)

  drawCard(520, 466, 440, 140)
  label('Billing Address', 544, 502)
  ctx.fillStyle = '#111827'
  ctx.font = '500 17px "Space Grotesk", sans-serif'
  ctx.fillText('221B Baker Street, Bandra West,', 544, 530)
  ctx.fillText('Mumbai 400050', 544, 554)
  label('Support Email', 544, 588)

  return canvas.toDataURL('image/png')
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
