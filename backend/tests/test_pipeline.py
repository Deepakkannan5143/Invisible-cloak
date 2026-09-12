import base64
import io

from PIL import Image, ImageDraw
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline.engine import run_pipeline
from app.schemas import ScanRequest, OcrToken

client = TestClient(app)


def _make_image_with_text(text, box):
    img = Image.new("RGB", (400, 200), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((box[0] + 4, box[1] + 2), text, fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_text_only_pipeline_contract():
    req = ScanRequest(text="email a@b.com card 4111 1111 1111 1111")
    resp = run_pipeline(req)
    assert resp.success is True
    assert resp.summary.total_detections == len(resp.detections)
    assert resp.protected_image is None
    for d in resp.detections:
        # masked, never raw
        assert "4111 1111 1111 1111" not in d.text
        assert d.status == "protected"


def test_privacy_score_is_100_when_empty():
    resp = run_pipeline(ScanRequest(text="nothing sensitive here"))
    assert resp.privacy_score == 100.0
    assert resp.summary.total_detections == 0


def test_tokens_with_image_produces_protected_png_and_verifies():
    box = [40, 80, 180, 24]
    img_b64 = _make_image_with_text("4111 1111 1111 1111", box)
    tokens = [
        OcrToken(text="Card", bbox=[5, 80, 30, 24]),
        OcrToken(text="4111", bbox=[40, 80, 45, 24]),
        OcrToken(text="1111", bbox=[88, 80, 45, 24]),
        OcrToken(text="1111", bbox=[136, 80, 45, 24]),
        OcrToken(text="1111", bbox=[184, 80, 45, 24]),
    ]
    req = ScanRequest(tokens=tokens, image_base64=img_b64,
                      image_width=400, image_height=200, mode="frosted")
    resp = run_pipeline(req)
    cards = [d for d in resp.detections if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    card = cards[0]
    assert card.status == "protected"
    assert card.verification_passed is True
    assert 1 <= card.attempts <= 3
    assert resp.protected_image is not None and resp.protected_image.startswith("data:image/png")
    # bbox is pixel-space [x, y, w, h]
    assert len(card.bbox) == 4 and card.bbox[2] > 0 and card.bbox[3] > 0


def test_api_endpoint_and_cors():
    body = {"text": "ssn 123-45-6789"}
    r = client.post("/api/scan", json=body, headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200
    data = r.json()
    assert data["success"] is True
    assert set(["success", "processing_time_ms", "privacy_score", "summary",
                "detections", "protected_image"]).issubset(data.keys())
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cors_preflight():
    r = client.options(
        "/api/scan",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert r.status_code in (200, 204)
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
