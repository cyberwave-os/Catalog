# twin-preview

Tool 1 of the [tool bag](../README.md) — see
[`TWIN_PREVIEW_TOOL_PLAN.md`](../../TWIN_PREVIEW_TOOL_PLAN.md) §3 for the full
design rationale. This is the short version.

**What it does**: renders one Catalog URDF+mesh asset and lets you drive its
joints by keyboard, using the *actual* rendering (`urdf-loader`) and joint-
control code (`vendor/cyberwave-frontend/`) that `cyberwave-frontend` runs —
so "moves correctly here" means "moves correctly there." No backend, no
Docker, no asset registration.

## Try it now — D1-T gripper walkthrough

```bash
pnpm --dir tools/twin-preview dev
```

Open **http://localhost:5173/** and click into the page so it has keyboard
focus — the D1-T gripper twin is already loaded, full-screen, no picker, no
panels. Hold any key below and the matching link rotates/slides live; these
are the *exact* bindings from `cyberwave-backend`'s
`controller:keyboard_autogen_d1_t_with_gripper:v1` (same `catalog_key`, same
keys — pulled via `export_controller_policy.py`, never retyped):

| Joint | Increase | Decrease |
|---|---|---|
| Joint1 | `1` | `2` |
| Joint2 | `3` | `4` |
| Joint3 | `5` | `6` |
| Joint4 | `7` | `8` |
| Joint5 | `9` | `0` |
| Joint6 | `Q` | `W` |
| Joint7_1 (gripper finger) | `E` | `R` |
| Joint7_2 (gripper finger) | `T` | `Y` |

The corner status line reads `D1_T_Gripper · ✓ 8/8 joints ok` throughout —
that's `runChecklist.ts` (§below) confirming every bound joint exists, has a
controllable type, and has sane limits, live, not just at load time.

**What this proves, and what it doesn't**: this *is* `cyberwave-frontend`'s
own joint-control code (vendored, not reimplemented — see below), so a joint
that moves correctly here will move correctly in the real frontend too.
What it does *not* do is put the twin inside the actual `cyberwave-frontend`
app — that still needs the deferred backend registration step
(`TWIN_PREVIEW_TOOL_PLAN.md` §10: a `CATALOG_ASSETS` entry,
`seed_asset_cyberwave_catalog`, and the real Docker stack), which this tool
bag deliberately holds off on until it's actually wanted.

## How it works end-to-end

```
seed_controllers.py (source of truth for bindings)
        │  export_controller_policy.py (ast, no Django)
        ▼
src/fixtures/*.controller.json  ──────────────┐
                                               │
Catalog/Unitree/D1_T/.../*.urdf + meshes/      │  loaded via public/catalog symlink
        │  urdf-loader (same version pinned    │
        │  in cyberwave-frontend's package.json)│
        ▼                                      ▼
   Viewer3D.tsx  ◀── keydown/keyup ──  vendor/cyberwave-frontend/keyboard-joint-bindings.ts
        │              (byte-for-byte copy, see MANIFEST.json)
        ▼
  robot.setJointValue(name, value)  →  visible motion + checklist result
```

Nothing in that chain is a reimplementation of frontend behavior — the only
code twin-preview itself owns is the three.js scene wiring
(`Viewer3D.tsx`/`main.tsx`) and the checklist (`checklist/runChecklist.ts`).
Everything that decides *how a keypress turns into a joint value* is the
same file that ships in `cyberwave-frontend`.

## Run it (general)

```bash
pnpm install
pnpm dev
```

Opens on **http://localhost:5173** (pinned port, see the plan's §9 registry).
The whole viewport is the twin — no picker, no side panel (plan §3.2).

- `?urdf=<path>` — path to the URDF, relative to the Catalog repo root.
  Defaults to `Unitree/D1_T/D1_T_Gripper/urdf/d1_t_gripper.urdf`.
- `?policy=<name>` — which generated controller fixture to drive it with
  (matches a file in `src/fixtures/*.controller.json`). Defaults to
  `d1_t_gripper`.

Example: `http://localhost:5173/?urdf=Unitree/D1_T/D1_T_GripFree/urdf/d1_t_gripfree.urdf&policy=d1_t_gripfree`
(once that fixture exists — see below).

## How assets are served

`public/catalog` is a symlink to the Catalog repo root (created once,
machine-local, gitignored — see setup below). URDFs and meshes are fetched
live from there at `/catalog/<path>`; nothing is copied in, so edits to a
Catalog asset show up on the next reload.

```bash
ln -s "$(git rev-parse --show-toplevel)" tools/twin-preview/public/catalog
```

## How the controller policy gets here — never hand-typed

```bash
python3 scripts/export_controller_policy.py \
  controller:keyboard_autogen_d1_t_with_gripper:v1 \
  --out src/fixtures/d1_t_gripper.controller.json
```

This parses `cyberwave-backend`'s `seed_controllers.py` as plain Python
source (via `ast`, no Django import) and extracts the one dict literal
matching that `catalog_key`, verbatim. Re-run it whenever that block changes
upstream — never edit the generated JSON by hand. Defaults to
`~/Documents/monorepos/1-first/cyberwave/cyberwave-backend/.../seed_controllers.py`;
override with `--seed-file` or `CYBERWAVE_MONOREPO` if your checkout differs.

## The `window.__twinPreview` control surface

Exposed for [`twin-mcp`](../twin-mcp) (Tool 4) to drive this tool headlessly
via Playwright's `browser_evaluate`, per plan §6.3:

```ts
window.__twinPreview.getJointState();          // { [jointName]: number }
window.__twinPreview.setJoint(name, value);    // clamped per the vendored logic
window.__twinPreview.getChecklistResult();     // { ok, jointCount, boundJointCount, results }
window.__twinPreview.loadAsset(urdfPath);      // swap the loaded asset at runtime
```

## Vendored files

`vendor/cyberwave-frontend/` — copied byte-for-byte from `cyberwave-frontend`,
pinned to a commit SHA in `vendor/cyberwave-frontend/MANIFEST.json`. Their
internal `@/...` imports are resolved via `resolve.alias` in `vite.config.ts`
(and mirrored in `tsconfig.json`'s `paths`) rather than rewritten, so a diff
against upstream stays meaningful. **Never hand-edit anything under
`vendor/`** — if something's wrong there, it's wrong upstream first; fix it
in `cyberwave-frontend`, then re-copy.

## Known gaps (fine for now, worth knowing)

- `defaultMeshLoader` (urdf-loader's own) only handles `.stl`/`.dae` out of
  the box — several other Catalog assets use `.obj`, which would need a
  custom `loader.loadMeshCb` (same pattern `cyberwave-frontend`'s
  `urdf-viewer.tsx` uses) to fully cover. Not needed for D1-T; add if/when
  this tool is pointed at an OBJ-based asset.
- The checklist result reported to `window.__twinPreview.getChecklistResult()`
  updates on load; if you want it live-recomputed after `setJoint` calls too,
  that's a small addition, not yet wired.
