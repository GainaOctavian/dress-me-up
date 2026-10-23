"""Dress the 3D mannequin like a game character (plan 19, v5).

Every item type wears a modelled 3D garment (MakeHuman CC0 / CC-BY clothes
in app/infra/clothes, bound to the body through .mhclo, so it follows any
shape and pose). The item's photo is taken apart (fabric.py): the cloth's
colour or a seamless tile of its pattern covers the whole garment at real
scale, and prints/logos/pockets go on the front where they are on the
photo, unstretched. A short
cloth simulation without gravity pushes every layer out of the body and
the layers under it (no clipping), then Blender takes the picture.

Items without a model (belts, hats, ties, bags...) aren't drawn yet.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np

from app.backend.renderer import dress, fabric, mhclo

CLOTHES = Path(os.getenv("CLOTHES", "/clothes"))

# item type -> (model for men, model for women)
MODEL = {
    **dict.fromkeys(["t_shirt", "undershirt", "tank_top", "top", "blouse"],
                    ("elvs_crude_t-shirt_male", "joepal_crude_t-shirt_female")),
    "polo": ("namuhekam_male_polo_shirt", "joepal_crude_t-shirt_female"),
    "shirt": ("elvs_male_shirt_untucked_bd1",) * 2,
    # jackets are cut out of suits (app/infra/clothes/split_parts.py)
    "blazer": ("toigo_male_blazer", "toigo_female_blazer"),
    **dict.fromkeys(["jacket", "denim_jacket", "leather_jacket", "bomber", "gilet", "puffer"],
                    ("toigo_male_jacket", "toigo_female_jacket")),
    **dict.fromkeys(["sweatshirt", "hoodie"], ("elvs_hooded_sweat_jacket1",) * 2),
    "sweater": ("mindfront_knitted_sweater_02",) * 2,
    **dict.fromkeys(["cardigan", "coat", "parka", "trench"], ("mindfront_cardigan_long_open_front",) * 2),
    **dict.fromkeys(["jeans", "trousers", "chinos", "sweatpants", "leggings", "tights"], ("toigo_wool_pants",) * 2),
    "shorts": ("cortu_jeans_shorts",) * 2,
    "skirt": ("toigo_tiered_mini_skirt",) * 2,
    **dict.fromkeys(["dress", "jumpsuit"], ("toigo_shift_dress",) * 2),
    "socks": ("joepal_crude_low_socks",) * 2,
    "sneakers": ("punkduck_running_shoes_01",) * 2,
    "boots": ("toigo_ankle_boots_male", "toigo_ankle_boots_female"),
    "dress_shoes": ("mindfront_shoes_oxford_male", "mindfront_shoes_oxford_female"),
    "loafers": ("mindfront_shoes_monk_strap_male", "mindfront_shoes_monk_strap_female"),
    "sandals": ("elvs_caesar_sandals1",) * 2,
    "heels": ("toigo_stiletto_booties",) * 2,
    "cap": ("mindfront_patrol_cap",) * 2,
    "hat": ("elvs_male_trilby_hat",) * 2,
    "beanie": ("mindfront_knitted_hat_01",) * 2,
    "glasses": ("spamrakuen_tbm_glasses_frames_01",) * 2,
    "sunglasses": ("elvs_ladies_sunglass1",) * 2,
    "tie": ("toigo_tie",) * 2,
    "bow_tie": ("toigo_bow_tie",) * 2,
    "gloves": ("toigo_gloves_short",) * 2,
    **dict.fromkeys(["bag", "backpack"], ("punkduck_handbag01",) * 2),
}
# no model: a band round the body (Band): (height, gap) in metres
BANDS = {"belt": (0.035, 0.004), "watch": (0.02, 0.004), "bracelet": (0.008, 0.003)}
RIGID = {"head", "eyes", "neck", "waist", "wrist", "hands", "bag", "feet"}  # no cloth sim
COLLIDE = {"neck", "waist"}  # rigid, but the tops settle over them (tie, belt)


# tailored garments keep their modelled shape in the sim (mhclo.settle hold)
HOLD = {**dict.fromkeys(["blazer", "jacket", "denim_jacket", "leather_jacket", "bomber", "gilet", "puffer"], 0.6),
        **dict.fromkeys(["jeans", "trousers", "chinos", "sweatpants"], 0.4)}  # waistbands bunched over tucked shirts
INFLATE = 0.005  # m per cloth layer already on: a garment starts outside the ones under it


@lru_cache(maxsize=1)
def _model():
    import anny
    import torch
    torch.set_num_threads(int(os.getenv("RENDER_THREADS", "8")))
    return anny.Anny(topology="anny-full").to(dtype=torch.float32)


@lru_cache(maxsize=16)
def _posed(body_id: str, pose_id: str):
    """(vertices, {bone: head position}) of the posed body."""
    import torch
    m = _model()
    pheno = {k: 0.5 for k in m.phenotype_labels} | {"gender": dress.GENDER[body_id]}
    pose = torch.from_numpy(np.load(dress.BODY_ASSETS / body_id / f"{pose_id}.pose.npy"))
    out = m(pose_parameters=pose[None], phenotype_kwargs=pheno)
    joints = dict(zip(m.bone_labels, out["bone_poses"][0, :, :3, 3].numpy()))
    return out["vertices"][0].numpy(), joints


def full_body(body_id: str, pose_id: str) -> np.ndarray:
    """The body in MakeHuman's hm08 topology (helpers included), posed."""
    return _posed(body_id, pose_id)[0]


class Band:
    """A belt / watch / bracelet: a ring round a slice of vertices (of the
    body, or of the trousers for a belt) picked on the neutral pose. The
    same vertices are used in every pose, so it follows the body. Duck-types
    mhclo.Clothes for render_outfit."""

    def __init__(self, name, source, neutral, idx, height, gap, n=32):
        self.name, self.source, self.idx = name, source, idx
        self.height, self.gap, self.n = height, gap, n
        self.delete_verts, self.texture = np.zeros(0, int), None
        p = source(neutral)[idx]
        axis, ref = self._frame(p)
        r = p - p.mean(axis=0)
        ang = np.arctan2(r @ np.cross(axis, ref), r @ ref)
        self.bins = ((ang + np.pi) / (2 * np.pi) * n).astype(int) % n
        self.uvs = np.array([[j / n, v] for v in (0, 1) for j in range(n + 1)])

    @staticmethod
    def _frame(p):
        """The ring's axis (the slice's thinnest direction) and a direction across it."""
        _, vec = np.linalg.eigh(np.cov((p - p.mean(axis=0)).T))
        return vec[:, 0] * (1 if vec[2, 0] >= 0 else -1), vec[:, 2]

    def fit(self, body):
        p = self.source(body)[self.idx]
        c = p.mean(axis=0)
        axis, _ = self._frame(p)
        ring = np.full((self.n, 3), np.nan)
        for j in range(self.n):
            if (self.bins == j).any():
                ring[j] = p[self.bins == j].mean(axis=0)
        ok = ~np.isnan(ring[:, 0])
        for d in range(3):  # empty bins: interpolate round the ring
            ring[:, d] = np.interp(np.arange(self.n), np.flatnonzero(ok), ring[ok, d], period=self.n)
        r = ring - c
        r -= np.outer(r @ axis, axis)
        r *= 1 + self.gap / np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-6)
        ring = np.vstack([c + r, c + r[:1]])  # the seam gets its own uv column
        return np.vstack([ring - axis * self.height / 2, ring + axis * self.height / 2])

    def triangles(self):
        m = self.n + 1
        tv = np.array([t for j in range(self.n) for t in ((j, j + 1, m + j + 1), (j, m + j + 1, m + j))])
        return tv, tv


def band(sub: str, wearing, body_id: str):
    """The Band for a belt (over the trousers: None without) / watch / bracelet (left wrist)."""
    height, gap = BANDS[sub]
    neutral, joints = _posed(body_id, "neutral")
    if sub == "belt":
        legs = [c for g, c in wearing if g.slot == "legs" and isinstance(c, mhclo.Clothes)]
        if not legs:
            return None
        v = legs[-1].fit(neutral)
        mid = v[:, 2].max() - 0.025  # just under the waistband's top edge
        idx = np.flatnonzero(np.abs(v[:, 2] - mid) < 0.012)
        return Band(sub, legs[-1].fit, neutral, idx, height, gap)
    wrist, fore = joints["wrist.L"], joints["lowerarm02.L"]
    axis = (wrist - fore) / np.linalg.norm(wrist - fore)
    d = neutral[:mhclo.BODY_VERTS] - (wrist - 0.03 * axis)  # just above the wrist joint
    idx = np.flatnonzero((np.abs(d @ axis) < 0.006) & (np.linalg.norm(d, axis=1) < 0.06))
    return Band(sub, lambda b: b[:mhclo.BODY_VERTS], neutral, idx, height, gap)


def body_faces() -> np.ndarray:
    faces = _model().faces.numpy()
    if faces.shape[1] == 4:
        faces = np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
    return faces[(faces < mhclo.BODY_VERTS).all(axis=1)]


def _onto(points, obj, gap):
    """`points` moved to the nearest spot on `obj`'s surface, `gap` outward
    (away from the vertical axis through their centre)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import bpy
    tree = BVHTree.FromObject(obj, bpy.context.evaluated_depsgraph_get())
    centre = points.mean(axis=0)
    out = []
    for p in points:
        loc = np.array(tree.find_nearest(Vector(p.tolist()))[0])
        side = loc - centre
        side[2] = 0
        out.append(loc + side / max(np.linalg.norm(side), 1e-6) * gap)
    return np.array(out)


def _hide_covered(drawn, front: float = 0.02, poke: float = 0.03):
    """Like delete_verts for the skin: faces of a garment with a later
    (outer) garment right in front of them (within `front` toward the
    camera) are hidden anyway - unless they poke through it, so they go.
    So do faces just in front of an outer one (within `poke`): they're
    the ones poking through. Where nothing is on top (a jacket's V, an
    open cardigan, below a hem) the inner garment stays whole."""
    import bmesh
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import bpy
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, depsgraph) for o in drawn]
    to_cam, away = Vector((0, -1, 0)), Vector((0, 1, 0))
    for i, inner in enumerate(drawn[:-1]):
        outer = trees[i + 1:]
        bm = bmesh.new()
        bm.from_mesh(inner.data)
        covered = {v.index for v in bm.verts
                   if any(tr.ray_cast(v.co, to_cam, front)[0] is not None
                          or tr.ray_cast(v.co, away, poke)[0] is not None for tr in outer)}
        # whole faces only: one sticking out past a lapel or a hem stays
        gone = [f for f in bm.faces if all(v.index in covered for v in f.verts)]
        if gone:
            bmesh.ops.delete(bm, geom=gone, context="FACES")
            bm.to_mesh(inner.data)
            inner.data.update()
        bm.free()


def render_outfit(body_id: str, pose_id: str, garments: List[dress.Garment], out_path: str) -> None:
    """`garments` bottom layer first (plan 11 draw order)."""
    import tempfile
    import trimesh
    from PIL import Image
    neutral, posed = full_body(body_id, "neutral"), full_body(body_id, pose_id)
    faces = body_faces()
    k = dress._keypoints(body_id)
    cam_n = dress.camera(neutral[:mhclo.BODY_VERTS])
    female = body_id.endswith("female")
    import bpy  # after torch (Anny): bpy needs the OpenMP runtime torch loads

    wearing = []
    for g in garments:
        name = MODEL.get(g.subcategory or "")
        if name:
            folder = CLOTHES / name[1 if female else 0]
            wearing.append((g, mhclo.load(str(next(folder.glob("*.mhclo"))))))
        elif g.subcategory in BANDS:
            b = band(g.subcategory, wearing, body_id)
            if b is not None:
                wearing.append((g, b))

    scene, cam, _ = dress._scene()
    cx, cz, _, _ = dress.camera(posed[:mhclo.BODY_VERTS])
    cam.location = (cx, -5, cz)
    hidden = np.zeros(len(posed), bool)
    for _, c in wearing:
        hidden[c.delete_verts] = True  # skin under the clothes
    body = dress._mesh(scene, "body", posed, faces[~hidden[faces].any(axis=1)])
    body.data.materials.append(dress._material("skin", color=(0.73, 0.73, 0.75)))
    collider = dress._mesh(scene, "collider", posed, faces)  # whole body, not rendered
    collider.hide_render = True
    colliders = [collider]
    from scipy.spatial import cKDTree
    normals = trimesh.Trimesh(posed[:mhclo.BODY_VERTS], faces, process=False).vertex_normals
    nearest = cKDTree(posed[:mhclo.BODY_VERTS])
    layers = 0  # cloth layers settled so far

    drawn = []  # final objects, bottom layer first
    tmp = tempfile.mkdtemp()
    for i, (g, c) in enumerate(wearing):
        rigid = g.slot in RIGID
        kind = "legs" if g.slot == "legs" else "top"
        vn, vp = c.fit(neutral), c.fit(posed)
        if isinstance(c, Band) and g.slot == "waist":  # onto the trousers as they settled
            vp = _onto(vp, [o for (gg, _), o in zip(wearing, drawn) if gg.slot == "legs"][-1], BANDS[g.subcategory][1])
        if not rigid and layers:  # models are made to sit on the body, not on our layers
            vp = vp + normals[nearest.query(vp)[1]] * INFLATE * layers
        tv, tu = c.triangles()
        mesh = bpy.data.meshes.new(c.name)
        mesh.from_pydata(vp.tolist(), [], tv.tolist())
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.uv_layers.new(name="uv").data.foreach_set("uv", c.uvs[tu.ravel()].astype(np.float32).ravel())
        detail = c.texture if c.texture and os.path.exists(c.texture) else None
        fab = fabric.analyse(g.image) if g.image is not None else fabric.Fabric(g.color)
        px = dress.to_px(vn, cam_n)
        q = fabric.photo_coords(px, mhclo.landmarks(px, kind, k), g.fit, g.image.shape[:2]) \
            if not rigid and g.image is not None and g.fit else None
        if q is None:  # no photo anchors (accessories, shoes, old items): colour; a tie keeps its pattern
            fab = fabric.Fabric(fab.colour, tile=fab.tile if g.slot == "neck" else None)
            q = px

        def uv_layer(name, uv):
            mesh.uv_layers.new(name=name).data.foreach_set("uv", uv[tv.ravel()].astype(np.float32).ravel())

        tile = decals = None
        if fab.tile is not None:  # repeats at its real size (photo px)
            th, tw = fab.tile.shape[:2]
            uv_layer("tile", np.stack([q[:, 0] / tw, -q[:, 1] / th], axis=1))
            tile = os.path.join(tmp, f"tile{i}.png")
            Image.fromarray(fab.tile).save(tile)
        if fab.decals is not None:  # where they are on the photo, unstretched
            ph, pw = fab.decals.shape[:2]
            uv_layer("decal", np.stack([q[:, 0] / pw, 1 - q[:, 1] / ph], axis=1))
            decals = os.path.join(tmp, f"decals{i}.png")
            Image.fromarray(fab.decals).save(decals)
        mesh.materials.append(mhclo.material(f"front{i}", fab.colour, tile, decals, detail))
        if decals:  # prints only on faces seen from the front (camera at -y)
            mesh.materials.append(mhclo.material(f"back{i}", fab.colour, tile, None, detail))
            fn = trimesh.Trimesh(vn, tv, process=False).face_normals
            mesh.polygons.foreach_set("material_index", ((fn[:, 1] > -0.2) & (fn[:, 2] < 0.6)).astype(int).tolist())
        mesh.update()
        obj = bpy.data.objects.new(c.name, mesh)
        scene.collection.objects.link(obj)
        if not rigid:
            obj = mhclo.settle(scene, obj, colliders, HOLD.get(g.subcategory, 0.0))
            colliders.append(obj)
            layers += 1
        elif g.slot in COLLIDE:  # not shoes: trousers are modelled to go into them
            colliders.append(obj)
        drawn.append(obj)

    _hide_covered(drawn)
    scene.render.filepath = os.path.abspath(out_path)
    bpy.ops.render.render(write_still=True)
