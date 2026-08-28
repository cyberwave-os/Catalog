# Amcrest IP4M-1041B

URDF-ready mesh for the Amcrest 4MP ProHD indoor pan/tilt RGB camera.

## Generation

- Source: user-supplied front product reference image
- Provider: Cyberwave image-to-mesh (`CYBERWAVE_API`, `hunyuan3d-2`)
- Cyberwave job: `2233155a-0260-40c1-bfee-edd9023117fc`
- Product envelope: 100.076 mm deep × 102.616 mm wide × 118.364 mm high
  (3.94 × 4.04 × 4.66 in)
- Coordinates: REP-103 (`+X` optical forward, `+Y` left, `+Z` up)
- The final camera was manually modeled as three independently movable meshes.
- Exported visual complexity: 5,379 polygons
  (base 2,010, horizontal housing 1,962, vertical head 1,407).

## Articulation

- `amcrest_pan_joint`: continuous rotation around `+Z`
- `amcrest_tilt_joint`: gimbal rotation around `+Y`
- Horizontal pivot: `0 0 0.036` m in the base frame
- Vertical pivot: `-0.000281259 0.001454012 0.044` m in the pan frame
- Blender source objects:
  - `IP4M_1041_visual`: fixed base
  - `IP4M_1041_visual.001`: horizontal housing
  - `Sphere`: vertical camera head

## Files

- `IP4M-1041.blend`: manually modeled three-part Blender source
- `meshes/IP4M_1041_base_visual.obj`: fixed base visual
- `meshes/IP4M_1041_pan_visual.obj`: rotating enclosure visual
- `meshes/IP4M_1041_tilt_visual.obj`: tilting camera-head visual
- `meshes/IP4M_1041_*_collision.stl`: per-link collision meshes
- `source/IP4M_1041_cyberwave_raw.glb`: unmodified Cyberwave result
- `source/IP4M_1041_visual.obj`: decimated combined shell retained as a backup
- `urdf/IP4M-1041.urdf`: articulated URDF with camera and optical frames

The OBJ and STL exports are expressed in each URDF link's local joint frame.
