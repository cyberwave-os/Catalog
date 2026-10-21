# UGV Beast Fusion — Asset Specification

Complete specification for `Waveshare__/UGVBeast_v2_fusion/`.

- **URDF:** `urdf/ugv_beast.urdf`
- **Robot name:** `ugv_beast`
- **Units:** metres (SI), matching the official convention
- **Lineage:** official kinematics from `Waveshare__/UGVBeast_v2__/`, high-detail
  geometry harvested from `Waveshare__/UGVBeast__/`
- **Companion docs:** `FUSION_NOTES.md` (mesh-fusion decisions),
  `../UGVBeast__/URDF_AUDIT.md` (original old-vs-official audit)

---

## 1. Provenance — which convention does this asset follow?

**It follows the new official `UGVBeast_v2__`, not the old `UGVBeast__` placeholder.**
Verified against every criterion in `../UGVBeast__/URDF_AUDIT.md`:

**15/16 criteria match the official. 0/16 match the old placeholder.**

| Criterion | FUSION | Official (v2) | Old placeholder |
|---|---|---|---|
| robot name | `ugv_beast` | `ugv_beast` ✅ | `ugv_beast_pt` |
| root offset z | `0.08` | `0.08` ✅ | `0.1` |
| `base_imu_link` | present | present ✅ | missing |
| wheel naming | up/down | up/down ✅ | front/rear |
| `3d_camera_link` | present | present ✅ | missing |
| lidar link | `base_lidar_link` | same ✅ | `lidar_link` |
| lidar yaw | `0 0 1.5708` | same ✅ | `0 0 0` |
| `pt_base_link` | present | present ✅ | missing |
| pan axis | `0 0 -1` | same ✅ | `0 0 1` |
| pan limits | ±3.14 | same ✅ | ±1.57 |
| tilt origin rpy | `1.5708 0 0` | same ✅ | `0 0 0` |
| tilt axis | `0 0 1` | same ✅ | `0 1 0` |
| tilt limits | −0.5233333 / +1.5707963 | same ✅ | ±1.57 |
| gimbal camera | `pt_camera_link` | same ✅ | `camera_link` |
| base_link mass | 2.03227 kg | same ✅ | 2.5 (placeholder) |
| unique meshes | **78** | 11 | 3 |

So it is the official kinematics throughout — the correct asymmetric tilt range,
the 90° lidar yaw, the real CAD-derived mass, the rocker up/down wheel layout,
and the full `pt_base_link` chain. **Nothing from the old placeholder's rig
survives.**

### The one non-match is intentional

The mesh row (78 vs 11) *is* the fusion work: 65 isolated gears + 2 belts + a
shoe template layered on top of the 11 official meshes. Crucially it is still
`scale = metres` like the official — **not** the old asset's
`scale="0.001 0.001 0.001"` millimetre convention. So even where it diverges, it
diverges in the official's units.

### What the old asset actually contributed

**Geometry only — never configuration.**

| From `UGVBeast__` | Used for |
|---|---|
| `meshes/ugv_body.stl` | high-detail body shell (`base_link`) |
| `meshes/UGV_Beast_PT.stl` | source for track shoes, gears, brackets, rails |

Everything was converted mm→m on the way in, so the old asset's millimetre
convention never leaked into the URDF.

> ### ⚠️ Known deviation: naming convention of added links
> The 13 official links and 12 official joints are **byte-identical** to
> `UGVBeast_v2__`. The **67 links added by the fusion** use their own scheme and
> do *not* follow the official pattern:
>
> | Official pattern | Added links | Compliance |
> |---|---|---|
> | always ends `_link` | `gear_left_13`, `track_belt_left` | **0/67** |
> | side prefix first (`left_up_wheel_link`) | side in middle (`gear_left_13`) | **0/67** |
> | positional words (`up`/`down`) | arbitrary indices (1…65) | — |
> | joints end `_joint` | ✅ | 67/67 |
> | no duplicated word | `gear_left_13_gear_joint` | **67/67 have it** |
>
> A conforming scheme would be `left_gear_13_link` with joint
> `left_gear_13_link_joint`. Renaming is a single pass through the build scripts,
> but any sensor mount or config already referencing a `gear_*` name would need
> re-pointing.

---

## 2. Kinematic rig

| | Count |
|---|---|
| Links | **80** (13 official + 67 added) |
| Joints | **79** (12 official, byte-identical + 67 added) |
| — `continuous` | **69** (4 official wheels + 65 gears) |
| — `revolute` | **2** (pan, tilt) |
| — `fixed` | **8** (incl. 2 track belts) |
| Root link | `base_footprint` — tree fully connected, acyclic |

### Official joints (unchanged)

| Joint | Type | Notes |
|---|---|---|
| `base_joint` | fixed | root offset `z = 0.08` |
| `imu_joint` | fixed | |
| `left_up/down_wheel_link_joint` | continuous | rocker layout |
| `right_up/down_wheel_link_joint` | continuous | |
| `3d_camera_link_joint` | fixed | OAK-D-Lite depth camera mount |
| `base_lidar_link_joint` | fixed | 90° yaw `rpy="0 0 1.5708"` |
| `pt_base_link_joint` | fixed | |
| `pt_base_link_to_pt_link1` | revolute | pan, axis `0 0 -1`, ±3.14 rad |
| `pt_link1_to_pt_link2` | revolute | tilt, axis `0 0 1`, −0.523 → +1.571 rad |
| `pt_link2_to_pt_camera_link` | fixed | optical frame `rpy="3.14 -1.5708 0"` |

---

## 3. Geometry / face budget

**382,899 faces across 78 unique meshes.**

| Category | Links | Faces | Share |
|---|---:|---:|---:|
| `base_link` (fused body) | 1 | 338,700 | 88.5 % |
| Isolated gears | 65 | 41,415 | 10.8 % |
| Official wheels / sensors / pan-tilt | 10 | 1,744 | 0.5 % |
| Track belt ribbons | 2 | 1,040 | 0.3 % |
| **Total** | **78** | **382,899** | |

Comparison:

| Asset | Unique meshes | Faces |
|---|---:|---:|
| Official v2 | 11 | 3,656 |
| Old placeholder | 3 | 142,722 |
| **Fusion** | **78** | **382,899** |

≈105× the official's geometry (its 11 meshes are coarse proxies — the whole
official body shell is only ~1,900 faces) and 2.7× the old placeholder, while
keeping the official's exact kinematics.

> **Collision = visual.** Every link points both `<visual>` and `<collision>` at
> the same mesh, so the collision set is another 382,899 faces. Fine for
> rendering, **too heavy for physics** — a simulator (Gazebo, Isaac, MuJoCo)
> should be given convex-hull or primitive collision proxies instead.

---

## 4. Animated drivetrain

### 4.1 Isolated gears (65)

Detected geometrically, not by hand: for each component, measure the circularity
of its cross-section in the X–Z plane (the plane a wheel sweeps when spinning
about its Y axle). A real gear shows near-complete angular coverage with a tight,
consistent outer radius.

| Detection threshold | Value |
|---|---|
| min triangles | 30 |
| angular coverage | > 0.82 |
| radial tightness (σ/μ of outer radius) | < 0.16 |
| lateral span vs radius | < 3.5 × r |

Each gear mesh is **recentred on its own measured axle** (URDF joints rotate
about the link origin, so the offset moves into the joint) and gets a
`continuous` joint on `base_link`.

**Spin rates scale as `1/radius`, not uniformly.** Every roller engages the same
belt, so they share one surface speed. Reference radius = 24.9 mm (official
up-wheel). Radii span 2.8 → 28.6 mm, giving ratios **0.87× → 8.92×**:

| Component | Radius | Spin rate |
|---|---:|---:|
| Drive sprockets (L/R) | 28.6 mm | 0.87× |
| Rear idler | 12.3 mm | 2.02× |
| Mid rollers | 8.1 mm | 3.08× |
| Bottom-run rollers | 6.0 mm | 4.13× |
| Small idlers | 2.8–3.6 mm | up to 8.92× |

> The large front component previously treated as a static *fender*
> (r = 28.6 mm at x = 84.8, z = 25.0) is in fact a **drive sprocket**, concentric
> with the official up-wheel axle at x = 83.2, z = 26.1. It was never bodywork.

**Axis-sign caveat.** The URDF's continuous axes are mixed — **30 at `(0,-1,0)`
and 39 at `(0,1,0)`** — inherited from the official model, which itself has
`right_down_wheel` opposite to `right_up_wheel`. Taken literally this spins half
the drivetrain *against* the other half. Consumers must normalise to one
rotational sense (rotating about +y by −θ ≡ about −y by +θ). The mixed axes were
deliberately left in the URDF so as not to silently diverge from the official
model; the reference viewer normalises at runtime.

### 4.2 Moving track belt (100 shoes)

Real geometry, not a texture illusion: one **812-face shoe** extracted from the
source CAD, instanced **50 per side**, repositioned every frame by arc length
along a 600-sample loop centre-line and oriented to the local tangent.

| Property | Value |
|---|---|
| Loop perimeter | 522.5 mm (left) / 522.4 mm (right) |
| Shoes per side | 50 |
| Shoe pitch | 10.5 mm |
| Track width | 44.5 mm |
| Belt speed | 34.9 mm/s (= ω·r at 1.4 rad/s) |
| Full circuit | 15.0 s |

**Path construction:** convex hull of the real track-plate footprint **plus**
explicit sampling of the wheel circles the belt wraps —
sprocket (84.8, 25.0, r 28.6), rear idler (−103.6, 2.5, r 12.3),
down wheel (−72.2, 35.6, r 12.2) — so the loop follows the wheels rather than
stopping short of them.

**Corner smoothing:** a raw convex hull is a polygon, leaving an ~81° kink where
the straight top run meets the sprocket arc. Two stages — Chaikin corner-cutting
(4 iterations, 26 → 416 points) then a windowed average over the closed path —
reduce the sharpest corner to **21.1°**. Both stages restore the original
envelope afterwards so smoothing never shrinks the belt off the track.

**Orientation:** shoe local **+X** = along path, **+Y** = across track,
**−Z** = treaded face (measured: 1373.6 vs 125.1 surface area). Basis is built
with `Z = −normal`, and the normal is a true 90° rotation of the tangent (not
"radial from centroid", which is only perpendicular on a circle). Verified
**tangent · normal = 0** and treads outward on all shoes.

The 104 original static shoes were **removed from `base_link`** — the moving
shoes replace them, so there is exactly one track, not a moving belt layered
over frozen plates.

### 4.3 Differential (skid) steering

Each track and its gears are driven independently.

| Mode | Left track | Right track | Result |
|---|---|---|---|
| Forward | forward | forward | drives ahead |
| Reverse | reverse | reverse | backs up |
| Turn left | **reverse** | **forward** | pivots left |
| Turn right | **forward** | **reverse** | pivots right |

Side assignment is **geometric** — the sign of the joint origin's lateral
coordinate (`xyz[1] > 0` → left) — so it cannot drift if naming changes.
Validated against the link names: **69/69 agree, zero disagreements, no joint at
y = 0**. Split: **29 left / 40 right**.

Both accumulators (belt arc-length and wheel angle) are signed per side, so
switching mode mid-motion reverses smoothly rather than snapping.

---

## 5. Source-CAD defect repaired

The long rails above the track runs were modelled **only on the left** in
`UGV_Beast_PT.stl`: the right side has both end caps (x ≈ −72 and x ≈ +79, at the
mirrored y range) but the 144 mm rail between them is simply absent.

Four left-only components (the 144 mm bar, its underside, two 66 mm strips —
247 triangles) are mirrored across y = 0 with winding reversed so normals stay
outward. The repair is scoped tightly: left-only, above the track runs (z > 55),
longer than 40 mm, and only where no right-side counterpart exists.

**No blanket symmetrisation was applied.** 955 left-only and 766 right-only
components exist across the model, and spot-checking showed many are genuinely
different parts at different positions rather than lost twins — mirroring all of
them would create duplicates and phantom geometry.

---

## 6. Deliberate exclusions

| Excluded | Why |
|---|---|
| Pan-tilt head above z = 92 mm (509 components) | renders from its own `pt_base_link` / `pt_link1` / `pt_link2` / `pt_camera_link` URDF links — would double-render |
| One component spanning to y = 420 mm | stray CAD sliver artifact in the source export |

---

## 7. File inventory

```
UGVBeast_v2_fusion/
├── SPECIFICATION.md          ← this document
├── FUSION_NOTES.md           mesh-fusion decisions and rationale
├── urdf/
│   └── ugv_beast.urdf        80 links, 79 joints
└── meshes/                   34 STL referenced by the URDF (0 missing, 0 orphaned)
    ├── base_link.stl                 fused body shell
    ├── gear_{left,right}_N.stl       65 isolated gears
    ├── track_belt_{left,right}.stl   belt ribbons
    ├── track_shoe.stl                shoe template (instanced at runtime)
    ├── left/right_{up,down}_wheel_link.stl
    ├── base_lidar_link.stl, 3d_camera_link.stl
    └── pt_base_link.stl, pt_link1.stl, pt_link2.stl, pt_camera_link.stl
```

`*_verts.npy` / `*_faces.npy` / `*_uv.npy` / `*_nrm.npy` are viewer fast-path
intermediates (indexed geometry). They are **not** required by the URDF and can
be deleted without affecting the asset.

---

## 8. Sensor specifications

Real hardware per the driver repo (`waveshareteam/ugv_ws`), **not** the URDF/SDF
placeholders:

| URDF link | Real hardware | H-FOV | V-FOV |
|---|---|---:|---:|
| `3d_camera_link` | Luxonis OAK-D-Lite (RGB) | 69° | **54°** |
| `3d_camera_link` | OAK-D-Lite (stereo/depth) | 73° | **58°** |
| `pt_camera_link` | USB camera via `usb_cam`, 640×480 | 95.7° | **79.2°** |

Pan-tilt camera FOV is computed from its **actual calibrated intrinsics**
(`fx = 289.11`, `fy = 289.75` from `ugv_vision/config/camera_info.yaml`) via
`FOV = 2·atan(dim / 2f)`.

> `ugv_description/model.sdf` labels the base camera `intel_realsense_r200` with
> `horizontal_fov: 1.02974` (≈59°). That is a **stale template placeholder** —
> an R200 is not fitted to this robot — and must not be used as a spec.

**Frontend note.** The `FOV (deg)` field is **vertical** FOV
(`THREE.PerspectiveCamera` convention: horizontal is derived as
`fov × aspectRatio`). Enter the V-FOV column above, and set resolution to
640×480 — both cameras are **4:3**, and the cone defaults to 16:9 if resolution
is left blank, which renders the horizontal spread too wide.
