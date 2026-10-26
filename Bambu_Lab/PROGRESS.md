# PROGRESS

- [x] Research: Cyberwave asset/capability docs, driver/edge docs, PR 4918 MCP, P2S specs
- [x] Execution plan written (`PLAN.md`)
- [x] MakerWorld download attempted: BLOCKED (login required; licence forbids redistribution). Proxy mesh generated.
- [x] M1 Catalog asset: urdf_doctor ok=True, mesh watertight 0.392x0.406x0.478, twin-preview renders (screenshot checked), README written
- [x] M2 Capabilities: printing group (validator+resolver), asset patch bambulab_p2s (camera + 10 scalar sensors), 271 backend tests in the touched areas pass in docker (test.yml)
- [x] M3 Local stack (isolated project, ports 8100/5433/6380/1884/9002/3100): 3 assets seeded via the real seed command, patches + cw-driver.yml applied; P2S twin added to an environment; screenshot confirms it renders and the right panel shows the 3D printing section
- [x] M4 Driver `cyberwave-edge-runtime/.../drivers/native/bambu/bambu_lab_p2s`: 40 tests (fake stdio MCP), ruff+mypy clean, docker image builds, driver imports with the real SDK, real `bambu-printer-mcp@1.1.33` starts and lists tools, real MCP reads a fake TLS-MQTT printer, entrypoint test list updated
- [x] M5 Frontend: `twin-printing-section` + `printable-asset-picker-dialog` + helpers; 14 vitest tests (200 across panels/utils pass); section is in both the edit-mode inspector and the Live panel; verified in the real UI: Print + opens a catalog filtered to the 2 printable assets, selection persists in twin metadata.print_job
- [x] M6 Printable catalog assets: Cyberwave/orin-nano-case-v3, Cyberwave/ax8-threaded-plate-v5 (urdf_doctor ok; STL/3MF files served by the backend; picker lists exactly these two)
- [x] M7 End-to-end (fake printer): real UI Live mode → Play → real driver container → download STL from backend → fix/slice (fake MCP) → progress → finish; UI shows progress and "Print finished", Live values show the sensors. Evidence in `evidence/`. **Not done: real P2S print, video stream** (see Blockers)

## Blockers (could not be completed here)
- **Real STEP/CAD**: MakerWorld requires a login (HTTP 403 "Please log in to download models") and the Standard Digital File License forbids redistributing it. Not bypassed. The twin uses a labelled proxy mesh (392x406x478 mm); replacement steps are in `P2S/README.md`.
- **Real printer**: none reachable. No real print was started. Runbook: `REAL_PRINTER_RUNBOOK.md`.
- **Video**: the RTSPS stream path is wired (`stream_video_background`) and its failure path was exercised (alert pushed, secret redacted), but no stream was received: no camera, and the local stack has no media service.
- **Slicing with supports on hardware profiles**: the fake MCP stands in for `slice_stl`/`print_3mf`; the Bambu Studio CLI and FTPS upload were not run.

## Assumptions
- A proxy envelope mesh stands in for the real CAD; sensors are limited to what Bambu documents or the MQTT report exposes (LiDAR, accelerometer, air-quality, toolhead camera were not confirmed, so not declared).
- `printing` is a new optional capability group (`can_print`, `technology`, `build_volume_mm`, `supported_file_formats`) plus the `printable` catalog tag; the picker filters on the tag (backend `capability_tags` is a tag substring match).
- Print files live in `metadata.print_files` (paths relative to the project root, served under `/media/urdf_projects/<slug>/`), the chosen asset in twin `metadata.print_job`.
- Only `source_type: "tele"` can start a print; `sim_tele`/`edit` are ignored. The Play press is treated as the human confirmation (`BAMBU_REQUIRE_CONFIRMATION=0`).
- Local stack: isolated compose project on remapped ports because another stack held the default ones; it uses `host.docker.internal` as the API URL so the driver container can download files.

## Bugs found only by running it for real (all fixed, each with a test)
1. `operating_range` must be `{min,max}` (list was flagged by the sensor-schema gate).
2. The twin/asset API resolves capabilities through `schema_capability_overrides` (explicit key list): `can_print` was dropped until a `printing` family was added.
3. Local `urdf_file` is a relative `/media/...` path: print URLs are now made absolute.
4. The Live panel is a different component from the edit inspector: the section is mounted in both.
5. The SDK's camera error echoes `rtsps://bblp:<code>@...`: it reached a backend alert and the logs. Now redacted.
6. Live values read `metrics.readings.<sensor>.{value,unit,at}` (timeseries README §7), not a free-form category: driver aligned.
7. Seed: catalog entries now accept `metadata` (tags, print_files).

## Out-of-scope findings (documented, not fixed)
- Pi_Camerav3.urdf: mesh path `meshes/` vs folder `stl/`, visual origin z=10 looks like a unit slip.
- `AssetBrowser.defaultTag` is unused; FE `drivers` type narrower than BE validator.
- cw-driver.yml telemetry direction / legacy webrtc shape inconsistencies (AX8); EDGE_DEVELOPMENT.md drift; video command docs (`sensor_id`) vs `VideoStreamMixin`.
- PR 4918 vendors GPL-2.0 code; its README says printing needs the `bambu-node` postinstall patch (the npm install in the Dockerfile keeps it).
- `tests/entrypoint/test_docker_entrypoint.py::test_metadata_wrapper_stripped` and `::test_edge_configs_wrapper_stripped` fail (Go2-specific `CYBERWAVE_METADATA_GO2_IP_ADDR`).
- ruff reports ~380 pre-existing errors elsewhere in `drivers/`; `tsc` reports many pre-existing errors in `__tests__/`.
- The SDK's bundled `assets_capabilities.json` / twin subclass resolution does not know `printing` (twins resolve via the API, so it is not needed here).
- The Orin case STL is not watertight per trimesh (two bodies on one plate) and its upstream design licence was not checked.
- Ports 3000/5432/6379/8000/1883 were held by someone else's running stack (`ugv_audit_*`, mounting `3-third`); it was not touched. Stopped `cyberwave_local_*` containers from a `2-second` checkout were left alone.
- Local DB contains one early alert with the fake access code in clear text (from before fix 5); it is test data in my throwaway stack.
