# RealSense™ LiDAR Camera L515

This Catalog entry uses the free, official L515 model from the
[RealSense ROS wrapper](https://github.com/realsenseai/realsense-ros/tree/4.54.1/realsense2_description).

## Contents

- `urdf/realsense_l515.urdf`: standalone URDF adapted for the Cyberwave Catalog
- `meshes/l515.dae`: official visual mesh
- `source/_l515.urdf.xacro`: unmodified upstream Xacro for provenance
- `LICENSE`: upstream Apache License 2.0

The standalone URDF removes the ROS/Xacro package dependency while retaining the
official visual transform, 61 mm × 26 mm collision envelope, 95 g mass, and
inertia values. The adapted URDF is a modified file under Apache-2.0.

Source revision: RealSense ROS `4.54.1` (`ae45d4969f5a7105a6a9e0deeadc785004d72441`).

RealSense and related marks belong to their respective owners. Their use here
identifies the source and compatible hardware; no endorsement is implied.
