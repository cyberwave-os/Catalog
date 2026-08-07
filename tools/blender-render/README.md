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

## Relationship to Tool 1 (`twin-preview`)

Independent — neither depends on the other running. Use `twin-preview` to
confirm a joint moves correctly per the real keyboard controller; use
`blender-render` to confirm the mesh itself looks right. A full asset review
typically wants both.
