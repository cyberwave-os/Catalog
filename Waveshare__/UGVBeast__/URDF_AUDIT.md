# UGV Beast — Catalog URDF Audit vs. Official Driver

Audit of `Waveshare__/UGVBeast__/urdf/NEWDATAUGV_BeastUGV_.urdf` against the
official Waveshare driver URDF used by `robot_state_publisher`
(`DUDULRX/ugv_ws` @ `ros2-humble-develop`,
`src/ugv_main/ugv_description/urdf/ugv_beast.urdf`).

Local reference checkout used for this audit:
`/Users/philiptambe/Documents/101/EDGEs/UGV-Beast/ws/ugv_ws/` (602 lines,
15,151 bytes — matches the described install artifact closely; confirmed
byte-identical to a second independent backup copy). No `install/` build was
present locally, but `.urdf` files are copied verbatim by colcon (no xacro
processing), so the source file is equivalent to what the robot driver loads.

---

## 1. Structural differences

| Aspect | Official (`ugv_beast.urdf`) | Catalog (`NEWDATAUGV_BeastUGV_.urdf`) |
|---|---|---|
| Robot name | `ugv_beast` | `ugv_beast_pt` |
| Root offset (`base_footprint` → `base_link`) | `z = 0.08` | `z = 0.1` |
| IMU | explicit `base_imu_link` + `imu_joint` | **missing entirely** |
| Wheels | 4 links (`left_up/down_wheel_link`, `right_up/down_wheel_link`), real mesh + collision + measured inertial, rocker-suspension layout (up/down pairs at different x/z) | 4 bare links (`left/right_front/rear_wheel`), **no geometry, no collision, no inertial**, simple rectangle layout |
| Depth camera | `3d_camera_link` — real mesh + inertial, own fixed joint | **missing entirely** — no equivalent link |
| Lidar | `base_lidar_link` — real mesh + inertial, mounted with 90° yaw (`rpy="0 0 1.5708"`) | `lidar_link` — bare link, no mesh, no rotation |
| Pan-tilt base | `pt_base_link` (mesh + inertial) between `base_link` and `pt_link1` | **missing** — `pt_link1` attaches straight to `base_link` |
| Pan joint (`pt_link1`) | axis `0 0 -1`, limits ±3.14 (±180°), mesh | axis `0 0 1` (reversed), limits ±1.57 (±90°), no mesh |
| Tilt joint (`pt_link1`→`pt_link2`) | origin rotated `rpy="1.5708 0 0"`, axis `0 0 1`, limits −0.523/+1.5708 (asymmetric) | origin `rpy="0 0 0"`, axis `0 1 0` (plain pitch), limits ±1.57 (symmetric) |
| Camera at gimbal tip | `pt_camera_link` — separate meshed link, optical-frame rotation `rpy="3.14 -1.5708 0"` | `camera_link` — bare link, no mesh, no rotation |
| Meshes | 9 dedicated STLs, one per part, `package://ugv_description/meshes/...`, authored in **meters** (no scale attr) | 3 STLs reused across all parts (`ugv_body.stl`, `pt_link1.stl`, `pt_link2.stl`), relative paths, authored in **millimeters** (`scale="0.001 0.001 0.001"`); 2 unused extra meshes present (`UGV_Beast_PT.stl`, `UGV_Beast_PT2.stl`) |
| Mass/inertia | CAD-derived per part (base ≈2.03 kg + precise wheel/sensor masses) | generic placeholders (base mass=2.5, pt links mass=0.1, **wheels have no inertial block at all**) |

**Bottom line:** the catalog file has the right high-level topology (4 wheels +
2-DOF pan-tilt + lidar/camera) but wrong joint axes/limits/origins, no lidar
or depth-camera mesh, no wheel collision geometry, and different unit
handling. It is not equivalent to the official driver's model.

---

## 2. The model floats above the ground plane

Measured bounding box of `meshes/ugv_body.stl` (binary STL, 123,246
triangles), after applying the URDF's `scale="0.001 0.001 0.001"`:

```
z_min = -0.0230 m
z_max =  0.1378 m
```

`base_footprint_joint` places `base_link`'s origin at `z = 0.1` above the
footprint. By ROS convention (`REP-120`), `base_footprint` **is** the ground
plane (`z = 0`). So the body's lowest point in world space is:

```
0.1 + (-0.023) = 0.077 m   →  ~7.7 cm gap above the floor
```

This is confirmed, not just inferred from the `0.08` vs `0.1` offset
difference — it's measured directly from the mesh geometry. It's also worse
than the offset alone suggests: `left/right_front/rear_wheel` links carry
**no visual/collision geometry**, so nothing is rendered at the wheel
positions to visually bridge the gap or fake ground contact.

**Fix options:**
- Lower `base_footprint_joint`'s `z` to roughly `0.02–0.03 m` (where this
  mesh's own bottom actually sits), or
- Add real wheel meshes sized/positioned so their bottom touches `z = 0`,
  which is what the official model does (4 separately meshed wheel links).

Using the official's `z = 0.08` alone would still leave ~5.7 cm of gap with
*this* body mesh — the offset and the mesh need to agree with each other.

---

## 3. Frontend "Target Link" dropdown — why `pt_base_link` isn't listed

The Sensor "Target Link" selector in `cyberwave-frontend` is **not**
hardcoded — it's populated dynamically at runtime:

1. `components/asset/urdf-viewer-with-controls.tsx` loads the asset's URDF
   via the `urdf-loader` npm package. After parsing, `handleRobotLoaded`
   (~lines 1243–1257) does:
   ```tsx
   const linkNames = Object.keys(robot.links);
   onLinksLoaded(linkNames);
   ```
   `robot.links` is keyed by actual `URDFLink` objects — one per `<link>`
   XML element in the parsed tree. A name that only appears as a `<joint>`'s
   `parent`/`child` attribute (with no matching `<link>` tag) never gets an
   entry here.
2. That list flows up through `asset-catalog-detail.tsx`'s `urdfLinkNames`
   state into the Target Link `<Select>` in
   `components/asset/capabilities-section.tsx` (~lines 909–939) and
   `edit-asset.tsx` (~lines 2178–2200). If the list is empty, the UI falls
   back to a free-text input rather than any static default.

Since the catalog URDF never declares `<link name="pt_base_link">` (see
§1 — the joint `pt_base_link_to_pt_link1` goes straight from `base_link` to
`pt_link1`), `urdf-loader` never instantiates that link, so it can't appear
in the dropdown. This is correct behavior reflecting a real gap in the URDF,
not a frontend bug — fixing it means adding the `pt_base_link` `<link>`
(with mesh/inertial) to the catalog URDF and re-parenting `pt_link1` to it.

---

## 4. Real camera hardware & FOV

### 4.1 Actual hardware (from the driver repo, not the URDF/SDF placeholder)

| URDF link | Real hardware | Source |
|---|---|---|
| `3d_camera_link` (base) | **Luxonis OAK‑D‑Lite** | `ugv_vision/launch/oak_d_lite.launch.py` launches `depthai_ros_driver` with `parent_frame='3d_camera_link'`; config `ugv_vision/config/oak_d_lite.yaml` |
| `pt_camera_link` (pan‑tilt head) | Generic USB camera via `usb_cam`, `/dev/video1`, 640×480, calibrated | `ugv_vision/config/params.yaml` (`frame_id: "pt_camera_link"`), calibration in `ugv_vision/config/camera_info.yaml` |

⚠️ `ugv_description/model.sdf` labels the base camera's Gazebo sim sensor
`intel_realsense_r200` with `horizontal_fov: 1.02974` rad (≈59°) — this is a
**stale template placeholder**, not the real hardware (an R200 isn't mounted
on this robot) and should not be used as a spec.

### 4.2 Real FOV values

| Camera | Source of numbers | Horizontal FOV | Vertical FOV | Diagonal FOV |
|---|---|---|---|---|
| `pt_camera_link` (usb_cam) | computed from **actual calibrated intrinsics** `fx=289.11`, `fy=289.75`, 640×480 (`camera_info.yaml`) | 95.7° | **79.2°** | ~108° |
| `3d_camera_link` — OAK‑D‑Lite RGB (IMX214) | Luxonis published datasheet | 69° | **54°** | 81° |
| `3d_camera_link` — OAK‑D‑Lite stereo/mono (OV7251) | Luxonis published datasheet | 73° | **58°** | 89.5° |

Pan-tilt camera FOV computed via the standard pinhole formula:
`FOV = 2·atan(dimension / (2·f))`, e.g.
`2·atan(640/(2·289.11)) ≈ 95.7°` (H), `2·atan(480/(2·289.75)) ≈ 79.2°` (V).

### 4.3 What to put in the frontend's "FOV (deg)" field

Traced end-to-end in `cyberwave-frontend`:

- Field: `edit-asset.tsx:2146` (existing sensor) / `:2619` (Add New Sensor),
  state key `fov_degrees`, clamped 1–179°.
- Type: `lib/types/asset.ts:167` — `fov_degrees?: number`, commented
  "camera field of view", grouped under "Camera-specific".
- **Consumption is the deciding factor** — `components/asset/sensor-fov-cones.tsx:49-51`:
  ```ts
  const fovRad = THREE.MathUtils.degToRad(fovDegrees);
  const halfHeight = length * Math.tan(fovRad / 2);
  const halfWidth = halfHeight * aspectRatio;
  ```
  This is **vertical FOV**, matching `THREE.PerspectiveCamera(fov, aspect, …)`
  convention — the horizontal cone edge is *derived* from `fov_degrees ×
  aspectRatio`, not entered directly. Backend agrees:
  `cyberwave-backend/.../sensor_geometry.py:75` aliases `fov_degrees` with
  `fovy`/`vertical_fov`, and derives horizontal via
  `2·atan(tan(vfov/2)·aspect)` at line 506-511.

**→ Enter the *vertical* FOV number:**

| Sensor | Put in "FOV (deg)" |
|---|---|
| `pt_camera_link` | **79** |
| `3d_camera_link` as `rgb` | **54** |
| `3d_camera_link` as `depth`/stereo | **58** |

**Also set resolution (width/height), not just FOV.** Both real cameras here
are 640×480 (4:3, aspect ≈1.333). The cone's `aspectRatio` defaults to 16:9
(≈1.778) if width/height are left blank — leaving FOV correct but the
horizontal cone spread visibly too wide.

**Don't use this field for `base_lidar_link`.** It's nominally
"camera-specific" (per the type comment), but the UI doesn't enforce that by
sensor type — however lidar has its own dedicated `fov_horizontal` /
`fov_vertical` sweep-angle fields elsewhere in the form (e.g. 270° default
for a 2D lidar in `sensor-parameter-forms.tsx:210-217`). Using the camera
"FOV (deg)" field on a lidar sensor would render a rectangular camera
frustum instead of a lidar sweep cone.

**Known frontend inconsistencies (not blocking, but worth knowing):**
- `lib/utils/sensor-utils.ts:53-59` (`getAssetFovSensors`) is documented as
  "Filters to only camera-type sensors" but performs no actual type check.
- `sensor-fov-cones.tsx:36-37` (`hasValidFov`) likewise has no sensor-type
  check — so any sensor with `fov_degrees` set renders a camera-style cone,
  regardless of type.

---

## 5. File map

- Official source: `/home/ws/ugv_ws/src/ugv_main/ugv_description/urdf/ugv_beast.urdf` (target machine; not present on this Mac)
- Local reference checkout used for this audit: `/Users/philiptambe/Documents/101/EDGEs/UGV-Beast/ws/ugv_ws/src/ugv_main/ugv_description/urdf/ugv_beast.urdf`
- Catalog asset audited: `Waveshare__/UGVBeast__/urdf/NEWDATAUGV_BeastUGV_.urdf`
- Catalog meshes: `Waveshare__/UGVBeast__/meshes/` (`ugv_body.stl`, `pt_link1.stl`, `pt_link2.stl`, + 2 unused: `UGV_Beast_PT.stl`, `UGV_Beast_PT2.stl`)
- Camera driver configs: `ugv_vision/config/oak_d_lite.yaml`, `ugv_vision/config/camera_info.yaml`, `ugv_vision/config/params.yaml`
- Frontend Target Link logic: `cyberwave-frontend/components/asset/urdf-viewer-with-controls.tsx`, `asset-catalog-detail.tsx`, `capabilities-section.tsx`, `edit-asset.tsx`
- Frontend FOV field/consumption: `cyberwave-frontend/components/asset/edit-asset.tsx`, `lib/types/asset.ts`, `components/asset/sensor-fov-cones.tsx`, `lib/utils/sensor-utils.ts`
- Backend FOV geometry: `cyberwave-backend/src/app/services/sensor_geometry.py`
