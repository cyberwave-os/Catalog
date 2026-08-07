# twin-preview

Tool 1 of the [tool bag](../README.md) — see
[`TWIN_PREVIEW_TOOL_PLAN.md`](../../TWIN_PREVIEW_TOOL_PLAN.md) §3 for the full
design rationale. This is the short version.

**What it does**: renders one Catalog URDF+mesh asset and lets you drive its
joints by keyboard, using the *actual* rendering (`urdf-loader`) and joint-
control code (`vendor/cyberwave-frontend/`) that `cyberwave-frontend` runs —
so "moves correctly here" means "moves correctly there." No backend, no
Docker, no asset registration.

## Run it

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
