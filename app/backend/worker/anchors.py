"""Garment anchors on the processed cutout (plan 13). Pure numpy on the
alpha mask, no model. Coordinates are normalized 0..1 in the processed
image (x right, y down); `_l`/`_r` are the garment's own sides, so for a
front photo `_l` is on the image's right (same convention as body keypoints).

One anchor set serves every garment; the client picks what its slot needs:
- collar: top center (tops, dresses -> body neck)
- top_l/r: ends of the top rows (waistband of trousers/skirts -> body waist)
- hem_l/r: lowest point of each half (garment length; trouser legs -> ankles)
- parts: big connected pieces (2 = a pair of shoes side by side)
- shoulder_l/r + sleeve_l/r (tops, when found): where each sleeve leaves the
  torso and its tip. The torso column is a low percentile of the run widths
  around the center in the lower half (curved shirt tails make the very last
  rows too narrow; hanging sleeves that touch the torso make some too wide);
  mask outside it, above the hem, is sleeve. Garments are symmetric: a
  sleeve found on one side only is mirrored, and when both sides disagree
  (> 30 degrees apart or one > 1.4x longer) the shorter one wins (the long one is usually a hem
  corner). Sleeves that touch the torso everywhere aren't found: the
  garment then just follows the torso. Plan 14
  bends the garment so these lie along the arms.

No torso width: sleeves hanging along the body merge with it on most photos,
so the client scales tops by length (collar -> hem) instead.
"""
from typing import Optional

import numpy as np

FORMAT = 2
SOLID = 200  # the glow tops out at 0.6 * 255 = 153, the garment is 255


def _run_around(row: np.ndarray, c: int):
    """[left, right] of the filled run containing column c."""
    gaps_left = np.flatnonzero(~row[:c])
    gaps_right = np.flatnonzero(~row[c + 1:])
    left = gaps_left[-1] + 1 if len(gaps_left) else 0
    right = c + gaps_right[0] if len(gaps_right) else len(row) - 1
    return left, right


def anchors(alpha: np.ndarray) -> Optional[dict]:
    from scipy import ndimage
    m = alpha > SOLID
    ys, xs = np.nonzero(m)
    if len(ys) < 100:
        return None
    h, w = m.shape
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    gh = y1 - y0 + 1
    c = int(round(xs.mean()))
    n = lambda x, y: [round(float(x) / w, 4), round(float(y) / h, 4)]

    top_cols = np.flatnonzero(m[y0:y0 + max(2, gh // 33)].any(0))

    def hem(cols):
        yy, xx = np.nonzero(m[:, cols])
        low = yy.max()
        return n(cols[0] + xx[yy == low].mean(), low)

    raw = {}  # side -> (shoulder, tip) in px
    runs = [_run_around(m[y], c) for y in range(y0 + gh * 55 // 100, y0 + gh * 95 // 100) if m[y, c]]
    if len(runs) > gh // 10:
        left, right = sorted(runs, key=lambda lr: lr[1] - lr[0])[len(runs) // 4]
        yy, xx = np.nonzero(m[:y0 + gh * 92 // 100])
        margin = max(2, (right - left) // 20)
        for side, edge, out in (("l", right, xx > right + margin), ("r", left, xx < left - margin)):
            if out.sum() < 0.01 * len(ys):
                continue
            shoulder = (edge, np.flatnonzero(m[:, edge])[0])
            d = (xx[out] - shoulder[0]) ** 2 + (yy[out] - shoulder[1]) ** 2
            tip = int(np.argmax(d))
            raw[side] = (np.array(shoulder, float), np.array([xx[out][tip], yy[out][tip]], float))

    mirror = lambda p: np.array([2 * c - p[0], p[1]])
    if len(raw) == 2:
        (sl, tl), (sr, tr) = raw["l"], raw["r"]
        vl, vr = tl - sl, mirror(tr) - mirror(sr)
        cos = vl @ vr / (np.linalg.norm(vl) * np.linalg.norm(vr))
        ll, lr = np.linalg.norm(vl), np.linalg.norm(vr)
        if cos < np.cos(np.radians(30)) or max(ll, lr) > 1.4 * min(ll, lr):
            keep = "l" if ll < lr else "r"
            raw = {keep: raw[keep]}
    if len(raw) == 1:
        (side, (s, t)), = raw.items()
        raw[{"l": "r", "r": "l"}[side]] = (mirror(s), mirror(t))
    sleeves = {}
    for side, (s, t) in raw.items():
        sleeves[f"shoulder_{side}"] = n(*s)
        sleeves[f"sleeve_{side}"] = n(*t)

    labels, count = ndimage.label(m)
    sizes = ndimage.sum(m, labels, range(1, count + 1)) if count else []

    return {
        "format": FORMAT,
        "collar": n(c, y0),
        "top_l": n(top_cols.max(), y0), "top_r": n(top_cols.min(), y0),
        "hem_l": hem(np.arange(c, x1 + 1)), "hem_r": hem(np.arange(x0, c + 1)),
        "parts": int(sum(s >= 0.25 * max(sizes) for s in sizes)),
        **sleeves,
    }


if __name__ == "__main__":
    # t-shirt: torso 40..80 wide, sleeves out to 10..110 in the top rows
    tee = np.zeros((140, 120), np.uint8)
    tee[10:130, 40:81] = 255
    tee[12:40, 10:111] = 255
    a = anchors(tee)
    assert a["collar"] == [0.5, round(10 / 140, 4)]
    assert a["hem_l"][1] == round(129 / 140, 4)
    assert a["parts"] == 1
    assert a["shoulder_l"] == [round(80 / 120, 4), round(10 / 140, 4)]
    assert a["sleeve_l"] == [round(110 / 120, 4), round(39 / 140, 4)]
    assert a["sleeve_r"][0] == round(10 / 120, 4)

    # one sleeve only (the other touches the torso): mirrored
    half = tee.copy()
    half[12:40, 81:111] = 0
    a = anchors(half)
    assert a["sleeve_l"][1] == a["sleeve_r"][1] and abs(a["sleeve_l"][0] + a["sleeve_r"][0] - 2 * a["collar"][0]) < 0.02

    # trousers: waistband 30..90, legs split from row 50 down
    jeans = np.zeros((200, 120), np.uint8)
    jeans[10:50, 30:91] = 255
    jeans[50:190, 30:56] = 255
    jeans[50:190, 65:91] = 255
    a = anchors(jeans)
    assert a["top_r"][0] == round(30 / 120, 4) and a["top_l"][0] == round(90 / 120, 4)
    assert a["hem_l"][1] == a["hem_r"][1] == round(189 / 200, 4)
    assert "sleeve_l" not in a  # legs split: no torso column at the bottom

    # pair of shoes
    shoes = np.zeros((60, 200), np.uint8)
    shoes[20:50, 10:90] = 255
    shoes[20:50, 110:190] = 255
    assert anchors(shoes)["parts"] == 2
    print("anchors self-check ok")
