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
| **OCR** | `app/pipeline/ocr.py` | Runs Tesseract via `pytesseract.image_to_data` when an image is supplied and no tokens were given. Emits tokens with `text`, pixel `bbox [x,y,w,h]` and `confidence`. A second **upscaled + grayscale preprocessing pass** recovers small / high-entropy tokens (API keys, tokens) the base pass reads with low confidence; extra tokens are rescaled to the base coordinate space and de-duplicated by bbox coverage. Credential-prefixed tokens (`sk-`, `ghp_`, `AKIA`, `eyJ`…) are kept even at low OCR confidence, because the prefix is strong intrinsic evidence. Degrades gracefully to no-op if the binary is missing. |
| **DETECT** | `app/pipeline/detectors.py`, `validators.py`, `context.py` | Regex pattern library + **Luhn**/**Verhoeff**/IPv4 validation, feeding a **context-aware confidence model** (see below): candidates are scored on intrinsic evidence *and* surrounding keywords, with negative-context suppression and a redaction threshold. |
| **LOCATE** | `app/pipeline/locate.py` | Groups OCR tokens into lines, merges horizontally adjacent tokens (e.g. `7730 \| 0889 \| 2163` → one candidate), **reconstructs numbers split across stacked lines**, **groups consecutive lines into a single multi-line address block**, pulls in **label text from nearby lines as spatial context** (LABEL-above-VALUE layouts), unions contributing boxes into ONE bbox, and pads it 10–15% of text height. |

### Context-aware detection (`context.py`)

The detector does not ask "does this match a regex?" but "is this candidate
*structurally consistent* with sensitive data, and does the surrounding OCR /
visual context corroborate that?". An additive point model combines:

| Signal | Weight |
|--------|--------|
| pattern match | +20 |
| strong validation (Luhn / Verhoeff / IPv4) | +40 |
| strong context keyword (e.g. "debit card number", "aadhaar", "cvv") | +30 |
| medium context ("card", "account", "bank") | +15 |
| weak context ("id", "number") | +6 |
| spatial proximity to a keyword | +10 |
| multiple corroborating cues | +10 |
| negative context ("order number", "invoice", "reference") | −30 |
| failed validation | −30 (−12 when a strong label is present) |
| bare numeric, no corroboration | −20 |

The final 0–100 score is normalized to a `0..1` confidence; a candidate is only
redacted when it clears `REDACT_THRESHOLD` (default 45). This gives high recall
for genuinely sensitive values while suppressing order/invoice/account numbers,
dates, CVV-shaped 3-digit numbers without card context, etc. The keyword
dictionary (`CONTEXT`) and `NEGATIVE_CONTEXT` list are centralized and easily
extended. Every detection records human-readable `signals` explaining *why* it
was flagged — never the raw value.
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
- `CLOAK_OCR_PREPROCESS` — run the second upscaled/grayscale OCR pass (default `true`; set `false` for a single fastest pass).
- `CLOAK_OCR_UPSCALE` — upscale factor for the preprocessing pass (default `2.0`).

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
  "enabled_types": ["aadhaar", "credit_card", "email", "phone", "address", "custom"],
  "custom_patterns": [{ "name": "Employee ID", "regex": "EMP-[0-9]{6}" }]
}
```

`enabled_types` accepts the frontend toggle labels / aliases (normalized to
canonical types) or the canonical names directly. See
[Controlling detection with `enabled_types`](#controlling-detection-with-enabled_types).

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

## Supported detection types

The frontend **Protection Settings** panel exposes exactly eight toggleable
detection layers. Each maps to a canonical backend `SensitiveType` and is only
run when it is present in the request's `enabled_types` (see below):

| Frontend toggle | `enabled_types` value(s) accepted | Canonical type | How it's detected |
|-----------------|-----------------------------------|----------------|-------------------|
| **Aadhaar** | `aadhaar`, `aadhar`, `uid`, `AADHAAR` | `AADHAAR` | 12-digit structure + **Verhoeff** checksum + Aadhaar context. |
| **Credit Card** | `credit_card`, `credit card`, `card`, `CREDIT_CARD` | `CREDIT_CARD` (+`DEBIT_CARD`) | 13–19-digit structure + **Luhn** checksum + payment context. |
| **API Key** | `api_key`, `api key`, `apikey`, `API_KEY` | `API_KEY` | Provider prefixes (`sk-`, `AKIA`, `ghp_`, `eyJ`…), charset/length, entropy, credential context. |
| **Password** | `password`, `passwd`, `pwd`, `PASSWORD` | `PASSWORD` | Label-anchored **value** capture (`Password: …`) — the secret, not the word. |
| **Email** | `email`, `e-mail`, `mail`, `EMAIL` | `EMAIL` | RFC-ish email syntax; works with or without a label. |
| **Phone Number** | `phone`, `phone_number`, `mobile`, `PHONE` | `PHONE` | E.164 / Indian groupings + digit-count + context; random numbers need more evidence. |
| **Address** | `address`, `home_address`, `ADDRESS` | `ADDRESS` | **Multi-signal block**: address label + street/unit/locality/state + PIN/postal + house number, grouped across lines. A lone "road"/"city" is not an address. |
| **Custom Pattern** | `custom`, `custom_pattern`, `CUSTOM` | `CUSTOM_PATTERN` | User-supplied regex/label from `custom_patterns` (validated & ReDoS-guarded). |

Detection **never depends on labels alone**: a bare, checksum-valid Aadhaar or
Luhn-valid card is still detected without a label, and a label alone (`"Email"`,
`"Credit Card"`, `"Address"`) is never treated as the sensitive value. Context
strengthens confidence but is spatially local — a keyword at the top of an image
does not classify an unrelated number at the bottom.

> The backend also ships additional detectors used internally / by the API
> (PAN, SSN, Passport, IBAN, SWIFT, IFSC, UPI, crypto wallets, JWT, private
> keys, IPv4, MAC, CVV/expiry as card context). These only run when explicitly
> enabled; the eight above are the frontend-exposed set. See `PATTERNS` in
> `app/pipeline/detectors.py`.

### Controlling detection with `enabled_types`

`enabled_types` is the **authoritative list** of what to detect and redact:

- **Omitted / `null`** → every detector runs.
- **A list** → only those types run; disabled categories are neither detected
  nor redacted, and their pixels are left untouched.
- Values are **normalized**: the frontend toggle labels and common aliases
  (`aadhar`→`AADHAAR`, `phone_number`→`PHONE`, `credit card`→`CREDIT_CARD`,
  `custom`→`CUSTOM_PATTERN`) all resolve to the canonical type. Enabling
  `credit_card` also protects `DEBIT_CARD` (one UI toggle, both card variants).

```jsonc
// Only Aadhaar runs — a credit card in the same image is left untouched.
{ "image_base64": "…", "enabled_types": ["aadhaar"] }
```

### Custom patterns (`custom_patterns`)

When **Custom Pattern** is enabled, user-defined patterns run against the OCR
text and matches are located + redacted like any other type:

```jsonc
{
  "image_base64": "…",
  "enabled_types": ["custom"],
  "custom_patterns": [
    { "name": "Employee ID", "regex": "EMP-[0-9]{6}" },
    { "name": "Project Falcon" }          // no regex → matched as a literal phrase
  ]
}
```

Each pattern accepts `name` (required), optional `regex`, `confidence`, and
`description`. Patterns are **validated defensively**: the source is
length-capped, catastrophic-backtracking (ReDoS) shapes are rejected, matching
is character-budgeted, and a single bad pattern is skipped rather than failing
the scan. No user input is ever `eval`'d — only `re.compile`'d.

## Confidence, thresholds & privacy score

Each detection carries a `0..1` `confidence` derived from the additive model
above. `REDACT_THRESHOLD` (default 45/100) decides redact vs. skip. The
`privacy_score` is honest about outcomes:

- **100** only when no *enabled* sensitive data was detected.
- **< 100** when data was detected and protected (residual risk by severity).
- **Significantly reduced** — and never 100 — if a detection's protection
  verification fails, or if an enabled detector crashes internally (the failure
  is logged privacy-safely and reported, never hidden).

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
