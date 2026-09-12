"""LOCATE stage: spatial reconstruction from OCR tokens.

OCR services emit fragmented tokens (e.g. ``7730 | 0889 | 2163``). This stage:

1. Groups tokens into lines by y-overlap.
2. Merges horizontally-adjacent tokens on a line into a continuous string,
   tracking each token's character span so a text match can be mapped back to
   the exact contributing token boxes.
3. Runs :func:`detect_text` over each reconstructed line.
4. Unions the contributing token boxes (IoU-style union) into ONE bbox per
   detection, then pads it proportionally to text height.
"""

from __future__ import annotations

from dataclasses import dataclass

from .detectors import Match, detect_text


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h


@dataclass
class Token:
    text: str
    box: Box
    # OCR confidence (0..100) when the token came from Tesseract; -1 otherwise.
    confidence: float = -1.0


@dataclass
class LocatedDetection:
    type: str
    severity: str
    confidence: float
    value: str
    box: Box


def _y_overlap(a: Box, b: Box) -> float:
    """Fraction of vertical overlap relative to the smaller height."""
    top = max(a.y, b.y)
    bottom = min(a.y2, b.y2)
    inter = max(0.0, bottom - top)
    denom = max(1e-6, min(a.h, b.h))
    return inter / denom


def group_into_lines(tokens: list[Token], y_overlap_thresh: float = 0.5) -> list[list[Token]]:
    """Cluster tokens into lines by vertical overlap, ordered left-to-right."""
    remaining = sorted(tokens, key=lambda t: (t.box.y, t.box.x))
    lines: list[list[Token]] = []
    for tok in remaining:
        placed = False
        for line in lines:
            # Compare against the line's representative (first) token.
            if _y_overlap(line[0].box, tok.box) >= y_overlap_thresh:
                line.append(tok)
                placed = True
                break
        if not placed:
            lines.append([tok])
    for line in lines:
        line.sort(key=lambda t: t.box.x)
    return lines


def union_box(boxes: list[Box]) -> Box:
    """Union (bounding rectangle) of several boxes."""
    x1 = min(b.x for b in boxes)
    y1 = min(b.y for b in boxes)
    x2 = max(b.x2 for b in boxes)
    y2 = max(b.y2 for b in boxes)
    return Box(x1, y1, x2 - x1, y2 - y1)


def iou(a: Box, b: Box) -> float:
    """Intersection-over-union of two boxes (used to dedupe overlapping hits)."""
    ix1, iy1 = max(a.x, b.x), max(a.y, b.y)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def pad_box(box: Box, ratio: float = 0.12, img_w: float | None = None,
            img_h: float | None = None) -> Box:
    """Expand a box outward by ``ratio`` of its text height on each side.

    Prevents edge-character leakage. Clamped to image bounds when provided.
    """
    pad = box.h * ratio
    x = box.x - pad
    y = box.y - pad
    w = box.w + 2 * pad
    h = box.h + 2 * pad
    if img_w is not None:
        x = max(0.0, x)
        w = min(img_w - x, w)
    if img_h is not None:
        y = max(0.0, y)
        h = min(img_h - y, h)
    return Box(x, max(0.0, y), max(0.0, w), h)


def locate(tokens: list[Token], enabled_types: set[str] | None,
           img_w: float | None = None, img_h: float | None = None,
           pad_ratio: float = 0.12) -> list[LocatedDetection]:
    """Reconstruct lines, detect, union contributing boxes, and pad."""
    located: list[LocatedDetection] = []

    for line in group_into_lines(tokens):
        # Build the merged line string and a char-offset -> token index map.
        parts: list[str] = []
        spans: list[tuple[int, int]] = []  # (start, end) per token in merged string
        cursor = 0
        for i, tok in enumerate(line):
            if i > 0:
                parts.append(" ")
                cursor += 1
            start = cursor
            parts.append(tok.text)
            cursor += len(tok.text)
            spans.append((start, cursor))
        merged = "".join(parts)

        for match in detect_text(merged, enabled_types):
            boxes = _tokens_for_span(line, spans, match)
            if not boxes:
                continue
            u = union_box(boxes)
            u = pad_box(u, pad_ratio, img_w, img_h)
            located.append(
                LocatedDetection(
                    type=match.type,
                    severity=match.severity,
                    confidence=match.confidence,
                    value=match.value,
                    box=u,
                )
            )

    return _dedupe(located)


def _tokens_for_span(line: list[Token], spans: list[tuple[int, int]],
                     match: Match) -> list[Box]:
    """Return the boxes of tokens whose char-span intersects the match span."""
    boxes: list[Box] = []
    for tok, (s, e) in zip(line, spans):
        if not (match.end <= s or match.start >= e):
            boxes.append(tok.box)
    return boxes


def _dedupe(located: list[LocatedDetection], iou_thresh: float = 0.6) -> list[LocatedDetection]:
    """Drop near-duplicate detections (same region), keeping higher confidence."""
    ordered = sorted(located, key=lambda d: d.confidence, reverse=True)
    kept: list[LocatedDetection] = []
    for d in ordered:
        if any(d.type == k.type and iou(d.box, k.box) >= iou_thresh for k in kept):
            continue
        kept.append(d)
    return kept
