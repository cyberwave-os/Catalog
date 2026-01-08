#!/usr/bin/env python3
"""
Scan a folder for visual (.obj) and collision (.stl) meshes and add them
to a MuJoCo XML file's <asset> section. For OBJ visual meshes, parse any
referenced .mtl files and add <material> entries to <asset>.

Usage:
  python3 mujoco_add_assets_from_meshes.py model.xml /path/to/meshes_folder [--recursive]

The script will modify the XML in-place (make a .bak copy). Mesh file paths
are written relative to the provided meshes folder, using forward slashes.
"""
import argparse
import os
import sys
import shutil
import xml.etree.ElementTree as ET
from collections import OrderedDict
import re


def find_asset_element(root):
    # find an <asset> element by local-name (ignore namespace)
    for child in root:
        if child.tag.endswith('asset'):
            return child
    return None


def parse_mtl_file(mtl_path):
    """Parse a .mtl file and return dict of material_name -> properties dict
    properties: {'Kd': (r,g,b), 'Ks': (r,g,b), 'Ns': float, 'd': float}
    """
    mats = OrderedDict()
    if not os.path.exists(mtl_path):
        return mats
    cur = None
    try:
        with open(mtl_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if not parts:
                    continue
                key = parts[0]
                if key == 'newmtl' and len(parts) >= 2:
                    cur = parts[1]
                    mats[cur] = {}
                elif cur is not None:
                    if key in ('Kd','Ks') and len(parts) >= 4:
                        try:
                            vals = tuple(float(x) for x in parts[1:4])
                            mats[cur][key] = vals
                        except Exception:
                            pass
                    elif key in ('Ns', 'Ni') and len(parts) >= 2:
                        try:
                            mats[cur][key] = float(parts[1])
                        except Exception:
                            pass
                    elif key in ('d','Tr') and len(parts) >= 2:
                        try:
                            mats[cur]['d'] = float(parts[1])
                        except Exception:
                            pass
    except Exception:
        pass
    return mats


def material_element_from_props(name, props):
    """Create an <material> ET.Element from parsed mtl props.
    Map Ks -> specular (avg), Ns -> shininess (normalized), Kd+d -> rgba.
    """
    Kd = props.get('Kd')
    Ks = props.get('Ks')
    Ns = props.get('Ns')
    d = props.get('d', 1.0)
    # compute specular as average of Ks or default 0.5
    specular = 0.5
    if Ks:
        try:
            specular = sum(Ks) / 3.0
        except Exception:
            specular = 0.5
    # normalize Ns (typical Ns ranges up to 1000); map to [0,1]
    shininess = 0.25
    if Ns is not None:
        try:
            shininess = float(Ns) / 1000.0
            if shininess > 1.0:
                shininess = 1.0
        except Exception:
            shininess = 0.25
    # rgba from Kd and d
    if Kd:
        r, g, b = Kd
    else:
        r, g, b = (0.5, 0.5, 0.5)
    a = d if d is not None else 1.0

    # format floats with 6 decimals like the example
    rgba_str = '{:.6f} {:.6f} {:.6f} {:.6f}'.format(r, g, b, a)
    mat = ET.Element('material')
    mat.set('name', name)
    mat.set('specular', '{:.6f}'.format(specular))
    mat.set('shininess', '{:.6f}'.format(shininess))
    mat.set('rgba', rgba_str)
    return mat


def add_materials_to_asset(asset, materials):
    # materials is dict name->props (props from parse_mtl_file)
    existing = set()
    for child in asset.findall('material') + asset.findall('{*}material'):
        n = child.get('name')
        if n:
            existing.add(n)
    for name, props in materials.items():
        if name in existing:
            continue
        mat_el = material_element_from_props(name, props)
        asset.append(mat_el)


def add_meshes_to_asset(asset, mesh_files, base_folder, tag_name='mesh', include_top_level=True, strip_prefix=None, add_prefix=None):
    # mesh_files: iterable of absolute paths
    # Add mesh elements with only 'file' and 'scale' attributes
    for p in sorted(mesh_files):
        rel_orig = os.path.relpath(p, base_folder).replace(os.path.sep, '/')
        rel = rel_orig
        # optionally strip a leading folder prefix (e.g. 'visual/')
        if strip_prefix and rel.startswith(strip_prefix):
            rel = rel[len(strip_prefix):]

        # If requested, skip top-level files (no '/')
        if not include_top_level and ('/' not in rel):
            continue

        # optionally add a prefix if missing (e.g. ensure 'collision/' prefix)
        if add_prefix and not rel.startswith(add_prefix):
            rel = add_prefix.rstrip('/') + '/' + rel

        el = ET.Element(tag_name)
        el.set('file', rel)
        el.set('scale', '1 1 1')
        asset.append(el)


def remove_meshes_from_asset(asset):
    """Remove all mesh elements from asset (by local-name)."""
    for child in list(asset):
        if isinstance(child.tag, str) and child.tag.endswith('mesh'):
            asset.remove(child)


def main():
    p = argparse.ArgumentParser(description='Add meshes and materials to a MuJoCo XML asset section')
    p.add_argument('xml', help='Path to mujoco xml file to modify')
    p.add_argument('meshes_folder', help='Folder containing visual (.obj/.mtl) and collision (.stl) meshes')
    p.add_argument('--recursive', action='store_true', help='Recurse into subdirectories')
    p.add_argument('--backup', action='store_true', help='Create a .bak backup of the original xml')
    args = p.parse_args()

    xml_path = args.xml
    base_folder = args.meshes_folder
    if not os.path.exists(xml_path):
        print('ERROR: xml file not found:', xml_path, file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(base_folder):
        print('ERROR: meshes_folder is not a directory:', base_folder, file=sys.stderr)
        sys.exit(3)

    # collect files
    obj_files = []
    stl_files = []
    for root, dirs, files in os.walk(base_folder):
        for fn in files:
            if fn.lower().endswith('.obj'):
                obj_files.append(os.path.join(root, fn))
            elif fn.lower().endswith('.stl'):
                stl_files.append(os.path.join(root, fn))
        if not args.recursive:
            break

    # parse materials by scanning obj files for mtllib lines
    materials = OrderedDict()
    # map from obj relative path (no leading visual/) to the first usemtl name found in that file
    obj_material_map = {}
    for obj in obj_files:
        try:
            with open(obj, 'r', encoding='utf-8', errors='ignore') as f:
                rel = os.path.relpath(obj, base_folder).replace(os.path.sep, '/')
                rel_no_visual = rel[len('visual/'):] if rel.startswith('visual/') else rel
                first_use = None
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    low = s.lower()
                    if low.startswith('mtllib'):
                        parts = s.split()
                        if len(parts) >= 2:
                            mtlname = parts[1].strip()
                            # resolve path relative to obj's directory
                            mtlpath = os.path.join(os.path.dirname(obj), mtlname)
                            if os.path.exists(mtlpath):
                                mats = parse_mtl_file(mtlpath)
                                for k, v in mats.items():
                                    if k not in materials:
                                        materials[k] = v
                    elif low.startswith('usemtl') and first_use is None:
                        parts = s.split()
                        if len(parts) >= 2:
                            first_use = parts[1].strip()
                if first_use:
                    # store by rel_no_visual (with folders, no leading 'visual/')
                    obj_material_map[rel_no_visual] = first_use
        except Exception:
            pass

    # parse the XML
    ET.register_namespace('', '')
    tree = ET.parse(xml_path)
    root = tree.getroot()
    asset = find_asset_element(root)
    if asset is None:
        # create asset as first child
        asset = ET.Element('asset')
        root.insert(0, asset)

    # remove any existing <mesh> elements (user requested to replace them)
    remove_meshes_from_asset(asset)

    # Ensure compiler meshdir points to '/meshes' so paths resolve correctly
    for child in root:
        if isinstance(child.tag, str) and child.tag.endswith('compiler'):
            # set meshdir to '/meshes' as requested
            # use relative meshes/ (no leading slash)
            child.set('meshdir', 'meshes/')
            break

    # Insert or replace <default> section right after <compiler>
    # Build the requested default tree
    def create_default_element():
        d_root = ET.Element('default')
        d_robot = ET.SubElement(d_root, 'default', {'class': 'robot'})
        d_motor = ET.SubElement(d_robot, 'default', {'class': 'motor'})
        ET.SubElement(d_motor, 'joint')
        ET.SubElement(d_motor, 'motor')
        # visual default
        d_visual = ET.SubElement(d_robot, 'default', {'class': 'visual'})
        ET.SubElement(d_visual, 'geom', {'contype': '0', 'conaffinity': '0', 'group': '2'})
        # collision default
        d_collision = ET.SubElement(d_robot, 'default', {'class': 'collision'})
        ET.SubElement(d_collision, 'geom', {
            'condim': '3', 'contype': '0', 'conaffinity': '1', 'priority': '1',
            'group': '1', 'solref': '0.005 1', 'solimp': '0.99 0.999 1e-05', 'friction': '1 0.01 0.01'
        })
        return d_root

    # remove existing default if present, then insert after compiler
    existing_default = None
    compiler_index = None
    for i, child in enumerate(list(root)):
        if isinstance(child.tag, str) and child.tag.endswith('default'):
            existing_default = child
        if isinstance(child.tag, str) and child.tag.endswith('compiler'):
            compiler_index = i
    if existing_default is not None:
        root.remove(existing_default)
    new_def = create_default_element()
    insert_pos = compiler_index + 1 if compiler_index is not None else 0
    root.insert(insert_pos, new_def)

    # (worldbody geom updates moved later, after meshes are added)

    # Add materials
    if materials:
        add_materials_to_asset(asset, materials)

    # Add visual (.obj) and collision (.stl) meshes using filenames only (basename)
    # Each entry will be <mesh name="<basename_noext>" content_type="..." file="<basename>" />
    added_files = set()
    for p in sorted(obj_files):
        rel = os.path.relpath(p, base_folder).replace(os.path.sep, '/')
        # make visual asset file paths relative to visual/ (e.g. visual/base/base_0.obj)
        rel_no_visual = rel[len('visual/'):] if rel.startswith('visual/') else rel
        # skip top-level obj files (require a subfolder under visual/)
        if '/' not in rel_no_visual:
            continue
        file_attr = 'visual/' + rel_no_visual
        if file_attr in added_files:
            continue
        name = os.path.splitext(os.path.basename(rel_no_visual))[0]
        m = ET.Element('mesh')
        # keep name for compatibility but reference file relative to the meshes folder
        m.set('name', name)
        m.set('content_type', 'model/obj')
        m.set('file', file_attr)
        # attach material if we parsed a usemtl from this obj
        mat = obj_material_map.get(rel_no_visual)
        if mat:
            m.set('material', mat)
        asset.append(m)
        added_files.add(file_attr)

    for p in sorted(stl_files):
        rel = os.path.relpath(p, base_folder).replace(os.path.sep, '/')
        # ensure collision mesh file paths use 'collision/' prefix
        rel_no_collision = rel[len('collision/'):] if rel.startswith('collision/') else (rel[len('visual/'):] if rel.startswith('visual/') else rel)
        file_attr = 'collision/' + rel_no_collision
        if file_attr in added_files:
            continue
        name = os.path.splitext(os.path.basename(rel_no_collision))[0]
        m = ET.Element('mesh')
        # collision meshes get a 'col_' prefix in their name attribute
        m.set('name', 'col_' + name)
        m.set('content_type', 'model/stl')
        m.set('file', file_attr)
        asset.append(m)
        added_files.add(file_attr)

    # Build a mapping from asset <mesh file="..."> entries to mesh names and types
    # Key: basename without extension (e.g. 'base_0' from 'base/base_0.obj')
    # Also collect parent-folder -> [asset dicts] for matching (e.g. parent 'base' -> [{'file':..., 'basename':...},...])
    asset_meshes = []
    for child in asset:
        if isinstance(child.tag, str) and child.tag.endswith('mesh'):
            f = child.get('file')
            if not f:
                continue
            # normalize
            f = f.replace('\\', '/')
            filename = os.path.basename(f)
            # prefer explicit name attribute if present (may include 'col_' prefix)
            name_attr = child.get('name')
            if name_attr:
                base = name_attr
            else:
                base = os.path.splitext(filename)[0]
            parent = f.split('/')[0] if '/' in f else None
            ext = os.path.splitext(filename)[1].lower()
            # logical basename without any 'col_' prefix for matching against world geoms
            logical = re.sub(r'^col_', '', base)
            asset_meshes.append({'file': f, 'filename': filename, 'basename': base, 'logical': logical, 'parent': parent, 'ext': ext})

    # Helper to reorder attributes: type, mesh, then the rest in original order
    def reorder_geom_attribs(elem):
        orig = list(elem.attrib.items())
        new = OrderedDict()
        # ensure type, mesh, class in that order
        if elem.get('type') is not None:
            new['type'] = elem.get('type')
        if elem.get('mesh') is not None:
            new['mesh'] = elem.get('mesh')
        if elem.get('class') is not None:
            new['class'] = elem.get('class')
        for k, v in orig:
            if k in ('type', 'mesh', 'class'):
                continue
            new[k] = v
        # clear and set in order
        elem.attrib.clear()
        elem.attrib.update(new)

    # Now update worldbody geoms to reference actual asset mesh basenames
    for child in root:
        if isinstance(child.tag, str) and child.tag.endswith('worldbody'):
            world = child
            break
    else:
        world = None

    if world is not None and asset_meshes:
        # build lookup structures
        basename_map = {}
        parent_map = {}
        obj_map = {}
        stl_map = {}
        for m in asset_meshes:
            # key maps by the logical basename (without col_ prefix) so we can
            # match existing worldbody geom mesh names which are typically logical.
            key = m.get('logical', m['basename'])
            basename_map.setdefault(key, []).append(m)
            if m['parent']:
                parent_map.setdefault(m['parent'], []).append(m)
            if m['ext'] == '.obj':
                obj_map.setdefault(key, []).append(m)
            if m['ext'] == '.stl':
                stl_map.setdefault(key, []).append(m)

        coll_attrs = ('contype', 'conaffinity', 'group', 'density', 'condim', 'priority', 'solref', 'solimp', 'friction')

        # iterate all geom elements
        for elem in world.iter():
            if not isinstance(elem.tag, str):
                continue
            if not elem.tag.endswith('geom'):
                continue
            # only consider mesh geoms (explicit type or mesh attr present)
            if elem.get('type') != 'mesh' and elem.get('mesh') is None:
                continue

            # detect if this geom is collision-like
            is_collision = any(k in elem.attrib for k in coll_attrs)

            current = elem.get('mesh')
            # normalize current mesh name to a logical key (strip any 'col_' prefix)
            current_key = re.sub(r'^col_', '', current) if current else None
            chosen_asset = None
            # Prefer matching by basename then by parent folder then by prefix
            if is_collision:
                # prefer stl with same basename
                if current_key and current_key in stl_map and stl_map[current_key]:
                    chosen_asset = stl_map[current_key][0]
                # else try basename_map for a stl entry
                if chosen_asset is None and current_key and current_key in basename_map:
                    for cand in basename_map[current_key]:
                        if cand['ext'] == '.stl':
                            chosen_asset = cand
                            break
                # else try parent folder matches
                if chosen_asset is None and current_key and current_key in parent_map:
                    for cand in parent_map[current_key]:
                        if cand['ext'] == '.stl':
                            chosen_asset = cand
                            break
            else:
                # visual: prefer obj entries
                if current_key and current_key in obj_map and obj_map[current_key]:
                    chosen_asset = obj_map[current_key][0]
                if chosen_asset is None and current_key and current_key in basename_map:
                    for cand in basename_map[current_key]:
                        if cand['ext'] == '.obj':
                            chosen_asset = cand
                            break
                if chosen_asset is None and current_key and current_key in parent_map:
                    for cand in parent_map[current_key]:
                        if cand['ext'] == '.obj':
                            chosen_asset = cand
                            break

            # fallback heuristics: prefix or substring match against basenames
            if chosen_asset is None and current_key:
                for b, lst in basename_map.items():
                    if b.startswith(current_key + '_'):
                        # pick an obj if possible, else any
                        for cand in lst:
                            if (not is_collision and cand['ext']=='.obj') or (is_collision and cand['ext']=='.stl'):
                                chosen_asset = cand
                                break
                        if chosen_asset:
                            break
                if chosen_asset is None:
                    for b, lst in basename_map.items():
                        if current in b:
                            for cand in lst:
                                if (not is_collision and cand['ext']=='.obj') or (is_collision and cand['ext']=='.stl'):
                                    chosen_asset = cand
                                    break
                            if chosen_asset:
                                break

            # If we found an asset, set geom@mesh to the asset file path and set class
            if chosen_asset is not None:
                # use the filename without extension for geom@mesh as requested
                elem.set('mesh', chosen_asset['basename'])
                if chosen_asset['ext'] == '.stl':
                    elem.set('class', 'collision')
                else:
                    elem.set('class', 'visual')
            else:
                # if no asset found, at least normalize class
                if is_collision:
                    elem.set('class', 'collision')
                else:
                    elem.set('class', 'visual')

            # remove collision-like attributes if present and replace with class
            for k in coll_attrs:
                if k in elem.attrib:
                    del elem.attrib[k]

            # reorder attributes as requested
            reorder_geom_attribs(elem)

        # Ensure every asset mesh has at least one geom in the worldbody.
        # Group assets by root name (strip trailing _<num> suffix) so assets like
        # 'base_0' and 'base_1' map to the same logical 'base' group and should
        # be attached to the same body.
        # Build a parent pointer map to find ancestor bodies.
        parent_of = {}
        for p in root.iter():
            for c in list(p):
                parent_of[c] = p

        # collect existing geoms by basename and note their container body
        # map keys include both the literal mesh name and the logical name
        # (without 'col_' prefix) so lookups succeed regardless of prefixing.
        existing_geoms = {}  # name_key -> list of (geom_elem, body_elem)
        for g in world.iter():
            if not isinstance(g.tag, str) or not g.tag.endswith('geom'):
                continue
            meshname = g.get('mesh')
            if not meshname:
                continue
            # find nearest ancestor body
            body = parent_of.get(g)
            while body is not None and not (isinstance(body.tag, str) and body.tag.endswith('body')):
                body = parent_of.get(body)
            existing_geoms.setdefault(meshname, []).append((g, body))
            logical = re.sub(r'^col_', '', meshname)
            if logical != meshname:
                existing_geoms.setdefault(logical, []).append((g, body))

        # group assets by root (strip trailing _<digits>) using logical basenames
        groups = {}
        for m in asset_meshes:
            rootname = re.sub(r'_[0-9]+$', '', m['logical'])
            groups.setdefault(rootname, []).append(m)

        # helper to find a body to attach to for a given root: prefer an existing
        # body that already contains a geom for this group, else find a body whose
        # name contains the root, else use the top-level world element.
        def find_body_for_root(rootname):
            # look for any existing geom bodies for members of this group
            for member in groups[rootname]:
                key = member['logical']
                if key in existing_geoms and existing_geoms[key]:
                    # return the first non-None body found
                    for (_, body) in existing_geoms[key]:
                        if body is not None:
                            return body
            # search bodies by name heuristics
            for b in world.iter():
                if not isinstance(b.tag, str):
                    continue
                if not b.tag.endswith('body'):
                    continue
                name = b.get('name','')
                if rootname in name:
                    return b
            # fallback to world
            return world

        # For each group, ensure each asset basename has a geom in the chosen body
        for rootname, members in groups.items():
            target_body = find_body_for_root(rootname)
            # try to find a source geom to copy pos/quat attributes from
            src_pos = None
            src_quat = None
            for member in members:
                key = member['logical']
                if key in existing_geoms and existing_geoms[key]:
                    # take first geom in that body if available
                    for (g_elem, g_body) in existing_geoms[key]:
                        if g_body is target_body or (target_body is world and g_body is None):
                            src_pos = g_elem.get('pos')
                            src_quat = g_elem.get('quat')
                            break
                    if src_pos is not None:
                        break

            for member in members:
                bn = member['basename']
                key = member['logical']
                # skip if this logical basename already exists anywhere (avoid duplicates)
                if key in existing_geoms:
                    continue
                # create a minimal geom inside target_body
                newg = ET.Element('geom')
                newg.set('type', 'mesh')
                newg.set('mesh', bn)
                newg.set('class', 'collision' if member['ext']=='.stl' else 'visual')
                if src_pos:
                    newg.set('pos', src_pos)
                if src_quat:
                    newg.set('quat', src_quat)
                reorder_geom_attribs(newg)
                # choose insertion index to preserve correct ordering:
                # prefer after existing collision geoms in the same body;
                # otherwise after the last joint or inertial; otherwise append.
                try:
                    children = list(target_body)
                except Exception:
                    children = []
                insert_idx = None
                # find last collision geom index
                for i, ch in enumerate(children):
                    if not isinstance(ch.tag, str):
                        continue
                    if ch.tag.endswith('geom') and ch.get('class') == 'collision':
                        insert_idx = i + 1
                # if no collision found, place after last joint or inertial
                if insert_idx is None:
                    for i, ch in enumerate(children):
                        if not isinstance(ch.tag, str):
                            continue
                        if ch.tag.endswith('joint') or ch.tag.endswith('inertial'):
                            insert_idx = i + 1
                if insert_idx is None:
                    target_body.append(newg)
                else:
                    # Element.insert exists: insert at computed index
                    target_body.insert(insert_idx, newg)

                # record it so subsequent members in same group see it
                existing_geoms.setdefault(bn, []).append((newg, target_body))
                # also register under the logical name (without 'col_')
                logical = re.sub(r'^col_', '', bn)
                if logical != bn:
                    existing_geoms.setdefault(logical, []).append((newg, target_body))

        # Do not reorder existing geom slots. New geoms are appended to the
        # target body and existing child order (joints, inertial, etc.) is preserved.

    # backup
    if args.backup:
        bak = xml_path + '.bak'
        shutil.copy2(xml_path, bak)
        print('Backup written to', bak)

    # write back (minified: no extra newlines or pretty-printing)
    try:
        # ET.tostring produces compact XML without added indentation/newlines
        xml_bytes = ET.tostring(root, encoding='utf-8', method='xml')
        with open(xml_path, 'wb') as f:
            f.write(xml_bytes)
    except Exception as e:
        print('ERROR: failed to write xml:', e, file=sys.stderr)
        sys.exit(4)

    print('Updated xml:', xml_path)


if __name__ == '__main__':
    main()
