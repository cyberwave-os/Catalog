# 42U Server Rack Cabinet

Static, single-link 42U 19" server rack cabinet (Sysracks-style: glass front
door with red trim, perforated side panels, vented rear door, levelling feet
and casters). Folder organisation follows `../Rail_Track/` and `../Rail_Bogie_Small/`;
collision follows the box-primitive convention of `../Black_Frame/`.

## Provenance

The intent was a Tencent Hunyuan3D generation through Blender MCP from the
product photo. Every `generate_3d` call (image-conditioned and text-conditioned)
failed inside the addon's generator pipeline with
`Nano Banana image generation call failed` on Blender 5.0.0 Beta, with the MCP
addon reported as outdated. The mesh here is therefore a **procedural Blender
model** built to the cabinet's nominal dimensions, not a generated or scanned
mesh. `source/build_server_rack_42u.py` rebuilds it from spec-sheet constants.
The exporter is mesh-agnostic: drop a generated cabinet into the
`RACK | 42U server cabinet` collection and re-run it to replace the visuals.

## Files

- `urdf/server_rack_42u.urdf`: single rigid link, OBJ visual, three box collisions.
- `meshes/server_rack_42u_visual.obj` / `.mtl`: material-preserving visual mesh
  (1,012 triangles; glass uses `d` alpha).
- `meshes/server_rack_42u_visual.stl`: same triangles as binary STL for viewers
  that need a mesh collision instead of primitives. Not referenced by the URDF.
- `source/server_rack_42u.blend`: editable source (Git LFS).
- `source/build_server_rack_42u.py`: rebuilds the procedural cabinet in the live scene.
- `source/export_server_rack_42u.py`: repeatable exporter; verifies the rail spacing against the spec.
- `source/export_report.json`: bounds, collision box fits, object grouping, placeholders.
- `source/render_preview.py`: renders the exported mesh with collision boxes as wireframes.
- `preview/server_rack_42u.png`: preview of the export.

## Dimensions and coordinates

Units are metres. **X is the front (glass door), Y is the width, Z is up.** The
origin is the footprint centre on the floor. Use asset/twin scale **1.0**.

| Quantity | Value |
| --- | --- |
| Cabinet envelope (D × W × H) | 0.800 × 0.600 × 2.138 m |
| Door handle protrusion beyond the door face | 0.015 m (+X) |
| Floor to base frame (feet / casters) | 0.050 m |
| Usable depth (front-to-rear rail centres) | 0.711 m (28") |
| Mounting rails | 42U × 44.45 mm = 1.867 m tall |
| Rail clear opening / hole-line spacing | 450.85 mm / 465.1 mm (19" EIA-310) |
| Rated load capacity (metadata only) | 726 kg (1600 lb) |

External depth, usable depth and load capacity come from the Sysracks
floor-standing spec sheet (32"/800 mm variant); width and overall height are
nominal catalogue values for the 24" × 32" × 84" cabinet, not measured hardware.
The exporter asserts the modelled rail spacing against these figures and
records them under `spec` and `rails` in `export_report.json`.

## Collision and simulation

Load with `fixed_base=true`. Collision is three axis-aligned boxes fitted by the
exporter to the visual geometry:

- `body_collision`: full cabinet envelope from the top of the feet to the roof.
- `feet_collision`: slab under the base frame covering feet and casters.
- `handle_collision`: the front door handle.

The interior is treated as solid; nothing can be placed inside the cabinet in
simulation. Mass (55.3 kg, from a 122 lb empty-cabinet listing) and the box-AABB
inertia are **unmeasured placeholders**. The 726 kg load capacity is recorded
as metadata only; no equipment mass is modelled. There are no joints: doors do
not open.

## Re-export

Open `source/server_rack_42u.blend` in Blender (or rebuild the geometry first
with `build_server_rack_42u.py`) and run:

```python
import runpy
runpy.run_path('/Users/lapsus/cw/Catalog/Generic_Objects/Server_Rack_42U/source/build_server_rack_42u.py', run_name='__main__')
runpy.run_path('/Users/lapsus/cw/Catalog/Generic_Objects/Server_Rack_42U/source/export_server_rack_42u.py', run_name='__main__')
```

Then render the preview from a shell:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python Generic_Objects/Server_Rack_42U/source/render_preview.py
```

Validation performed: URDF parsed, mesh paths resolved, every `usemtl` defined
in the MTL, STL byte length matches its triangle count, rail spacing asserted
by the exporter, collision box fits checked visually in the preview. No physics-engine rollout was performed.
