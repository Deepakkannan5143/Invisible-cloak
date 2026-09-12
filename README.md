# Invisible Cloak — Privacy Intelligence

> Before sharing a screenshot, automatically detect Aadhaar numbers, credit card
> numbers, API keys, passwords and other sensitive information and blur / redact them.

A premium, AI-privacy-product frontend that visualizes the flow:

**SCREENSHOT → AI SCANS → SENSITIVE DATA DETECTED → INVISIBLE CLOAK ACTIVATED → SAFE SCREENSHOT**

The interface uses a clean white → light-gray → soft-silver palette with subtle
liquid/flowing ambient effects, a rotating "Cloak Core" scanner orb, an animated
scanning beam, a flowing privacy-membrane redaction sweep, and LED / monospace
technical detailing.

## Tech Stack

- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS** for styling
- **Framer Motion** for animation
- **Lucide React** for icons
- **HTML5 Canvas** for particle field, sample-screenshot generation, and baking
  redactions into the downloadable image

## Getting Started

```bash
npm install
npm run dev      # start the dev server
npm run build    # type-check + production build
npm run preview  # preview the production build
```

## Backend engine (optional)

A real detection & redaction service lives in [`backend/`](backend/README.md) —
a FastAPI implementation of the **IMAGE → OCR → DETECT → LOCATE → PROTECT →
VERIFY** pipeline (Tesseract OCR, regex + Luhn/Verhoeff validation, OCR-token
merging, IoU bbox union, adaptive Pillow obfuscation, re-OCR verification). It
extracts sensitive data from uploaded images server-side — the frontend never
runs OCR. The frontend uses the in-browser mock by default; set
`VITE_USE_REAL_BACKEND=true` (see `.env.example`) to route scans to it.

## How It Works

The frontend works entirely without a backend via a **mock scanning engine**.

- `src/lib/mockScanner.ts` implements the `ScannerEngine` interface and returns
  realistic detections with normalized bounding boxes, masked values, confidence
  and severity.
- `src/hooks/useImageScanner.ts` drives the scan → detect → cloak animation
  sequence and produces the final protected image.
- `src/lib/imageProcessor.ts` bakes the chosen redaction mode (blur / pixelate /
  redact / frosted cloak) into a canvas and exports a downloadable PNG.

To connect a real backend, replace `MockScanner` with your own implementation of
the `ScannerEngine` interface in `src/types/scanner.ts` — no UI changes required.

```ts
scanImage(input) => Promise<{
  scanId, detections: [{ detectedType, boundingBox, confidence, maskedValue, severity }],
  privacyScore, latencyMs, timestamp
}>
```

### Demo Mode

Click **Try Demo** to auto-load a canvas-generated sample screenshot (containing
only fake data) and run the entire scan → cloak → protect sequence, ending with a
privacy score and a "Safe to share" result.

## Project Structure

```
src/
  components/       UI components (Navbar, Hero, CloakOrb, UploadZone, Scanner,
                    ScreenshotPreview, DetectionOverlay, ProtectionReport,
                    SecurityScore, ScanTimeline, BeforeAfterSlider,
                    ProtectionSettings, ShareResult, LiquidBackground, LiquidFlow,
                    Particles, HowItWorks, DataTypes, SystemStatus,
                    SecurityVisualization, Statistics, Footer, Modal, ToastViewport,
                    ProtectFlow)
  hooks/            useImageScanner, useCloakAnimation, useReducedMotion, useToast
  lib/              mockScanner, imageProcessor, sampleScreenshot, typeMeta, typeIcons
  types/            scanner.ts (domain types + ScannerEngine contract)
```

## Accessibility & Performance

- Keyboard navigation, visible focus rings, ARIA roles/labels, a skip link and
  semantic HTML.
- `prefers-reduced-motion` is respected — ambient and decorative animations are
  disabled or minimized.
- Animations favor transforms/opacity and `requestAnimationFrame`; the particle
  field runs on a single canvas.

## Privacy Note

No sensitive values are ever displayed — detections are shown masked
(e.g. `XXXX XXXX XXXX 4821`, `sk-••••••••••••`). All processing happens locally
in the browser.
