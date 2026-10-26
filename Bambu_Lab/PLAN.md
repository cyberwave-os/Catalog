# Bambu Lab P2S digital twin + print driver — execution plan

Stay focused on the task at hand. Anything outside the scope below is **documented in
`PROGRESS.md` under "Out-of-scope findings" and left unfixed**. After any review comment,
re-check that the issue is actually in scope before touching it.

Sources of truth (read before each milestone): `cyberwave-contracts` JSON schemas, backend API
docs (`cyberwave-backend/docs`, `docs-mintlify`), the Python SDK, `cyberwave-edge-runtime/agents.md`,
`EDGE_DEVELOPMENT.md`, and the AX8 driver as the layout template. Use Context7 for library docs.
After every milestone: review what was done, run its tests, tick `PROGRESS.md`.

## Scope

In scope
- Catalog asset `Bambu_Lab/P2S` (URDF + meshes), validated with `Catalog/tools` (mesh-doctor, twin-preview).
- A `printing` capability (+ `printable` tag) and P2S sensors in `capabilities.sensors`.
- Backend seed/patch entry for the asset; upload to a local Cyberwave and place it in an environment.
- Native driver `cyberwave-edge-runtime/runtime-services/drivers/native/bambu/bambu_lab_p2s`
  (Python, Cyberwave SDK), bridging to `bambu-printer-mcp` (PR 4918).
- Frontend: "Print +" section in the twin right panel (P2S only), catalog picker filtered by `printable`.
- Two printable catalog assets: Orin Nano case v3, FLIR AX8 v5.0 (with 3MF/STL print files).

Out of scope (document only): unrelated frontend/backend bugs, other printers' drivers, refactors
of existing capability code, fixing PR 4918 itself, licence resolution of the vendored GPL code.

Facts that shape the plan
- MakerWorld model 2590690 needs a login to download (HTTP 403 "Please log in") and its
  *Standard Digital File License* forbids redistribution/derivatives hosting. The login is not
  bypassed. Interim geometry is a **proxy** (392×406×478 mm envelope) clearly named `*_proxy`;
  the real STEP must be placed by the user and converted with the documented command.
- Catalog assets reach Cyberwave through `CATALOG_ASSETS` / `CATALOG_ASSET_SENSORS` (backend seeding) and
  `asset_patches/<vendor>_<model>.py`.
- `CapabilitiesValidator` drops unknown capability groups, so `printing` must be added to the validator first.
- Picker filtering is substring match on `metadata.tags` (`capability_tags`), so `printable` is also a tag.
- Real printer is not reachable from this session: live print is verified against a fake printer
  (MQTT/FTPS stub); real-robot steps are left as a runbook, not claimed as done.

## Milestones

### M1 — Catalog asset
Goal: `Catalog/Bambu_Lab/P2S` is a valid, previewable catalog asset.
Success criteria:
1. `urdf/bambu_lab_p2s.urdf` uses relative mesh paths, metre scale, positive-definite inertia; `urdf_doctor` reports ok.
2. Meshes pass `mesh_fixes` (watertight, extents match 0.392×0.406×0.478 m).
3. `twin-preview` loads the URDF without errors (checklist OK).
4. README documents source, licence, proxy status and STEP→mesh replacement steps.

### M2 — Capabilities, sensors, printing
Goal: asset metadata fully describes the P2S.
Success criteria:
1. Sensors (from verified P2S specs only) are defined with valid types (`temperature`, `status`, `rgb`, ...).
2. `printing` capability accepted by `CapabilitiesValidator`, surfaced by `get_cyberwave_capabilities`, typed in FE; backend tests pass in docker.
3. `asset_patches/bambu_lab_p2s.py` returns valid patches; unit test asserts them.

### M3 — Upload and environment check
Goal: asset appears correctly in a local Cyberwave environment.
Success criteria:
1. Local stack up (`make backend` / compose); asset seeded.
2. Twin added to an environment in edit mode; browser screenshot shows it correctly placed.

### M4 — Driver
Goal: driver follows edge contracts and passes tests.
Success criteria:
1. Files: manifest, `cw-driver.yml`, Dockerfile, entrypoint, src, tests; entrypoint test list updated.
2. Commands declared in `cw-driver.yml` (`print`, `pause`, `resume`, `cancel`, `start_video`, `stop_video`).
3. Pipeline prepare→(orient/supports/slice via MCP)→upload→start; progress telemetry; finish event.
4. Video via `stream_video_background` from the RTSPS URL.
5. Unit tests + fake-printer integration test pass; ruff/mypy via `RT/lint.sh` pass.

### M5 — Frontend "Print +"
Goal: selectable printable assets from the P2S panel.
Success criteria:
1. Panel section appears only for assets with `printing` capability.
2. "Print +" opens the catalog filtered to `printable`; selection stored on the twin (metadata).
3. FE type-check/lint/tests pass; browser verification in edit and live mode.

### M6 — Printable catalog assets
Goal: Orin case + AX8 plate uploaded as printable.
Success criteria:
1. Both assets in Catalog with URDF, STL, 3MF; tag `printable`; `printing`-related metadata lists print files.
2. They show up in the picker when "Print +" is pressed.

### M7 — End-to-end validation
Success criteria:
1. Full flow against fake printer: select asset → play → upload → progress → finish event.
2. Screenshots of environment, panel, picker. Real-printer runbook written; real print explicitly **not** claimed.

## Assumptions
Recorded in `PROGRESS.md`.
