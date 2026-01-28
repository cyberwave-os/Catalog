#!/usr/bin/env python3
"""
Generate URDF from xacro files without requiring a full ROS 2 environment.
This script substitutes $(find openarm_description) with the actual package path.
"""

import os
import sys
import tempfile
import shutil
import re

def substitute_find_commands(content, package_path):
    """Replace $(find openarm_description) with the actual path."""
    pattern = r'\$\(find openarm_description\)'
    return re.sub(pattern, package_path, content)

def process_xacro_files(package_path, temp_dir):
    """Copy and process all xacro and yaml files, substituting package paths."""
    for subdir in ['urdf', 'config']:
        src_dir = os.path.join(package_path, subdir)
        dst_dir = os.path.join(temp_dir, subdir)
        
        if not os.path.exists(src_dir):
            continue
            
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith('.xacro') or file.endswith('.yaml'):
                    src_file = os.path.join(root, file)
                    rel_path = os.path.relpath(src_file, package_path)
                    dst_file = os.path.join(temp_dir, rel_path)
                    
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                    
                    with open(src_file, 'r') as f:
                        content = f.read()
                    
                    # Replace $(find openarm_description) with temp_dir path
                    content = substitute_find_commands(content, temp_dir)
                    
                    with open(dst_file, 'w') as f:
                        f.write(content)

def main():
    # Get the package directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    package_path = script_dir
    
    # Create a temporary directory for processed files
    temp_dir = tempfile.mkdtemp(prefix='openarm_xacro_')
    
    try:
        print(f"Processing xacro files...")
        print(f"Temporary directory: {temp_dir}")
        
        # Copy and process all xacro and yaml files
        process_xacro_files(package_path, temp_dir)
        
        # Copy meshes directory (for mesh references)
        meshes_src = os.path.join(package_path, 'meshes')
        meshes_dst = os.path.join(temp_dir, 'meshes')
        if os.path.exists(meshes_src):
            shutil.copytree(meshes_src, meshes_dst)
        
        # Run xacro
        xacro_file = os.path.join(temp_dir, 'urdf', 'robot', 'v10.urdf.xacro')
        output_file = os.path.join(package_path, 'urdf', 'robot', 'openarm_robot.urdf')
        
        # Verify the file exists
        if not os.path.exists(xacro_file):
            print(f"Error: Xacro file not found: {xacro_file}")
            print(f"Contents of temp_dir/urdf/robot/:")
            robot_dir = os.path.join(temp_dir, 'urdf', 'robot')
            if os.path.exists(robot_dir):
                for f in os.listdir(robot_dir):
                    print(f"  - {f}")
            sys.exit(1)
        
        # Import xacro and process
        try:
            import xacro
        except ImportError:
            print("Error: xacro module not found. Install with: pip3 install xacro")
            sys.exit(1)
        
        # Process the xacro with arguments to disable hand (simpler URDF)
        print(f"Processing: {xacro_file}")
        print(f"Arguments: hand:=false, ee_type:=none, ros2_control:=false, bimanual:=false")
        
        # Create mappings for xacro arguments
        mappings = {
            'hand': 'false',
            'ee_type': 'none',
            'ros2_control': 'false',
            'bimanual': 'false'
        }
        
        doc = xacro.process_file(xacro_file, mappings=mappings)
        urdf_content = doc.toprettyxml(indent='  ')
        
        # Clean up XML - remove extra blank lines
        lines = urdf_content.split('\n')
        clean_lines = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            clean_lines.append(line)
            prev_blank = is_blank
        
        urdf_content = '\n'.join(clean_lines)
        
        # Write the URDF
        with open(output_file, 'w') as f:
            f.write(urdf_content)
        
        print(f"\n✓ Successfully generated URDF: {output_file}")
        print(f"  File size: {os.path.getsize(output_file)} bytes")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    main()
