"""Dress the 3D mannequin like a game character (plan 19, v4).

Every item type wears a modelled 3D garment (MakeHuman CC0 clothes in
app/infra/clothes, bound to the body through .mhclo, so it follows any
shape and pose); the item's photo is its texture (front projection,
mhclo.photo_uv) and the back gets the photo's cloth colour. A short
cloth simulation without gravity pushes every layer out of the body and
the layers under it (no clipping), then Blender takes the picture.

Items without a model (belts, hats, ties, bags...) aren't drawn yet.
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import List

import numpy as np

from app.backend.renderer import dress, mhclo

CLOTHES = Path(os.getenv("CLOTHES", "/clothes"))

# item type -> (model for men, model for women)
MODEL = {
    **dict.fromkeys(["t_shirt", "undershirt", "tank_top", "top", "blouse"],
                    ("elvs_crude_t-shirt_male", "joepal_crude_t-shirt_female")),
    "polo": ("namuhekam_male_polo_shirt", "joepal_crude_t-shirt_female"),
    # no button-up shirts / jackets / coats in the CC0 packs yet: long-sleeved knit
    **dict.fromkeys(["shirt", "sweater", "sweatshirt", "hoodie", "cardigan", "blazer", "jacket",
                     "denim_jacket", "leather_jacket", "bomber", "gilet", "puffer", "coat", "parka",
                     "trench"], ("toigo_fisherman_sweater",) * 2),
    **dict.fromkeys(["jeans", "trousers", "chinos", "sweatpants", "leggings", "tights"], ("toigo_wool_pants",) * 2),
    "shorts": ("cortu_jeans_shorts",) * 2,
    "skirt": ("toigo_tiered_mini_skirt",) * 2,
    **dict.fromkeys(["dress", "jumpsuit"], ("toigo_shift_dress",) * 2),
    **dict.fromkeys(["sneakers", "boots", "dress_shoes", "loafers", "sandals", "heels", "socks"],
                    ("toigo_ankle_boots_male", "toigo_flats")),
}


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

    tmp = tempfile.mkdtemp()
    for i, (g, c) in enumerate(wearing):
        shoes = g.slot == "feet"
        kind = "legs" if g.slot == "legs" else "top"
        vn, vp = c.fit(neutral), c.fit(posed)
        tv, tu = c.triangles()
        colour = g.color
        if g.image is not None:
            opaque = g.image[g.image[..., 3] > 200][:, :3]
            if len(opaque):
                colour = tuple(np.median(opaque, axis=0) / 255)
        puv = None
        if not shoes and g.image is not None and g.fit:
            puv = mhclo.photo_uv(dress.to_px(vn, cam_n), kind, k, g.fit, g.image.shape[:2], g.image[..., 3] > 128)
        mesh = bpy.data.meshes.new(c.name)
        mesh.from_pydata(vp.tolist(), [], tv.tolist())
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.uv_layers.new(name="uv").data.foreach_set("uv", c.uvs[tu.ravel()].astype(np.float32).ravel())
        detail = c.texture if c.texture and os.path.exists(c.texture) else None
        if puv is not None:
            mesh.uv_layers.new(name="photo").data.foreach_set("uv", puv[tv.ravel()].astype(np.float32).ravel())
            path = os.path.join(tmp, f"photo{i}.png")
            Image.fromarray(mhclo.fill_photo(g.image)).save(path)
            mesh.materials.append(mhclo.photo_material(f"front{i}", path, detail))
            mesh.materials.append(mhclo.photo_material(f"back{i}", None, detail, colour))
            # faces seen from the front (and the shoulders' tops) get the photo
            fn = trimesh.Trimesh(vn, tv, process=False).face_normals
            mesh.polygons.foreach_set("material_index", ((fn[:, 1] > -0.2) & (fn[:, 2] < 0.6)).astype(int).tolist())
        else:
            mesh.materials.append(mhclo.photo_material(f"plain{i}", None, detail, colour))
        mesh.update()
        obj = bpy.data.objects.new(c.name, mesh)
        scene.collection.objects.link(obj)
        if shoes:  # rigid; trousers are modelled to go into them
            continue
        colliders.append(mhclo.settle(scene, obj, colliders))

    scene.render.filepath = os.path.abspath(out_path)
    bpy.ops.render.render(write_still=True)
