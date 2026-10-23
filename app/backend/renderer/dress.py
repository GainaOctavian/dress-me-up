"""Shared scene pieces of the 3D renderer (plan 19): the mannequin camera
(the same orthographic camera the body PNGs use), the body's neutral
keypoints, the item-as-garment record and small Blender helpers.
outfit3d.py does the dressing.
"""
import json
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

# same camera as app/infra/body-assets/render_bodies.py (keep in sync)
SIZE = (1200, 1800)
WORLD_H = 1.85
FLOOR_Y = 0.97
BODY_ASSETS = Path(os.getenv("BODY_ASSETS", "/body-assets"))  # render_bodies.py's out/
GENDER = {"mannequin_male": 0.0, "mannequin_female": 1.0}


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


@lru_cache(maxsize=1)
def _manifest():
    return json.loads((BODY_ASSETS / "bodies.json").read_text())


def camera(verts):
    """(cx, cz, world_w, world_h): the fixed camera, soles at FLOOR_Y."""
    world_w = WORLD_H * SIZE[0] / SIZE[1]
    return 0.0, verts[:, 2].min() + (FLOOR_Y - 0.5) * WORLD_H, world_w, WORLD_H


def to_px(points, cam):
    """World (x, z) -> body image px (x right, y down)."""
    cx, cz, w, h = cam
    return np.stack([((points[:, 0] - cx) / w + 0.5) * SIZE[0],
                     (0.5 - (points[:, 2] - cz) / h) * SIZE[1]], axis=1)


def _keypoints(body_id):
    kp = _manifest()[body_id]["poses"]["neutral"]["keypoints"]
    return {k: np.array([v[0] * SIZE[0], v[1] * SIZE[1]]) for k, v in kp.items()}


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
    # all cores starved Docker Desktop's VM (and everything in it) during renders
    scene.render.threads_mode = "FIXED"
    scene.render.threads = int(os.getenv("RENDER_THREADS", "8"))
    scene.cycles.use_denoising = True
    r.resolution_x, r.resolution_y, r.resolution_percentage = *SIZE, 100
    r.film_transparent = True
    r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGBA"
    scene.view_settings.view_transform = "Standard"
    return scene, cam_obj, world_w


def _mesh(scene, name, verts, faces, uv=None, edges=None):
    import bpy
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts.tolist(), [] if edges is None else edges.tolist(), faces.tolist())
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


def _material(name, color=None, image_path=None, alpha_only=False):
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
        if alpha_only:  # the photo's outline, a plain colour (back panels)
            bsdf.inputs["Base Color"].default_value = (*[c ** 2.2 for c in color], 1)
        else:
            mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        mat.node_tree.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (*[c ** 2.2 for c in color], 1)
    return mat
