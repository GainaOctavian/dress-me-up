"""MakeHuman clothes (.mhclo + .obj, CC0 asset packs) on the Anny mannequin.

Like clothes in games: every garment is a modelled mesh bound to the body.
Each garment vertex = w0*B[a] + w1*B[b] + w2*B[c] + offset * body scale,
where B is the body in MakeHuman's hm08 topology - which Anny produces with
topology="anny-full" (19158 vertices, helpers included), posed. So a
garment follows the body's shape and pose with no simulation.
`delete_verts` are body vertices hidden under the garment (no skin poking
through).

MakeHuman axes are Y up / Z forward; Anny's are Z up / -Y forward. The
scale factors are ratios measured on the current body, so units come out
right by themselves.
"""
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import numpy as np

BODY_VERTS = 13380  # hm08: body vertices first, helper geometry after


def to_mh(v):
    """Anny (x, y, z) -> MakeHuman axes (x, up, forward)."""
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], axis=-1)


def from_mh(v):
    return np.stack([v[..., 0], -v[..., 2], v[..., 1]], axis=-1)


@dataclass
class Clothes:
    name: str
    refs: np.ndarray        # (n, 3) body vertex indices
    weights: np.ndarray     # (n, 3)
    offsets: np.ndarray     # (n, 3) MakeHuman axes
    scales: dict            # axis -> (vert a, vert b, reference distance)
    delete_verts: np.ndarray
    faces: List[List[int]]  # obj faces (vertex indices), quads or tris
    face_uvs: List[List[int]]
    uvs: np.ndarray         # (m, 2)
    z_depth: int = 50
    texture: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def fit(self, body: np.ndarray) -> np.ndarray:
        """Garment vertices on a body (Anny anny-full vertices, metres)."""
        mh = to_mh(body)
        base = (mh[self.refs] * self.weights[:, :, None]).sum(axis=1)
        scale = np.ones(3)
        for axis, (a, b, ref) in self.scales.items():
            scale[axis] = abs(mh[a, axis] - mh[b, axis]) / ref
        return from_mh(base + self.offsets * scale)

    def triangles(self):
        """(tris vertex indices, tris uv indices)."""
        tv, tu = [], []
        for f, u in zip(self.faces, self.face_uvs):
            for i in range(1, len(f) - 1):
                tv.append((f[0], f[i], f[i + 1]))
                tu.append((u[0], u[i], u[i + 1]))
        return np.array(tv), np.array(tu)


def _ranges(tokens):
    """'1355 - 1357 1361' -> [1355, 1356, 1357, 1361] (ranges are spaced)."""
    out, i = [], 0
    while i < len(tokens):
        if i + 2 < len(tokens) and tokens[i + 1] == "-":
            out.extend(range(int(tokens[i]), int(tokens[i + 2]) + 1))
            i += 3
        else:
            out.append(int(tokens[i]))
            i += 1
    return out


@lru_cache(maxsize=128)
def load(mhclo_path: str) -> Clothes:
    path = Path(mhclo_path)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    meta, refs, weights, offsets, delete = {}, [], [], [], []
    section = None
    for line in lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        head = s.split()[0]
        if head == "verts":
            section = "verts"
            continue
        if head == "delete_verts":
            section = "delete"
            continue
        if section == "verts" and head[0].isdigit():
            p = s.split()
            if len(p) >= 9:
                refs.append([int(x) for x in p[:3]])
                weights.append([float(x) for x in p[3:6]])
                offsets.append([float(x) for x in p[6:9]])
            else:  # a vertex pinned to a single body vertex
                refs.append([int(p[0])] * 3)
                weights.append([1.0, 0.0, 0.0])
                offsets.append([0.0, 0.0, 0.0])
            continue
        if section == "delete" and (head[0].isdigit()):
            delete.extend(_ranges(s.split()))
            continue
        section = None
        meta.setdefault(head, []).append(s.split()[1:])
    scales = {}
    for axis, key in enumerate(("x_scale", "y_scale", "z_scale")):
        if key in meta:
            a, b, ref = meta[key][0]
            scales[axis] = (int(a), int(b), float(ref))
        elif f"l_shear_{key[0]}" in meta:  # newer MakeClothes: "a b x1 x2", scale = (B[a]-B[b]) / (x1-x2)
            a, b, x1, x2 = meta[f"l_shear_{key[0]}"][0]
            scales[axis] = (int(a), int(b), abs(float(x1) - float(x2)))
    obj = path.parent / meta["obj_file"][0][0]
    faces, face_uvs, uvs = [], [], []
    for line in obj.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("vt "):
            uvs.append([float(x) for x in line.split()[1:3]])
        elif line.startswith("f "):
            parts = [p.split("/") for p in line.split()[1:]]
            faces.append([int(p[0]) - 1 for p in parts])
            face_uvs.append([int(p[1]) - 1 if len(p) > 1 and p[1] else 0 for p in parts])
    texture = None
    mat = path.parent / meta["material"][0][0] if "material" in meta else None
    if mat and mat.exists():
        for line in mat.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("diffuseTexture"):
                texture = str(path.parent / line.split()[1])
    return Clothes(
        name=meta.get("name", [[path.stem]])[0][0],
        refs=np.array(refs), weights=np.array(weights), offsets=np.array(offsets),
        scales=scales, delete_verts=np.array(sorted(set(delete)), dtype=int),
        faces=faces, face_uvs=face_uvs, uvs=np.array(uvs) if uvs else np.zeros((1, 2)),
        z_depth=int(meta.get("z_depth", [[50]])[0][0]), texture=texture,
        tags=[t[0].lower() for t in meta.get("tag", []) if t],
    )


SETTLE_FRAMES = 15


def settle(scene, obj, colliders, pin_top: float = 0.0):
    """A short cloth simulation on a garment that already sits on the body:
    it pushes the cloth out of the body and the layers below (no clipping)
    and lets it drape. `pin_top` > 0 holds the top band of that many metres
    (waistbands) so trousers don't slide. Returns a static copy (the next
    layer collides with it)."""
    import bmesh
    import bpy
    # some garments carry duplicate vertices (seams modelled as two edges at
    # the same spot): springs between them blow the simulation up
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    for c in colliders:
        if "collision" not in c.modifiers:
            c.modifiers.new("collision", "COLLISION")
            c.collision.thickness_outer = 0.004
            c.collision.cloth_friction = 10.0  # sleeves mustn't slide down slanted arms
    mod = obj.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    # Blender's tuned pair (0.3 kg/vertex with stiffness 15): gram-light
    # vertices made the system too stiff for the time step and it exploded.
    # The sim is short, so the weight has no time to drag the cloth down.
    s.quality = 12
    s.mass = 0.3
    s.tension_stiffness = s.compression_stiffness = 15
    s.shear_stiffness = 5
    s.bending_stiffness = 0.5
    s.air_damping = 1.0
    c = mod.collision_settings
    c.use_collision = True
    c.distance_min = 0.005
    c.use_self_collision = False
    if pin_top > 0:
        z = np.array([v.co.z for v in obj.data.vertices])
        top = np.flatnonzero(z > z.max() - pin_top)
        group = obj.vertex_groups.new(name="pin")
        group.add([int(i) for i in top], 1.0, "REPLACE")
        s.vertex_group_mass = "pin"
    # no gravity: the point is only to push cloth out of what's under it
    # (clipping), not to let it slide or fall
    s.effector_weights.gravity = 0.0
    mod.point_cache.frame_start, mod.point_cache.frame_end = 1, SETTLE_FRAMES
    scene.frame_start, scene.frame_end = 1, SETTLE_FRAMES
    for f in range(1, SETTLE_FRAMES + 1):
        scene.frame_set(f)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph))
    _carry_small_parts(obj.data, mesh)
    done = bpy.data.objects.new(obj.name + "_settled", mesh)
    scene.collection.objects.link(done)
    bpy.data.objects.remove(obj)
    return done


# ---------------------------------------------------------------- photo texture
# A front flat-lay photo looks like the garment seen from the front in the
# neutral pose: the same landmarks (collar, shoulders, hem, waistband) are
# found on the 3D garment's front projection, so fabric.photo_coords can
# place the photo on it. The MakeHuman texture's shading (seams, folds) is
# kept by multiplying.

def _carry_small_parts(before, after, small: float = 0.2):
    """Buttons, cuffs, pocket flaps (loose parts under `small` of the biggest
    piece) have nothing holding them in the simulation and fly off: move
    them like the nearest bit of the big pieces instead."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    n = len(before.vertices)
    if n != len(after.vertices):
        return
    co0, co1 = np.zeros(n * 3), np.zeros(n * 3)
    before.vertices.foreach_get("co", co0)
    after.vertices.foreach_get("co", co1)
    co0, co1 = co0.reshape(-1, 3), co1.reshape(-1, 3)
    e = np.zeros(len(before.edges) * 2, int)
    before.edges.foreach_get("vertices", e)
    e = e.reshape(-1, 2)
    _, part = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), shape=(n, n)))
    sizes = np.bincount(part)
    loose = sizes[part] < small * sizes.max()
    if not loose.any() or loose.all():
        return
    _, near = cKDTree(co0[~loose]).query(co0[loose])
    co1[loose] = co0[loose] + (co1[~loose] - co0[~loose])[near]
    after.vertices.foreach_set("co", co1.ravel())
    after.update()


def landmarks(px: np.ndarray, kind: str, k: dict) -> dict:
    """Garment landmarks on its front projection (body image px, y down),
    named like the worker's photo anchors; `_l` = the wearer's left = image right."""
    x, y = px[:, 0], px[:, 1]
    cx = k["neck"][0]
    out = {}

    def lowest(side):
        sel = (x > cx) if side == "l" else (x < cx)
        ys = y[sel]
        low = ys.max()
        return [float(x[sel][ys > low - 6].mean()), float(low)]

    out["hem_l"], out["hem_r"] = lowest("l"), lowest("r")
    if kind == "legs":
        top = y.min()
        band = y < top + 12
        out["top_l"] = [float(x[band].max()), float(top)]
        out["top_r"] = [float(x[band].min()), float(top)]
        out["collar"] = [float(cx), float(top)]
        # crotch: the highest garment point between the legs; leg centres
        # halfway down and at the hem
        mid = np.abs(x - cx) < 8
        low_mid = y[mid & (y > top + 0.2 * (out["hem_l"][1] - top))]
        if len(low_mid):
            crotch = float(low_mid.min())
            out["crotch"] = [float(cx), crotch]
            for t, name in ((0.5, "knee"), (0.95, "shin")):
                yy = crotch + t * (max(out["hem_l"][1], out["hem_r"][1]) - crotch)
                row = np.abs(y - yy) < 10
                for s, sel in (("l", x > cx), ("r", x < cx)):
                    if (row & sel).sum() > 2:
                        out[f"{name}_{s}"] = [float(x[row & sel].mean()), float(yy)]
        return out
    near = np.abs(x - cx) < 25
    out["collar"] = [float(cx), float(y[near].min())]
    chest_half = k["chest_l"][0] - cx
    mid_chest = k["shoulder_l"][1] + 0.35 * (k["waist"][1] - k["shoulder_l"][1])
    band = (np.abs(y - mid_chest) < 15) & (np.abs(x - cx) < 1.35 * chest_half)
    if band.sum() > 4:
        for s, edge in (("l", x[band].max()), ("r", x[band].min())):
            col = np.abs(x - edge) < 10
            out[f"shoulder_{s}"] = [float(edge), float(y[col].min())]
            d = np.asarray(k[f"wrist_{s}"]) - np.asarray(k[f"shoulder_{s}"])
            d = d / np.linalg.norm(d)
            side = (x > edge) if s == "l" else (x < edge)
            if side.sum() > 4:
                along = (px[side] - np.asarray(k[f"shoulder_{s}"])) @ d
                out[f"sleeve_{s}"] = [float(v) for v in px[side][np.argmax(along)]]
    return out


def material(name, colour, tile_path=None, decals_path=None, detail_path=None):
    """Base (`colour`, or the seamless `tile` repeated on UV map "tile"),
    prints over it (`decals`, UV map "decal", clipped), times the MakeHuman
    texture's luminance (UV map "uv")."""
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85

    def image(path, uv_map, extension, non_colour=False):
        tex = nodes.new("ShaderNodeTexImage")
        tex.image = bpy.data.images.load(path)
        if non_colour:
            tex.image.colorspace_settings.name = "Non-Color"
        tex.extension = extension
        uvm = nodes.new("ShaderNodeUVMap")
        uvm.uv_map = uv_map
        links.new(uvm.outputs["UV"], tex.inputs["Vector"])
        return tex

    if tile_path:
        base_out = image(tile_path, "tile", "REPEAT").outputs["Color"]
    else:
        base = nodes.new("ShaderNodeRGB")
        base.outputs[0].default_value = (*[c ** 2.2 for c in colour], 1)
        base_out = base.outputs[0]
    if decals_path:
        dec = image(decals_path, "decal", "CLIP")
        over = nodes.new("ShaderNodeMixRGB")
        links.new(dec.outputs["Alpha"], over.inputs["Fac"])
        links.new(base_out, over.inputs["Color1"])
        links.new(dec.outputs["Color"], over.inputs["Color2"])
        base_out = over.outputs["Color"]
    if detail_path:
        bw = nodes.new("ShaderNodeRGBToBW")
        links.new(image(detail_path, "uv", "REPEAT", non_colour=True).outputs["Color"], bw.inputs["Color"])
        # luminance around 1: shading from the model, colour from the photo
        norm = nodes.new("ShaderNodeMath")
        norm.operation = "MULTIPLY"
        norm.inputs[1].default_value = 1.6
        links.new(bw.outputs["Val"], norm.inputs[0])
        mix = nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 0.7
        links.new(base_out, mix.inputs["Color1"])
        links.new(norm.outputs["Value"], mix.inputs["Color2"])
        base_out = mix.outputs["Color"]
    links.new(base_out, bsdf.inputs["Base Color"])
    return mat
