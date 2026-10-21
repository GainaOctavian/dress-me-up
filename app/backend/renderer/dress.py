"""3D fitting (plan 19): dress the Anny mannequin with garment shells and
render it with Blender. No I/O besides the body assets and the output file.

A garment is a shell cut out of the body mesh, pushed out along the
normals, and textured with the cutout photo:
- every body vertex is projected into the neutral body image (the same
  orthographic camera the body PNGs use);
- a thin-plate spline (TPS) built from garment anchors <-> body keypoints maps
  that image point into the garment photo: that's the vertex's UV;
- vertices where the photo is opaque belong to the garment; the texture's
  alpha clips the exact edge (hems, necklines follow the photo);
- the shell's distance from the skin grows with the plan 11 draw band, so
  layers stack (tucked shirt < trousers < untucked shirt < coat).
Anny's topology is the same in every pose, so the UVs found on the neutral
pose dress the posed mesh as is.

Shoes, hats, belts and scarves are body regions in the item's color (their
side-view photos can't texture a front view).
"""
import json
import math
import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

# same camera as app/infra/body-assets/render_bodies.py (keep in sync)
SIZE = (1200, 1800)
WORLD_H = 1.85
FLOOR_Y = 0.97
BODY_ASSETS = Path(os.getenv("BODY_ASSETS", "/body-assets"))  # render_bodies.py's out/
GENDER = {"mannequin_male": 0.0, "mannequin_female": 1.0}

# hem level per type: 0 waist, 1 hip, 2 crotch, 3 knee, 4 ankle (= utils/fit.ts LENGTH)
LENGTH = {
    "tank_top": 1.2, "undershirt": 1.2, "t_shirt": 1.5, "polo": 1.5, "blouse": 1.5,
    "shirt": 1.8, "sweater": 1.4, "sweatshirt": 1.4, "hoodie": 1.5, "cardigan": 1.5,
    "blazer": 1.8, "jacket": 1.6, "denim_jacket": 1.4, "leather_jacket": 1.4, "bomber": 1.2,
    "gilet": 1.4, "puffer": 1.6, "coat": 3.2, "parka": 2.6, "trench": 3.3,
    "dress": 2.9, "jumpsuit": 4.0,
}
FULL_LENGTH = {"jeans", "trousers", "chinos", "sweatpants", "leggings", "tights"}
ROLE_PAD = {"base": 1.0, "mid": 1.03, "insulation": 1.07, "outer": 1.12, "over": 1.18}
EASE = 1.1
ARM_RADIUS_PX = 0.045 / WORLD_H * SIZE[1]  # upper arm, in body image px
SLEEVE_EASE = 1.15
FLAT_TO_WORN = 1.38


@dataclass
class Garment:
    """One outfit item, ready to wear. `image` is the glow-free cutout
    (RGBA uint8 array), `fit` the worker anchors, `band` its plan 11 z."""
    subcategory: Optional[str]
    slot: Optional[str]
    role: Optional[str]
    band: int
    image: Optional[np.ndarray] = None
    fit: Optional[dict] = None
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5)  # sRGB 0..1


# ---------------------------------------------------------------- body


@lru_cache(maxsize=1)
def _anny():
    import anny
    import torch
    return anny.Anny().to(dtype=torch.float32)


@lru_cache(maxsize=1)
def _manifest():
    return json.loads((BODY_ASSETS / "bodies.json").read_text())


@lru_cache(maxsize=16)
def body_mesh(body_id: str, pose_id: str):
    """(vertices m, faces) of a body in a pose (pose params pre-solved by
    render_bodies.py)."""
    import torch
    model = _anny()
    pheno = {k: 0.5 for k in model.phenotype_labels} | {"gender": GENDER[body_id]}
    pose = torch.from_numpy(np.load(BODY_ASSETS / body_id / f"{pose_id}.pose.npy"))
    out = model(pose_parameters=pose[None], phenotype_kwargs=pheno)
    return out["vertices"][0].numpy(), model.faces.numpy()


def camera(verts):
    """(cx, cz, world_w, world_h): the fixed camera, soles at FLOOR_Y."""
    world_w = WORLD_H * SIZE[0] / SIZE[1]
    return 0.0, verts[:, 2].min() + (FLOOR_Y - 0.5) * WORLD_H, world_w, WORLD_H


def to_px(points, cam):
    """World (x, z) -> body image px (x right, y down)."""
    cx, cz, w, h = cam
    return np.stack([((points[:, 0] - cx) / w + 0.5) * SIZE[0],
                     (0.5 - (points[:, 2] - cz) / h) * SIZE[1]], axis=1)


# ---------------------------------------------------------------- correspondences


def _keypoints(body_id):
    kp = _manifest()[body_id]["poses"]["neutral"]["keypoints"]
    return {k: np.array([v[0] * SIZE[0], v[1] * SIZE[1]]) for k, v in kp.items()}


def _level_y(k, t):
    """Body image y of a hem level (0 waist .. 4 ankle)."""
    ys = [k["waist"][1], (k["hip_l"][1] + k["hip_r"][1]) / 2, k["crotch"][1],
          (k["knee_l"][1] + k["knee_r"][1]) / 2, (k["ankle_l"][1] + k["ankle_r"][1]) / 2]
    i = min(int(t), 3)
    return ys[i] + (ys[i + 1] - ys[i]) * (t - i)


def _leg_centers(mask, y):
    """Centers of the two leg runs left/right of the middle at row y."""
    cols = np.flatnonzero(mask[y])
    if len(cols) == 0:
        return None
    mid = (cols.min() + cols.max()) / 2
    left, right = cols[cols < mid], cols[cols >= mid]
    if len(left) == 0 or len(right) == 0:
        return None
    return left.mean(), right.mean()


def _cross_section(mask, point, normal, reach=400):
    """Centre and half width of the mask along `normal` through `point`."""
    def extent(sign):
        for d in range(reach):
            x, y = (point + sign * normal * d).round().astype(int)
            if not (0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]) or not mask[y, x]:
                return d
        return reach
    d_plus, d_minus = extent(1), extent(-1)
    return point + normal * (d_plus - d_minus) / 2, (d_plus + d_minus) / 2


def correspondences(g: Garment, k) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """(body image px, garment px) point pairs for the TPS, or None when the
    garment isn't a top/dress/bottom with anchors."""
    if g.fit is None or g.image is None:
        return None
    gh, gw = g.image.shape[:2]
    a = {n: np.array(v, float) * [gw, gh] for n, v in g.fit.items() if isinstance(v, list)}
    mask = g.image[..., 3] > 128
    pad = ROLE_PAD.get(g.role or "mid", 1.03)
    body, garment = [], []

    def pair(b, gpt):
        body.append(b)
        garment.append(gpt)

    if g.slot in ("torso", "full"):
        neck, eye = k["neck"], (k["eye_l"] + k["eye_r"]) / 2
        top = neck[1] - 0.45 * (neck[1] - eye[1])
        hem_y = _level_y(k, LENGTH.get(g.subcategory or "", 1.6))
        collar = a["collar"]
        g_hem = max(a["hem_l"][1], a["hem_r"][1])
        sy = (hem_y - top) / max(1.0, g_hem - collar[1])
        if "shoulder_l" in a and "shoulder_r" in a:
            g_left, g_right = a["shoulder_r"][0], a["shoulder_l"][0]
        else:
            g_left, g_right = a["hem_r"][0], a["hem_l"][0]
        half = (k["chest_l"][0] - k["chest_r"][0]) / 2 * EASE * pad
        if "shoulder_l" not in a:
            half = max(half, (g_right - g_left) / 2 * sy / FLAT_TO_WORN * pad)
        by = lambda gy: top + (gy - collar[1]) * sy
        for t in (0.0, 0.35, 0.7, 1.0):  # torso: center and both edges, top to hem
            gy = collar[1] + 0.02 * gh + t * (g_hem - collar[1] - 0.02 * gh)
            pair([neck[0], by(gy)], [collar[0], gy])
            pair([neck[0] - half, by(gy)], [g_left, gy])
            pair([neck[0] + half, by(gy)], [g_right, gy])
        for s in ("l", "r"):
            if f"sleeve_{s}" not in a:
                continue
            sh, tip = a[f"shoulder_{s}"], a[f"sleeve_{s}"]
            joint = k[f"shoulder_{s}"]
            arm = k[f"wrist_{s}"] - joint
            length = min(np.linalg.norm(tip - sh) * sy, np.linalg.norm(arm) * 1.05)
            direction = arm / np.linalg.norm(arm)
            normal = np.array([-direction[1], direction[0]])
            g_dir = (tip - sh) / max(1.0, np.linalg.norm(tip - sh))
            g_normal = np.array([-g_dir[1], g_dir[0]])
            # shoulder cap: the top of the body's shoulder <-> where the sleeve
            # leaves the garment's top edge (just inside the cloth)
            out_x = 1 if s == "l" else -1
            pair(joint + [0, -ARM_RADIUS_PX * 0.9], sh + [out_x * 0.01 * gw, 0.03 * gh])
            # the sleeve's centre line and both edges, mapped onto the arm
            for t in (0.3, 0.65, 0.95):
                centre, half_w = _cross_section(mask, sh + (tip - sh) * t, g_normal)
                b = joint + direction * length * t
                arm_half = ARM_RADIUS_PX * (1 - 0.25 * t) * SLEEVE_EASE
                pair(b, centre)
                if half_w > 2:
                    # outer edge everywhere; the inner edge only away from the
                    # armpit, where it would sit on top of the torso-edge point
                    # and fold the spline (holes under the arms)
                    outer = 1 if (normal @ (b - k["neck"])) > 0 else -1
                    pair(b + outer * normal * arm_half, centre + outer * g_normal * half_w * np.sign(g_normal @ (centre - collar)))
                    if t > 0.5:
                        pair(b - outer * normal * arm_half, centre - outer * g_normal * half_w * np.sign(g_normal @ (centre - collar)))
    elif g.slot == "legs":
        wy = k["waist"][1] + 0.35 * ((k["hip_l"][1] + k["hip_r"][1]) / 2 - k["waist"][1])
        cx = k["crotch"][0]
        half = ((k["waist_l"][0] - k["waist_r"][0]) * 0.65 + (k["hip_l"][0] - k["hip_r"][0]) * 0.35) / 2 * pad
        tl, tr = a["top_l"], a["top_r"]
        g_top = tl[1]
        g_hem = max(a["hem_l"][1], a["hem_r"][1])
        sx = 2 * half / max(1.0, tl[0] - tr[0])
        pair([cx - half, wy], tr)
        pair([cx + half, wy], tl)
        pair([cx, wy], [(tl[0] + tr[0]) / 2, g_top])
        full = (g.subcategory or "") in FULL_LENGTH
        floor = (k["ankle_l"][1] + k["ankle_r"][1]) / 2
        hem_body = (floor + k["heel_l"][1]) / 2 if full else wy + (g_hem - g_top) * sx * FLAT_TO_WORN / pad
        sy = (hem_body - wy) / max(1.0, g_hem - g_top)
        center = min(int(round((tl[0] + tr[0]) / 2)), mask.shape[1] - 1)
        # crotch: the first gap after the opaque waistband (the very top rows
        # can be transparent between belt loops). Legs photographed
        # overlapping have no gap until the hems: assume a typical rise.
        col = mask[int(g_top):int(g_hem), center]
        on = int(np.argmax(col))
        gap = np.flatnonzero(~col[on:])
        rise = (on + gap[0]) / (g_hem - g_top) if len(gap) else 1.0
        if g.subcategory != "skirt":
            g_crotch = g_top + (on + gap[0] if 0.15 < rise < 0.6 else 0.3 * (g_hem - g_top))
            pair([cx, k["crotch"][1]], [center, g_crotch])
            for t in (0.5, 1.0):  # each leg's centre line, crotch -> hem
                gy = int(g_crotch + (g_hem - 2 - g_crotch) * t)
                legs = _leg_centers(mask, gy)
                if legs is None:
                    continue
                knee_or_hem = lambda s: (k[f"knee_{s}"] if t == 0.5 else
                                         np.array([k[f"ankle_{s}"][0], hem_body]))
                if not full:  # shorts: same proportion down the thigh
                    knee_or_hem = lambda s: k[f"hip_joint_{s}"] + (k[f"knee_{s}"] - k[f"hip_joint_{s}"]) * (
                        (wy + (gy - g_top) * sy - k[f"hip_joint_{s}"][1]) / (k[f"knee_{s}"][1] - k[f"hip_joint_{s}"][1]))
                pair(knee_or_hem("r"), [legs[0], gy])
                pair(knee_or_hem("l"), [legs[1], gy])
        else:  # skirt: a trapezoid
            pair([cx - half * 1.3, hem_body], a["hem_r"])
            pair([cx + half * 1.3, hem_body], a["hem_l"])
    else:
        return None
    return np.array(body, float), np.array(garment, float)


def close_notches(image: np.ndarray, top_rows_from: Optional[int] = None) -> np.ndarray:
    """Fill the notches of a flat-lay photo with the nearest cloth colour:
    on a body they're cloth (the arm's underside, the torso's side).
    Tops (`top_rows_from` = first row below the shoulders): every row is
    filled between its outermost cloth pixels, so the triangle under each
    sleeve closes while the neckline above stays open. Bottoms: only narrow
    notches (a closing), so the gap between the legs stays."""
    from scipy import ndimage
    mask = image[..., 3] > 128
    if top_rows_from is not None:
        closed = mask.copy()
        for y in range(max(0, top_rows_from), mask.shape[0]):
            cols = np.flatnonzero(mask[y])
            if len(cols):
                closed[y, cols[0]:cols[-1] + 1] = True
    else:
        r = max(3, int(0.05 * max(mask.shape)))
        disk = np.hypot(*np.mgrid[-r:r + 1, -r:r + 1]) <= r
        closed = ndimage.binary_closing(np.pad(mask, r), structure=disk)[r:-r, r:-r]
    fill = closed & ~mask
    if not fill.any():
        return image
    _, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)
    out = image.copy()
    out[fill, :3] = image[iy[fill], ix[fill], :3]
    out[fill, 3] = 255
    return out


def garment_uv(g: Garment, k, verts_px) -> Optional[np.ndarray]:
    """Garment px for every body vertex (projected on the neutral image)."""
    pairs = correspondences(g, k)
    if pairs is None:
        return None
    from scipy.interpolate import RBFInterpolator
    body_pts, garment_pts = pairs
    # drop duplicates (TPS needs distinct sources)
    _, keep = np.unique(np.round(body_pts, 1), axis=0, return_index=True)
    tps = RBFInterpolator(body_pts[keep], garment_pts[keep], kernel="thin_plate_spline", smoothing=1.0)
    return tps(verts_px)


def region(g: Garment, k, verts_px) -> Optional[np.ndarray]:
    """Color-only items: which body vertices they cover (by image y)."""
    y = verts_px[:, 1]
    eye = (k["eye_l"][1] + k["eye_r"][1]) / 2
    if g.slot == "feet":
        return y > (k["ankle_l"][1] + k["ankle_r"][1]) / 2 - 15
    if g.slot == "head":
        return y < eye - (k["neck"][1] - eye) * 0.35
    if g.slot == "waist":
        wy = k["waist"][1] + 0.35 * ((k["hip_l"][1] + k["hip_r"][1]) / 2 - k["waist"][1])
        return np.abs(y - wy) < 22
    if g.subcategory == "scarf":
        return np.abs(y - k["neck"][1]) < 40
    return None


# ---------------------------------------------------------------- scene


def _scene():
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    world_w = WORLD_H * SIZE[0] / SIZE[1]
    cam = bpy.data.cameras.new("cam")
    cam.type, cam.ortho_scale = "ORTHO", WORLD_H
    cam_obj = bpy.data.objects.new("cam", cam)
    cam_obj.rotation_euler = (math.pi / 2, 0, 0)  # look +Y, Z up
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    for name, energy, rx, rz in (("key", 2.2, 55, -30), ("rim", 0.8, 110, 160)):
        sun = bpy.data.lights.new(name, "SUN")
        sun.energy, sun.angle = energy, math.radians(20)
        obj = bpy.data.objects.new(name, sun)
        obj.rotation_euler = (math.radians(rx), 0, math.radians(rz))
        scene.collection.objects.link(obj)
    scene.world = bpy.data.worlds.new("world")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.18, 0.2, 1)
    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device, scene.cycles.samples = "CPU", 48
    scene.cycles.use_denoising = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = *SIZE, 100
    r.film_transparent = True
    r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGBA"
    scene.view_settings.view_transform = "Standard"
    return scene, cam_obj, world_w


def _mesh(scene, name, verts, faces, uv=None):
    import bpy
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [], faces.tolist())
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    if uv is not None:
        layer = mesh.uv_layers.new(name="uv")
        loop_verts = np.zeros(len(mesh.loops), dtype=np.int32)
        mesh.loops.foreach_get("vertex_index", loop_verts)
        layer.data.foreach_set("uv", uv[loop_verts].astype(np.float32).ravel())
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    return obj


def _material(name, color=None, image_path=None):
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85
    if image_path:
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(image_path)
        tex.extension = "CLIP"  # outside the photo = transparent
        mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (*[c ** 2.2 for c in color], 1)
    return mat


def render_outfit(body_id: str, pose_id: str, garments: List[Garment], out_path: str) -> None:
    """Render the mannequin wearing `garments` (bottom layer first)."""
    import trimesh
    neutral, faces = body_mesh(body_id, "neutral")
    posed, _ = body_mesh(body_id, pose_id)
    import bpy  # after torch (Anny): bpy needs the OpenMP runtime torch loads
    k = _keypoints(body_id)
    verts_px = to_px(neutral, camera(neutral))
    normals = trimesh.Trimesh(posed, faces, process=False).vertex_normals
    eye_y = (k["eye_l"][1] + k["eye_r"][1]) / 2
    head = verts_px[:, 1] < k["neck"][1] - 0.2 * (k["neck"][1] - eye_y)  # chin and up

    scene, cam_obj, _ = _scene()
    cx, cz, _, _ = camera(posed)
    cam_obj.location = (cx, -5, cz)
    body = _mesh(scene, "body", posed, faces)
    body.data.materials.append(_material("skin", color=(0.73, 0.73, 0.75)))

    tmp = tempfile.mkdtemp()
    for i, g in enumerate(garments):
        if g.image is not None and g.slot in ("torso", "full", "legs"):
            shoulders = [g.fit[s][1] for s in ("shoulder_l", "shoulder_r") if g.fit and s in g.fit]
            below = int((max(shoulders) + 0.05) * g.image.shape[0]) if shoulders and g.slot != "legs" else None
            g.image = close_notches(g.image, below)
        uv = garment_uv(g, k, verts_px)
        if uv is not None:
            gh, gw = g.image.shape[:2]
            ix = np.clip(uv[:, 0].round().astype(int), 0, gw - 1)
            iy = np.clip(uv[:, 1].round().astype(int), 0, gh - 1)
            inside = (uv[:, 0] >= 0) & (uv[:, 0] < gw) & (uv[:, 1] >= 0) & (uv[:, 1] < gh)
            covered = inside & (g.image[iy, ix, 3] > 64)
        else:
            covered = region(g, k, verts_px)
            if covered is None:
                continue
        if g.slot not in ("head", "eyes"):
            covered = covered & ~head
        keep = covered[faces].any(axis=1)
        if not keep.any():
            continue
        used = np.unique(faces[keep])
        remap = np.full(len(posed), -1)
        remap[used] = np.arange(len(used))
        # m: cloth layers stack by draw band; colour shells (shoes, caps) sit
        # on the skin whatever their band
        offset = (2.0 + 0.3 * g.band) / 1000.0 if uv is not None else 0.004
        shell_verts = posed[used] + normals[used] * offset
        if uv is not None:
            from PIL import Image
            path = os.path.join(tmp, f"g{i}.png")
            Image.fromarray(g.image).save(path)
            gh, gw = g.image.shape[:2]
            shell_uv = np.stack([uv[used, 0] / gw, 1 - uv[used, 1] / gh], axis=1)
            obj = _mesh(scene, f"g{i}", shell_verts, remap[faces[keep]], shell_uv)
            obj.data.materials.append(_material(f"m{i}", image_path=path))
        else:
            # a colour shell is a soft cover (shoe, cap), not a second skin:
            # smooth away toes/ears, then push it out a bit more
            shell = trimesh.Trimesh(shell_verts, remap[faces[keep]], process=False)
            # no volume constraint: on an open shell it rescales around the origin
            trimesh.smoothing.filter_laplacian(shell, iterations=20, volume_constraint=False)
            shell_verts = np.asarray(shell.vertices) + normals[used] * 0.006
            obj = _mesh(scene, f"g{i}", shell_verts, remap[faces[keep]])
            color = g.color
            if g.image is not None:  # the photo's own colour beats the palette name
                opaque = g.image[g.image[..., 3] > 200][:, :3]
                if len(opaque):
                    color = tuple(np.median(opaque, axis=0) / 255)
            obj.data.materials.append(_material(f"m{i}", color=color))

    scene.render.filepath = os.path.abspath(out_path)
    bpy.ops.render.render(write_still=True)
