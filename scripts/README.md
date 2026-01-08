Convert URDF to xml using Mujoco 

Requirements:

$ uv pip install mujoco
$ uv pip install obj2mjcf

1. Visual mesheas:
   
   If .dae -> use blender tool to convert to .obj --> visual meshes
   From script folder:
   $ blender-3.3 --background --python convert_dae_to_obj.py -- ../Universal_Robots/UR5e/meshes/visual/ ../Universal_Robots/UR5e/meshes/visual/

   or

   $ blender-3.3 --background --python convert_dae_to_obj.py -- ../KUKA/LBR_iiwa14_R820/meshes/visual/ ../KUKA/LBR_iiwa14_R820/meshes/visual/

2. Collision meshes:
   
   If .dae -> use blender tool to convert to .stl --> collision meshes

3. Split .obj: 
   
   $ obj2mjcf --obj-dir ../Universal_Robots/UR5e/meshes/visual --overwrite --save-mjcf

   or 

   $ obj2mjcf --obj-dir ../KUKA/LBR_iiwa14_R820/meshes/visual/ --overwrite --save-mjcf

-----

4. URDF -> urdf_to_xml.py 

   $ python3 urdf_to_xml.py ../Universal_Robots/UR5e/ur5e.urdf --out ur5e.xml

   Saves ur3.xml on .

5. Generate modded .xml file

   $ python3 mjcf_xml_from_meshes.py ur5e.xml ../Universal_Robots/UR5e/meshes/ --recursive

-----

6. URDF -> urdf2mcjf (better?)

   $ urdf2mjcf --output ur5e.xml ur5e.urdf 
