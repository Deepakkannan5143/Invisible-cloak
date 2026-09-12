"""Invisible Cloak API — FastAPI entrypoint.

Endpoints:
  GET  /health      liveness probe
  POST /api/scan    run DETECT -> LOCATE -> PROTECT -> VERIFY over a payload
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .pipeline.engine import run_pipeline
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

app = FastAPI(
    title="Invisible Cloak API",
    version=__version__,
    description="Sensitive data detection & adaptive redaction engine.",
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
    return {"status": "ok", "version": __version__}


@app.post("/api/scan", response_model=ScanResponse)
def scan(req: ScanRequest) -> ScanResponse:
    return run_pipeline(req)
