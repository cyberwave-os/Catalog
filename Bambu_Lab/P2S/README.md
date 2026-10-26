# Bambu Lab P2S

Digital twin of the Bambu Lab P2S enclosed FDM printer (build volume 256 x 256 x 256 mm,
outer envelope 392 x 406 x 478 mm, 14.9 kg).

## Geometry status: PROXY
`meshes/p2s_body_proxy.stl` and `meshes/p2s_build_plate.stl` are generated envelope meshes (metres,
watertight), **not** the real CAD. The reference model is MakerWorld 2590690 (creator "shay",
`Bambu-P2S-CAD.step`). It requires a MakerWorld login to download and is under the Standard Digital
File License (no redistribution / hosting of derivatives), so it is deliberately not committed here.

To swap in the real model: download the STEP while logged in, convert and fix it, then replace the two
proxy meshes (keep the file names or update the URDF):
```bash
cd Catalog/tools/mesh-doctor
python3 -m mesh_doctor.mesh_fixes /path/to/Bambu-P2S-CAD.stl --rescale 0.001 --recenter bbox --fix-normals --out ../../Bambu_Lab/P2S/meshes/p2s_body.stl
python3 -m mesh_doctor.urdf_doctor ../../Bambu_Lab/P2S/urdf/bambu_lab_p2s.urdf
```
(STEP -> STL conversion: e.g. FreeCAD or Blender; confirm the licence allows your use first.)

## Frames
z up, origin at floor centre; `p2s_build_plate_link` top face at z = 0.092 m; `p2s_camera_link`
is the chamber camera frame (sensor `chamber_camera`).

## Validation
- `urdf_doctor`: ok. `mesh_fixes`: watertight, extents 0.392 x 0.406 x 0.478 m.
- `twin-preview ?urdf=Bambu_Lab/P2S/urdf/bambu_lab_p2s.urdf` renders it. The status line shows joint
  errors only because twin-preview defaults to the D1-T keyboard policy; the P2S has no actuated joints.
