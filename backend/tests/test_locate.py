from app.pipeline.locate import Box, Token, group_into_lines, iou, locate, pad_box, union_box


def test_group_into_lines_by_y_overlap():
    toks = [
        Token("A", Box(0, 100, 20, 20)),
        Token("B", Box(30, 102, 20, 20)),   # same line
        Token("C", Box(0, 200, 20, 20)),    # new line
    ]
    lines = group_into_lines(toks)
    assert len(lines) == 2
    assert [t.text for t in lines[0]] == ["A", "B"]


def test_union_and_iou():
    a = Box(0, 0, 10, 10)
    b = Box(5, 0, 10, 10)
    u = union_box([a, b])
    assert (u.x, u.y, u.w, u.h) == (0, 0, 15, 10)
    assert 0 < iou(a, b) < 1


def test_pad_box_clamps():
    p = pad_box(Box(0, 0, 100, 20), ratio=0.5, img_w=200, img_h=200)
    assert p.x == 0 and p.y == 0  # clamped, not negative
    assert p.w >= 100


def test_locate_merges_split_card_tokens():
    # Split Luhn-valid card "4111 1111 1111 1111" across four tokens on one line.
    toks = [
        Token("Card", Box(0, 100, 40, 20)),
        Token("4111", Box(50, 100, 40, 20)),
        Token("1111", Box(95, 100, 40, 20)),
        Token("1111", Box(140, 100, 40, 20)),
        Token("1111", Box(185, 100, 40, 20)),
    ]
    dets = locate(toks, None, img_w=400, img_h=200)
    cards = [d for d in dets if d.type == "CREDIT_CARD"]
    assert len(cards) == 1
    # union box must span from first to last digit token
    box = cards[0].box
    assert box.x <= 50 and box.x + box.w >= 225


def test_locate_produces_union_not_fragments():
    toks = [
        Token("7730", Box(10, 50, 40, 18)),
        Token("0889", Box(55, 50, 40, 18)),
        Token("2163", Box(100, 50, 40, 18)),
        Token("4926", Box(145, 50, 40, 18)),  # -> 7730 0889 2163 4926
    ]
    # Not a valid Aadhaar checksum, but AADHAAR require_valid=False so still detected.
    dets = locate(toks, {"AADHAAR"}, img_w=400, img_h=200)
    assert len(dets) == 1
