# twin-mcp

Tool 4 of the [tool bag](../README.md) — see
[`TWIN_PREVIEW_TOOL_PLAN.md`](../../TWIN_PREVIEW_TOOL_PLAN.md) §6 for the
full design rationale (why this is Microsoft's `@playwright/mcp` pointed at
[`twin-preview`](../twin-preview), rather than a bespoke MCP server).

**There is no runtime code in this folder.** `twin-mcp` is a *seam*: the
`window.__twinPreview` control surface already exposed by `twin-preview`
(§6.3), plus registering an existing, maintained MCP server against it. That's
it — the value is in not building anything here.

## Setup

1. `twin-preview` must be running: `pnpm --dir ../twin-preview dev` (port
   5173, per the plan's §9 port registry).
2. Merge `.mcp-snippet.json` into the Catalog repo's `.mcp.json` (same
   pattern used earlier in this session's work to register the Blender MCP
   server — reviewed by hand, not auto-merged, since `.mcp.json` may already
   have other entries).
3. Restart Claude Code (or whichever MCP client) so it picks up the new
   server — MCP servers load at startup only.

## Using it — the loop from plan §8, step by step

Once registered, an agent (me) can run the fix→render→test→feedback loop
without a human clicking through `twin-preview` each time:

```
browser_navigate("http://localhost:5173/?urdf=Unitree/D1_T/D1_T_Gripper/urdf/d1_t_gripper.urdf")
browser_evaluate("() => window.__twinPreview.getChecklistResult()")
  → { ok: true, jointCount: 8, boundJointCount: 8, results: [] }

browser_evaluate("() => window.__twinPreview.getJointState()")
  → { Joint1: 0, Joint2: 0, ..., Joint7_1: 0, Joint7_2: 0 }

browser_evaluate("() => window.__twinPreview.setJoint('Joint1', 0.5)")
browser_take_screenshot()
  → visual confirmation the arm actually moved

browser_console_messages()
  → catches a bad mesh reference or a URDF parse error as structured text
     instead of a silently blank canvas
```

That's the entire primitive: `getChecklistResult` for structural pass/fail,
`getJointState`/`setJoint` for driving and reading kinematics,
`browser_take_screenshot` for the visual check, `browser_console_messages`
for anything that threw. No custom Playwright script, no per-asset glue code
— every call is generic across any asset `twin-preview` can load.

## Why this, and not a bespoke MCP server

Covered in depth in the plan's §6.2 and §7 — short version: no existing
open-source project already combines "MCP + URDF + three.js + joint control
+ screenshot feedback," but Microsoft's own `@playwright/mcp` already
provides the exact three tools this loop needs (`browser_evaluate`,
`browser_take_screenshot`, `browser_console_messages`) against *any* local
dev server, so there's nothing project-specific worth writing from scratch.
The `--allowed-origins localhost:5173` flag in `.mcp-snippet.json` scopes it
to exactly this tool's port, per the plan's §1.3/§9 no-conflict rules.
