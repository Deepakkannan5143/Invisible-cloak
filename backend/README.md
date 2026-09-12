# Invisible Cloak — Backend Engine

A real FastAPI service implementing the **DETECT → LOCATE → PROTECT → VERIFY**
sensitive-data redaction pipeline. It accepts free text and/or OCR tokens with
pixel bounding boxes, detects PII / credentials / financial identifiers,
reconstructs their spatial location, bakes adaptive obfuscation into the image,
verifies the result, and returns a strict JSON contract.

## Pipeline

| Stage | Module | What it does |
|-------|--------|--------------|
| **DETECT** | `app/pipeline/detectors.py`, `validators.py` | Regex pattern library over text; **Luhn** (cards) and **Verhoeff** (Aadhaar) checksum validation; context-keyword scoring; overlap resolution. |
| **LOCATE** | `app/pipeline/locate.py` | Groups OCR tokens into lines, merges horizontally adjacent tokens (e.g. `7730 \| 0889 \| 2163` → one candidate), unions contributing token boxes (IoU-style) into ONE bbox, and pads it 10–15% of text height. |
| **PROTECT** | `app/pipeline/protect.py` | Masks the reported text (never raw); applies adaptive Pillow obfuscation — frosted glass / deep blur for **critical**, strong blur/pixelation for **high**, moderate blur otherwise. |
| **VERIFY** | `app/pipeline/verify.py` | Re-checks each redacted region and escalates protection strength up to 3 attempts. Pluggable `ocr_fn` enables a true re-OCR pass; the default is an honest structural check that confirms the pixels were actually degraded (see caveat below). |

### Honesty note on VERIFY

This service does **not** bundle an OCR engine, so the default verification pass
does not literally re-read the image with OCR. Instead it measures that a
region's visual detail dropped substantially after masking. To get a true
re-OCR verification loop, pass an `ocr_fn` (e.g. Tesseract / PaddleOCR) into
`verify_region`; detection then re-runs over the recognized text and the region
only passes when zero sensitive tokens remain.

## API

`POST /api/scan`

Request (any combination of `text`, `tokens`, `image_base64`):

```json
{
  "text": "optional free text",
  "tokens": [{ "text": "4111", "bbox": [40, 80, 45, 24] }],
  "image_base64": "data:image/png;base64,...",
  "image_width": 400,
  "image_height": 200,
  "mode": "frosted",
  "enabled_types": ["AADHAAR", "CREDIT_CARD"]
}
```

Response (strict contract):

```json
{
  "success": true,
  "processing_time_ms": 2.3,
  "privacy_score": 98.8,
  "summary": { "total_detections": 1, "critical_count": 1, "protected_count": 1 },
  "detections": [
    {
      "type": "CREDIT_CARD",
      "text": "XXXX XXXX XXXX 1111",
      "confidence": 0.99,
      "severity": "critical",
      "bbox": [42.6, 45.6, 192.8, 24.8],
      "status": "protected",
      "verification_passed": true,
      "attempts": 1
    }
  ],
  "protected_image": "data:image/png;base64,..."
}
```

- `bbox` is pixel-space `[x, y, width, height]`.
- `confidence` is `0..1`. `text` is always masked — raw values are never returned.
- `protected_image` is `null` when no `image_base64` was supplied.

`GET /health` → `{"status": "ok", "version": "1.0.0"}`.

## Detected categories

National IDs (Aadhaar, PAN, SSN, Passport, UK NINO, KR RRN), payment cards
(Luhn-validated), IBAN / SWIFT / IFSC / UPI / crypto wallets, API keys (OpenAI
`sk-`, AWS `AKIA`, GitHub `ghp_`), JWTs, private keys, passwords, emails, phones,
IPv4, MAC addresses. See `PATTERNS` in `app/pipeline/detectors.py`.

## Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

CORS allows `http://localhost:5173` (the Vite frontend) by default; override
with `CLOAK_CORS_ORIGINS="https://a.com,https://b.com"`.

## Test

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Connect the frontend

The React app defaults to its in-browser `MockScanner`. To route scans to this
backend, create `../.env.local`:

```
VITE_USE_REAL_BACKEND=true
VITE_CLOAK_API_URL=http://localhost:8000
```

`src/lib/realScanner.ts` maps this contract onto the frontend's `ScanResult`
(pixel bbox → normalized `0..1`, confidence `0..1` → `0..100`).
