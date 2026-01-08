#!/usr/bin/env python3
"""
Convert a URDF file to a MuJoCo MJCF XML file.

Usage:
    python urdf_to_mjcf.py path/to/robot.urdf -o path/to/robot.xml

Assumptions:
    - The URDF references meshes with *relative* paths, e.g.
        meshes/visual/...
        meshes/collision/...
    - Those folders exist next to the URDF file.
"""

import argparse
import os
from pathlib import Path

import mujoco  # pip install mujoco
import re
import tempfile


def urdf_to_mjcf(urdf_path: Path, out_path: Path) -> None:
    urdf_path = urdf_path.resolve()
    out_path = out_path.resolve()

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Temporarily cd into the URDF directory so relative mesh paths like
    # "meshes/visual/..." and "meshes/collision/..." resolve correctly.
    cwd = os.getcwd()
    try:
        os.chdir(urdf_path.parent)
        # Use only the filename here; working dir is now the URDF folder
        # Prepare input XML: if it doesn't already contain a <mujoco> block,
        # create a temporary copy with the <mujoco><compiler .../></mujoco>
        # inserted right after the opening <robot> tag. We do this *before*
        # letting MuJoCo process the file so the compiler settings take effect.
        temp_path = None
        try:
            original_txt = urdf_path.read_text(encoding='utf-8')
        except Exception:
            original_txt = None

        input_filename = urdf_path.name
        if original_txt is not None and '<mujoco' not in original_txt.lower():
            m = re.search(r'(<robot[^>]*>)', original_txt, flags=re.IGNORECASE)
            if m:
                insert = (
                    "\n  <mujoco>\n"
                    "    <compiler discardvisual=\"false\" meshdir=\"meshes/visual\"/>\n"
                    "  </mujoco>\n"
                )
                new_txt = original_txt[: m.end()] + insert + original_txt[m.end():]

                # Parse the XML and replace any <mesh filename="...*.dae"> -> .obj
                try:
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(new_txt)
                    changed = False
                    for el in root.iter():
                        tag = el.tag
                        local = tag.split('}')[-1] if '}' in tag else tag
                        if local.lower() != 'mesh':
                            continue
                        fn = el.get('filename')
                        if fn and (fn.lower().endswith('.dae') or '.dae' in fn.lower()):
                            # Robustly replace the trailing extension to .obj.
                            # Some URDF filenames may include query params or extra
                            # characters, so prefer a direct suffix replace when
                            # possible and fall back to a case-insensitive regex.
                            if fn.lower().endswith('.dae'):
                                newfn = fn[:-4] + '.obj'
                            else:
                                newfn = re.sub(r'\\.dae', '.obj', fn, flags=re.IGNORECASE)
                            el.set('filename', newfn)
                            changed = True
                    if changed:
                        # Note: ET.tostring may alter formatting/whitespace
                        new_txt = ET.tostring(root, encoding='unicode')
                except Exception:
                    # If parsing fails, fall back to a case-insensitive string replace
                    new_txt = re.sub(r'\\.dae', '.obj', new_txt, flags=re.IGNORECASE)

                # write temp file in the same directory so relative mesh paths resolve
                tf = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', dir=str(urdf_path.parent), suffix='.xml')
                tf.write(new_txt)
                tf.close()
                temp_path = tf.name
                input_filename = os.path.basename(temp_path)

        try:
            model = mujoco.MjModel.from_xml_path(input_filename)
            mujoco.mj_saveLastXML(str(out_path), model)
        finally:
            # cleanup temporary file if any
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
    finally:
        os.chdir(cwd)


def main():
    parser = argparse.ArgumentParser(description="Convert URDF to MuJoCo MJCF XML")
    parser.add_argument("urdf", type=Path, help="Path to the input URDF file")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="Path to the output MJCF XML file (default: same name, .xml)",
    )
    args = parser.parse_args()

    urdf_path: Path = args.urdf
    out_path: Path = args.out or urdf_path.with_suffix(".xml")

    urdf_to_mjcf(urdf_path, out_path)
    print(f"Saved MuJoCo XML to: {out_path}")


if __name__ == "__main__":
    main()
