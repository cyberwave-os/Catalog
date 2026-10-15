"""Export the procedurally modeled 42U server rack cabinet as a single rigid URDF link.

Follows the Rail_Bogie_Small OBJ/MTL + STL pattern (same writers), with the
Black_Frame convention of box-primitive collisions instead of a collision mesh.
Run in Blender with __file__ set to this script, e.g.:

    import runpy
    runpy.run_path('/abs/path/to/export_server_rack_42u.py', run_name='__main__')

The live scene is not transformed; a copy of the blend is saved beside the script.
"""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path
import xml.etree.ElementTree as ET

import bpy
from mathutils import Matrix, Vector


ASSET_DIR = Path(__file__).resolve().parents[1]
ASSET_NAME = "server_rack_42u"
SOURCE_BLEND = ASSET_DIR / "source" / f"{ASSET_NAME}.blend"
MESH_DIR = ASSET_DIR / "meshes"
REPORT_PATH = ASSET_DIR / "source" / "export_report.json"

COLLECTION = "RACK | 42U server cabinet"
# Empty-cabinet mass from the Sysracks 42U 24"x32"x84" listing (122 lb). Placeholder.
MASS_KG = 55.3
RACK_UNITS = 42
U_METRES = 0.04445

# Collision groups are axis-aligned boxes fitted to these object-name prefixes.
# Anything not matched falls into the main cabinet body box.
COLLISION_GROUPS = {
    "feet": ("foot_", "caster_"),
    "handle": ("door_handle",),
}


def linear_to_srgb(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return 12.92 * value if value <= 0.0031308 else 1.055 * value ** (1.0 / 2.4) - 0.055


def material_colour_srgb(material: bpy.types.Material) -> tuple[float, ...]:
    """Constant shader colours in the catalog sRGB convention (as in Rail_Bogie_Small)."""
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
    return (*(linear_to_srgb(channel) for channel in colour[:3]), colour[3])


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def mesh_objects(objects) -> list[bpy.types.Object]:
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
            flip = transform.determinant() < 0
            for triangle in mesh.loop_triangles:
                indices = list(triangle.vertices)
                if flip:
                    indices.reverse()
                vertices = [transform @ mesh.vertices[index].co for index in indices]
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
        handle.write(f"# 42U server rack visual mesh; units: metres; X front, Y width, Z up\nmtllib {path.stem}.mtl\n")
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
        handle.write("# 42U server rack material colours; Kd values are sRGB, d is alpha\n")
        fallback = linear_to_srgb(0.18)
        handle.write(f"newmtl default_material\nKd {fallback:.6g} {fallback:.6g} {fallback:.6g}\nKs 0.04 0.04 0.04\nNs 32\n\n")
        for material_name, material in sorted(materials.items()):
            colour = material_colour_srgb(material)
            metallic = float(getattr(material, "metallic", 0.0))
            roughness = float(getattr(material, "roughness", 0.5))
            if material.use_nodes:
                shader = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
                if shader:
                    metallic = float(shader.inputs["Metallic"].default_value)
                    roughness = float(shader.inputs["Roughness"].default_value)
            handle.write(f"newmtl {material_name}\n")
            handle.write(f"Kd {colour[0]:.6g} {colour[1]:.6g} {colour[2]:.6g}\n")
            handle.write(f"d {colour[3]:.6g}\n")
            handle.write(f"Ks {metallic:.6g} {metallic:.6g} {metallic:.6g}\n")
            handle.write(f"Ns {max(1.0, (1.0 - roughness) * 250.0):.6g}\n\n")
    return {"objects": len(objects), "triangles": len(triangles)}


def write_binary_stl(path: Path, objects: list[bpy.types.Object], origin: Vector) -> dict[str, int]:
    triangles = list(iter_triangles(objects, origin))
    header = b"Cyberwave 42U server rack visual mesh".ljust(80, b"\0")
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
    points = [vertex for _, vertices, _, _ in iter_triangles(objects, origin) for vertex in vertices]
    minimum = Vector(min(point[i] for point in points) for i in range(3))
    maximum = Vector(max(point[i] for point in points) for i in range(3))
    return {
        "min": list(minimum),
        "max": list(maximum),
        "size": list(maximum - minimum),
        "center": list((minimum + maximum) / 2.0),
    }


def fmt(values) -> str:
    return " ".join(f"{v:.10g}" for v in values)


def write_urdf(report: dict) -> None:
    robot = ET.Element("robot", name=ASSET_NAME)
    robot.append(ET.Comment(
        " Static 42U server rack cabinet: load with fixed_base=true. "
        "Collision is a set of axis-aligned boxes fitted to the visual mesh; "
        "mass and inertia are listing-based placeholders, not measured. "))
    link = ET.SubElement(robot, "link", name=f"{ASSET_NAME}_link")
    visual = ET.SubElement(link, "visual", name="cabinet_visual")
    ET.SubElement(visual, "origin", xyz="0 0 0", rpy="0 0 0")
    geometry = ET.SubElement(visual, "geometry")
    ET.SubElement(geometry, "mesh", filename=f"../meshes/{ASSET_NAME}_visual.obj", scale="1 1 1")
    for name, group in report["collision_boxes"].items():
        link.append(ET.Comment(f" {group['comment']} "))
        collision = ET.SubElement(link, "collision", name=f"{name}_collision")
        ET.SubElement(collision, "origin", xyz=fmt(group["center"]), rpy="0 0 0")
        geometry = ET.SubElement(collision, "geometry")
        ET.SubElement(geometry, "box", size=fmt(group["size"]))
    inertial = ET.SubElement(link, "inertial")
    body = report["collision_boxes"]["body"]
    ET.SubElement(inertial, "origin", xyz=fmt(body["center"]), rpy="0 0 0")
    ET.SubElement(inertial, "mass", value=f"{MASS_KG:.10g}")
    x, y, z = body["size"]
    m = MASS_KG
    ET.SubElement(inertial, "inertia",
                  ixx=f"{m*(y*y+z*z)/12:.10g}", iyy=f"{m*(x*x+z*z)/12:.10g}", izz=f"{m*(x*x+y*y)/12:.10g}",
                  ixy="0", ixz="0", iyz="0")
    ET.indent(robot)
    (ASSET_DIR / "urdf").mkdir(exist_ok=True)
    ET.ElementTree(robot).write(ASSET_DIR / "urdf" / f"{ASSET_NAME}.urdf", encoding="utf-8", xml_declaration=True)


def main() -> None:
    if abs(bpy.context.scene.unit_settings.scale_length - 1.0) > 1e-9:
        raise ValueError("Expected metre scene units; refusing an ambiguous rescale")
    objects = mesh_objects(bpy.data.collections[COLLECTION].all_objects)
    assert objects, f"No mesh objects in collection {COLLECTION!r}"

    # Keep the authored XY origin (cabinet footprint centre); place the lowest point on Z=0.
    raw = bounds(objects, Vector((0, 0, 0)))
    origin = Vector((0.0, 0.0, raw["min"][2]))

    groups: dict[str, list[bpy.types.Object]] = {name: [] for name in COLLISION_GROUPS}
    groups["body"] = []
    for obj in objects:
        for name, prefixes in COLLISION_GROUPS.items():
            if obj.name.startswith(prefixes):
                groups[name].append(obj)
                break
        else:
            groups["body"].append(obj)
    assert sum(map(len, groups.values())) == len(objects)

    comments = {
        "body": "Cabinet envelope: frame, panels, doors, rails and interior, feet top to roof.",
        "feet": "Levelling feet and casters under the base frame.",
        "handle": "Front door handle protruding from the door face.",
    }
    collision_boxes = {}
    for name in ("body", "feet", "handle"):
        if not groups[name]:
            continue
        box = bounds(groups[name], origin)
        collision_boxes[name] = {**box, "comment": comments[name], "object_names": [o.name for o in groups[name]]}

    MESH_DIR.mkdir(parents=True, exist_ok=True)
    visual = write_obj(MESH_DIR / f"{ASSET_NAME}_visual.obj", objects, origin)
    stl = write_binary_stl(MESH_DIR / f"{ASSET_NAME}_visual.stl", objects, origin)

    report = {
        "units": "metres",
        "scene_unit_system": bpy.context.scene.unit_settings.system,
        "scene_scale_length": 1.0,
        "mesh_scale": [1, 1, 1],
        "axes": "X front (glass door), Y width, Z up; origin at footprint centre on the floor",
        "source_blend": str(SOURCE_BLEND),
        "source_origin_metres": list(origin),
        "bounds": bounds(objects, origin),
        "rack_units": RACK_UNITS,
        "rack_unit_metres": U_METRES,
        "mounting_rail_height_metres": RACK_UNITS * U_METRES,
        "visual": visual,
        "stl_triangles": stl["triangles"],
        "collision_boxes": collision_boxes,
        "mass_kg": MASS_KG,
        "fixed_base": True,
        "dynamics_note": "Mass from a Sysracks 42U 24x32x84in listing (122 lb, empty); inertia is the body box AABB formula. Unmeasured placeholders.",
        "geometry_note": "Procedural Blender model (Hunyuan3D generation through Blender MCP failed); dimensions nominal 600 x 800 x 2134 mm.",
        "excluded_objects": [o.name for o in bpy.context.scene.objects if o not in objects],
    }
    write_urdf(report)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE_BLEND), copy=True, compress=True)
    print(json.dumps({"asset": str(ASSET_DIR), "size_m": report["bounds"]["size"],
                      "triangles": visual["triangles"],
                      "collision_boxes": {k: v["size"] for k, v in collision_boxes.items()}}, indent=2))


if __name__ == "__main__":
    main()
