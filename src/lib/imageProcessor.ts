import type { Detection, ProtectionMode } from '../types/scanner'

// ---------------------------------------------------------------------------
// Image processing utilities. Uses HTML5 Canvas to bake redactions into the
// image so the user can download a genuinely protected file.
// ---------------------------------------------------------------------------

export interface LoadedImage {
  src: string
  width: number
  height: number
  element: HTMLImageElement
}

export function loadImage(src: string): Promise<LoadedImage> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () =>
      resolve({
        src,
        width: img.naturalWidth,
        height: img.naturalHeight,
        element: img,
      })
    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = src
  })
}

export function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
}

/** Applies a boxed effect for a single detection region. */
function paintRegion(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  d: Detection,
  mode: ProtectionMode,
  W: number,
  H: number,
) {
  const x = d.boundingBox.x * W
  const y = d.boundingBox.y * H
  const w = d.boundingBox.width * W
  const h = d.boundingBox.height * H

  ctx.save()
  ctx.beginPath()
  const r = Math.min(8, h / 2)
  roundRect(ctx, x, y, w, h, r)
  ctx.clip()

  if (mode === 'redact') {
    ctx.fillStyle = '#111827'
    ctx.fillRect(x, y, w, h)
  } else if (mode === 'pixelate') {
    pixelate(ctx, img, x, y, w, h, W, H)
  } else {
    // blur & frosted both use a blurred draw; frosted adds a light glass tint
    blurRegion(ctx, img, x, y, w, h, W, H, mode === 'frosted' ? 10 : 8)
    if (mode === 'frosted') {
      ctx.fillStyle = 'rgba(255,255,255,0.35)'
      ctx.fillRect(x, y, w, h)
    }
  }
  ctx.restore()

  // subtle protected border
  ctx.save()
  ctx.strokeStyle = 'rgba(16,185,129,0.6)'
  ctx.lineWidth = Math.max(1, W / 900)
  roundRect(ctx, x, y, w, h, Math.min(8, h / 2))
  ctx.stroke()
  ctx.restore()
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number,
) {
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function blurRegion(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  x: number,
  y: number,
  w: number,
  h: number,
  W: number,
  H: number,
  amount: number,
) {
  // draw a scaled-down then scaled-up copy for a cheap blur, plus canvas filter
  ctx.filter = `blur(${amount}px)`
  ctx.drawImage(img, 0, 0, W, H)
  ctx.filter = 'none'
  void x
  void y
  void w
  void h
}

function pixelate(
  ctx: CanvasRenderingContext2D,
  img: HTMLImageElement,
  x: number,
  y: number,
  w: number,
  h: number,
  W: number,
  H: number,
) {
  const blocks = 10
  const tmp = document.createElement('canvas')
  tmp.width = Math.max(1, blocks)
  tmp.height = Math.max(1, Math.round((blocks * h) / w))
  const tctx = tmp.getContext('2d')
  if (!tctx) return
  tctx.drawImage(img, x, y, w, h, 0, 0, tmp.width, tmp.height)
  ctx.imageSmoothingEnabled = false
  ctx.drawImage(tmp, 0, 0, tmp.width, tmp.height, x, y, w, h)
  ctx.imageSmoothingEnabled = true
  void W
  void H
}

/**
 * Renders the protected image (redactions baked in) and returns a data URL.
 */
export async function renderProtectedImage(
  imageSrc: string,
  detections: Detection[],
  mode: ProtectionMode,
): Promise<string> {
  const { element, width, height } = await loadImage(imageSrc)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas unavailable')

  ctx.drawImage(element, 0, 0, width, height)
  for (const d of detections) {
    paintRegion(ctx, element, d, mode, width, height)
  }
  return canvas.toDataURL('image/png')
}

export async function dataUrlToBlob(dataUrl: string): Promise<Blob> {
  const res = await fetch(dataUrl)
  return res.blob()
}

export function downloadDataUrl(dataUrl: string, filename: string) {
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
}
