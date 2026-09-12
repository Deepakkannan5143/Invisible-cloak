"""Detector failure handling (§29) and custom-pattern safety at the API layer.

If an enabled detector crashes internally, the pipeline must NOT silently
return success with an empty detection list and a perfect privacy score. It
must report the failure (via a privacy-safe log and a reduced score) and never
leak sensitive text through the exception path.
"""

import app.pipeline.engine as engine
from app.schemas import CustomPattern, ScanRequest


def test_detector_crash_does_not_report_perfect_privacy(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("synthetic detector failure")

    # Force the text-detection path to raise.
    monkeypatch.setattr(engine, "detect_text", boom)

    resp = engine.run_pipeline(ScanRequest(text="Aadhaar Number: 4829 1736 4926"))
    # Success flag stays True (the request was handled), but the score must not
    # claim 100% because we could not vouch for the content.
    assert resp.privacy_score < 100.0
    assert resp.summary.total_detections == 0


def test_custom_patterns_bad_entries_do_not_break_scan():
    # A mix of valid, invalid, and dangerous patterns; the scan still succeeds
    # and the valid one is honoured.
    req = ScanRequest(
        text="ticket ABC-123 and EMP-654321",
        enabled_types=["custom"],
        custom_patterns=[
            CustomPattern(name="Ticket", regex="ABC-[0-9]{3}"),
            CustomPattern(name="redos", regex="(a+)+$"),
            CustomPattern(name="broken", regex="([unclosed"),
        ],
    )
    resp = engine.run_pipeline(req)
    assert resp.success is True
    assert any(d.type == "CUSTOM_PATTERN" for d in resp.detections)


def test_custom_pattern_value_never_in_response():
    req = ScanRequest(
        text="secret code SECRET-999999 here",
        enabled_types=["custom"],
        custom_patterns=[CustomPattern(name="Code", regex="SECRET-[0-9]{6}")],
    )
    resp = engine.run_pipeline(req)
    for d in resp.detections:
        assert "SECRET-999999" not in d.text
