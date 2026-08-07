# Plan: Twin Validation Tool Bag

Status: **planning document only** — nothing in this file has been executed yet.
Scope: build a self-contained **tool bag** inside this repo for validating and
fixing Catalog twins (URDF + meshes) — render them, move their joints, and
catch formatting problems — using the *same* rendering/joint-control tech
`cyberwave-frontend` uses, and Blender for visual/mesh-level inspection. No
backend registration, no Docker, no Postgres. That step is real but explicitly
deferred — see §10.

Repos referenced:
- `Catalog` — this repo (asset source of truth for URDFs + meshes)
- `cyberwave` — `github.com/cyberwave-os/cyberwave` (production/dev branch), the
  monorepo checked out locally at `~/Documents/monorepos/1-first/cyberwave/`,
  containing `cyberwave-frontend/`, `cyberwave-backend/`, `cyberwave-robot-format/`
  as plain subfolders of one git repo (**not** git submodules)

**Standing rule, unconditional:** `cyberwave-frontend` is always the source of
truth for how a twin renders and moves. Every tool in this bag exists to prove
an asset will behave correctly *there* — never to define its own,
independent notion of "correct."

---

## 1. What the investigation found

### 1.1 Frontend joint control (`cyberwave-frontend`)

- URDF parsing/rendering goes through the **`urdf-loader`** npm package
  (`urdf-loader: ^0.12.5`), wrapped by `components/asset/urdf-viewer.tsx` and
  friends (`urdf-viewer-with-controls.tsx`, `URDFAsset.tsx`,
  `combined-twin-preview.tsx`). No custom URDF parser exists on the frontend.
- Joint names are matched **exactly, case-sensitively** against the URDF's
  `<joint name="...">` attribute — `urdf-loader` keys `scene.joints` by that
  literal string (`node_modules/urdf-loader/src/URDFLoader.js:255-258`).
- **Prismatic joints are natively supported**, same as revolute/continuous
  (`URDFClasses.js:207-265`, `setJointValue` switches on `jointType`).
- The keyboard-teleop runtime lives in
  `components/environment/keyboard-teleoperation-controller.tsx`, delegating
  per-tick math to `lib/utils/keyboard-joint-bindings.ts`
  (`applyKeyboardJointBindingDelta`, `getJointStepSize`, `clampJointValue`).
- **Step size is fixed, not derived from the URDF**:
  `getJointStepSize` → `0.05 rad` for revolute/continuous, `0.01 m` for
  prismatic, per tick, regardless of `<limit velocity="...">` or `effort`.
  `velocity`/`effort` are read only for *validating a typed pose value*
  (`lib/workflows/send-pose-config.ts`) — never for scaling teleop speed.
  **A joint with `velocity="0" effort="0"` still moves fine under keyboard
  control.** This directly de-risks a concern raised earlier in this task.
- `lower`/`upper` limits **are** respected for clamping
  (`lib/utils/motion.ts:physicalPositionRange`); `continuous` joints are
  unbounded and wrap at ±π instead.
- A joint is only offered as a controllable target if its URDF `type` is
  `revolute | prismatic | continuous` (never `fixed`), and it is not a mimic
  slave — checked in three duplicated places
  (`lib/utils/joint-name-mapping.ts`, `lib/utils/schema-mimic-joints.ts`,
  `keyboard-binding-editor.tsx`).
- **Native `<mimic>` tags are understood automatically** by `urdf-loader`
  whenever `robot.setJointValue()` is called — no controller metadata needed.
  The separate `mimicJoints` field on a `keyboard_bindings` entry is a *second,
  independent* mechanism used only by the teleop command/value accumulator
  that publishes over MQTT (for assets whose coupling is schema-declared, not
  URDF-declared — e.g. Kinova + Robotiq). **Our D1-T gripper needs neither**:
  `Joint7_1`/`Joint7_2` are bound to separate keys (E/R, T/Y) as two
  independently-controlled fingers, matching the existing keyboard config
  exactly — no `<mimic>` tag or `mimicJoints` entry required.

**Conclusion: our existing `d1_t_gripper.urdf` / `d1_t_gripfree.urdf` already
satisfy every frontend requirement as-is.** Joint names, types
(`revolute`/`prismatic`), and non-degenerate `lower`/`upper` limits all match
what the keyboard controller needs. No URDF edits are required for frontend
compatibility — this is exactly what the tool bag should let us *prove*,
not just claim.

### 1.2 Backend ingestion — reference only, not something we act on now

`cyberwave-backend` resolves a controller's `asset_registry_ids` against a
free-text `Asset.registry_id` field, populated by an explicit
`CATALOG_ASSETS` entry (`seed_asset_cyberwave_catalog.py`) that maps a
registry id to a `Catalog` subfolder + URDF path, fetched via a zip/clone of
this repo. Actual URDF parsing/validation there runs through
`cyberwave_robot_format.urdf.parser.URDFParser` — a standalone, Django-free
package — which we confirmed has no rejection path our URDFs would hit
(joint types, limits-of-zero, mimic detection all tolerate our files as-is).

**This confirms there's nothing backend-shaped blocking us** — but per your
call, registering the asset, seeding, and running the real Docker stack is
explicitly **out of scope for this tool bag** and deferred (§10). The tool bag
validates the twin against the *frontend's* rendering/motion code and, where
useful, against `cyberwave_robot_format`'s parser directly (it's a pure
Python library — no Django needed to run it standalone, see §3.5) — without
ever touching a database or a container.

### 1.3 Port / process inventory (so nothing in the bag can collide)

From `cyberwave/CLAUDE.md`'s services table and the repo's own
`docker-compose*.yml` files:

| Service | Port(s) | Source |
|---|---|---|
| Django API | 8000 | `cyberwave-backend`, `local.yml` |
| Postgres | 5432 | `cyberwave-backend`, `local.yml` |
| Redis | 6379 | `cyberwave-backend`, `local.yml` |
| MQTT | 1883 | `cyberwave-backend`, `local.yml` |
| MQTT WebSocket | 9001 | `cyberwave-backend`, `local.yml` |
| Frontend (Next.js) | 3000 | `cyberwave-frontend`, `docker-compose.dev.yml` + host `pnpm dev` |

Container names in use: `cyberwave_dev_frontend`, `cyberwave_local_django`
(and siblings), all attached to an external Docker network `cyberwave_net`.

**Everything in the tool bag must avoid 3000/8000/5432/6379/1883/9001 and must
not join `cyberwave_net` or reuse a `cyberwave_*` container/image name.** See
§9 for the bag's own port registry (kept separately so tools inside the bag
don't collide with *each other* either, as the bag grows).

---

## 2. The tool bag — concept

```
Catalog/
  tools/
    README.md              # index: what's in the bag, status, ports, how to add a tool
    twin-preview/           # Tool 1 — three.js, render + move joints, validate
    blender-render/         # Tool 2 — Blender MCP, mesh/material inspection + high-fidelity render
    mesh-doctor/             # Tool 3 — trimesh/PyMeshLab/yourdfpy, automated mesh+URDF repair
    twin-mcp/                # Tool 4 — Playwright MCP wired to twin-preview, closes the loop
    <future-tool>/           # anything added later follows the same shape
```

Ground rules for anything living under `tools/`, now and in future:

1. **Self-contained folder per tool** — its own deps, its own README, no
   shared global config that couples tools together.
2. **Reuse real Cyberwave code/tech where the tool's job is to predict
   Cyberwave's behavior** (twin-preview vendors the actual frontend joint
   logic — §3). Tools whose job is inspection/authoring/repair rather than
   behavior prediction (Blender, mesh-doctor) don't need this constraint —
   they can use whatever's best-in-class for their own narrow job — but must
   still hand off a plain URDF + STL/OBJ/DAE with relative mesh paths at the
   end, since that's the only format Cyberwave's frontend actually reads.
   **An intermediate tool's internal representation never has to be
   Cyberwave-compatible; the asset that comes out the other end of the bag
   always does.**
3. **No port/container collision** — with the real Cyberwave stack (§1.3)
   *or* with any other tool already in the bag. `tools/README.md` keeps the
   running port registry (§9) as the bag grows.
4. **cyberwave-frontend remains the source of truth.** No tool result is a
   pass/fail verdict on its own — it's a prediction of what the real frontend
   will do. If a tool and the real frontend ever disagree, the frontend wins
   and the tool has a bug.
5. **Minimal.** A tool earns its place by answering one concrete question
   ("does this render", "do these joints move", "is this mesh clean") — not
   by growing into a second product.
6. **Standing rule, not a one-off**: once `twin-preview` exists, every new
   Catalog asset (URDF + meshes) gets run through it — and through
   `mesh-doctor`'s checks where relevant — *before* it's considered done, the
   same way tests gate a code change. This plan document is not a one-time
   exercise for the D1-T asset; it's the process for every asset after it too.

These six rules are what make the tool bag a genuine feedback loop rather
than a pile of scripts: Tool 3 fixes, Tool 1 renders+moves+checks, Tool 4
closes the loop by letting an agent drive Tool 1 and read back the result
without a human clicking through it each time, and Tool 2 gives the final
human-reviewable image. §8 connects all four into one explicit loop.

---

## 3. Tool 1 — `twin-preview` (three.js, render + move + validate)

### 3.1 What it answers

"If I open this asset in `cyberwave-frontend` and drive it with its keyboard
controller, will it render correctly and will every bound joint move?" —
answered *without* Docker, Postgres, or asset registration, by running the
same rendering (`urdf-loader`) and joint-control code
(`keyboard-joint-bindings.ts` et al.) the real frontend runs, against the
Catalog file directly.

### 3.2 Scope check against the real page — what to leave out

The real URL for this (`/{workspace}/envs/{envSlug}`) is
`app/(app)/[vendor]/envs/[envSlug]/page.tsx` in `cyberwave-frontend`, which
resolves the slug against the backend and renders
`app/(app)/environments/[environmentUuid]/environment-page.tsx` — a genuinely
heavy page: `EnvironmentHeader`, `OrganizationCreditBanner`,
`SplatUploadDialog`, `CreateMeshModal`, `HardwareSetupDialog`, product tour
hooks, edge-core/telemetry status, chat, environment-mode state, a
leave-with-running-simulation confirmation dialog, and more (554 lines before
even reaching the viewer). Exactly one part of that page is what we need:
`EnvironmentViewer3D` (`components/environment/environment-viewer-3d.tsx`)
plus the keyboard-teleop runtime it hosts.

**As a user opening this tool, you should see only that core: the twin,
rendered, movable by keyboard — nothing else.** Concretely, that means:

- No login, no organization/workspace concept, no environment CRUD, no chat,
  no credit banner, no product tours, no splat/mesh authoring dialogs.
- No asset-picker "product" chrome, either — this isn't a second catalog
  browser. One asset in, via a trivial path/URL param.
- No standing checklist *panel*. Validation checks (§3.7) still run and still
  matter, but they surface as an unobtrusive pass/fail line or a browser
  console log, not a docked sidebar competing for attention with the 3D view.

The 3D viewport should be effectively the whole screen, the way the real
page's viewer is the whole point of visiting it — just without the 554 lines
of surrounding product around it.

### 3.3 Proposed location & stack

```
Catalog/
  tools/
    twin-preview/
      package.json            # standalone, pnpm, NOT part of any workspace
      vite.config.ts          # dev server on port 5173 (confirmed clear, §1.3)
      index.html
      src/
        main.tsx               # reads one asset path (URL param or hardcoded
                                 # default), no picker UI
        Viewer3D.tsx            # thin wrapper: three.js + urdf-loader, pinned
                                 # to the exact version in cyberwave-frontend's
                                 # package.json — fills the viewport, full-bleed
        StatusLine.tsx           # one line, corner-anchored: asset name +
                                 # ✓/✗ from the checklist — not a panel
        checklist/
          runChecklist.ts        # joint-name / joint-type / limit / mimic
                                 # checks, codifying §1.1's rules directly
      vendor/
        cyberwave-frontend/
          MANIFEST.json          # {repo, ref, files:[...]}  — see §3.6
          keyboard-joint-bindings.ts   # vendored, unmodified
          motion.ts                    # vendored, unmodified
          joint-name-mapping.ts        # vendored, unmodified
          schema-mimic-joints.ts       # vendored, unmodified
          urdf.ts                      # vendored, unmodified (types only)
      scripts/
        sync_vendor.sh          # re-pulls the files in MANIFEST.json from the
                                 # pinned ref, diffs before overwrite (§3.6)
        export_controller_policy.py  # extracts one catalog_key's dict literal
                                 # out of seed_controllers.py via `ast`, without
                                 # importing Django — see §3.5
        validate_urdf.py         # optional strict pass via the real
                                 # cyberwave_robot_format parser — see §3.5
      README.md
```

Why Vite + vanilla React (not Next.js): the tool has no server-side routes,
no auth, no API — Next.js's app-router/server-component machinery would add
build complexity for zero benefit, and would invite exactly the kind of
page/route sprawl §3.2 is trying to avoid. Vite gives a sub-second dev server
on a free port with no Docker involvement at all.

### 3.4 What "move it" means without a backend

The real frontend gets a twin's controllable-joint list from
`/api/v1/twins/{uuid}/joints`, which is server-derived. Without a backend,
`twin-preview` derives the equivalent list **client-side**, directly from the
same `urdf-loader` parse the viewer already did (`robot.joints`), shaped to
match `URDFParser.get_joints()`'s `{name, type, limits}` output (§1.2) so the
checklist is testing the same shape the backend would eventually see.

### 3.5 Where the tool's inputs come from — no hand-duplication

Two things must never be hand-copied, because hand-copying is exactly how the
current `unitree/d1-t-with-gripper` controller block went stale (§1.2):

- **Joint list**: as above (§3.4). As an optional stricter pass,
  `scripts/validate_urdf.py` can `pip install cyberwave-robot-format` (it's
  dependency-free of Django — confirmed via its `pyproject.toml`) and run the
  **actual** `URDFParser` from `cyberwave_robot_format.urdf.parser` against
  the file, surfacing any `ParseError`/`add_error` the real backend would
  also hit, entirely locally.
- **Keyboard bindings**: extracted from the real `seed_controllers.py` dict
  via `export_controller_policy.py` (`ast.literal_eval` on the specific dict
  literal keyed by `catalog_key`, no Django import needed) → dumped as JSON →
  consumed directly by `Viewer3D.tsx` (to drive the twin) and
  `checklist/runChecklist.ts` (to validate it) — never re-typed by hand. This
  guarantees the tool is always testing the *exact* bindings that will
  eventually be seeded, not a copy that can drift.

### 3.6 Staying aligned with upstream `cyberwave-frontend`

The umbrella `cyberwave` repo is one git repo (not submodules), so there's no
clean `git submodule` pointer at a subfolder. Proposed approach instead:

1. `vendor/cyberwave-frontend/MANIFEST.json` pins an exact upstream **commit
   SHA** (of `cyberwave-os/cyberwave`) plus the list of vendored file paths.
2. `scripts/sync_vendor.sh <new-ref>` does a shallow, sparse fetch of just
   those paths at `<new-ref>` (`git archive` over the network, or a
   `sparse-checkout` clone into a scratch dir) and diffs against the current
   vendored copies **before** overwriting — printing the diff for manual
   review rather than silently applying it, since our checklist code may
   depend on these files' exact exported function signatures.
3. The tool's `README.md` states plainly: *these files are vendored, read-only
   copies; cyberwave-frontend is the source of truth; a bug found here must be
   fixed upstream first, then re-synced here — never patched only in
   `vendor/`.*
4. Optional (flag for later, not building now): a scheduled check (cron/CI) in
   this repo that runs `sync_vendor.sh --check` against the latest
   `cyberwave-os/cyberwave` `production` branch and opens an issue if the
   vendored files have diverged, so drift is visible instead of silent.

### 3.7 What the checklist actually validates

- Every mesh referenced by the URDF resolves relative to the URDF's own path
  (the exact check already run by hand with Playwright earlier in this task).
- Every joint referenced in the controller's `keyboard_bindings[].jointName`
  (and `mimicJoints[].jointName`) exists in the URDF, with matching case.
- Every such joint's `type` is `revolute | prismatic | continuous` (flags it
  loudly if someone binds a `fixed` joint).
- `lower != upper` for every non-continuous bound joint.
- No bound joint is simultaneously a native URDF `<mimic>` slave.
- Interactive keyboard-drive using the *actual* `keyboard-joint-bindings.ts`
  step/clamp logic (vendored, §3.6), rendered through the *actual*
  `urdf-loader` version — "moves correctly here" and "moves correctly in
  cyberwave-frontend" are the same code path.

### 3.8 Human-in-the-loop usage

`pnpm --dir tools/twin-preview dev -- --asset Unitree/D1_T/D1_T_Gripper` →
open `localhost:5173` → the twin fills the screen, already loaded, already
keyboard-driven per §3.7's bindings → a single unobtrusive corner line reads
`D1_T_Gripper · ✓ 9/9 joints ok` (or flags exactly what's wrong) → done. No
navigation, no picker, no dashboard — the same one-page-one-purpose feel as
opening `/{workspace}/envs/{envSlug}` for a single twin, minus everything
that page carries for product reasons we don't need here (§3.2). Also
reusable headlessly (Playwright, same technique already used earlier in this
session for the three.js `viewer.html`) for an automated check later, without
building that now.

---

## 4. Tool 2 — `blender-render` (Blender MCP, mesh/material inspection)

### 4.1 What it answers, and how it differs from Tool 1

`twin-preview` proves *motion* (does the right joint move the right amount in
the frontend's own code). It intentionally does **not** do high-fidelity
rendering, mesh cleanup, or material/texture inspection — three.js in a
browser is for confirming kinematics, not for spotting a flipped normal or an
oddly-scaled STL. **Blender is a second, complementary lens**: better
rendering, real mesh-editing tools if a fix is needed (rescale, re-export,
fix normals, decimate), and a human-reviewable image as the actual
"preview" artifact — which is exactly what the D1-T Blender MCP setup earlier
in this session was already building toward. This tool formalizes that,
rather than treating it as superseded.

### 4.2 What already exists (from earlier in this session)

- The `ahujasid/blender-mcp` addon (`addon.py`, v1.2) is installed in
  Blender's local addon folder and starts a socket server on **port 9876**
  (confirmed clear of the Cyberwave port table, §1.3) via
  `bpy.ops.blendermcp.start_server()`.
- `Catalog/.mcp.json` registers the `blender` MCP server
  (`command: uvx`, `args: ["blender-mcp"]`) for this Claude Code project.
- A startup script (currently only in the session scratchpad) launches
  Blender non-headless with `--python <script>` to auto-enable the addon and
  call `start_server()`, so no manual UI clicking is needed.

### 4.3 Proposed location & stack

```
Catalog/
  tools/
    blender-render/
      README.md                 # prerequisites + step-by-step usage
      start_blendermcp.py        # moved in from the session scratchpad;
                                  # enables the addon + starts the port-9876
                                  # server on Blender launch
      render_asset.py            # optional helper: standardized camera/
                                  # lighting/turntable setup for consistent,
                                  # comparable preview renders across assets
      presets/
        studio_three_point.json   # camera/light presets so every asset's
                                  # preview render is visually comparable
```

### 4.4 Workflow

1. `blender --python tools/blender-render/start_blendermcp.py` — opens
   Blender with the MCP server already listening on 9876 (no manual "Start
   Server" click needed).
2. Restart/reload the Claude Code session so it picks up `Catalog/.mcp.json`
   (MCP servers load at startup — this is a one-time step per session, not
   per asset).
3. Drive the Blender MCP tools (import mesh/URDF-derived geometry, position
   camera per `presets/`, render) — same pattern already exercised for D1-T
   earlier in this session, just formalized into a repeatable script instead
   of an ad hoc scratchpad one.
4. The rendered image is the human-in-the-loop artifact — same role the
   three.js screenshots played earlier, but higher fidelity and with real
   mesh-editing available in the same session if something needs fixing.

### 4.5 Relationship to Tool 1

Both tools operate on the same Catalog asset folders. Neither depends on the
other running. A typical asset review would use `twin-preview` to confirm
motion/kinematics and `blender-render` to confirm visual/mesh quality — a
human (or me) can run either independently depending on what's being
checked.

---

## 5. Tool 3 — `mesh-doctor` (automated mesh + URDF repair)

### 5.1 What it answers

"This asset's mesh origin is nowhere near its geometry, or it's in
millimetres, or a face is inverted, or the URDF references a mesh that
doesn't exist — can these be fixed automatically, before anyone even opens a
viewer?" Grounded in dedicated research (§7) into `trimesh`, `PyMeshLab`,
and `yourdfpy` — no single existing tool does all of this, so this is a thin,
purpose-built script collection, not a vendored product.

### 5.2 Proposed location & stack

```
Catalog/
  tools/
    mesh-doctor/
      pyproject.toml          # trimesh[easy] (pulls in scipy for convex_hull),
                                # pymeshlab, yourdfpy
      mesh_doctor/
        mesh_fixes.py          # trimesh-based: recenter (apply_translation
                                 # against bounding_box.centroid), rescale
                                 # (apply_scale), fix_normals, convex_hull
                                 # for a simplified <collision> mesh
        mesh_repair_heavy.py    # PyMeshLab fallback for what trimesh can't
                                 # do: meshing_repair_non_manifold_edges,
                                 # meshing_close_holes,
                                 # meshing_decimation_quadric_edge_collapse
        urdf_doctor.py          # yourdfpy-based structural checks: every
                                 # joint's parent/child link exists, every
                                 # mesh file resolves (yourdfpy's own
                                 # validate_filenames()), inertia tensor is
                                 # positive-definite + satisfies the triangle
                                 # inequalities (hand-written — no existing
                                 # tool checks this, only computes it)
      README.md                 # what each check/fix does and why it's safe
                                 # to run automatically vs. needs a human call
```

### 5.3 What runs automatically vs. what needs a human decision

Two different classes of operation, and the tool should never blur them:

- **Safe to auto-apply**: recentering geometry, mm→m rescale (once confirmed,
  §1.1 already tells us the frontend doesn't care about units beyond
  render/motion — but a wildly-scaled mesh still looks wrong), normal/winding
  fixes, generating a convex-hull collision mesh, removing duplicate
  vertices/faces. These are corrections to unambiguous defects.
- **Needs a human call, not an auto-fix**: anything where "correct" depends
  on the real asset's design intent — e.g. is a visible gap between two links
  (like the D1-T gripper's wrist-to-finger gap found in the earlier three.js
  preview) a mesh bug or the actual hardware's mounting geometry? `mesh-doctor`
  flags these, it doesn't guess at them. This is exactly the class of
  question the render/screenshot step (Tool 1, and Tool 4's loop) surfaces
  for a human or for me to look at, not something a script should silently
  "fix."

### 5.4 Relationship to the rest of the bag

`mesh-doctor` runs *before* `twin-preview` in the loop (§8) — cheap,
Docker-free, browser-free static checks and fixes on the files themselves.
It never needs cyberwave-frontend running to do its job, but its output
(still plain URDF + STL/OBJ/DAE) is exactly what `twin-preview` then renders.

---

## 6. Tool 4 — `twin-mcp` (Playwright MCP, closes the loop)

### 6.1 What it answers

"Can an agent (me) drive `twin-preview`, command joints, see the result, and
decide pass/fail — without a human clicking through every check?" This is
the piece that turns "fix → render → test → feedback → analyze → fix again"
from a manual loop into one I can actually run.

### 6.2 Why this doesn't need a bespoke MCP server

Dedicated research (§7) into existing MCP-based robot/twin control (chem-0,
ros-mcp-server, realvirtual.mcp) found no ready-made "URDF-in-three.js twin"
MCP server to adopt — but it also found something better than building one
from scratch: **Microsoft's own `playwright-mcp`** (real, Apache-2.0, 35.9k★,
actively maintained) already exposes exactly the primitives needed as MCP
tools, generic enough to point at any local dev server:

- `browser_evaluate` — run arbitrary JS in the page and get the return value.
  Since `twin-preview`'s joint state lives inside a WebGL canvas (invisible
  to `playwright-mcp`'s accessibility-tree tools like `browser_snapshot`),
  this is the one that matters: it calls into a tiny control API
  `twin-preview` exposes on `window` (see §6.3) to read/set joint values and
  pull the checklist result as plain JSON.
- `browser_take_screenshot` — the visual check, same role the Playwright
  screenshots played by hand earlier in this session, now available as an
  MCP tool with no custom script per asset.
- `browser_console_messages` — catches render/JS exceptions (a bad mesh
  reference, a malformed URDF) as structured feedback instead of a silent
  blank canvas.

This is precisely the `chem-0` pattern (image-tool + structured-state-tool +
validated-command-tool) — just assembled from an existing, maintained,
general-purpose MCP server instead of one built bespoke per project.

### 6.3 What `twin-preview` needs to expose for this to work

A small, deliberate control surface on `window`, e.g.:

```ts
window.__twinPreview = {
  loadAsset(path: string): Promise<void>;
  getJointState(): Record<string, number>;          // name -> current value
  setJoint(name: string, value: number): void;       // clamped per §1.1's rules
  getChecklistResult(): ChecklistResult;              // §3.7's checks, as JSON
};
```

This is the only new surface `twin-preview` needs beyond §3 — everything else
(rendering, keyboard control, the checklist) already exists per that section.
`browser_evaluate` calls straight into this object; no Playwright scripting,
no per-asset glue code.

### 6.4 Proposed location & stack

```
Catalog/
  tools/
    twin-mcp/
      README.md               # how to register @playwright/mcp for this
                                # repo, pointed at twin-preview's dev server
      .mcp-snippet.json         # the exact mcpServers entry to merge into
                                # Catalog/.mcp.json (mirrors how the blender
                                # server was registered earlier in this
                                # session) — not auto-merged, reviewed by hand
```

No new runtime code here beyond the `window.__twinPreview` surface in Tool 1
— `twin-mcp` is mostly *configuration*: registering the existing
`@playwright/mcp` server against `twin-preview`'s dev server (§9's port),
plus the README documenting the specific `browser_evaluate` call shapes an
agent should use against §6.3's API.

### 6.5 Relationship to the rest of the bag

`twin-mcp` is the only tool in the bag that *drives* another tool rather than
standing alone — it has no meaning without `twin-preview` already running.
It's what makes §8's loop actually runnable by an agent instead of only by a
human following §3.8's manual steps.

---

## 7. Prior art surveyed (grounding for §5–§6)

Deep-research pass across three clusters, each independently verified (repo
existence, activity, real feature set — not assumed from memory):

**Browser-based URDF editors/viewers** — `gkjohnson/urdf-loaders` (the
library `cyberwave-frontend` itself depends on, 809★, pushed within days) is
the most directly relevant: it ships its own minimal drag-and-drop
viewer/example, confirming Tool 1's "build directly on the same loader"
approach rather than going through a third party.
`UNLINEARITY/URDF-Visualizer` (22★, MIT, solo-maintained but very active,
pure client-side, URDF/Xacro-native) is a good source of specific UI
patterns (measurement tool, kinematic-tree panel, "sweep all joints" demo)
worth mining later if `twin-preview` needs richer inspection UI.
`OpenLegged/URDF-Studio` (450★, Apache-2.0, real team, React Three Fiber,
built-in "AI Assistant" concept) is the most architecturally sophisticated,
but is built around its own `.usp` project format — URDF is a first-class
*export*, not the native working format, so adopting it would mean an
explicit "export to URDF" step, not a base to build directly on. BrowserBotics
could not be verified (no GitHub presence, fully client-rendered site) —
treated as unusable/unverified, not cited as fact anywhere else in this plan.

**Agentic browser/MCP control** — `browser-use` (108k★, Playwright-based,
provider-agnostic) is excellent for driving ordinary HTML UI via DOM-element
indexing, but that advantage disappears for content rendered inside a WebGL
`<canvas>` — ruled out as the loop driver for exactly that reason.
`microsoft/playwright-mcp` (35.9k★, official, actively maintained) is the
adopted primitive (§6.2) — `browser_evaluate` sidesteps the canvas problem
entirely by calling app-level JS instead of trying to address canvas content
through the accessibility tree. `JacobFV/chem-0` was checked directly against
its own source: it's real but narrower than commonly described (LeRobot
SO-101 hardware target, OpenAI-specific autonomous loop, hand-rolled URDF
parser with no `urdf-loader`/MCP-screenshot wiring at all for its own 3D
view) — not reusable code, but its MCP tool *shape* (a camera/image tool, a
structured-pose tool, a validated-command tool) is the pattern §6.2 imitates.
No existing project combines "MCP + URDF + three.js + joint control +
screenshot feedback" end-to-end — confirming this is worth building (§6)
rather than adopting.

**Mesh/URDF repair** — `trimesh` (v5.0.0, actively released, MIT) covers
recenter/rescale/hull/normal-fix cleanly; `PyMeshLab` (v2025.7, ~4.5M
downloads, confirmed headless-clean on macOS) adds non-manifold repair,
hole-filling, and quality-aware decimation trimesh lacks; `yourdfpy` (293★,
MIT, numpy-native origins, built-in `validate_filenames()`) is the
best-maintained URDF read/rewrite layer, ahead of the largely-dormant
`urdf_parser_py`. No unified "URDF doctor" tool exists anywhere (`check_urdf`
from ROS's `urdfdom` only validates XML/schema structure, not mesh existence
or inertia plausibility) — confirmed as a genuine gap that `mesh-doctor`'s
`urdf_doctor.py` fills rather than duplicates.

---

## 8. The full feedback loop — fix → render → test → feedback → analyze → repeat

This is the direct answer to "connect all the pieces": how Tools 1–4 compose
into one loop, and — per the standing rule (§2.2) — why an intermediate
stage's format never has to match Cyberwave's, only the final output does.

```
 ┌─────────────┐   ┌──────────────┐   ┌───────────────┐   ┌─────────────┐
 │  Intake:     │   │ mesh-doctor  │   │ twin-preview   │   │ twin-mcp    │
 │  new/edited  │──▶│ (Tool 3)     │──▶│ (Tool 1)       │◀─▶│ (Tool 4)    │
 │  URDF+meshes │   │ auto-fix +   │   │ render, move,  │   │ drives Tool │
 │  in Catalog  │   │ doctor pass  │   │ checklist      │   │ 1 headlessly│
 └─────────────┘   └──────────────┘   └───────┬────────┘   └──────┬──────┘
                            ▲                  │                   │
                            │           ✓ pass │ ✗ fail            │ screenshot +
                            │                  ▼                   │ console +
                            │           ┌────────────┐             │ joint state
                            └───────────┤  analyze:  │◀────────────┘
                                         │  human or  │
                                         │  me reads  │
                                         │  the result│
                                         └─────┬──────┘
                                               │ specific fix instruction
                                               ▼
                                     back to mesh-doctor or a
                                     direct URDF/mesh edit,
                                     loop until clean
                                               │
                                               ▼
                                     ┌───────────────────┐
                                     │ blender-render     │
                                     │ (Tool 2) — final   │
                                     │ human-reviewable   │
                                     │ sign-off image     │
                                     └─────────┬──────────┘
                                               ▼
                                    §10 (deferred): register
                                    with the real backend,
                                    verify in real cyberwave-
                                    frontend — the only
                                    definition of "done"
```

Concretely, per iteration:

1. **Fix** — `mesh-doctor` (Tool 3) auto-applies the unambiguous corrections
   (§5.3) and flags anything ambiguous rather than guessing.
2. **Represent** — `twin-preview` (Tool 1) loads the current state of the
   asset through the *actual* `urdf-loader` + vendored frontend joint logic.
3. **Test / move** — either a human drives it by keyboard (§3.8), or
   `twin-mcp` (Tool 4) drives it via `browser_evaluate` calls into
   `window.__twinPreview` (§6.3), exercising every bound joint.
4. **Feedback** — a screenshot (`browser_take_screenshot`), the checklist
   result (`getChecklistResult()`), and any console errors
   (`browser_console_messages`) come back as one bundle.
5. **Analyze** — a human, or me looking at the screenshot/checklist/console
   output, decides: clean (proceed to Tool 2 and eventually §10), or not
   (a specific, concrete fix — "recentre `Link3`'s mesh", "Joint7_2's
   `lower`/`upper` are swapped") goes back to step 1.
6. **Repeat** until the loop reports clean two rounds in a row (mirrors the
   "loop-until-dry" pattern — a single clean pass can be luck, e.g. a check
   that only fires when a specific joint is driven past its limit).
7. **Sign off** — `blender-render` (Tool 2) produces the final human-facing
   image once the loop is clean; §10's deferred backend steps are the only
   thing that makes an asset actually live for real users.

**Why intermediate incompatibility is fine, and the end must not be**:
nothing in steps 1–3 requires touching Cyberwave-shaped anything — `trimesh`/
`PyMeshLab`/`yourdfpy` operate on plain STL/OBJ/DAE/URDF files directly, and
even a *hypothetically* adopted tool with its own project format (like
`URDF-Studio`'s `.usp`, §7) would only ever be used for an editing session
that exports back to plain URDF before the loop's next stage. What can never
drift is the artifact that exits the loop: plain URDF + relative-path meshes,
because that — and only that — is what `cyberwave-frontend`'s `urdf-loader`
actually reads (§1.1).

---

## 9. Tool bag port/process registry

| Tool | Port(s) | Notes |
|---|---|---|
| `twin-preview` | 5173 (Vite dev default) | host process, no Docker |
| `blender-render` | 9876 (Blender MCP addon socket) | local Blender process, no Docker |
| `mesh-doctor` | none | CLI/library only, no server |
| `twin-mcp` | none of its own | stdio-transport MCP server; drives `twin-preview` at its existing 5173, doesn't add a port |

None of these overlap the Cyberwave stack's ports (§1.3). As new tools are
added to the bag, append a row here before picking a port.

---

## 10. Deferred — real Cyberwave registration (not being executed now)

Kept for when you're ready to actually wire an asset into the real backend —
this is **not** part of the current build:

1. Merge the asset's PR to `main` in `Catalog` (backend's default zip-fetch
   flow reads from `main`).
2. Add a `CATALOG_ASSETS` entry in
   `cyberwave-backend/.../seed_asset_cyberwave_catalog.py` (`registry_id`,
   `subfolder`, `main_file_path`).
3. Start the local stack (`docker compose -f local.yml up -d` in
   `cyberwave-backend`, `pnpm run dev` in `cyberwave-frontend`).
4. `python manage.py seed_asset_cyberwave_catalog --assets <key>`.
5. Regenerate the controller for real: `python manage.py seed_controllers
   --autogen-controllers` — replaces the currently-uncommitted, hand-typed
   `unitree/d1-t-with-gripper` block (which lives in
   `AUTOGENERATED_CONTROLLERS` and would be silently clobbered by this same
   command anyway) with one actually derived from the asset's
   `universal_schema`.
6. Verify live in the real frontend, commit the backend changes as a normal
   PR.

Each of these touches shared/running infrastructure — confirm before running,
same as before.

---

## 11. Build sequencing

1. `tools/twin-preview` — scaffold, vendor the frontend files (§3.6), wire up
   `Viewer3D` + `StatusLine` (no picker, no panels — §3.2), get
   `D1_T_Gripper` rendering and moving via keyboard, expose
   `window.__twinPreview` (§6.3) from the start even before Tool 4 exists —
   cheap to add now, and it's the seam Tool 4 needs later. This is the
   higher-value, higher-effort piece and the one that actually proves motion
   correctness.
2. `tools/mesh-doctor` — `mesh_fixes.py` (trimesh) first, since it covers the
   most common real defects (origin, scale, normals) with the least
   dependency weight; `urdf_doctor.py`'s structural checks next (cheap,
   yourdfpy-based); `mesh_repair_heavy.py` (PyMeshLab) only if/when a
   specific asset needs non-manifold repair or decimation trimesh can't do.
3. `tools/twin-mcp` — register `@playwright/mcp` against `twin-preview`'s dev
   server, document the `browser_evaluate` call shapes against
   `window.__twinPreview` in its README. This is mostly configuration once
   step 1 exposes the control surface.
4. `tools/blender-render` — move the scratchpad script into the repo, write
   `render_asset.py` + a first camera/light preset, produce a formalized D1-T
   render as the first real artifact from this tool.
5. `tools/README.md` — index all four tools, the port registry (§9), the
   ground rules (§2, including the standing-rule requirement), and §8's loop
   diagram for anything added later.

## 12. Open questions for you

- `pnpm` in the `Catalog` repo for `twin-preview` — proceeding on this
  assumption since it matches `cyberwave-frontend`'s own tooling and keeps
  the vendored files' syntax/imports directly comparable; say so if you'd
  rather this live in a different repo.
- `render_asset.py`'s camera/light preset (§4.3) is a design choice with no
  existing convention to copy — happy to default to a simple 3-point studio
  turntable setup unless you want something specific.
- `mesh-doctor`'s "safe to auto-apply" list (§5.3) is my own judgment call
  about which defects are unambiguous — worth a look before it runs
  unattended on real assets, in case something on that list should require
  a human nod too.
