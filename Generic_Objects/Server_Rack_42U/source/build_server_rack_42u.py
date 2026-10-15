"""Build the procedural 42U server rack cabinet in the live Blender scene.

Rebuilds the "RACK | 42U server cabinet" collection from scratch, in metres:
X is the front (glass door), Y the width, Z up, origin at the footprint centre
on the floor. Dimensions follow the Sysracks floor-standing spec sheet for the
32" (800 mm) depth variant and EIA-310 for the 19" rails. Run with:

    import runpy
    runpy.run_path('/abs/path/to/build_server_rack_42u.py', run_name='__main__')

then run export_server_rack_42u.py.
"""
import bpy
from mathutils import Vector

W, D = 0.600, 0.800            # external width (Y) and external depth (X): 24" x 32"
H_TOP = 2.134                  # overall height, 84" listing
Z_FEET = 0.05                  # casters / levelling feet height
BASE_T = 0.04                  # base frame thickness
TOP_T = 0.04
POST = 0.04
U = 0.04445                    # 1U per EIA-310
RACK_UNITS = 42
RAIL_H = RACK_UNITS * U        # 1.8669 m
USABLE_DEPTH = 0.711           # 28": front-to-rear mounting rail centre spacing
EIA_RAIL_OPENING = 0.45085     # 17.75": clear width between the 19" rails
RAIL_W = 0.03                  # mounting rail width (Y); hole line at +/-0.23255 lies inside it
RAIL_T = 0.02                  # mounting rail thickness (X)

COLLECTION = "RACK | 42U server cabinet"


def material(name, rgb, metallic=0.0, roughness=0.5, alpha=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    m.diffuse_color = (*rgb, alpha)
    if alpha < 1.0:
        try:
            m.blend_method = 'BLEND'
        except Exception:
            pass
    return m


def main():
    coll = bpy.data.collections.get(COLLECTION)
    if coll:
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    else:
        coll = bpy.data.collections.new(COLLECTION)
        bpy.context.scene.collection.children.link(coll)

    m_black = material("rack_black_steel", (0.012, 0.013, 0.015), 0.3, 0.55)
    m_perf = material("rack_perforated_black", (0.02, 0.021, 0.024), 0.3, 0.7)
    m_glass = material("rack_door_glass", (0.05, 0.07, 0.09), 0.0, 0.05, 0.35)
    m_trim = material("rack_red_trim", (0.75, 0.03, 0.02), 0.0, 0.4)
    m_rail = material("rack_galvanized_rail", (0.45, 0.47, 0.5), 0.9, 0.35)
    m_chrome = material("rack_chrome", (0.8, 0.8, 0.82), 1.0, 0.25)

    def link(o):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
        return o

    def box(name, size, center, mat):
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
        o = bpy.context.active_object
        o.name = name
        o.scale = size
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(mat)
        return link(o)

    def cyl(name, radius, depth, center, mat, axis='Z'):
        rot = {'Z': (0, 0, 0), 'Y': (1.5707963, 0, 0), 'X': (0, 1.5707963, 0)}[axis]
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=radius, depth=depth, location=center, rotation=rot)
        o = bpy.context.active_object
        o.name = name
        o.data.materials.append(mat)
        return link(o)

    hx, hy = D / 2, W / 2
    z_body0, z_body1 = Z_FEET, H_TOP
    z_post0, z_post1 = z_body0 + BASE_T, z_body1 - TOP_T
    post_h = z_post1 - z_post0

    box("base_frame | steel", (D, W, BASE_T), (0, 0, z_body0 + BASE_T / 2), m_black)
    box("top_panel | steel", (D, W, TOP_T), (0, 0, z_body1 - TOP_T / 2), m_black)
    box("top_vent | perforated", (0.5, 0.4, 0.004), (0, 0, z_body1 + 0.002), m_perf)

    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"corner_post_{'f' if sx > 0 else 'r'}{'l' if sy > 0 else 'r'} | steel",
                (POST, POST, post_h), (sx * (hx - POST / 2), sy * (hy - POST / 2), z_post0 + post_h / 2), m_black)
    for sy in (-1, 1):
        box(f"side_panel_{'l' if sy > 0 else 'r'} | perforated", (D - 2 * POST, 0.012, post_h),
            (0, sy * (hy - 0.006), z_post0 + post_h / 2), m_perf)
    box("rear_door | perforated", (0.018, W - 2 * POST, post_h), (-(hx - 0.009), 0, z_post0 + post_h / 2), m_perf)

    # Front door: frame, glass, red trim stripes, handle.
    door_x = hx - 0.010
    door_w = W - 2 * POST
    stile, rail_t = 0.09, 0.07
    box("front_door_stile_l | steel", (0.02, stile, post_h), (door_x, door_w / 2 - stile / 2, z_post0 + post_h / 2), m_black)
    box("front_door_stile_r | steel", (0.02, stile, post_h), (door_x, -(door_w / 2 - stile / 2), z_post0 + post_h / 2), m_black)
    box("front_door_rail_top | steel", (0.02, door_w - 2 * stile, rail_t), (door_x, 0, z_post1 - rail_t / 2), m_black)
    box("front_door_rail_bottom | steel", (0.02, door_w - 2 * stile, rail_t), (door_x, 0, z_post0 + rail_t / 2), m_black)
    glass_h, glass_w = post_h - 2 * rail_t, door_w - 2 * stile
    box("front_door_glass | glass", (0.005, glass_w, glass_h), (door_x + 0.004, 0, z_post0 + post_h / 2), m_glass)
    for sy in (-1, 1):
        box(f"red_trim_{'l' if sy > 0 else 'r'} | trim", (0.004, 0.014, glass_h),
            (door_x + 0.010, sy * (glass_w / 2 - 0.012), z_post0 + post_h / 2), m_trim)
    box("door_handle | chrome", (0.02, 0.025, 0.12), (door_x + 0.015, -(door_w / 2 - stile / 2), 1.05), m_chrome)

    # 19" EIA-310 mounting rails: clear opening 450.85 mm, front/rear centres 711 mm apart.
    rail_y = EIA_RAIL_OPENING / 2 + RAIL_W / 2
    rail_x = USABLE_DEPTH / 2
    rail_z0 = z_post0 + 0.05
    for sx, tag in ((rail_x, "front"), (-rail_x, "rear")):
        for sy in (-1, 1):
            box(f"mount_rail_{tag}_{'l' if sy > 0 else 'r'} | rail", (RAIL_T, RAIL_W, RAIL_H),
                (sx, sy * rail_y, rail_z0 + RAIL_H / 2), m_rail)

    box("shelf | steel", (0.45, 0.44, 0.012), (0.0, 0, 1.00), m_black)

    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(f"caster_{'f' if sx > 0 else 'r'}{'l' if sy > 0 else 'r'} | steel", 0.030, 0.025,
                (sx * (hx - 0.08), sy * (hy - 0.07), 0.030), m_black, axis='Y')
            cyl(f"foot_{'f' if sx > 0 else 'r'}{'l' if sy > 0 else 'r'} | chrome", 0.022, Z_FEET,
                (sx * (hx - 0.045), sy * (hy - 0.045), Z_FEET / 2), m_chrome, axis='Z')

    objs = [o for o in coll.objects if o.type == 'MESH']
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = Vector(min(p[i] for p in pts) for i in range(3))
    hi = Vector(max(p[i] for p in pts) for i in range(3))
    print("objects:", len(objs), "size:", tuple(round(v, 4) for v in (hi - lo)))
    print("rail centres x:", (-rail_x, rail_x), "rail inner faces y:", (-EIA_RAIL_OPENING / 2, EIA_RAIL_OPENING / 2))


if __name__ == "__main__":
    main()
