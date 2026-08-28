# Generic Rail Bogie

Articulated URDF conversion of the detailed Blender rail-bogie model. The
editable source is preserved alongside link-local visual and collision meshes.

## Files

- `urdf/rail_bogie.urdf` — frame plus two rotating wheelset links
- `meshes/*_visual.obj` / `.mtl` — material-preserving visual meshes
- `meshes/*_collision.stl` — collision meshes for the same link geometry
- `source/rail_bogie.blend` — editable Blender source
- `source/export_rail_bogie.py` — deterministic mesh exporter
- `source/render_preview.py` — deterministic Blender Workbench preview renderer
- `source/export_report.json` — object grouping, joint offsets, and bounds
- `preview/rail_bogie.png` — rendered catalog preview

## Kinematics

The coordinate system follows REP-103: X is the direction of travel, Y is the
axle direction, and Z is up. The two wheelsets rotate continuously about +Y:

- `front_wheelset_joint` at X = -3.403616428
- `rear_wheelset_joint` at X = +3.403616428

Each Blender wheelset object contains a rigid axle and its paired wheels, so a
single continuous joint per axle preserves the real mechanical relationship.
URDF defines the bogie's internal articulation; rail contact or a constraint
that keeps the bogie on a track belongs in the simulator/environment model.

## Scale and dynamics

The Blender file declares metric units at a scale length of 1.0, and the meshes
are exported without a scale correction. The resulting visual envelope is
approximately 11.13 m long, 8.26 m wide, and 4.32 m high. Verify this against a
known real-world measurement before production use; if the Blender geometry was
modeled in arbitrary units, apply one uniform scale consistently to all six
mesh references and both joint X offsets.

Masses and inertias in the URDF are engineering placeholders intended to keep
the model well-formed. Replace them with measured or CAD-derived values before
dynamics-sensitive simulation.

## Re-exporting

Open `source/rail_bogie.blend` in Blender and run:

```python
exec(compile(open("/Users/lapsus/cw/Catalog/Generic_Objects/Rail_Bogie/source/export_rail_bogie.py").read(), "export_rail_bogie.py", "exec"))
```

The exporter rebuilds the visual/collision meshes and report, then saves the
Blender source.
