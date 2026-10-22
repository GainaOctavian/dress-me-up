"""What an item's photo says about its fabric, in parts (plan 19, v5).

Instead of stretching the whole photo over the 3D garment, split it into:
- base: the cloth's dominant colour (folds and shadows tolerated);
- pattern: a repeating tile (plaid, stripes, knit), when the cloth isn't
  one colour - repeated at its real scale over the whole garment;
- decals: on one-colour cloth, whatever isn't that colour (prints, logos,
  pockets, patches), kept as cut-outs placed at their spot, unstretched.

Photo and garment are related by a similarity (scale + shift: collar and
shoulder width, `photo_coords`), so nothing is warped.
"""
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import ndimage

PLAIN = 0.6     # share of cloth within NEAR of the base colour -> one-colour cloth
NEAR, FAR = 12.0, 22.0  # Lab distances (lightness counted half: folds, shadows)
MIN_DECAL = 0.0008      # of the cloth area


@dataclass
class Fabric:
    colour: tuple                       # sRGB 0..1
    tile: Optional[np.ndarray] = None   # RGB uint8, repeats every tile.shape[:2] photo px
    decals: Optional[np.ndarray] = None  # RGBA uint8, photo-sized, transparent but the prints


def _lab(rgb):
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.2126, 0.0193], [0.3576, 0.7152, 0.1192], [0.1805, 0.0722, 0.9505]])
    xyz /= [0.9505, 1.0, 1.089]
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def analyse(image: np.ndarray) -> Fabric:
    """`image`: the item's RGBA cutout."""
    cloth = ndimage.binary_erosion(image[..., 3] > 128, iterations=4)
    if cloth.sum() < 100:
        cloth = image[..., 3] > 128
    lab = _lab(image[..., :3].astype(float))
    base = np.median(lab[cloth], axis=0)
    d = np.sqrt((((lab - base) * [0.5, 1, 1]) ** 2).sum(-1))
    near = cloth & (d < NEAR)
    colour = tuple(np.median(image[..., :3][near if near.any() else cloth], axis=0) / 255)
    if (d[cloth] < NEAR).mean() >= PLAIN:
        return Fabric(colour, decals=_decals(image, cloth, d, lab, base))
    return Fabric(colour, tile=_tile(image, cloth, lab))


def _decals(image, cloth, d, lab, base):
    off = ndimage.binary_closing(ndimage.binary_opening(cloth & (d > FAR), iterations=1), iterations=3)
    labels, n = ndimage.label(off)
    if not n:
        return None
    edge = ndimage.distance_transform_edt(image[..., 3] > 128) < 12
    grad = ndimage.gaussian_gradient_magnitude(lab[..., 0], 1.0)
    keep = np.zeros_like(off)
    for i in range(1, n + 1):
        c = labels == i
        if c.sum() <= MIN_DECAL * cloth.sum() or (c & edge).any():
            continue  # specks; touching the outline = structure (hood, trim, collar), not a print
        dl = np.median(lab[c][:, 0]) - base[0]
        dc = np.linalg.norm(np.median(lab[c][:, 1:], axis=0) - base[1:])
        rim = c & ~ndimage.binary_erosion(c, iterations=2)
        sharp = grad[rim].mean() / max(1.0, abs(dl))  # prints have crisp edges, folds soft ones
        if sharp < 0.12 or (dl < 0 and dc < 12 and sharp < 0.2):
            continue  # a fold, a shadow, the inside of a neck hole
        keep |= c
    if not keep.any():
        return None
    # letters of one print: keep their insides too (soft edge)
    alpha = ndimage.gaussian_filter(keep.astype(float), 1.0)
    out = image.copy()
    out[..., 3] = (np.clip(alpha * 1.5, 0, 1) * 255).astype(np.uint8)
    return out


def _tile(image, cloth, lab):
    """The pattern: a small cloth-only square (about an eighth of the
    garment's width) with no buttons/shadows in it and the cloth's average
    colour, made seamless (edges cross-faded with the opposite edges),
    repeats at its real size. ponytail: no period detection - real photos
    (folds, perspective) don't repeat exactly."""
    ys, xs = np.nonzero(cloth)
    n = max(24, int(0.12 * (xs.max() - xs.min())))
    lum = lab[..., 0]
    lo, hi = np.percentile(lum[cloth], [3, 97])
    odd = (lum < lo) | (lum > hi)
    inside = ndimage.minimum_filter(cloth, n)  # a square around the centre fits in the cloth
    best, at = None, None
    for cy in range(n // 2, cloth.shape[0] - n // 2, max(4, n // 4)):
        for cx in range(n // 2, cloth.shape[1] - n // 2, max(4, n // 4)):
            if not inside[cy, cx]:
                continue
            sl = np.s_[cy - n // 2:cy - n // 2 + n, cx - n // 2:cx - n // 2 + n]
            score = odd[sl].mean() * 100 + np.linalg.norm(lab[sl].mean((0, 1)) - lab[cloth].mean(0))
            if best is None or score < best:
                best, at = score, sl
    if at is None:
        at = np.s_[ys.min():ys.min() + n, xs.min():xs.min() + n]
    tile = image[at][..., :3].astype(float)
    # seamless: blend a band at each edge with the opposite edge
    band = max(2, tile.shape[0] // 5)
    for axis in (0, 1):
        tile = np.moveaxis(tile, axis, 0)
        w = np.linspace(0.5, 0, band)[:, None, None]
        head, tail = tile[:band].copy(), tile[-band:][::-1].copy()
        tile[:band] = head * (1 - w) + tail * w
        tile[-band:] = (tail * (1 - w) + head * w)[::-1]
        tile = np.moveaxis(tile, 0, axis)
    return np.clip(tile, 0, 255).astype(np.uint8)


def photo_coords(px: np.ndarray, garment: dict, photo_fit: dict, photo_shape) -> Optional[np.ndarray]:
    """Photo pixel under each garment vertex (`px`: its front projection,
    `garment`: mhclo.landmarks of it), anchored at the collar / waistband
    middle. Scale from the length (collar to hem): a flat-lay is wider than
    the same cloth wrapped round a body seen from the front."""
    ph, pw = photo_shape
    p = {k: np.array(v) * [pw, ph] for k, v in photo_fit.items() if isinstance(v, list)}
    need = ("collar", "hem_l", "hem_r")
    if not all(n in p and n in garment for n in need):
        return None
    length = lambda m: (m["hem_l"][1] + m["hem_r"][1]) / 2 - m["collar"][1]
    s = length(p) / max(1.0, length(garment))
    if s <= 0:
        return None
    return p["collar"] + (px - np.asarray(garment["collar"])) * s


if __name__ == "__main__":  # self-check on synthetic cloth
    img = np.zeros((200, 200, 4), np.uint8)
    img[20:180, 20:180] = (200, 30, 30, 255)
    img[60:100, 60:140, :3] = (250, 250, 250)  # a print
    f = analyse(img)
    assert f.tile is None and f.decals is not None and f.decals[80, 100, 3] > 200 and f.decals[150, 50, 3] == 0
    assert abs(f.colour[0] - 200 / 255) < 0.02
    stripes = img.copy()
    stripes[20:180, 20:180, :3] = np.where((np.arange(160) // 8 % 2)[:, None, None], (20, 20, 160), (240, 240, 240))
    f = analyse(stripes)
    assert f.tile is not None and f.decals is None and f.tile.shape[0] == 24, f.tile.shape
    print("ok")
