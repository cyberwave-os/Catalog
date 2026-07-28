# UGV Beast — Update Notes

`Waveshare__/UGVBeast_update/` is a copy of the original placeholder asset
`Waveshare__/UGVBeast__/` with **nine kinematic values migrated to the official
Waveshare specification**. Meshes, link naming, and overall structure are
otherwise unchanged.

- **URDF:** `urdf/NEWDATAUGV_BeastUGV_.urdf`
- **Robot name:** `ugv_beast_pt` *(unchanged — see §3)*
- **Copied from:** `Waveshare__/UGVBeast__/`
- **Reference for official values:** `Waveshare__/UGVBeast_official/urdf/ugv_beast.urdf`
- **Original gap analysis:** `Waveshare__/UGVBeast__/URDF_AUDIT.md`

**Compliance: 9/16 audit criteria now match the official** (the original asset
matched 0/16).

---

## 1. What changed

All nine requested values, verified after edit:

| Criterion | Before | After | Why it matters |
|---|---|---|---|
| root offset z | `0.1` | **`0.08`** | `0.1` left the hull floating ~7.7 mm above the ground plane |
| lidar yaw | `0 0 0` | **`0 0 1.5708`** | the real lidar is mounted rotated 90° |
| `pt_base_link` | missing | **added** (+ `pt_base_link_joint`) | restores the official pan-tilt chain |
| pan axis | `0 0 1` | **`0 0 -1`** | pan was rotating the wrong way |
| pan limits | ±1.57 (±90°) | **±3.14 (±180°)** | real pan servo has full ±180° travel |
| tilt origin rpy | `0 0 0` | **`1.5708 0 0`** | rotates the joint frame so tilt is a true pitch |
| tilt axis | `0 1 0` | **`0 0 1`** | pairs with the rotated origin above |
| tilt limits | ±1.57 (symmetric) | **−0.5233333 / +1.5707963** | real tilt is asymmetric: −30° down, +90° up |
| base mass | `2.5` (placeholder) | **`2.03227373732274` kg** | CAD-derived value |

### Why tilt needs *both* the rpy and the axis change

They only work as a pair. With `rpy="1.5708 0 0"` the joint frame's **z** axis
lands on the vehicle's **lateral** axis, so `axis="0 0 1"` becomes a true pitch.
Changing either one alone would leave the tilt rotating about the wrong axis —
which is why the official model ships them together.

### Structure of the new pan-tilt chain

Before — `pt_link1` hung directly off the body:

```
base_link ──pt_base_link_to_pt_link1──> pt_link1 ──> pt_link2
```

After — official three-stage chain:

```
base_link ──pt_base_link_joint(fixed)──> pt_base_link
          ──pt_base_link_to_pt_link1(revolute, pan)──> pt_link1
          ──pt_link1_to_pt_link2(revolute, tilt)──> pt_link2
```

> ### ⚠ Design decision: how the pan pivot offset was split
> Inserting `pt_base_link` means one joint origin becomes two, and the offsets
> had to be divided. Rather than copy the official **absolute** offsets — which
> would have moved the pan pivot ~9 mm upward, off this asset's own body mesh —
> the split preserves the original pivot location:
>
> | Joint | Origin xyz |
> |---|---|
> | `base_link` → `pt_base_link` | `-0.013651 0 0.088` |
> | `pt_base_link` → `pt_link1` | `0.010151 0 0.048` *(official internal offset)* |
> | **Sum** | **`-0.0035 0 0.136`** = the original single-joint origin, exactly |
>
> So the head sits precisely where it did before, while the chain structure and
> the official internal offset are both adopted. If you would rather have the
> pure official absolute values, use
> `-0.0143274614150036 0 0.0973030807319928` on `pt_base_link_joint`; the
> pan-tilt will then sit ~9 mm higher relative to this asset's meshes.

---

## 2. Validation

Every requested value re-read from the written file, plus a structural check:

| Check | Result |
|---|---|
| All 9 requested values applied | ✅ 11/11 assertions pass |
| Links / joints | 11 / 10 |
| Root link | `base_footprint` (single root) |
| Reachable from root | 11/11 — fully connected, acyclic |
| Unknown link references | none |
| Links with 2+ parents | none |
| Missing mesh files | none |
| Pan pivot preserved | `-0.013651 + 0.010151 = -0.0035` ✓, `0.088 + 0.048 = 0.136` ✓ |

Each edit was applied by exact-context match and asserted to hit exactly one
site, so no unintended `<origin>`/`<limit>` blocks elsewhere in the file were
touched. File grew 3,821 → 4,343 bytes.

---

## 3. What was deliberately NOT changed

Seven audit criteria still differ from the official. These were **outside the
requested scope** and are listed so the remaining gap is explicit, not hidden:

| Criterion | This asset | Official | Notes |
|---|---|---|---|
| robot name | `ugv_beast_pt` | `ugv_beast` | cosmetic, but a lookup key for some tools |
| `base_imu_link` | missing | present | no IMU frame to mount to |
| wheel naming | `left/right_front/rear_wheel` | `left/right_up/down_wheel_link` | different names **and** a different layout (rectangle vs rocker) |
| `3d_camera_link` | missing | present | no depth-camera frame (OAK-D-Lite) |
| lidar link name | `lidar_link` | `base_lidar_link` | the *yaw* is now official; only the name differs |
| gimbal camera link | `camera_link` | `pt_camera_link` | also lacks the official optical-frame rotation `rpy="3.14 -1.5708 0"` |
| meshes | 3 unique, mm (`scale="0.001"`) | 11 unique, metres | one body mesh reused; wheels/lidar/camera have **no geometry at all** |

### Two known inconsistencies introduced or left behind

1. **`base_link` inertia is now mismatched.** The mass was updated to the
   CAD-derived `2.03227373732274` kg, but the inertia tensor remains the
   placeholder `ixx = iyy = izz = 0.01`. For physics use, apply the official
   tensor as well:
   `ixx=0.00454892624270289`, `iyy=0.00640381872536097`, `izz=0.00806050395736081`.
2. **`pt_base_link` is a frame-only link** — it has inertial but **no visual or
   collision geometry**, because this asset has no `pt_base_link.stl`. It will be
   invisible in a viewer. That is consistent with how `lidar_link` and
   `camera_link` are already bare here. To render it, copy
   `../UGVBeast_official/meshes/pt_base_link.stl` (metres, so reference it
   *without* a `scale` attribute) and add a `<visual>` block.

Also note the wheels remain **bare links with no geometry, collision, or
inertial** — so this asset still cannot be used for dynamics, regardless of the
corrected joint values.

---

## 4. Relationship to the other assets

| Asset | Role |
|---|---|
| `UGVBeast__` | original placeholder — 0/16 official criteria, left untouched |
| **`UGVBeast_update`** | **this asset** — placeholder meshes + 9/16 official kinematics |
| `UGVBeast_official` | the official Waveshare model (`ugv_beast.urdf`), 16/16 by definition |
| `UGVBeast_v2_fusion` | official kinematics + high-detail fused geometry + animated drivetrain (see its `SPECIFICATION.md`) |

Pick `UGVBeast_update` when you need the placeholder's lightweight meshes but
correct pan-tilt behaviour and ground height. Pick `UGVBeast_v2_fusion` when you
need full fidelity and moving tracks.

---

## 5. File inventory

```
UGVBeast_update/
├── UPDATE_NOTES.md   ← this document
├── URDF_AUDIT.md     inherited from UGVBeast__ (see caveat below)
├── urdf/
│   └── NEWDATAUGV_BeastUGV_.urdf   11 links, 10 joints
└── meshes/
    ├── ugv_body.stl        body shell (mm, scale="0.001")
    ├── pt_link1.stl        pan link
    ├── pt_link2.stl        tilt link
    ├── UGV_Beast_PT.stl    unreferenced by the URDF
    └── UGV_Beast_PT2.stl   unreferenced by the URDF
```

> **`URDF_AUDIT.md` in this folder is stale.** It was copied verbatim from
> `UGVBeast__` and describes the *pre-update* state, so its "Catalog" column no
> longer reflects this asset for the nine corrected rows. It is kept for the
> reasoning and measurements it contains (floor-clearance analysis, camera FOV
> derivations, frontend Target-Link explanation), all of which remain valid.
> Treat **this** document as authoritative for what the URDF currently contains.
