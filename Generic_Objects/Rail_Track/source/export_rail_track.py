"""Run in the authored testbed.blend scene via Blender MCP or Python console.

exec(compile(open(path).read(), path, 'exec'), {'__file__': path})
The output directory is derived from this script, never the current blend path.
"""
import json
import struct
from pathlib import Path
import xml.etree.ElementTree as ET

import bpy
from mathutils import Vector


def main():
    root = Path(__file__).resolve().parents[1]
    for folder in ('meshes', 'textures', 'urdf', 'source'):
        (root / folder).mkdir(exist_ok=True)
    objects = [bpy.data.objects[name] for name in ('0', '0.001', '0.002')]
    scale = bpy.context.scene.unit_settings.scale_length
    graph = bpy.context.evaluated_depsgraph_get()
    records = []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            assert mesh.uv_layers.active, obj.name
            normals = evaluated.matrix_world.to_3x3().inverted().transposed()
            for triangle in mesh.loop_triangles:
                corners = []
                loops = list(triangle.loops)
                if evaluated.matrix_world.determinant() < 0:
                    loops.reverse()
                for loop in loops:
                    vertex = mesh.vertices[mesh.loops[loop].vertex_index]
                    corners.append((scale * (evaluated.matrix_world @ vertex.co),
                                    mesh.uv_layers.active.data[loop].uv.copy(),
                                    (normals @ mesh.corner_normals[loop].vector).normalized()))
                records.append((obj.name, corners))
        finally:
            evaluated.to_mesh_clear()
    points = [corner[0] for _, corners in records for corner in corners]
    low = Vector(min(p[i] for p in points) for i in range(3))
    high = Vector(max(p[i] for p in points) for i in range(3))
    # Keep authored X travel/Y gauge/Z up; center XY and place the base on Z=0.
    origin = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    material = objects[0].data.materials[0]
    assert all(list(o.data.materials) == [material] for o in objects)
    textures = {}
    for node_name, role in [('Image Texture', 'base_color'),
                            ('Image Texture.001', 'normal'),
                            ('Image Texture.002', 'occlusion')]:
        image = material.node_tree.nodes[node_name].image
        assert image.packed_file and image.file_format == 'JPEG'
        path = root / 'textures' / f'rail_track_{role}.jpg'
        path.write_bytes(bytes(image.packed_file.data))
        textures[role] = {'file': path.relative_to(root).as_posix(),
                          'size': list(image.size), 'colorspace': image.colorspace_settings.name}
    mesh_dir = root / 'meshes'
    with (mesh_dir / 'rail_track_visual.obj').open('w') as obj_file, (mesh_dir / 'rail_track_collision.stl').open('wb') as stl:
        obj_file.write('# Metres; X travel, Y gauge, Z up\nmtllib rail_track_visual.mtl\nusemtl rail_track\n')
        stl.write(b'Rail track collision'.ljust(80, b'\0'))
        stl.write(struct.pack('<I', len(records)))
        previous = None
        for index, (name, corners) in enumerate(records):
            if name != previous:
                obj_file.write(f'o track_section_{name.replace(".", "_")}\n')
                previous = name
            positions = [p - origin for p, _, _ in corners]
            for position, (_, uv, normal) in zip(positions, corners):
                obj_file.write('v ' + ' '.join(f'{v:.9g}' for v in position) + '\n')
                obj_file.write('vt ' + ' '.join(f'{v:.9g}' for v in uv) + '\n')
                obj_file.write('vn ' + ' '.join(f'{v:.9g}' for v in normal) + '\n')
            indices = range(index * 3 + 1, index * 3 + 4)
            obj_file.write('f ' + ' '.join(f'{i}/{i}/{i}' for i in indices) + '\n')
            normal = (positions[1] - positions[0]).cross(positions[2] - positions[0]).normalized()
            stl.write(struct.pack('<12fH', *normal, *(v for p in positions for v in p), 0))
    (mesh_dir / 'rail_track_visual.mtl').write_text(
        '# norm is a tangent-space normal-map extension; support varies by viewer.\n'
        '# Occlusion is preserved separately; classic MTL has no standard AO slot.\n'
        'newmtl rail_track\nKa 1 1 1\nKd 1 1 1\nKs 0 0 0\nd 1\nillum 2\nNs 0\nPr 1\nPm 0\n'
        'map_Kd ../textures/rail_track_base_color.jpg\n'
        'norm ../textures/rail_track_normal.jpg\n')
    robot = ET.Element('robot', name='rail_track')
    robot.append(ET.Comment('Static scenery: load with fixed_base=true. No inferred mass or articulation.'))
    link = ET.SubElement(robot, 'link', name='rail_track_link')
    for kind, filename in [('visual', 'rail_track_visual.obj'), ('collision', 'rail_track_collision.stl')]:
        element = ET.SubElement(link, kind)
        ET.SubElement(element, 'origin', xyz='0 0 0', rpy='0 0 0')
        geometry = ET.SubElement(element, 'geometry')
        ET.SubElement(geometry, 'mesh', filename='../meshes/' + filename, scale='1 1 1')
    ET.indent(robot)
    ET.ElementTree(robot).write(root / 'urdf/rail_track.urdf', encoding='utf-8', xml_declaration=True)
    report = {'units': 'metres', 'source_objects': [o.name for o in objects],
              'scene_scale_length': scale, 'source_origin_metres': list(origin),
              'bounds': {'min': list(low-origin), 'max': list(high-origin), 'size': list(high-low)},
              'triangles': len(records), 'textures': textures, 'fixed_base': True}
    (root / 'source/export_report.json').write_text(json.dumps(report, indent=2) + '\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(root / 'source/rail_track.blend'), copy=True, compress=True)
    print(json.dumps(report, indent=2))


main()
