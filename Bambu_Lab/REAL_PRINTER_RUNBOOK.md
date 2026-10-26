# Real P2S runbook (not yet executed)

Everything below was verified against a **fake printer** only. A real print was never started.

1. Printer: enable **LAN Only** and **Developer** mode; note IP, serial, LAN access code. Clear any HMS notice on the screen.
2. Twin: set `metadata.ip_address` and `metadata.serial` on the P2S twin. Give the driver the access code only through `CYBERWAVE_P2S_ACCESS_CODE` (never twin metadata).
3. Slicer: the driver slices STL with the Bambu Studio CLI. Build the image with `--build-arg BAMBU_STUDIO_APPIMAGE_URL=<release asset>` or mount a CLI and set `CYBERWAVE_P2S_SLICER_PATH`. Without it only pre-sliced 3MF jobs can print.
4. First print: use the AX8 plate (12 g, 39 min), plate clear, filament loaded, you at the machine. Watch the first layer; `cancel_print` is the stop button in the panel.
5. Things to confirm on hardware (all unverified): tree-support process-profile keys (`driver/src/printer.py` `SUPPORT_PROFILE`), the `door` / `filament_runout` / `filament_tangle` report fields, the fan 0–15 scale, RTSPS camera access with LAN Liveview, FTPS upload on port 990 with the printer's firmware.
6. Real geometry: download the P2S STEP from MakerWorld model 2590690 while logged in (licence: no redistribution), convert and replace `meshes/p2s_body_proxy.stl` (see `P2S/README.md`).
