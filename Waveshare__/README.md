# Waveshare — Asset Index

One row per asset in this folder.

| Asset | What it is |
|---|---|
| `UGVBeast__/` | Asset currently used in Cyberwave — has missing fields and values not aligned to the official, which makes it sit **7.7 cm above the floor** (flying) in the 3D environment |
| `UGVBeast_official/` | Official UGV Beast asset (`ugv_beast.urdf`), never modified |
| `UGVBeast_update/` | The currently used asset with 9 values updated to match the official — fixes the pan-tilt kinematics and cuts the float from 7.7 → 5.7 cm (**does not fully land it — see note**) |
| `UGVBeast_v2_fusion/` | Official UGV Beast asset fused with the currently used one — official kinematics + high-detail geometry + animated drivetrain (65 gears, 100 moving track shoes) |
| `UGVRovers_official/` | Official UGV Rover asset (`ugv_rover.urdf`), never modified — both PI5 and Jetson Orin variants |

---

## Key numbers

| Asset | robot name | Links | Joints | Meshes | Faces | Official criteria met |
|---|---|---:|---:|---:|---:|---:|
| `UGVBeast__` | `ugv_beast_pt` | 10 | 9 | 3 | 142,722 | 0/16 |
| `UGVBeast_official` | `ugv_beast` | 13 | 12 | 11 | 3,656 | 16/16 |
| `UGVBeast_update` | `ugv_beast_pt` | 11 | 10 | 3 | 142,722 | **9/16** |
| `UGVBeast_v2_fusion` | `ugv_beast` | 80 | 79 | 78 | 382,899 | 15/16 * |
| `UGVRovers_official` | `ugv_rover` | 13 | 12 | 11 | 2,806 | reference |

\* the one non-match is the mesh count — that *is* the fusion work.

---

## ⚠ Note on the "flying" problem

Measured ground clearance (root offset + lowest visual geometry, in the
`base_footprint` frame — positive means the hull floats):

| Asset | Root offset z | Lowest geometry | Ground clearance |
|---|---:|---:|---:|
| `UGVBeast__` | 0.100 | −0.0230 m | **+7.7 cm** |
| `UGVBeast_update` | 0.080 | −0.0230 m | **+5.7 cm** |
| `UGVBeast_official` | 0.080 | −0.0210 m | **+5.9 cm** |
| `UGVBeast_v2_fusion` | 0.080 | −0.0234 m | **+5.7 cm** |

**Correcting the root offset to the official `0.08` does not fully land the
asset.** It removes 2 cm of the 7.7 cm, but ~5.7 cm remains — and the **official
model itself floats 5.9 cm**, so matching the official cannot close the gap.

The root offset was therefore only part of the cause. To actually seat the robot
on the ground plane, the root offset needs to be ~`0.023` rather than `0.08`
(so the lowest geometry lands at z ≈ 0), **or** the environment must place the
asset by its geometry rather than by `base_footprint`.

Worth knowing: `UGVBeast__` and `UGVBeast_update` also have **bare wheel links
with no geometry, collision, or inertial**, so nothing exists at wheel level to
make contact with the ground in the first place.

---

## Which one to use

- **Rendering / demos with full fidelity and moving tracks** → `UGVBeast_v2_fusion`
- **Faithful reference, no local changes** → `UGVBeast_official` / `UGVRovers_official`
- **Lightweight meshes but correct pan-tilt behaviour** → `UGVBeast_update`
- **Physics / dynamics** → none of the above as-is: the fusion asset uses its full
  382,899-face visual mesh as collision (needs convex proxies), and the
  placeholder-derived assets have no wheel inertials at all.

---

## Per-asset documentation

| Asset | Docs |
|---|---|
| `UGVBeast__/` | `URDF_AUDIT.md` — original old-vs-official gap analysis, floor-clearance measurements, camera FOV derivations |
| `UGVBeast_update/` | `UPDATE_NOTES.md` — the 9 changed values, the `pt_base_link` pivot split, and the 7 remaining deviations |
| `UGVBeast_v2_fusion/` | `SPECIFICATION.md` — full spec (provenance, rig, face budget, drivetrain, steering); `FUSION_NOTES.md` — mesh-fusion decisions |
| `UGVBeast_official/`, `UGVRovers_official/` | none — unmodified upstream from `waveshareteam/ugv_ws` |
