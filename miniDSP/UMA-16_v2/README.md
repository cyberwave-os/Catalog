# miniDSP UMA-16 v2 USB mic array

URDF-ready reconstruction based on the official miniDSP product photography and the published overall dimensions of **132 x 202 x 18 mm**.

## Files

- `urdf/uma16_v2.urdf` — single-link URDF
- `meshes/uma16_v2_visual.stl` — detailed visual geometry
- `meshes/uma16_v2_collision.stl` — simplified two-part collision envelope
- `source/uma16_v2.blend` — editable Blender source with materials and separate components
- `reference/uma16_v2_preview.png` — rendered geometry preview

## Frame convention

- `+X`: width across the 132 mm microphone board
- `+Y`: from the USB/interface tail toward the top of the microphone array
- `+Z`: component/front side of the PCB
- Origin: center of the 132 x 202 mm overall planform, on the microphone PCB plane

The STL coordinates are in meters, so the URDF uses `scale="1 1 1"`.

## Modeled features

- 132 mm square open-frame microphone PCB
- 3 x 3 open-window structure and center camera aperture
- 4 x 4 MEMS microphone arrangement
- Four camera mounting points and four outer M3 mounting points
- Interface tail, stacked MCHStreamer Lite board, headers, ICs, Mini-B USB connector, and underside pins

The geometry is intended for visualization, mounting-envelope work, and robotics simulation. Small component placement is reconstructed from photographs rather than manufacturer STEP data. The 0.18 kg mass and inertia values are estimates and should be replaced with measured values for dynamics-sensitive simulation.

## Reference

- Official product page: https://www.minidsp.com/products/usb-audio-interface/uma-16-microphone-array
