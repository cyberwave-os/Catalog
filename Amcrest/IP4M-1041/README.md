# Amcrest IP4M-1041 4MP ProHD Indoor Camera

URDF-ready visual and collision meshes for the black Amcrest IP4M-1041B pan/tilt RGB camera. The white IP4M-1041W uses the same housing geometry.

## Files

- `urdf/IP4M-1041.urdf` — articulated base, pan cradle, tilting camera, and ROS optical frame
- `meshes/*_visual.obj` / `.mtl` — material-preserving visual meshes in metres
- `meshes/*_collision.stl` — simplified collision meshes in metres
- `IP4M-1041.blend` — editable Blender source
- `preview/amcrest_ip4m_1041.png` — rendered preview

## Coordinate system and scale

The root frame follows REP-103: X points forward through the lens, Y points left, and Z points up. Meshes are authored in metres and need no URDF scale correction. Each mesh is local to its corresponding URDF link origin.

Published overall dimensions are 4.04 × 3.94 × 4.66 in (102.6 × 100.1 × 118.4 mm), and published mass is 0.60 lb (290 g). The link masses sum to 0.290 kg; inertias are engineering approximations from the component envelopes.

The model captures the external envelope, pan base, tilt cradle, lens stack, IR emitters, status indicator, branding, and rear connector locations. It is intended for visualization, scene layout, collision checking, and robotics simulation—not manufacturing.

## Motion

- `amcrest_pan_joint`: continuous rotation about +Z
- `amcrest_tilt_joint`: approximately 70° up / 25° down about +Y
- `amcrest_camera_optical_frame`: ROS camera optical convention (Z forward, X right, Y down)

## Product references

- Amcrest IP4M-1041 technical specification: 4 mm fixed lens, 90° field of view, 10 m IR range, 102.6 × 100.1 × 118.4 mm, 290 g
- Google Images search for IP4M-1041B/IP4M-1041W front and three-quarter housing views
