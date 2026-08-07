"""Standardized camera/lighting render of a Catalog asset's meshes, so every
asset's preview image is visually comparable instead of depending on
whatever the last interactive session's viewport happened to show.

This is a plain headless Blender batch script — independent of the
BlenderMCP addon/socket server (start_blendermcp.py's job). Use this one for
repeatable, scriptable preview renders; use the MCP server for interactive,
Claude-driven mesh inspection/fixing.

Usage:
    blender --background --python render_asset.py -- \\
        --meshes-dir ../../Unitree/D1_T/D1_T_Gripper/meshes \\
        --preset presets/studio_three_point.json \\
        --out /tmp/d1_t_gripper_render.png
"""

import argparse
import json
import math
import sys
from pathlib import Path

import bpy


def parse_args():
    # Blender passes its own args before "--"; only what's after belongs to us.
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meshes-dir", help="directory of .stl meshes to import (non-recursive)")
    parser.add_argument("--meshes", nargs="+", help="explicit list of mesh files, alternative to --meshes-dir")
    parser.add_argument("--preset", required=True, help="path to a camera/lighting preset JSON")
    parser.add_argument("--out", required=True, help="output PNG path")
    return parser.parse_args(argv)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)


def import_meshes(paths: list[Path]) -> list[bpy.types.Object]:
    imported = []
    for path in paths:
        before = set(bpy.context.scene.objects)
        bpy.ops.wm.stl_import(filepath=str(path))
        after = set(bpy.context.scene.objects)
        imported.extend(after - before)
    return imported


def scene_bounds(objects: list[bpy.types.Object]):
    import mathutils

    min_v = mathutils.Vector((math.inf, math.inf, math.inf))
    max_v = mathutils.Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_v = mathutils.Vector(min(a, b) for a, b in zip(min_v, world_corner))
            max_v = mathutils.Vector(max(a, b) for a, b in zip(max_v, world_corner))
    center = (min_v + max_v) / 2
    size = max_v - min_v
    return center, size


def spherical_offset(azimuth_deg: float, elevation_deg: float, distance: float):
    az = math.radians(azimuth_deg)
    el = math.radians(elevation_deg)
    x = distance * math.cos(el) * math.cos(az)
    y = distance * math.cos(el) * math.sin(az)
    z = distance * math.sin(el)
    return x, y, z


def point_at(obj: bpy.types.Object, target, location):
    import mathutils

    obj.location = location
    direction = mathutils.Vector(target) - mathutils.Vector(location)
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_camera(preset: dict, center, max_dim: float):
    cam_cfg = preset["camera"]
    distance = max_dim * cam_cfg["distance_multiplier"]
    offset = spherical_offset(cam_cfg["azimuth_deg"], cam_cfg["elevation_deg"], distance)
    location = (center.x + offset[0], center.y + offset[1], center.z + offset[2])

    cam_data = bpy.data.cameras.new("PreviewCamera")
    cam_data.lens = cam_cfg["lens_mm"]
    cam_obj = bpy.data.objects.new("PreviewCamera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    point_at(cam_obj, center, location)
    bpy.context.scene.camera = cam_obj


def setup_lights(preset: dict, center, max_dim: float):
    for light_cfg in preset["lights"]:
        distance = max_dim * light_cfg["distance_multiplier"]
        offset = spherical_offset(light_cfg["azimuth_deg"], light_cfg["elevation_deg"], distance)
        location = (center.x + offset[0], center.y + offset[1], center.z + offset[2])

        light_data = bpy.data.lights.new(light_cfg["name"], type=light_cfg["type"])
        light_data.energy = light_cfg["energy"]
        if hasattr(light_data, "size"):
            light_data.size = light_cfg["size"]
        light_obj = bpy.data.objects.new(light_cfg["name"], light_data)
        bpy.context.scene.collection.objects.link(light_obj)
        point_at(light_obj, center, location)


def setup_world_background(color: list[float]):
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (*color, 1.0)


def setup_render(preset: dict, out_path: str):
    render_cfg = preset["render"]
    scene = bpy.context.scene
    scene.render.engine = render_cfg["engine"]
    scene.render.resolution_x, scene.render.resolution_y = render_cfg["resolution"]
    if scene.render.engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        scene.eevee.taa_render_samples = render_cfg["samples"]
    elif scene.render.engine == "CYCLES":
        scene.cycles.samples = render_cfg["samples"]
    scene.render.filepath = out_path
    scene.render.image_settings.file_format = "PNG"


def main():
    args = parse_args()
    preset = json.loads(Path(args.preset).read_text())

    if args.meshes:
        mesh_paths = [Path(p) for p in args.meshes]
    elif args.meshes_dir:
        mesh_paths = sorted(Path(args.meshes_dir).glob("*.STL")) + sorted(Path(args.meshes_dir).glob("*.stl"))
    else:
        raise SystemExit("pass --meshes or --meshes-dir")

    if not mesh_paths:
        raise SystemExit(f"no .stl meshes found")

    clear_scene()
    objects = import_meshes(mesh_paths)
    center, size = scene_bounds(objects)
    max_dim = max(size.x, size.y, size.z) or 1.0

    setup_camera(preset, center, max_dim)
    setup_lights(preset, center, max_dim)
    setup_world_background(preset["background_color"])
    setup_render(preset, args.out)

    bpy.ops.render.render(write_still=True)
    print(f"rendered {len(mesh_paths)} meshes -> {args.out}")


if __name__ == "__main__":
    main()
