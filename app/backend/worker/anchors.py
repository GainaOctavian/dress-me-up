"""Garment anchors on the processed cutout (plan 13). Pure numpy on the
alpha mask, no model. Coordinates are normalized 0..1 in the processed
image (x right, y down); `_l`/`_r` are the garment's own sides, so for a
front photo `_l` is on the image's right (same convention as body keypoints).

One anchor set serves every garment; the client picks what its slot needs:
- collar: top center (tops, dresses -> body neck)
- top_l/r: ends of the top rows (waistband of trousers/skirts -> body waist)
- hem_l/r: lowest point of each half (garment length; trouser legs -> ankles)
- parts: big connected pieces (2 = a pair of shoes side by side)

No torso width: sleeves hanging along the body merge with it on most photos,
so the client scales tops by length (collar -> hem) instead.
"""
from typing import Optional

import numpy as np

FORMAT = 1
SOLID = 200  # the glow tops out at 0.6 * 255 = 153, the garment is 255


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

    labels, count = ndimage.label(m)
    sizes = ndimage.sum(m, labels, range(1, count + 1)) if count else []

    return {
        "format": FORMAT,
        "collar": n(c, y0),
        "top_l": n(top_cols.max(), y0), "top_r": n(top_cols.min(), y0),
        "hem_l": hem(np.arange(c, x1 + 1)), "hem_r": hem(np.arange(x0, c + 1)),
        "parts": int(sum(s >= 0.25 * max(sizes) for s in sizes)),
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

    # trousers: waistband 30..90, legs split from row 50 down
    jeans = np.zeros((200, 120), np.uint8)
    jeans[10:50, 30:91] = 255
    jeans[50:190, 30:56] = 255
    jeans[50:190, 65:91] = 255
    a = anchors(jeans)
    assert a["top_r"][0] == round(30 / 120, 4) and a["top_l"][0] == round(90 / 120, 4)
    assert a["hem_l"][1] == a["hem_r"][1] == round(189 / 200, 4)

    # pair of shoes
    shoes = np.zeros((60, 200), np.uint8)
    shoes[20:50, 10:90] = 255
    shoes[20:50, 110:190] = 255
    assert anchors(shoes)["parts"] == 2
    print("anchors self-check ok")
