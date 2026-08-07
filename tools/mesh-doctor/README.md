# mesh-doctor

Tool 3 of the [tool bag](../README.md) — see
[`TWIN_PREVIEW_TOOL_PLAN.md`](../../TWIN_PREVIEW_TOOL_PLAN.md) §5 for the
full design rationale.

Automated mesh + URDF repair, running *before* `twin-preview` in the loop
(plan §8) — cheap, Docker-free, browser-free checks and fixes on the files
themselves. No single existing tool combines what this does (confirmed by
the plan's §7 prior-art research), so this is a thin, purpose-built script
collection over three real, actively-maintained libraries — not a vendored
product.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## `mesh_fixes.py` — trimesh, the "safe to auto-apply" fixes (plan §5.3)

```bash
python3 -m mesh_doctor.mesh_fixes path/to/link.stl \
  --recenter bbox \
  --rescale 0.001 \
  --fix-normals \
  --collision-hull-out path/to/link_collision.stl \
  --out path/to/link.stl
```

Recentering, mm→m rescale, normal/winding fixes, and a convex-hull collision
mesh — corrections to unambiguous defects. Verified against the real
`Unitree/D1_T/D1_T_Gripper/meshes/base_link.STL` while building this: extents
`[0.118, 0.108, 0.058]` m, watertight, correctly *not* flagged as
likely-still-millimetres.

## `urdf_doctor.py` — yourdfpy, structural checks (plan §5.2)

```bash
python3 -m mesh_doctor.urdf_doctor path/to/asset.urdf
```

Checks, in one pass, what no single existing tool checks together: every
joint's parent/child link exists, every mesh file referenced actually
resolves (via yourdfpy's own `validate_filenames()`), and every inertia
tensor is positive-definite and satisfies the triangle inequalities. Verified
clean (`ok=True`) against `d1_t_gripper.urdf`.

## `mesh_repair_heavy.py` — PyMeshLab fallback (plan §5.2)

Only reach for this when `mesh_fixes.py` isn't enough — non-manifold repair,
hole-filling, quality-aware decimation for a `<collision>` mesh that needs to
stay close to the real shape (a convex hull is often the better default via
`mesh_fixes.convex_hull_collision`; this is for when it isn't):

```bash
python3 -m mesh_doctor.mesh_repair_heavy path/to/link.stl \
  --repair-non-manifold --close-holes --reorient-normals \
  --decimate-for-collision 500 \
  --out path/to/link_collision.stl
```

## What this does *not* decide (plan §5.3)

Anything where "correct" depends on the asset's actual design intent — e.g.
the D1-T gripper's visible gap between the wrist and finger meshes found
earlier in `twin-preview`'s render: is that a mesh bug, or the real
hardware's mounting geometry? `mesh-doctor` doesn't guess. That class of
question belongs to a human, or to me looking at `twin-preview`'s render —
not to an auto-fix here.
