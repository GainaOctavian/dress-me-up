"""The dressed scene as a GLB, for the app's 3D viewer (turn the mannequin
round, zoom). glTF only carries plain materials (a colour or one texture),
while ours mix a colour or pattern tile, print decals and the MakeHuman
shading on several UV maps. So each garment gets its own non-overlapping
UV map ("bake", smart project) and Cycles bakes its colour into one
texture there; then the material becomes that texture alone.
"""
import math

BAKE_SIZE = 1024


def _only(obj):
    import bpy
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def _bake(obj, size: int):
    import bpy
    mesh = obj.data
    if not mesh.polygons or not mesh.materials:
        return
    _only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bake_uv = mesh.uv_layers.new(name="bake")
    mesh.uv_layers.active = bake_uv
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")

    image = bpy.data.images.new(f"{obj.name}_bake", size, size)
    for mat in mesh.materials:  # the bake writes into each material's active image node
        node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        mat.node_tree.nodes.active = node
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=4, use_clear=True)
    image.pack()

    flat = bpy.data.materials.new(f"{obj.name}_flat")
    flat.use_nodes = True
    nodes, links = flat.node_tree.nodes, flat.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.85
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    uvm = nodes.new("ShaderNodeUVMap")
    uvm.uv_map = "bake"
    links.new(uvm.outputs["UV"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.clear()
    mesh.materials.append(flat)
    for layer in [layer.name for layer in mesh.uv_layers if layer.name != "bake"]:
        mesh.uv_layers.remove(mesh.uv_layers[layer])


def export(objects, path: str, size: int = BAKE_SIZE) -> None:
    """`objects`: what to export (the body: plain colour, no bake; garments
    are baked). Call after the still render: it changes the materials."""
    import bpy
    scene = bpy.context.scene
    scene.cycles.samples = 1  # colour only: no light paths to sample
    scene.render.bake.use_pass_direct = scene.render.bake.use_pass_indirect = False
    for obj in objects:
        if any(m and m.node_tree and len(m.node_tree.nodes) > 2 for m in obj.data.materials):
            _bake(obj, size)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in objects)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_cameras=False, export_lights=False,
        export_image_format="JPEG", export_jpeg_quality=85,
    )  # no Draco: the bpy wheel doesn't ship its library
