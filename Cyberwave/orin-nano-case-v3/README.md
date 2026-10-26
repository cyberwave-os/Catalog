# Orin Nano case v3 (printable)

Jetson Orin Nano case for the Bambu Lab P2S: main body and base plate on one plate, floor-down,
no supports needed (designer's orientation analysis: 0 floating regions). Tagged `printable`.

| File | Use |
|---|---|
| `meshes/orin-case-main-v3.stl` | visual mesh and print geometry (mm, 235.6 x 103 x 34.8) |
| `print/orin-case-main-v3.3mf` | native unsliced Bambu Studio project |
| `print/orin-case-main-v3-p2s-sliced.3mf` | P2S-sliced plate (174 layers, ~2 h 51 m, ~99 g PLA) |

Provenance: derived from the `orin-nano-case-main` design in the cyberwave-3d workspace
(`orin-case/orin-nano-case-main/v3`); the upstream design's licence has not been checked.
The STL is not reported watertight by trimesh (two bodies on one plate); Bambu Studio slices it.
Not physically printed.

## Asset metadata to set on upload
```json
{"tags": ["printable", "case", "jetson"],
 "print_files": [
   {"name": "orin-case-main-v3.stl", "format": "stl", "path": "meshes/orin-case-main-v3.stl"},
   {"name": "orin-case-main-v3.3mf", "format": "3mf", "path": "print/orin-case-main-v3.3mf"}]}
```
