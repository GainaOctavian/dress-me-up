"""Image pipeline for clothing photos:
cut out the item, add an indigo glow on its contour, detect colors (pixels)
and suggest category + tags (CLIP zero-shot). Pure functions, no I/O,
so it can be checked on local files."""
import io
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter

MAX_SIDE = 1024
GLOW_RGB = (99, 102, 241)  # app primarySoft (#6366f1)
GLOW_OPACITY = 0.6

# ---------------------------------------------------------------- cutout


@lru_cache(maxsize=1)
def _rembg_session():
    from rembg import new_session  # heavy import, load once
    # u2net leaves far fewer half-transparent "smoky" areas on clothes
    # than isnet-general-use (measured on the seed photos)
    return new_session("u2net")


def _plain_background_mask(rgb: np.ndarray):
    """For product shots on a plain light background: foreground = every
    pixel not connected to the border through near-background color.
    Catches what the model misses (black tee on white). None if the
    background isn't plain (normal phone photos)."""
    from scipy import ndimage
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(float)
    # median + share, not mean/std: the item often touches the frame
    bg = np.median(border, axis=0)
    on_bg = np.abs(border - bg).max(-1) < 28
    if bg.min() < 215 or on_bg.mean() < 0.6:
        return None
    near_bg = np.abs(rgb.astype(float) - bg).max(-1) < 28
    labels, _ = ndimage.label(near_bg)
    edge_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    background = np.isin(labels, edge_labels[edge_labels > 0])
    fg = ndimage.binary_fill_holes(~background)
    fg = ndimage.binary_opening(fg, iterations=2)  # drop specks
    return fg


def _drop_small_parts(alpha: np.ndarray, keep_ratio: float = 0.05) -> np.ndarray:
    """Remove islands smaller than keep_ratio of the biggest one (captions,
    logos, specks), keeping e.g. both shoes of a pair."""
    from scipy import ndimage
    labels, n = ndimage.label(alpha > 128)
    if n <= 1:
        return alpha
    sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
    keep = np.isin(labels, 1 + np.flatnonzero(sizes >= keep_ratio * sizes.max()))
    # grow the kept area a little so soft edges around it survive
    keep = ndimage.binary_dilation(keep, iterations=3)
    return alpha * keep


def cut_out(image: Image.Image) -> Image.Image:
    """RGBA with a transparent background, cropped to the item."""
    from rembg import remove
    rgb_img = image.convert("RGB")
    rgb_img.thumbnail((1600, 1600))
    rgba = remove(rgb_img, session=_rembg_session()).convert("RGBA")
    # harden the matte: faint/half pixels become clean edges, not haze
    alpha = np.asarray(rgba.getchannel("A")).astype(float)
    alpha = np.clip((alpha - 50) * 255 / (200 - 50), 0, 255)
    plain = _plain_background_mask(np.asarray(rgb_img))
    # only when the model clearly missed the item (black tee -> just its
    # print); otherwise the plain mask would add shadows under the item
    if plain is not None and (alpha > 128).sum() < 0.6 * plain.sum():
        alpha = np.maximum(alpha, plain * 255.0)
    alpha = _drop_small_parts(alpha)
    mask = Image.fromarray(alpha.astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.8))
    rgba.putalpha(mask)
    bbox = mask.point(lambda a: 255 if a > 12 else 0).getbbox()
    return rgba.crop(bbox) if bbox else rgba


def add_glow(cutout: Image.Image) -> Image.Image:
    """Soft indigo glow behind the item's contour (the 'pop'), on a padded
    transparent canvas so the glow isn't clipped."""
    cutout.thumbnail((MAX_SIDE, MAX_SIDE))
    w, h = cutout.size
    pad = max(8, int(max(w, h) * 0.06))
    canvas_size = (w + 2 * pad, h + 2 * pad)

    alpha = Image.new("L", canvas_size, 0)
    alpha.paste(cutout.getchannel("A"), (pad, pad))
    spread = alpha.filter(ImageFilter.MaxFilter(_odd(pad // 3)))
    blurred = spread.filter(ImageFilter.GaussianBlur(pad * 0.45))
    glow_alpha = blurred.point(lambda a: int(a * GLOW_OPACITY))

    glow = Image.new("RGBA", canvas_size, GLOW_RGB + (0,))
    glow.putalpha(glow_alpha)
    glow.alpha_composite(cutout, (pad, pad))
    return glow


def _odd(n: int) -> int:
    return max(3, n | 1)


def to_png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()

# ---------------------------------------------------------------- colors


# name -> sRGB; names match what users type in the item form
PALETTE = {
    "black": (25, 25, 25), "white": (245, 245, 242), "gray": (128, 128, 128),
    "light gray": (200, 200, 200), "navy": (30, 40, 80), "blue": (45, 95, 200),
    "light blue": (150, 185, 230), "red": (200, 30, 40), "burgundy": (110, 25, 45),
    "pink": (240, 150, 180), "orange": (240, 130, 40), "yellow": (240, 210, 60),
    "beige": (215, 195, 160), "brown": (115, 75, 45), "khaki": (165, 150, 105),
    "green": (45, 140, 65), "olive": (95, 105, 50), "purple": (110, 60, 150),
}


def _to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0-255, Nx3) -> CIELAB, so 'closest color' matches perception."""
    c = rgb / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    xyz = c @ np.array([[0.4124, 0.3576, 0.1805],
                        [0.2126, 0.7152, 0.0722],
                        [0.0193, 0.1192, 0.9505]]).T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[:, 1] - 16,
                     500 * (f[:, 0] - f[:, 1]),
                     200 * (f[:, 1] - f[:, 2])], axis=1)


_PALETTE_NAMES = list(PALETTE)
_PALETTE_LAB = _to_lab(np.array([PALETTE[n] for n in _PALETTE_NAMES], dtype=float))


def dominant_colors(cutout: Image.Image, k: int = 4, min_share: float = 0.15) -> list:
    """Named colors covering >= min_share of the item, biggest first."""
    rgba = np.asarray(cutout.convert("RGBA")).reshape(-1, 4)
    pixels = rgba[rgba[:, 3] > 200][:, :3].astype(float)
    if len(pixels) == 0:
        return []
    rng = np.random.default_rng(0)
    if len(pixels) > 6000:
        pixels = pixels[rng.choice(len(pixels), 6000, replace=False)]
    lab = _to_lab(pixels)
    # small k-means in Lab space
    centers = lab[rng.choice(len(lab), min(k, len(lab)), replace=False)]
    for _ in range(12):
        labels = np.argmin(((lab[:, None] - centers[None]) ** 2).sum(-1), axis=1)
        centers = np.array([lab[labels == i].mean(0) if (labels == i).any() else centers[i]
                            for i in range(len(centers))])
    shares = np.bincount(labels, minlength=len(centers)) / len(lab)
    names = []
    for i in np.argsort(-shares):
        if shares[i] < min_share:
            break
        name = _PALETTE_NAMES[int(np.argmin(((_PALETTE_LAB - centers[i]) ** 2).sum(-1)))]
        if name not in names:
            names.append(name)
    return names[:3]

# ---------------------------------------------------------------- CLIP tags


# specific garment -> app category; the garment also becomes a tag
GARMENTS = {
    "t-shirt": "top", "shirt": "top", "polo shirt": "top", "sweater": "top",
    "hoodie": "top", "tank top": "top",
    "jeans": "bottom", "trousers": "bottom", "shorts": "bottom", "sweatpants": "bottom",
    "dress": "dress",
    "jacket": "outerwear", "coat": "outerwear", "parka": "outerwear", "blazer": "outerwear",
    "sneakers": "shoes", "boots": "shoes", "dress shoes": "shoes", "sandals": "shoes",
    "belt": "accessory", "tie": "accessory", "cap": "accessory", "hat": "accessory",
    "beanie": "accessory", "bag": "accessory", "watch": "accessory",
    "sunglasses": "accessory", "scarf": "accessory", "gloves": "accessory",
}

# one tag per group, only when CLIP is fairly sure
TAG_GROUPS = {
    # no "business" (overlaps formal, landed on graphic tees) and no
    # "nylon" (CLIP picked it for nearly everything)
    "style": ["casual", "formal", "sporty", "streetwear", "outdoor", "vintage"],
    "pattern": ["plain", "striped", "plaid", "graphic print", "logo"],
    "material": ["denim", "leather", "knit", "cotton", "wool", "suede", "canvas"],
    # "all-season" lets CLIP decline instead of forcing summer vs winter
    "season": ["summer", "winter", "all-season"],
}
# tuned on the seed photos: lower values made "nylon"/"business"/"winter"
# show up on almost everything
TAG_MIN_PROB = {"style": 0.5, "pattern": 0.45, "material": 0.55, "season": 0.6}
SKIP_TAGS = {"plain", "all-season"}  # informative for the model, noise as a tag


@lru_cache(maxsize=1)
def _clip():
    import open_clip
    import torch
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )
    model.eval()
    tokenizer = open_clip.get_tokenizer("ViT-B-32")

    def encode_texts(texts):
        with torch.no_grad():
            t = model.encode_text(tokenizer(texts))
        return t / t.norm(dim=-1, keepdim=True)

    prompts = {
        "garment": encode_texts([f"a product photo of {g}" for g in GARMENTS]),
        **{group: encode_texts([f"a photo of {t} clothing" for t in tags])
           for group, tags in TAG_GROUPS.items()},
    }
    return model, preprocess, prompts


def suggest(cutout: Image.Image) -> dict:
    """{"category": ..., "tags": [...]} from CLIP zero-shot."""
    import torch
    model, preprocess, prompts = _clip()
    # CLIP was trained on normal photos: show it the item on white
    flat = Image.new("RGB", cutout.size, (255, 255, 255))
    flat.paste(cutout, mask=cutout.getchannel("A"))
    with torch.no_grad():
        img = model.encode_image(preprocess(flat).unsqueeze(0))
    img = img / img.norm(dim=-1, keepdim=True)

    def probs(text_features):
        return (100.0 * img @ text_features.T).softmax(dim=-1)[0]

    garment_names = list(GARMENTS)
    garment = garment_names[int(probs(prompts["garment"]).argmax())]
    tags = [garment]
    for group, names in TAG_GROUPS.items():
        p = probs(prompts[group])
        best = int(p.argmax())
        if float(p[best]) >= TAG_MIN_PROB[group] and names[best] not in SKIP_TAGS:
            tags.append(names[best])
    return {"category": GARMENTS[garment], "tags": tags}


def process(original: bytes) -> dict:
    """Full pipeline on the uploaded bytes."""
    image = Image.open(io.BytesIO(original))
    image.load()
    cutout = cut_out(image)
    result = suggest(cutout)
    result["colors"] = dominant_colors(cutout)
    final = add_glow(cutout)
    result["png"] = to_png_bytes(final)
    result["width"], result["height"] = final.size
    return result
