# blender-render

Tool 2 of the [tool bag](../README.md) — see
[`TWIN_PREVIEW_TOOL_PLAN.md`](../../TWIN_PREVIEW_TOOL_PLAN.md) §4 for the
full design rationale. Two independent scripts here, for two different jobs:

## `start_blendermcp.py` — interactive, MCP-driven mesh inspection/fixing

```bash
blender --python tools/blender-render/start_blendermcp.py
```

Opens Blender with the `ahujasid/blender-mcp` addon enabled and its socket
server already listening on **port 9876** (no manual "Start Server" click
needed). Register it in `Catalog/.mcp.json` (already done in this repo) and
restart Claude Code (MCP servers load at startup only) to drive it live —
import a mesh, inspect it, fix it, re-render, all in one Claude-driven
session. This is the higher-fidelity, human-in-the-loop complement to
`twin-preview`'s motion checks (plan §4.1) — three.js confirms kinematics,
Blender confirms mesh/material quality.

## `render_asset.py` — batch, repeatable preview renders

```bash
blender --background --python tools/blender-render/render_asset.py -- \
  --meshes-dir ../../Unitree/D1_T/D1_T_Gripper/meshes \
  --preset presets/studio_three_point.json \
  --out /tmp/preview.png
```

A plain headless Blender script — **independent of the MCP server**, no
addon required, nothing to click. Imports every `.stl` in a directory (or an
explicit `--meshes` list), fits a standardized 3-point studio light rig +
3/4 camera angle (`presets/studio_three_point.json`) to the combined bounding
box, and renders one PNG. This is what makes two different assets'
preview images actually comparable — same lighting, same camera convention,
every time, rather than whatever a one-off manual Blender session happened
to look like.

Verified against the real `Unitree/D1_T/D1_T_Gripper/meshes/` — all 9 pieces
imported and rendered correctly in one pass (`Blender 5.1.2`,
`BLENDER_EEVEE`).

### Presets

`presets/studio_three_point.json` — camera (azimuth/elevation/distance as a
multiple of the scene's largest bounding-box dimension, so it fits any asset
regardless of scale) + three area lights (key/fill/rim) + render settings
(engine/resolution/samples). Add a new preset file and pass `--preset` to
use a different look; nothing in `render_asset.py` is hardcoded to this one.

### Known gaps (found rendering the Livox Mid-360 / RealSense D435i, both `.dae`)

- **No native Collada import.** `bpy.ops.wm.collada_import` doesn't exist in
  Blender 5.x (removed from core) — `import_meshes` only handles `.stl` and
  `.glb`/`.gltf`. Convert a `.dae` first with trimesh, which the repo already
  depends on via `mesh-doctor`: `trimesh.load(path).export("out.glb")`
  (loads as a `Scene`, so multi-geometry Collada files keep every sub-part).
- **Light `energy` doesn't auto-scale with asset size.** The preset's Watts
  values were tuned against D1_T's meshes (tens of cm). `distance_multiplier`
  scales light *position* with the asset's own bounding box, but Blender's
  physically-based area lights don't get dimmer on their own just because
  they're now much closer — a small asset (the D435i is ~9cm) at the same
  relative distance is many times overexposed at those energies. Scale
  `energy` down for a small asset (or up for a much larger one) rather than
  assuming `studio_three_point.json` is exposure-correct at every scale.
- **A camera angle chosen for an assembled robot may not suit a bare sensor
  mesh.** `studio_three_point.json`'s azimuth/elevation assume the
  interesting side of the asset is roughly in front at a modest elevation —
  true for an arm/base sitting on a table, not necessarily for a standalone
  sensor `.dae` in its own authored orientation (e.g. the D435i's lens face
  sits at a high elevation angle in its native frame, not azimuthally). Worth
  sweeping a few azimuth/elevation values for a new asset shape rather than
  assuming the stock preset finds the interesting face.

## Relationship to Tool 1 (`twin-preview`)

Independent — neither depends on the other running. Use `twin-preview` to
confirm a joint moves correctly per the real keyboard controller; use
`blender-render` to confirm the mesh itself looks right. A full asset review
typically wants both.
