# Generic Rail Track

Textured, rigid railway track section exported from the authored `testbed.blend`
scene through Blender MCP. Folder organization follows `../Rail_Bogie/`.
All three source mesh objects (`0`, `0.001`, `0.002`) retain their relative poses.

## Files

- `urdf/rail_track.urdf`: single rigid link with visual and collision geometry.
- `meshes/rail_track_visual.obj` / `.mtl`: triangulated visual geometry, UVs,
  corner normals, and relative texture references.
- `meshes/rail_track_collision.stl`: matching detailed collision surface.
- `textures/rail_track_*.jpg`: original packed 4096 × 4096 base-color,
  tangent-space normal, and occlusion images, extracted without recompression.
- `source/rail_track.blend`: compressed editable copy with packed textures.
- `source/export_rail_track.py`: reproducible exporter.
- `source/export_report.json`: bounds, source grouping, texture roles and counts.

## Placement and simulation

Units are metres, with X along the track, Y across it and Z up. The exported
origin is the XY center at the lowest mesh point. Dimensions are approximately
3.8884 × 1.3115 × 0.3105 m. Authored scale is preserved; no real-world rail-gauge
calibration is claimed. Use asset/twin scale `1.0`.

Load with `fixed_base=true`. This is static scenery, with no joints or invented
mass/inertia. Collision uses the original 188,312 triangles and is intended for
static triangle-mesh collision; simulation engines that convexify meshes may
require a dedicated collision approximation.

The OBJ material references base color and the normal-map `norm` extension.
Normal-map support depends on the viewer. Classic MTL has no standard occlusion
slot, so the occlusion image is provided separately and its original shader
connection remains in the Blender source. No roughness or metallic texture
connections have been invented.

## Re-export

Open `source/rail_track.blend`. In Blender's Python console, set `path` to the
absolute path of `source/export_rail_track.py`, then run:

```python
exec(compile(open(path).read(), path, 'exec'), {'__file__': path})
```

The script rebuilds the URDF, meshes, textures and report beside itself, then
saves a copy of the Blender scene. It does not change the active source file.

Validation: visual OBJ re-imported through Blender MCP with all 188,312 faces,
UVs and base-color texture resolved; relative URDF/MTL paths and binary STL
triangle count checked. No physics-engine rollout was performed.
