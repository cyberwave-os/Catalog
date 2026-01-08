#!/usr/bin/env python3
"""
DAE/STL to OBJ Converter for MuJoCo using Blender 3.3+
Can split .dae files by material into separate .stl files
Usage: blender --background --python convert_to_obj.py -- <input_folder> [output_folder] [--split-materials]
"""

import bpy
import sys
from pathlib import Path


def split_by_material(input_file, output_path):
    """Split a DAE file into multiple STL files by material"""
    base_name = input_file.stem
    exported_count = 0
    
    # Get all mesh objects in the scene
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    # If there's only one mesh object, split by material-assigned faces
    if len(mesh_objects) == 1:
        obj = mesh_objects[0]
        
        # Get all materials used in this object
        materials = [slot.material for slot in obj.material_slots if slot.material]
        
        if not materials:
            # No materials, export as single STL
            safe_name = "no_material"
            stl_file = output_path / f"{base_name}_{safe_name}.stl"
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            bpy.ops.export_mesh.stl(
                filepath=str(stl_file),
                use_selection=True,
                global_scale=1.0,
                axis_forward='Y',
                axis_up='Z',
                use_scene_unit=False
            )
            print(f"  ↳ Exported: {base_name}_{safe_name}.stl")
            return 1
        
        # Separate by material
        for mat in materials:
            mat_name = mat.name
            safe_mat_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in mat_name)
            
            # Duplicate the object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.duplicate()
            
            dup_obj = bpy.context.active_object
            
            # Enter edit mode and deselect all
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Select faces with this material
            mat_index = obj.material_slots.find(mat.name)
            for poly in dup_obj.data.polygons:
                if poly.material_index == mat_index:
                    poly.select = True
            
            # Delete non-selected faces
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='INVERT')
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Export this material's STL
            stl_file = output_path / f"{base_name}_{safe_mat_name}.stl"
            bpy.ops.export_mesh.stl(
                filepath=str(stl_file),
                use_selection=True,
                global_scale=1.0,
                axis_forward='Y',
                axis_up='Z',
                use_scene_unit=False
            )
            
            # Delete the duplicate
            bpy.ops.object.delete()
            
            print(f"  ↳ Exported material '{mat_name}': {base_name}_{safe_mat_name}.stl")
            exported_count += 1
    
    else:
        # Multiple objects - group by material
        material_groups = {}
        
        for obj in mesh_objects:
            if len(obj.material_slots) > 0:
                mat = obj.material_slots[0].material
                mat_name = mat.name if mat else "no_material"
            else:
                mat_name = "no_material"
            
            if mat_name not in material_groups:
                material_groups[mat_name] = []
            material_groups[mat_name].append(obj)
        
        # Export each material group
        for mat_name, objects in material_groups.items():
            safe_mat_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in mat_name)
            stl_file = output_path / f"{base_name}_{safe_mat_name}.stl"
            
            # Deselect all
            bpy.ops.object.select_all(action='DESELECT')
            
            # Select and join objects with this material
            for obj in objects:
                obj.select_set(True)
            
            bpy.context.view_layer.objects.active = objects[0]
            
            # Join selected objects into one
            if len(objects) > 1:
                bpy.ops.object.join()
            
            # Export as STL
            bpy.ops.export_mesh.stl(
                filepath=str(stl_file),
                use_selection=True,
                global_scale=1.0,
                axis_forward='Y',
                axis_up='Z',
                use_scene_unit=False
            )
            
            print(f"  ↳ Exported material '{mat_name}': {base_name}_{safe_mat_name}.stl")
            exported_count += 1
    
    return exported_count


def convert_to_obj(input_folder, output_folder=None, split_materials=False):
    """Convert all .dae and .stl files in input_folder to .obj format"""
    
    input_path = Path(input_folder).resolve()
    
    if not input_path.exists():
        print(f"Error: Input folder '{input_folder}' does not exist")
        return
    
    # Set output folder
    if output_folder is None:
        output_path = input_path / "converted"
    else:
        output_path = Path(output_folder).resolve()
    
    # Create output folder if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all .dae and .stl files
    dae_files = list(input_path.glob("*.dae"))
    stl_files = list(input_path.glob("*.stl"))
    all_files = dae_files + stl_files
    
    if not all_files:
        print(f"No .dae or .stl files found in {input_folder}")
        return
    
    print(f"Converting files from: {input_path}")
    print(f"Output folder: {output_path}")
    print(f"Found {len(dae_files)} .dae file(s) and {len(stl_files)} .stl file(s) to convert")
    if split_materials:
        print("Material splitting: ENABLED (DAE files will be split by material into STL files)")
    print("---")
    
    converted_count = 0
    
    for input_file in all_files:
        base_name = input_file.stem
        file_ext = input_file.suffix.lower()
        obj_file = output_path / f"{base_name}.obj"
        
        try:
            # Clear the scene
            bpy.ops.object.select_all(action='SELECT')
            bpy.ops.object.delete()
            
            # Clear mesh data
            for mesh in bpy.data.meshes:
                bpy.data.meshes.remove(mesh)
            
            # Import file based on extension
            if file_ext == '.dae':
                print(f"Converting: {base_name}{file_ext}")
                bpy.ops.wm.collada_import(filepath=str(input_file))
                
                if split_materials:
                    # Split by material into STL files
                    mat_count = split_by_material(input_file, output_path)
                    print(f"✓ Successfully split into {mat_count} STL file(s) by material")
                    converted_count += mat_count
                else:
                    # Export as single OBJ
                    bpy.ops.wm.obj_export(
                        filepath=str(obj_file),
                        export_triangulated_mesh=True,
                        export_normals=True,
                        export_uv=True,
                        export_materials=True,
                        path_mode='STRIP',
                        forward_axis='Y',
                        up_axis='Z'
                    )
                    print(f"✓ Successfully converted: {base_name}.obj")
                    converted_count += 1
                    
            elif file_ext == '.stl':
                print(f"Converting: {base_name}{file_ext} -> {base_name}.obj")
                bpy.ops.import_mesh.stl(filepath=str(input_file))
                
                # Export as OBJ
                bpy.ops.wm.obj_export(
                    filepath=str(obj_file),
                    export_triangulated_mesh=True,
                    export_normals=True,
                    export_uv=True,
                    export_materials=True,
                    path_mode='STRIP',
                    forward_axis='Y',
                    up_axis='Z'
                )
                print(f"✓ Successfully converted: {base_name}.obj")
                converted_count += 1
            
        except Exception as e:
            print(f"✗ Failed to convert {base_name}{file_ext}: {str(e)}")
        
        print("---")
    
    print(f"Conversion complete! Converted {converted_count} file(s).")


if __name__ == "__main__":
    # Get arguments after the '--' separator
    argv = sys.argv
    
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        print("Usage: blender --background --python convert_to_obj.py -- <input_folder> [output_folder] [--split-materials]")
        print("Example: blender --background --python convert_to_obj.py -- ./models ./converted")
        print("Example with material split: blender --background --python convert_to_obj.py -- ./models ./converted --split-materials")
        sys.exit(1)
    
    if len(argv) < 1:
        print("Error: Please provide an input folder")
        print("Usage: blender --background --python convert_to_obj.py -- <input_folder> [output_folder] [--split-materials]")
        sys.exit(1)
    
    input_folder = argv[0]
    output_folder = None
    split_materials = False
    
    # Parse remaining arguments
    for i in range(1, len(argv)):
        if argv[i] == "--split-materials":
            split_materials = True
        elif output_folder is None:
            output_folder = argv[i]
    
    convert_to_obj(input_folder, output_folder, split_materials)