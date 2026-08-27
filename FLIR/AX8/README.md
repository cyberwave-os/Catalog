# FLIR AX8

URDF-ready visual and collision geometry for the FLIR AX8 fixed thermal imaging camera.

## Files

- `urdf/AX8.urdf` — single rigid body with thermal and visible optical frames
- `meshes/AX8_visual.obj` and `meshes/AX8_visual.mtl` — material-preserving visual mesh
- `meshes/AX8_collision.stl` — simplified collision mesh
- `AX8.blend` — editable Blender source
- `preview/ax8.png` — rendered preview

## Coordinate system and scale

The root `ax8_link` follows REP-103: X forward through the camera lenses, Y left, and Z up. Mesh coordinates are in metres and require no URDF scale factor.

Nominal body dimensions are 54 × 25 × 79 mm without connectors and 54 × 25 × 95 mm with connectors. The detailed mechanical drawing rounds these to approximately 55 × 25.6 × 80 mm; the mesh follows the drawing while the simplified collision mesh measures 25.6 × 55 × 94.8 mm in XYZ.

The published device mass is 0.125 kg. Inertia is approximated from the principal body envelope.
