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
    # Human-readable evidence for the classification (never the raw value).
    signals: tuple[str, ...] = ()


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


def _line_box(line: list[Token]) -> Box:
    return union_box([t.box for t in line])


def _spatial_context_prefix(line: list[Token], all_lines: list[list[Token]]) -> str:
    """Collect text from lines that are the *label* for ``line``.

    Handles the common "LABEL: VALUE" and stacked "LABEL \\n VALUE" layouts by
    pulling in the text of lines that sit directly above (and vertically close)
    or that share the block — so a label like "Aadhaar Number" one line above
    the digits still counts as context (§4). Kept intentionally simple and
    local; no full layout engine.
    """
    lb = _line_box(line)
    line_h = lb.h if lb.h > 0 else 1.0
    prefix_words: list[str] = []
    for other in all_lines:
        if other is line:
            continue
        ob = _line_box(other)
        vertical_gap = lb.y - ob.y2  # >0 when `other` is above `line`
        # A label directly above within ~2 line-heights, roughly x-aligned.
        above = -0.5 * line_h <= vertical_gap <= 2.5 * line_h
        x_overlap = min(lb.x2, ob.x2) - max(lb.x, ob.x)
        near_x = x_overlap > -3 * line_h  # tolerant horizontal alignment
        if above and near_x:
            prefix_words.append(" ".join(t.text for t in other))
    return " ".join(prefix_words)


def locate(tokens: list[Token], enabled_types: set[str] | None,
           img_w: float | None = None, img_h: float | None = None,
           pad_ratio: float = 0.12) -> list[LocatedDetection]:
    """Reconstruct lines, detect with spatial context, union boxes, and pad."""
    located: list[LocatedDetection] = []
    lines = group_into_lines(tokens)

    for line in lines:
        # Spatial context: prepend label text from nearby lines so a candidate
        # sees its label even when OCR put it on a separate line. The prefix is
        # separated so the value's own char spans start after it.
        prefix = _spatial_context_prefix(line, lines)
        prefix_str = (prefix + " \n ") if prefix else ""
        offset = len(prefix_str)

        # Build the merged line string and a char-offset -> token index map.
        parts: list[str] = []
        spans: list[tuple[int, int]] = []  # (start, end) per token in merged string
        cursor = offset
        for i, tok in enumerate(line):
            if i > 0:
                parts.append(" ")
                cursor += 1
            start = cursor
            parts.append(tok.text)
            cursor += len(tok.text)
            spans.append((start, cursor))
        merged = prefix_str + "".join(parts)

        for match in detect_text(merged, enabled_types):
            # Ignore matches that fall entirely inside the context prefix
            # (that text belongs to a different line and is handled there).
            if match.end <= offset:
                continue
            boxes = _tokens_for_span(line, spans, match)
            if not boxes:
                continue
            u = pad_box(union_box(boxes), pad_ratio, img_w, img_h)
            located.append(
                LocatedDetection(
                    type=match.type, severity=match.severity,
                    confidence=match.confidence, value=match.value,
                    box=u, signals=match.signals,
                )
            )

    # Cross-line reconstruction for numbers split across stacked lines.
    located.extend(
        _reconstruct_cross_line(lines, enabled_types, img_w, img_h, pad_ratio)
    )

    return _dedupe(located)


def _is_numeric_token(text: str) -> bool:
    digits = sum(c.isdigit() for c in text)
    return digits >= 2 and digits >= len(text) - 1  # mostly digits


def _is_card_group_token(text: str) -> bool:
    """A token shaped like a card/Aadhaar group: exactly 3-4 digits, no '/'.

    Excludes date fragments (``09/29``) and stray short numbers so cross-line
    reconstruction only ever stitches genuine card/Aadhaar groups together.
    """
    if "/" in text:
        return False
    core = text.strip()
    return core.isdigit() and 3 <= len(core) <= 4


def _reconstruct_cross_line(
    lines: list[list[Token]],
    enabled_types: set[str] | None,
    img_w: float | None,
    img_h: float | None,
    pad_ratio: float,
) -> list[LocatedDetection]:
    """Merge digit tokens from vertically-stacked lines into one candidate.

    Handles layouts where a card / Aadhaar number wraps across lines::

        Card Number
        5264 1234
        5678 9012

    Consecutive lines that are predominantly numeric and vertically close are
    concatenated; the combined digit string is re-run through the detectors
    (with the label lines as spatial context), and every contributing token box
    is unioned into one region.
    """
    out: list[LocatedDetection] = []
    if len(lines) < 2:
        return out

    n = len(lines)
    for i in range(n):
        numeric_run: list[list[Token]] = []
        j = i
        prev_box: Box | None = None
        while j < n:
            line = lines[j]
            # A reconstructable line is composed *entirely* of card/Aadhaar
            # group tokens (3-4 digits). A "CVV: 482" or "Expiry: 09/29" line
            # contains a label / slash and is therefore excluded.
            group_toks = [t for t in line if _is_card_group_token(t.text)]
            if not group_toks or len(group_toks) != len(line):
                break
            num_toks = group_toks
            lb = _line_box(line)
            if prev_box is not None:
                gap = lb.y - prev_box.y2
                if gap > 1.6 * max(lb.h, 1.0):  # too far apart vertically
                    break
            numeric_run.append(num_toks)
            prev_box = lb
            j += 1
        if len(numeric_run) < 2:
            continue

        # Concatenate digit tokens across the run, tracking contributing boxes.
        contributing: list[Box] = []
        digit_parts: list[str] = []
        for ln in numeric_run:
            for t in ln:
                digit_parts.append(t.text)
                contributing.append(t.box)
        merged_value = " ".join(digit_parts)

        # Spatial context: the label sits above the first numeric line.
        prefix = _spatial_context_prefix(numeric_run[0], lines)
        probe = (prefix + " \n " + merged_value) if prefix else merged_value

        for match in detect_text(probe, enabled_types):
            # Reconstruction targets long numeric identifiers that wrap across
            # lines (cards, Aadhaar). Phone/other shorter numerics are handled
            # by the per-line pass, so don't resurrect them here.
            if match.type not in ("CREDIT_CARD", "DEBIT_CARD", "AADHAAR"):
                continue
            digits_only = "".join(c for c in match.value if c.isdigit())
            if len(digits_only) < 12:
                continue
            # Only trust a cross-line merge when the reconstructed value is
            # genuinely a card/Aadhaar: it must pass its checksum, otherwise a
            # coincidental stack of unrelated numeric lines (CVV + expiry) could
            # masquerade as a card. Validation is the deciding evidence here.
            if "strong validation passed" not in match.signals:
                continue
            u = pad_box(union_box(contributing), pad_ratio, img_w, img_h)
            out.append(
                LocatedDetection(
                    type=match.type, severity=match.severity,
                    confidence=match.confidence, value=match.value,
                    box=u, signals=match.signals + ("reconstructed across lines",),
                )
            )
    return out


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
