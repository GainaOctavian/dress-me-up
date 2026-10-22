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
    # collared, buttoned: closest model for shirts and jackets (CC-BY, see app/infra/clothes)
    **dict.fromkeys(["shirt", "blazer", "jacket", "denim_jacket", "leather_jacket", "bomber", "gilet",
                     "puffer"], ("elvs_male_shirt_untucked_bd1",) * 2),
    **dict.fromkeys(["sweatshirt", "hoodie"], ("elvs_hooded_sweat_jacket1",) * 2),
    "sweater": ("mindfront_knitted_sweater_02",) * 2,
    **dict.fromkeys(["cardigan", "coat", "parka", "trench"], ("mindfront_cardigan_long_open_front",) * 2),
    **dict.fromkeys(["jeans", "trousers", "chinos", "sweatpants", "leggings", "tights"], ("toigo_wool_pants",) * 2),
    "shorts": ("cortu_jeans_shorts",) * 2,
    "skirt": ("toigo_tiered_mini_skirt",) * 2,
    **dict.fromkeys(["dress", "jumpsuit"], ("toigo_shift_dress",) * 2),
    **dict.fromkeys(["sneakers", "boots", "dress_shoes", "loafers", "sandals", "heels", "socks"],
                    ("toigo_ankle_boots_male", "toigo_flats")),
}


OPEN = {"F_Cardigan_Long_Open_Front"}  # open-front models: what's under them shows


@lru_cache(maxsize=1)
def _model():
    import anny
    import torch
    return anny.Anny(topology="anny-full").to(dtype=torch.float32)


@lru_cache(maxsize=16)
def full_body(body_id: str, pose_id: str) -> np.ndarray:
    """The body in MakeHuman's hm08 topology (helpers included), posed."""
    import torch
    m = _model()
    pheno = {k: 0.5 for k in m.phenotype_labels} | {"gender": dress.GENDER[body_id]}
    pose = torch.from_numpy(np.load(dress.BODY_ASSETS / body_id / f"{pose_id}.pose.npy"))
    return m(pose_parameters=pose[None], phenotype_kwargs=pheno)["vertices"][0].numpy()


def body_faces() -> np.ndarray:
    faces = _model().faces.numpy()
    if faces.shape[1] == 4:
        faces = np.concatenate([faces[:, [0, 1, 2]], faces[:, [0, 2, 3]]])
    return faces[(faces < mhclo.BODY_VERTS).all(axis=1)]


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
        if not name:
            continue
        folder = CLOTHES / name[1 if female else 0]
        wearing.append((g, mhclo.load(str(next(folder.glob("*.mhclo"))))))

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

    # untucked closed tops hide the trousers' waist under them: not drawn,
    # or it pokes through the hem (like delete_verts does for the skin)
    centre = neutral[:mhclo.BODY_VERTS, :2].mean(axis=0)
    sector = lambda v: ((np.arctan2(*(v[:, :2] - centre).T[::-1]) + np.pi) / (2 * np.pi) * 36).astype(int) % 36

    def hem(v):  # lowest point of a top, per 10 degrees round the body
        out = np.full(36, np.inf)
        np.minimum.at(out, sector(v), v[:, 2])
        return out
    hems = [hem(c.fit(neutral)) if g.slot not in ("legs", "feet") and c.name not in OPEN else None
            for g, c in wearing]
    tmp = tempfile.mkdtemp()
    for i, (g, c) in enumerate(wearing):
        shoes = g.slot == "feet"
        kind = "legs" if g.slot == "legs" else "top"
        vn, vp = c.fit(neutral), c.fit(posed)
        tv, tu = c.triangles()
        over = [h for h in hems[i + 1:] if h is not None]
        if kind == "legs" and over:
            cut = np.min(over, axis=0)[sector(vn)] + 0.01
            shown = ~(vn[:, 2] > cut)[tv].all(axis=1)
            tv, tu = tv[shown], tu[shown]
        mesh = bpy.data.meshes.new(c.name)
        mesh.from_pydata(vp.tolist(), [], tv.tolist())
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.uv_layers.new(name="uv").data.foreach_set("uv", c.uvs[tu.ravel()].astype(np.float32).ravel())
        detail = c.texture if c.texture and os.path.exists(c.texture) else None
        fab = fabric.analyse(g.image) if g.image is not None else fabric.Fabric(g.color)
        px = dress.to_px(vn, cam_n)
        q = fabric.photo_coords(px, mhclo.landmarks(px, kind, k), g.fit, g.image.shape[:2]) \
            if not shoes and g.image is not None and g.fit else None
        if q is None:  # no photo anchors: shoes, or old items - colour only
            fab = fabric.Fabric(fab.colour)
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
        if shoes:  # rigid; trousers are modelled to go into them
            continue
        colliders.append(mhclo.settle(scene, obj, colliders))

    scene.render.filepath = os.path.abspath(out_path)
    bpy.ops.render.render(write_still=True)
