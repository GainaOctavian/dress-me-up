"""Generate the built-in mannequins (plan 12).

Anny (Z up, front = -Y, .L = +X) gives the posed mesh and joints; Blender
renders a front orthographic PNG with a transparent background. Keypoints are
projected with the same camera, so they line up with the image exactly.

    docker run --rm -v <this dir>:/work dress-me-up-body-assets python render_bodies.py

Writes out/<body_id>/neutral.png and out/bodies.json (read by seed.py).
"""
import json
import math
import os

import anny
import bpy
import numpy as np
import torch
import trimesh

SIZE = (1200, 1800)  # px, 2:3
# Same camera for every body: same scale, feet on the same baseline
WORLD_H = 1.85  # m shown top to bottom
FLOOR_Y = 0.97  # image y (0..1) of the soles
OUT = "out"
BODIES = {"mannequin_male": 0.0, "mannequin_female": 1.0}  # Anny gender value

model = anny.Anny().to(dtype=torch.float32)
BONE = {b: i for i, b in enumerate(model.bone_labels)}


def rot(axis: str, deg: float) -> torch.Tensor:
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
    r = torch.eye(4)
    r[i, i], r[i, j], r[j, i], r[j, j] = c, -s, s, c
    return r


def run(pheno, pose):
    out = model(pose_parameters=pose[None], phenotype_kwargs=pheno)
    return out["vertices"][0].numpy(), out["bone_poses"][0, :, :3, 3].numpy()


def straighten_arms(pheno) -> torch.Tensor:
    """Anny's rest pose is an A-pose with forearms bent forward. Rotate each
    forearm (local x, then z) so the wrist continues the upper-arm line:
    a flat arm in the image plane is what 2D sleeves can follow."""
    pose = torch.eye(4)[None].repeat(model.bone_count, 1, 1)
    for side in ("L", "R"):
        fore = BONE[f"lowerarm01.{side}"]

        def miss(ax, az):
            pose[fore] = rot("x", ax) @ rot("z", az)
            _, j = run(pheno, pose)
            sh, el, wr = j[BONE[f"upperarm01.{side}"]], j[fore], j[BONE[f"wrist.{side}"]]
            d = (el - sh) / np.linalg.norm(el - sh)
            return np.linalg.norm(wr - (el + d * np.linalg.norm(wr - el)))

        ax = az = 0.0
        for step in (8, 2, 0.5):  # coordinate descent, coarse to fine
            for _ in range(2):
                ax = min((ax + k * step for k in range(-4, 5)), key=lambda a: miss(a, az))
                az = min((az + k * step for k in range(-4, 5)), key=lambda a: miss(ax, a))
        print(f"  forearm.{side}: x={ax} z={az} miss={miss(ax, az) * 100:.1f}cm")
        pose[fore] = rot("x", ax) @ rot("z", az)
    return pose


def torso_section(mesh, z):
    """Closed torso outline at height z (the loop around x=0, arms dropped)."""
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    loops = [np.asarray(d) for d in sec.discrete] if sec else []
    loops = [l for l in loops if l[:, 0].min() < 0 < l[:, 0].max()]
    return max(loops, key=lambda l: np.ptp(l[:, 0]), default=None)


def keypoints_and_measures(verts, faces, j):
    mesh = trimesh.Trimesh(verts, faces, process=False)
    J = lambda b: j[BONE[b]]
    z_top, z_floor = verts[:, 2].max(), verts[:, 2].min()
    z_hip = (J("upperleg01.L")[2] + J("upperleg01.R")[2]) / 2
    z_sh = (J("upperarm01.L")[2] + J("upperarm01.R")[2]) / 2

    # crotch: highest point of the gap between the legs
    mid = verts[(np.abs(verts[:, 0]) < 0.01) & (verts[:, 2] < z_hip) & (verts[:, 2] > J("lowerleg01.L")[2])]
    z_crotch = mid[:, 2].min()

    # waist: narrowest torso between hips and chest; chest: widest-front
    # point (max depth) in the upper torso
    def sections(lo, hi):
        secs = [(z, torso_section(mesh, z)) for z in np.linspace(lo, hi, 30)]
        return [(z, s) for z, s in secs if s is not None]

    torso = z_sh - z_hip
    z_waist, waist = min(sections(z_hip + 0.15 * torso, z_hip + 0.5 * torso),
                         key=lambda t: np.ptp(t[1][:, 0]))
    upper = sections(z_waist + 0.08, z_sh - 0.06)
    z_chest, chest = max(upper, key=lambda t: np.ptp(t[1][:, 1]))
    hips = torso_section(mesh, z_hip - 0.04)

    def edges(name, z, s):
        return {f"{name}_r": [s[:, 0].min(), z], f"{name}_l": [s[:, 0].max(), z]}

    pts = {
        "head_top": [0.0, z_top],
        "eye_l": J("eye.L")[[0, 2]], "eye_r": J("eye.R")[[0, 2]],
        "neck": J("neck01")[[0, 2]],
        "chest": [0.0, z_chest], "waist": [0.0, z_waist],
        "crotch": [0.0, z_crotch],
        **edges("chest", z_chest, chest), **edges("waist", z_waist, waist),
        **edges("hip", z_hip - 0.04, hips),
    }
    for name, bone in (("shoulder", "upperarm01"), ("elbow", "lowerarm01"),
                       ("wrist", "wrist"),
                       ("knee", "lowerleg01"), ("ankle", "foot")):
        pts[f"{name}_l"] = J(f"{bone}.L")[[0, 2]]
        pts[f"{name}_r"] = J(f"{bone}.R")[[0, 2]]
    for side in ("l", "r"):
        foot = verts[(verts[:, 2] < z_floor + 0.03) & ((verts[:, 0] > 0) == (side == "l"))]
        pts[f"heel_{side}"] = [foot[:, 0].mean(), z_floor]
        pts[f"toe_{side}"] = [foot[np.argmin(foot[:, 1]), 0], z_floor]

    perim = lambda s: float(np.sum(np.linalg.norm(np.diff(s, axis=0, append=s[:1]), axis=1)))
    cm = lambda m: round(float(m) * 100, 1)
    measures = {
        "height": cm(z_top - z_floor),
        "shoulder_width": cm(np.linalg.norm(J("upperarm01.L") - J("upperarm01.R"))),
        "chest": cm(perim(chest)), "waist": cm(perim(waist)), "hips": cm(perim(hips)),
        "inseam": cm(z_crotch - z_floor),
    }
    return {k: np.asarray(v, dtype=float) for k, v in pts.items()}, measures


def render(verts, faces, path):
    """Front orthographic Cycles render; returns the camera's world box."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    mesh = bpy.data.meshes.new("body")
    mesh.from_pydata(verts.tolist(), [], faces.tolist())
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.update()
    mat = bpy.data.materials.new("matte")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.53, 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    mesh.materials.append(mat)
    scene.collection.objects.link(bpy.data.objects.new("body", mesh))

    lo, hi = verts.min(0), verts.max(0)
    world_h, world_w = WORLD_H, WORLD_H * SIZE[0] / SIZE[1]
    cx, cz = 0.0, lo[2] + (FLOOR_Y - 0.5) * world_h
    assert hi[2] < cz + world_h / 2 and max(-lo[0], hi[0]) < world_w / 2, "body outside frame"
    cam = bpy.data.cameras.new("cam")
    cam.type, cam.ortho_scale = "ORTHO", world_h  # ortho_scale = larger side
    cam_obj = bpy.data.objects.new("cam", cam)
    cam_obj.location = (cx, -5, cz)
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
    scene.cycles.device, scene.cycles.samples = "CPU", 64
    r.resolution_x, r.resolution_y, r.resolution_percentage = *SIZE, 100
    r.film_transparent = True
    r.image_settings.file_format, r.image_settings.color_mode = "PNG", "RGBA"
    scene.view_settings.view_transform = "Standard"
    r.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)
    return cx, cz, world_w, world_h


def to_image(p, cx, cz, w, h):
    """World (x, z) -> image 0..1 (x right, y down). Camera looks +Y, so the
    body's left (+X) is on the image's right."""
    return [round(float((p[0] - cx) / w + 0.5), 4), round(float(0.5 - (p[1] - cz) / h), 4)]


def main():
    manifest = {}
    for body_id, gender in BODIES.items():
        print(body_id)
        pheno = {k: 0.5 for k in model.phenotype_labels} | {"gender": gender}
        pose = straighten_arms(pheno)
        verts, joints = run(pheno, pose)
        faces = model.faces.numpy()
        pts, measures = keypoints_and_measures(verts, faces, joints)
        os.makedirs(f"{OUT}/{body_id}", exist_ok=True)
        box = render(verts, faces, f"{OUT}/{body_id}/neutral.png")
        manifest[body_id] = {
            "gender": "female" if gender else "male",
            "measurements_cm": measures,
            "poses": {"neutral": {
                "size": list(SIZE),
                "keypoints": {k: to_image(v, *box) for k, v in pts.items()},
            }},
        }
        print(" ", measures)
    with open(f"{OUT}/bodies.json", "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
