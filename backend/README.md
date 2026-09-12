# Invisible Cloak — Backend Engine

A real, end-to-end FastAPI service implementing the
**IMAGE → OCR → DETECT → LOCATE → PROTECT → VERIFY** sensitive-data redaction
pipeline. Give it an image (or text, or pre-computed OCR tokens); it runs
Tesseract OCR to extract positioned tokens, detects PII / credentials /
financial identifiers, reconstructs their spatial location, bakes adaptive
obfuscation into the image, verifies the result by re-OCR, and returns a strict
JSON contract. The frontend never has to run OCR.

## Pipeline

| Stage | Module | What it does |
|-------|--------|--------------|
| **OCR** | `app/pipeline/ocr.py` | Runs Tesseract via `pytesseract.image_to_data` when an image is supplied and no tokens were given. Emits tokens with `text`, pixel `bbox [x,y,w,h]` and `confidence`. Degrades gracefully to no-op if the binary is missing. |
| **DETECT** | `app/pipeline/detectors.py`, `validators.py` | Regex pattern library over text; **Luhn** (cards) and **Verhoeff** (Aadhaar) checksum validation; context-keyword scoring; overlap resolution. |
| **LOCATE** | `app/pipeline/locate.py` | Groups OCR tokens into lines, merges horizontally adjacent tokens (e.g. `7730 \| 0889 \| 2163` → one candidate), unions contributing token boxes (IoU-style) into ONE bbox, and pads it 10–15% of text height. |
| **PROTECT** | `app/pipeline/protect.py` | Masks the reported text (never raw); applies adaptive Pillow obfuscation — frosted glass / deep blur for **critical**, strong blur/pixelation for **high**, moderate blur otherwise. |
| **VERIFY** | `app/pipeline/verify.py` | After masking, **re-OCRs the redacted region with Tesseract** and re-runs detection on the recovered text; if the value is still readable, protection strength escalates and retries (max 3 attempts). When Tesseract is unavailable it falls back to a structural check that the region's pixels were substantially degraded. |

### Honesty note on VERIFY

When Tesseract is installed, verification is a **real re-OCR loop**: the masked
region is cropped, re-read by OCR, and re-run through the detectors — a region
only passes when zero sensitive tokens of its type survive. Verification is
never reported as passed if OCR can still read the value; instead protection is
strengthened (up to 3 attempts). If the `tesseract` binary is absent, the
pipeline falls back to a structural check (confirms the pixels were degraded)
and image OCR simply finds nothing rather than crashing.

## OCR / Tesseract (system dependency)

OCR uses **Tesseract**, a *system* package (the `tesseract` binary + language
data), driven by the `pytesseract` Python wrapper. Install the binary
separately from the pip deps.

**Ubuntu / Debian:**

```bash
sudo apt-get update && sudo apt-get install -y tesseract-ocr
```

macOS (Homebrew): `brew install tesseract`. Fedora/RHEL: `dnf install tesseract`.
Conda-forge (no root): `micromamba install -c conda-forge tesseract`.

Optional env overrides:

- `TESSERACT_CMD` — full path to the `tesseract` binary if not on `PATH`.
- `TESSDATA_PREFIX` — path to the `tessdata` language directory (for non-standard installs).
- `CLOAK_OCR_MIN_CONF` — minimum per-token OCR confidence to keep (default `30`).

Verify it is reachable: `GET /health` returns `"ocr_available": true`.

## Logging & privacy

Raw detected values are **never** logged. Debug logging is opt-in:

- `CLOAK_DEBUG=false` (default) — only privacy-safe INFO summaries.
- `CLOAK_DEBUG=true` — extra DEBUG lines; any value is still masked via
  `logging_util.mask_for_log`.

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

**Token source priority:** explicit `tokens` (if supplied) → OCR of
`image_base64` via Tesseract (automatic) → raw `text`. The frontend only sends
`image_base64`; the backend does the OCR.

`GET /health` → `{"status": "ok", "version": "1.0.0", "ocr_available": true}`.

## Detected categories

National IDs (Aadhaar, PAN, SSN, Passport, UK NINO, KR RRN), payment cards
(Luhn-validated), IBAN / SWIFT / IFSC / UPI / crypto wallets, API keys (OpenAI
`sk-`, AWS `AKIA`, GitHub `ghp_`), JWTs, private keys, passwords, emails, phones,
IPv4, MAC addresses. See `PATTERNS` in `app/pipeline/detectors.py`.

## Run

```bash
# 1. system OCR engine (once)
sudo apt-get install -y tesseract-ocr

# 2. backend
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
