"""Invisible Cloak API — FastAPI entrypoint.

Endpoints:
  GET  /health      liveness probe
  POST /api/scan    run DETECT -> LOCATE -> PROTECT -> VERIFY over a payload
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .logging_util import DEBUG, info
from .pipeline.engine import run_pipeline
from .pipeline.ocr import ocr_unavailable_reason
from .schemas import ScanRequest, ScanResponse

# Frontend host(s) allowed to call the API. Configurable via env; defaults
# include the Vite dev server host from the spec.
_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_origins = os.getenv("CLOAK_CORS_ORIGINS")
ALLOWED_ORIGINS = (
    [o.strip() for o in _origins.split(",") if o.strip()]
    if _origins
    else _DEFAULT_ORIGINS
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    reason = ocr_unavailable_reason()
    if reason:
        info("OCR unavailable — image scans find nothing until Tesseract is installed (%s)", reason)
    else:
        info("OCR ready (Tesseract detected). CLOAK_DEBUG=%s", DEBUG)
    yield


app = FastAPI(
    title="Invisible Cloak API",
    version=__version__,
    description="Sensitive data detection & adaptive redaction engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "ocr_available": ocr_unavailable_reason() is None,
    }


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    resp = run_pipeline(req)
    # Privacy-safe summary log (no raw values, no image bytes).
    info(
        "scan: detections=%d protected=%d critical=%d score=%.1f",
        resp.summary.total_detections,
        resp.summary.protected_count,
        resp.summary.critical_count,
        resp.privacy_score,
    )
    return resp
