"""Export the authored Blender bogie as link-local URDF meshes.

Run from Blender's Python console:
    exec(compile(open(__file__).read(), __file__, "exec"))

The scene was authored with the frame rooted at ``Cube.004`` and the two
wheelsets rooted at ``Cylinder.037`` and ``Cylinder.038``.  Exported vertices
are expressed in metres relative to their corresponding URDF joint frame.
"""

from __future__ import annotations

import json
import math
import re
import struct
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ASSET_DIR = Path("/Users/lapsus/cw/Catalog/Generic_Objects/Rail_Bogie")
SOURCE_BLEND = ASSET_DIR / "source" / "rail_bogie.blend"
MESH_DIR = ASSET_DIR / "meshes"
REPORT_PATH = ASSET_DIR / "source" / "export_report.json"

FRAME_ROOT = "Cube.004"
WHEELSET_ROOTS = ("Cylinder.037", "Cylinder.038")


# Catalog appearance, expressed in the sRGB values expected by Three.js MTLLoader.
# The original viewport swatch for the body was near-black after MTL loading.
BODY_COLOUR_SRGB = (0.75, 0.75, 0.75)


def linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1.0 / 2.4) - 0.055


def material_colour_srgb(material: bpy.types.Material) -> tuple[float, ...]:
    """Export constant shader colors, with a stable light-gray body override."""
    colour = tuple(material.diffuse_color)
    if material.use_nodes and material.node_tree:
        output = next((node for node in material.node_tree.nodes
                       if node.type == "OUTPUT_MATERIAL" and node.is_active_output), None)
        if output and output.inputs["Surface"].is_linked:
            shader = output.inputs["Surface"].links[0].from_node
            if shader.type == "BSDF_PRINCIPLED":
                base = shader.inputs["Base Color"]
                if base.is_linked:
                    raise ValueError(f"{material.name}: textured colors require a texture-aware exporter")
                colour = (*base.default_value[:3], shader.inputs["Alpha"].default_value)
    if material.name == "Material.001":
        return (*BODY_COLOUR_SRGB, colour[3])
    return (*(linear_to_srgb(channel) for channel in colour[:3]), colour[3])


def descendants(root: bpy.types.Object) -> set[bpy.types.Object]:
    result = {root}
    pending = [root]
    while pending:
        current = pending.pop()
        for child in current.children:
            if child not in result:
                result.add(child)
                pending.append(child)
    return result


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def mesh_objects(objects: set[bpy.types.Object]) -> list[bpy.types.Object]:
    return sorted((obj for obj in objects if obj.type == "MESH"), key=lambda obj: obj.name)


def iter_triangles(objects: list[bpy.types.Object], origin: Vector):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    offset = Matrix.Translation(-origin)
    for obj in objects:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            transform = offset @ evaluated.matrix_world
            normal_transform = transform.to_3x3().inverted().transposed()
            for triangle in mesh.loop_triangles:
                vertices = [transform @ mesh.vertices[index].co for index in triangle.vertices]
                normal = normal_transform @ triangle.normal
                normal.normalize()
                material = None
                if 0 <= triangle.material_index < len(mesh.materials):
                    material = mesh.materials[triangle.material_index]
                yield obj.name, vertices, normal, material
        finally:
            evaluated.to_mesh_clear()


def write_obj(path: Path, objects: list[bpy.types.Object], origin: Vector) -> dict[str, int]:
    materials: dict[str, bpy.types.Material] = {}
    triangles = list(iter_triangles(objects, origin))
    vertex_index = 1
    with path.open("w", encoding="utf-8") as handle:
        handle.write(f"# Rail bogie visual mesh; units: metres\nmtllib {path.stem}.mtl\n")
        current_object = None
        current_material = None
        for object_name, vertices, _normal, material in triangles:
            if object_name != current_object:
                handle.write(f"o {safe_name(object_name)}\n")
                current_object = object_name
            material_name = safe_name(material.name) if material else "default_material"
            if material_name != current_material:
                handle.write(f"usemtl {material_name}\n")
                current_material = material_name
            if material:
                materials[material_name] = material
            for vertex in vertices:
                handle.write(f"v {vertex.x:.9g} {vertex.y:.9g} {vertex.z:.9g}\n")
            handle.write(f"f {vertex_index} {vertex_index + 1} {vertex_index + 2}\n")
            vertex_index += 3

    with path.with_suffix(".mtl").open("w", encoding="utf-8") as handle:
        handle.write("# Rail bogie material colours; Kd values are sRGB\n")
        fallback = linear_to_srgb(0.18)
        handle.write(f"newmtl default_material\nKd {fallback:.6g} {fallback:.6g} {fallback:.6g}\nKs 0.04 0.04 0.04\nNs 32\n\n")
        for material_name, material in sorted(materials.items()):
            colour = material_colour_srgb(material)
            metallic = float(getattr(material, "metallic", 0.0))
            roughness = float(getattr(material, "roughness", 0.5))
            handle.write(f"newmtl {material_name}\n")
            handle.write(f"Kd {colour[0]:.6g} {colour[1]:.6g} {colour[2]:.6g}\n")
            handle.write(f"d {colour[3]:.6g}\n")
            handle.write(f"Ks {metallic:.6g} {metallic:.6g} {metallic:.6g}\n")
            handle.write(f"Ns {max(1.0, (1.0 - roughness) * 250.0):.6g}\n\n")
    return {"objects": len(objects), "triangles": len(triangles)}


def write_binary_stl(path: Path, objects: list[bpy.types.Object], origin: Vector) -> dict[str, int]:
    triangles = list(iter_triangles(objects, origin))
    header = b"Cyberwave rail bogie collision mesh".ljust(80, b"\0")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for _object_name, vertices, normal, _material in triangles:
            values = [normal.x, normal.y, normal.z]
            for vertex in vertices:
                values.extend((vertex.x, vertex.y, vertex.z))
            handle.write(struct.pack("<12fH", *values, 0))
    return {"objects": len(objects), "triangles": len(triangles)}


def bounds(objects: list[bpy.types.Object], origin: Vector) -> dict[str, list[float]]:
    points: list[Vector] = []
    offset = Matrix.Translation(-origin)
    for obj in objects:
        transform = offset @ obj.matrix_world
        points.extend(transform @ Vector(corner) for corner in obj.bound_box)
    minimum = Vector(min(point[i] for point in points) for i in range(3))
    maximum = Vector(max(point[i] for point in points) for i in range(3))
    return {
        "min": list(minimum),
        "max": list(maximum),
        "size": list(maximum - minimum),
        "center": list((minimum + maximum) / 2.0),
    }


def main() -> None:
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_BLEND.parent.mkdir(parents=True, exist_ok=True)

    frame_root = bpy.data.objects[FRAME_ROOT]
    wheel_roots = [bpy.data.objects[name] for name in WHEELSET_ROOTS]
    wheel_groups = [descendants(root) for root in wheel_roots]
    wheel_objects = set().union(*wheel_groups)
    frame_objects = set(bpy.context.scene.objects) - wheel_objects

    axle_centres = [root.matrix_world.translation.copy() for root in wheel_roots]
    frame_origin = sum(axle_centres, Vector()) / len(axle_centres)

    groups = {
        "frame": (mesh_objects(frame_objects), frame_origin),
        "front_wheelset": (mesh_objects(wheel_groups[0]), axle_centres[0]),
        "rear_wheelset": (mesh_objects(wheel_groups[1]), axle_centres[1]),
    }

    report = {
        "units": "metres",
        "scene_unit_system": bpy.context.scene.unit_settings.system,
        "scene_scale_length": bpy.context.scene.unit_settings.scale_length,
        "source_blend": str(SOURCE_BLEND),
        "frame_origin_world": list(frame_origin),
        "joint_origins": {
            "front_wheelset_joint": list(axle_centres[0] - frame_origin),
            "rear_wheelset_joint": list(axle_centres[1] - frame_origin),
        },
        "groups": {},
    }

    for name, (objects, origin) in groups.items():
        obj_report = write_obj(MESH_DIR / f"rail_bogie_{name}_visual.obj", objects, origin)
        stl_report = write_binary_stl(MESH_DIR / f"rail_bogie_{name}_collision.stl", objects, origin)
        report["groups"][name] = {
            **obj_report,
            "collision_triangles": stl_report["triangles"],
            "bounds": bounds(objects, origin),
            "object_names": [obj.name for obj in objects],
        }

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_BLEND))
    print(json.dumps(report, indent=2))


main()
