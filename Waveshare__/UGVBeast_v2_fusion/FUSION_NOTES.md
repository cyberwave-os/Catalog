# UGV Beast — Fusion Notes

This asset starts from `Waveshare__/UGVBeast_v2__` (official `ugv_beast.urdf` +
official meshes) and swaps in higher-detail geometry sourced from the older
placeholder asset `Waveshare__/UGVBeast__`. The original 12 official joints are
untouched; the URDF has since been **extended** with isolated drive gears and
track belts (see "Animated drivetrain" below).

## Animated drivetrain (drive gears + scrolling tracks)

The official model animates only 4 wheel links; everything else in the track
run was static. Two additions changed that, and both are now written into
`urdf/ugv_beast.urdf` so the asset is self-contained — no side-channel data.

**21 isolated gears / rollers.** Rotationally-symmetric components were detected
geometrically rather than by hand: for each component, measure the circularity of
its cross-section in the X–Z plane (the plane a wheel sweeps when spinning about
its Y axle). A real gear shows near-complete 360° angular coverage with a tight,
consistent outer radius. Each detected gear was recentred on its own measured
axle (URDF joints rotate about the link origin, so the offset moved into the
joint) and given a `continuous` joint on `base_link`.

Because every roller engages the same track belt they share one surface speed,
so angular rate scales as `1/radius` — **not** uniformly. Each gear joint carries
its derived ratio as an XML comment:

| Component | Radius | Spin rate |
|---|---|---|
| Drive sprockets (L/R) | 28.6 mm | 0.87× |
| Rear idler | 12.3 mm | 2.02× |
| Mid rollers | 8.1 mm | 3.08× |
| Bottom-run rollers | 6.0 mm | 4.13× |
| Small idlers | 3.6 mm | 6.88× |

Left and right gears get opposed axes (`0 -1 0` / `0 1 0`) so they turn the
correct opposite directions.

> **Note:** the large front component previously treated as a static *fender*
> (`r = 28.6 mm` at `x = 84.8, z = 25.0`) is in fact a **drive sprocket** —
> concentric with the official up-wheel axle at `x = 83.2, z = 26.1`. It was
> never bodywork.

**2 UV-scrolling track belts.** Rather than animating ~100 individual track
shoes, each side gets one 520-face ribbon (`track_belt_left/right.stl`) using the
standard *UV-scrolling continuous belt* technique. The path is the convex hull of
the real track-plate footprint (562 mm perimeter, X = [-120.8, 110.7],
Z = [-23.0, 52.2]), so it follows the genuine track silhouette rather than an
invented path. UVs run `u` = 0→1 once around the loop and `v` = 0→1 across the
width, so a tread texture tiling 56× (one tile ≈ one 10 mm shoe) scrolls
seamlessly.

Belts are `fixed` joints — the *texture* moves, not the mesh. To drive them,
scroll `texture.offset.x` by `v·dt / perimeter` where `v = ω·r` is the drive
wheels' rim speed; advancing offset by 1.0 is exactly one circuit. At the
viewer's default 1.4 rad/s that's 0.0349 m/s, a full circuit every 16.1 s.
Locking to `v = ω·r` is what keeps the tread from drifting against the sprockets
it wraps.

The static track plates were deliberately **kept** rather than deleted; the belt
layers over them as the moving tread face (with `polygonOffset` to avoid
z-fighting). Removing ~100k triangles of real track structure was judged the
worse risk.

### Rig summary

| | Count |
|---|---|
| Links (all connected, single root `base_footprint`) | 36 |
| Joints | 35 |
| — `continuous` (4 official wheels + 21 gears) | 25 |
| — `revolute` (pan/tilt) | 2 |
| — `fixed` (incl. 2 belts) | 8 |

## What was swapped, and why

| Link | Swapped in | Official (v2) | Fusion | Confidence |
|---|---|---|---|---|
| `base_link` | old `ugv_body.stl` | 1,912 tri | **123,246 tri** | High — X/Y footprint matches official within ~2mm on every edge (same pivot/origin convention). Z height is 42.8mm taller in the old mesh; that's a genuine design difference, not a bug — the old body includes more raised structure. |
| `pt_link2` | old `pt_link2.stl` | 294 tri | **14,877 tri** | Good — X-axis span matches official to within 0.4mm (the critical "reach" axis for where `pt_camera_link` attaches). Y/Z differ somewhat, consistent with genuinely extra surface detail rather than a different part. |

Both source files were converted from the old asset's native millimeters to
meters (×0.001) and baked directly into new binary STLs — no `scale` attribute
was added to the URDF, so the mesh tags are untouched.

## What was deliberately NOT swapped

| Link | Reason |
|---|---|
| `pt_link1` | Old `pt_link1.stl` extends to X=+65mm vs. official's X=+18mm — a 47mm mismatch on the axis where `pt_link2` attaches. Too large a discrepancy to trust as "the same part with more detail"; swapping it risked a visually broken arm (overlap or a gap where the tilt joint meets). Left as official. |
| 4 wheels | The old asset's closest analogues (from decomposing `UGV_Beast_PT2.stl` into its 1,586 connected components) are two mirrored ~4,500-triangle components that look like a fused wheel+track assembly per side — not two independently-rigged wheels. Using them would mean giving up the 4 independent continuous joints the official rig has. Left as official; worth a separate pass if you want that track detail specifically. |
| `base_lidar_link`, `3d_camera_link`, `pt_base_link`, `pt_camera_link` | The old placeholder asset never modeled a lidar or 3D camera at all, and never had a `pt_base_link` (its `pt_link1` attached straight to `base_link` — see `URDF_AUDIT.md` in `UGVBeast__`). No equivalent detail exists to pull from. Left as official. |

## Source

- Base: `Waveshare__/UGVBeast_v2__/` (official `waveshareteam/ugv_ws`, `ugv_beast.urdf`)
- Detail source: `Waveshare__/UGVBeast__/meshes/ugv_body.stl`, `pt_link2.stl`
