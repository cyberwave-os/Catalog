# Catalog tool bag

Full design rationale: [`../TWIN_PREVIEW_TOOL_PLAN.md`](../TWIN_PREVIEW_TOOL_PLAN.md).
This README is the index; that document is the source of truth for *why*.

**Unconditional rule**: `cyberwave-frontend` is always the source of truth
for how a twin renders and moves. Every tool here exists to prove an asset
will behave correctly *there* — never to define its own, independent notion
of "correct." Once an asset passes these tools, it's ready for registration
into the real backend (plan §10, deliberately not automated by anything
here).

**Standing rule**: every new Catalog asset gets run through `twin-preview`
(and `mesh-doctor` where relevant) before it's considered done — the same
way tests gate a code change. Not a one-time exercise for the D1-T asset.

## The four tools

| Tool | Job | Port | Depends on |
|---|---|---|---|
| [`twin-preview`](twin-preview) | Render + keyboard-move a URDF+mesh asset, using the actual `cyberwave-frontend` joint-control code | 5173 | nothing |
| [`mesh-doctor`](mesh-doctor) | Fix/validate mesh + URDF files (origin, scale, normals, structural checks) — cheap, before you even open a viewer | none | nothing |
| [`blender-render`](blender-render) | High-fidelity, comparable-across-assets render; interactive mesh inspection via Blender MCP | 9876 (MCP addon socket) | nothing |
| [`twin-mcp`](twin-mcp) | Lets an agent drive `twin-preview` headlessly — the loop closer | none of its own | `twin-preview` running |

None of these overlap the real Cyberwave stack's ports
(3000/8000/5432/6379/1883/9001 — plan §1.3) or join its Docker network.

## The loop (plan §8)

```
mesh-doctor → twin-preview → (twin-mcp drives it headlessly, or a human drives it by hand)
     ▲              │
     └────  fix  ◀───┘ analyze: clean? → blender-render (sign-off) → plan §10 (deferred registration)
                                         not clean? → back to mesh-doctor with a specific fix
```

Nothing in `mesh-doctor`/`blender-render`'s internal process needs to be
Cyberwave-shaped — only the URDF + relative-path meshes that come out the
other end does, because that's the only format `cyberwave-frontend`'s
`urdf-loader` actually reads.

## Verified so far

Built and tested against the real `Unitree/D1_T/D1_T_Gripper` asset while
building this tool bag:

- `twin-preview`: loads the real URDF, checklist reports `8/8 joints ok`,
  keyboard-driving `Joint1` and the gripper fingers (`Joint7_1`/`Joint7_2`)
  moves them correctly, including clamping `Joint7_1` at its real `0.03`
  upper limit — using the actual vendored `cyberwave-frontend` logic, not a
  reimplementation.
- `mesh-doctor`: `urdf_doctor` reports the URDF structurally clean; `mesh_fixes`
  confirms `base_link.STL`'s real-world extents (`0.118 × 0.108 × 0.058 m`,
  watertight) and correctly does *not* flag it as still-in-millimetres.
- `blender-render`: `render_asset.py` imported all 9 D1_T_Gripper meshes and
  rendered a clean studio-lit preview in one headless pass.
- `twin-mcp`: configuration only (Playwright's official MCP server,
  registered in `Catalog/.mcp.json`) — needs a session restart to become
  callable; not yet exercised end-to-end as an agent-driven loop.

## Adding a new tool to the bag (plan §2)

1. Self-contained folder under `tools/`, its own deps, its own README.
2. If its job is to predict Cyberwave's behavior, reuse the actual
   Cyberwave code/tech (vendor it, don't reimplement). If its job is
   inspection/authoring/repair, use whatever's best — just hand off plain
   URDF + relative-path meshes at the end.
3. Pick a port that's not in the Cyberwave table above *or* in the table
   above — update it here before you pick one.
4. Never let a tool's result be the final word — it's a prediction of what
   the real frontend will do.
