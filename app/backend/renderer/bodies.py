"""Bodies garments are put on (plans 12, 14, 16): Anny (Z up, front = -Y,
.L = +X) shaped by its phenotype, posed, rendered from the front with a
transparent background, plus keypoints projected with the same camera.

Used offline for the built-in mannequins (app/infra/body-assets/
render_bodies.py) and online for the user's own body (`build`, a
`body_build` job): `fit_phenotype` turns their measurements into Anny's
phenotype (plan 16a: only their proportions are used, never a photo).
Poses (plan 14) are built on top of neutral; the spine never moves, so the
torso outline keypoints come from neutral and only joints/feet are re-read.
"""
import math
import os
from functools import lru_cache
from typing import Dict, Optional

import numpy as np

SIZE = (1200, 1800)  # px, 2:3
# Same camera for every body: same scale, feet on the same baseline
# m shown top to bottom: up to ~2.03 m tall, arms out to 1.40 m (1.85 cut
# off users over ~1.79 m and wide A-poses)
WORLD_H = 2.10
FLOOR_Y = 0.97  # image y (0..1) of the soles
POSES = ["neutral", "relaxed", "hand_on_hip", "walk"]
GENDER = {"male": 0.0, "female": 1.0}  # Anny's gender value


@lru_cache(maxsize=1)
def model():
    import anny
    import torch
    torch.set_num_threads(int(os.getenv("RENDER_THREADS", "8")))
    return anny.Anny().to(dtype=torch.float32)


def bone(name: str) -> int:
    return model().bone_labels.index(name)


def rot(axis: str, deg: float):
    import torch
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
    r = torch.eye(4)
    r[i, i], r[i, j], r[j, i], r[j, j] = c, -s, s, c
    return r


def run(pheno, pose):
    out = model()(pose_parameters=pose[None], phenotype_kwargs=pheno)
    return out["vertices"][0].numpy(), out["bone_poses"][0, :, :3, 3].numpy()


def straighten_arms(pheno):
    """Anny's rest pose is an A-pose with forearms bent forward. Rotate each
    forearm (local x, then z) so the wrist continues the upper-arm line:
    a flat arm in the image plane is what 2D sleeves can follow."""
    import torch
    pose = torch.eye(4)[None].repeat(model().bone_count, 1, 1)
    for side in ("L", "R"):
        fore = bone(f"lowerarm01.{side}")

        def miss(ax, az):
            pose[fore] = rot("x", ax) @ rot("z", az)
            _, j = run(pheno, pose)
            sh, el, wr = j[bone(f"upperarm01.{side}")], j[fore], j[bone(f"wrist.{side}")]
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
    import trimesh
    mesh = trimesh.Trimesh(verts, faces, process=False)
    J = lambda b: j[bone(b)]
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
    pts.update(joint_points(verts, j))

    perim = lambda s: float(np.sum(np.linalg.norm(np.diff(s, axis=0, append=s[:1]), axis=1)))
    cm = lambda m: round(float(m) * 100, 1)
    measures = {
        "height": cm(z_top - z_floor),
        "shoulder_width": cm(np.linalg.norm(J("upperarm01.L") - J("upperarm01.R"))),
        "chest": cm(perim(chest)), "waist": cm(perim(waist)), "hips": cm(perim(hips)),
        "inseam": cm(z_crotch - z_floor),
    }
    return {k: np.asarray(v, dtype=float) for k, v in pts.items()}, measures


def joint_points(verts, j):
    """Pose-dependent keypoints: joints, head top, and each foot's own sole
    (in a walk one foot is lifted)."""
    J = lambda b: j[bone(b)]
    pts = {"head_top": [0.0, verts[:, 2].max()],
           "eye_l": J("eye.L")[[0, 2]], "eye_r": J("eye.R")[[0, 2]],
           "neck": J("neck01")[[0, 2]]}
    for name, b in (("shoulder", "upperarm01"), ("elbow", "lowerarm01"),
                    ("wrist", "wrist"), ("hip_joint", "upperleg01"),
                    ("knee", "lowerleg01"), ("ankle", "foot")):
        pts[f"{name}_l"] = J(f"{b}.L")[[0, 2]]
        pts[f"{name}_r"] = J(f"{b}.R")[[0, 2]]
    for side in ("l", "r"):
        half = verts[(verts[:, 0] > 0) == (side == "l")]
        sole = half[:, 2].min()
        foot = half[half[:, 2] < sole + 0.03]
        pts[f"heel_{side}"] = [foot[:, 0].mean(), sole]
        pts[f"toe_{side}"] = [foot[np.argmin(foot[:, 1]), 0], sole]
    return {k: np.asarray(v, dtype=float) for k, v in pts.items()}


def turn(pose, b, side, axis, deg):
    """Local rotation on top of the current pose; .R mirrors y/z."""
    i = bone(f"{b}.{side}")
    pose[i] = pose[i] @ rot(axis, -deg if side == "R" and axis in "yz" else deg)


def reach(pheno, pose, side, target):
    """Bend the forearm so the wrist lands on `target` (coordinate descent
    over its three axes; the shoulder stays where the caller put it)."""
    fore = bone(f"lowerarm01.{side}")
    base_fore = pose[fore].clone()
    s = 1 if side == "L" else -1

    def miss(a):
        pose[fore] = base_fore @ rot("x", a[0]) @ rot("y", s * a[1]) @ rot("z", s * a[2])
        return np.linalg.norm(run(pheno, pose)[1][bone(f"wrist.{side}")] - target)

    a = [0.0] * 3
    for step in (32, 8, 2, 0.5):
        for _ in range(2):
            for k in range(3):
                a[k] = min((a[k] + d * step for d in range(-4, 5)),
                           key=lambda v: miss(a[:k] + [v] + a[k + 1:]))
    print(f"  reach.{side}: {a} miss={miss(a) * 100:.1f}cm")


def make_pose(pheno, name, neutral_pts, straight=None):
    """`straight`: straighten_arms(pheno), when the caller already has it."""
    pose = (straight if straight is not None else straighten_arms(pheno)).clone()
    if name == "relaxed":
        for s in "LR":
            turn(pose, "upperarm01", s, "y", 28)
    elif name == "hand_on_hip":
        turn(pose, "upperarm01", "R", "y", 28)
        turn(pose, "upperarm01", "L", "y", -8)  # elbow out
        hip = neutral_pts["hip_l"]
        reach(pheno, pose, "L", np.array([hip[0] + 0.03, 0.0, hip[1] + 0.06]))
    elif name == "walk":
        turn(pose, "upperleg01", "L", "x", -18)  # left leg forward, knee bent
        turn(pose, "lowerleg01", "L", "x", 22)
        turn(pose, "upperleg01", "R", "x", 10)   # right leg back
        turn(pose, "lowerleg01", "R", "x", 8)
        for s in "LR":
            turn(pose, "upperarm01", s, "y", 26)
        turn(pose, "upperarm01", "L", "x", 15)   # arms swing opposite to legs
        turn(pose, "upperarm01", "R", "x", -15)
    return pose


def render(verts, faces, path):
    """Front orthographic Cycles render; returns the camera's world box."""
    import bpy  # after torch (Anny): bpy needs the OpenMP runtime torch loads
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
    r.threads_mode, r.threads = "FIXED", int(os.getenv("RENDER_THREADS", "8"))
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


def build(pheno: Dict[str, float], out_dir: str) -> dict:
    """Every pose of one body: <out_dir>/<pose>.png + <pose>.pose.npy (Anny
    pose params, re-read by the 3D renderer). Returns {measurements_cm,
    poses: {pose: {size, keypoints}}} (bodies.json / Body doc shape)."""
    faces = model().faces.numpy()
    os.makedirs(out_dir, exist_ok=True)
    straight = straighten_arms(pheno)  # every pose starts from it
    poses, neutral, measures = {}, None, None
    for name in POSES:
        pose = straight.clone() if name == "neutral" else make_pose(pheno, name, neutral, straight)
        verts, joints = run(pheno, pose)
        np.save(f"{out_dir}/{name}.pose.npy", pose.numpy())
        if name == "neutral":
            neutral, measures = keypoints_and_measures(verts, faces, joints)
            pts = neutral
        else:
            pts = {**neutral, **joint_points(verts, joints)}
        box = render(verts, faces, f"{out_dir}/{name}.png")
        poses[name] = {"size": list(SIZE), "keypoints": {k: to_image(v, *box) for k, v in pts.items()}}
        print(" ", name, "rendered", flush=True)
    return {"measurements_cm": measures, "poses": poses}


# ---------------------------------------------------------------- plan 16a
FIT = ["height", "weight", "muscle", "proportions"]  # what the measurements move; gender and age stay


@lru_cache(maxsize=1)
def _girth_loops():
    """Vertex loops round the chest and hips of the average body (like
    Anthropometry's waist loop): their perimeter is a girth on any body."""
    pheno = {k: 0.5 for k in model().phenotype_labels}
    verts, joints = run(pheno, straighten_arms_cached())
    neutral, _ = keypoints_and_measures(verts, model().faces.numpy(), joints)
    loops = {}
    for name, edge in (("chest", "chest_l"), ("hips", "hip_l")):
        x_edge, z = neutral[edge]
        idx = np.flatnonzero((np.abs(verts[:, 2] - z) < 0.02) & (np.abs(verts[:, 0]) < x_edge + 0.01))  # no arms
        ang = np.arctan2(verts[idx, 1] - verts[idx, 1].mean(), verts[idx, 0])
        bins = ((ang + np.pi) / (2 * np.pi) * 48).astype(int) % 48
        # one vertex per direction, the closest to the girth's height
        loops[name] = np.array([idx[b == bins][np.argmin(np.abs(verts[idx[b == bins], 2] - z))]
                                for b in range(48) if (bins == b).any()])
    return loops


@lru_cache(maxsize=1)
def straighten_arms_cached():
    return straighten_arms({k: 0.5 for k in model().phenotype_labels})


AVERAGE_BMI = 22.5  # what Anny's average body (weight 0.5) stands for


def measure(pheno) -> Dict[str, float]:
    """height, mass (kg) and girths (m) of a body in its rest pose."""
    raw = _raw_measure(pheno)
    return raw | {"mass": raw["mass"] * _mass_scale(pheno["gender"])}


def _raw_measure(pheno) -> Dict[str, float]:
    import anny
    import torch
    m = model()
    with torch.no_grad():
        rest = m(phenotype_kwargs=pheno)["rest_vertices"]
    out = anny.Anthropometry(m)(rest)
    v = rest[0].numpy()
    loop = lambda idx: float(np.linalg.norm(v[idx] - np.roll(v[idx], 1, axis=0), axis=1).sum())
    loops = _girth_loops()
    return {"height": float(out["height"][0]), "mass": float(out["mass"][0]),
            "waist": float(out["waist_circumference"][0]),
            "chest": loop(loops["chest"]), "hips": loop(loops["hips"])}


@lru_cache(maxsize=2)
def _mass_scale(gender: float) -> float:
    """Anny's volume x 980 kg/m3 is light (its average body has BMI ~20 for
    men, ~18 for women), which put normal weights at the slider's top:
    scale it so the average body weighs AVERAGE_BMI."""
    avg = _raw_measure({k: 0.5 for k in model().phenotype_labels} | {"gender": gender})
    return AVERAGE_BMI * avg["height"] ** 2 / avg["mass"]


def fit_phenotype(gender: str, height_cm: float, weight_kg: float, chest_cm: Optional[float] = None,
                  waist_cm: Optional[float] = None, hips_cm: Optional[float] = None) -> Dict[str, float]:
    """Anny's phenotype closest to the measurements (least squares over FIT,
    each kept in 0..1; muscle and proportions pulled gently towards average
    so height + weight alone still give a plausible body)."""
    from scipy.optimize import least_squares
    base = {k: 0.5 for k in model().phenotype_labels} | {"gender": GENDER[gender]}
    # residual scales: 1 cm, 1 kg, 2 cm of girth
    targets = [("height", height_cm / 100, 0.01), ("mass", weight_kg, 1.0)]
    targets += [(k, v / 100, 0.02) for k, v in (("chest", chest_cm), ("waist", waist_cm), ("hips", hips_cm)) if v]

    def residuals(x):
        got = measure(base | dict(zip(FIT, x)))
        prior = [(x[2] - 0.5) / 0.5, (x[3] - 0.5) / 0.5]  # muscle, proportions
        return [(got[k] - t) / s for k, t, s in targets] + prior

    x = least_squares(residuals, [0.5] * len(FIT), bounds=(0, 1), diff_step=0.02, max_nfev=60).x
    return base | {k: round(float(v), 4) for k, v in zip(FIT, x)}
