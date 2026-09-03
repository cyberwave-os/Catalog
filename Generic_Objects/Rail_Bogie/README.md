# Generic Rail Bogie

Articulated URDF conversion of the detailed Blender rail-bogie model. The
editable source is preserved alongside link-local visual and collision meshes.

## Files

- `urdf/rail_bogie.urdf` — fixed rail root, translating bogie frame, and two
  passive rotating wheelset links
- `meshes/*_visual.obj` / `.mtl` — material-preserving visual meshes
- `meshes/*_collision.stl` — collision meshes for the same link geometry
- `source/rail_bogie.blend` — editable Blender source
- `source/export_rail_bogie.py` — deterministic mesh exporter
- `source/render_preview.py` — deterministic Blender Workbench preview renderer
- `source/export_report.json` — object grouping, joint offsets, and bounds
- `preview/rail_bogie.png` — rendered catalog preview

## Kinematics

The coordinate system follows REP-103: X is the direction of travel, Y is the
axle direction, and Z is up. `rail_base_link` is the fixed root, and the bogie
frame translates along local X through `rail_joint`. The joint's zero position
is the authored spawn pose; its `[-100, 100]` metre limits provide a generic
200 metre straight rail extent. Deployments with a known rail length should
replace those bounds with the real endpoints.

The two wheelsets rotate passively about +Y:

- `front_wheelset_joint` at X = -0.30632547852 m
- `rear_wheelset_joint` at X = +0.30632547852 m

Each Blender wheelset object contains a rigid axle and its paired wheels, so a
single continuous joint per axle preserves the real mechanical relationship.
The wheel joints are visual articulation only and must not be used as a
differential-drive declaration. Cyberwave actuates only `rail_joint`; this
suppresses the generic movable-joint motor fallback and leaves both wheelsets
passive.

When publishing or updating the catalog asset, set `fixed_base` to `true` and
retain `mujoco` in `supported_simulation_backends`. Fixing the asset root is
load-bearing: without it the simulator adds a free joint above
`rail_base_link`, allowing the complete rail constraint to drift through the
world. The matching Cyberwave asset patch supplies the `rail_joint` velocity
actuator, zero home position, and stationary capability metadata.

## Scale and dynamics

The Blender source is oversized relative to the intended Cyberwave asset. The
URDF bakes in the previously environment-authored `0.09` uniform scale across
all visual and collision meshes, wheelset offsets, inertial centres, and inertia
tensors. The resulting visual envelope is approximately 1.00 m long, 0.74 m
wide, and 0.39 m high, so twins should now be authored at scale `1.0`.

Masses are preserved while inertia tensors are scaled by `0.09²`; they remain
engineering placeholders and should be replaced with measured values before
dynamics-sensitive use. The editable Blender geometry and export report remain
in their original source scale.

## Re-exporting

Open `source/rail_bogie.blend` in Blender and run:

```python
exec(compile(open("/Users/lapsus/cw/Catalog/Generic_Objects/Rail_Bogie/source/export_rail_bogie.py").read(), "export_rail_bogie.py", "exec"))
```

The exporter rebuilds the visual/collision meshes and report, then saves the
Blender source.
