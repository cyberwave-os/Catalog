#!/usr/bin/env python3
"""
Convert a URDF to a MuJoCo MJCF XML and inject meshes from a meshes folder.

This script preprocesses a URDF to replace visual `.dae` references with `.obj` 
(only in `<mesh filename=...>`), inserts a small `<mujoco><compiler/></mujoco>` 
block if missing, runs MuJoCo to generate an initial MJCF XML, then scans a 
provided meshes folder (recursively) to populate the `<asset>` section 
(visual under `visual/` and collision under `collision/`), add parsed materials 
from .mtl files, and normalize `<worldbody>` geoms so they reference the asset names. 
Collision asset `name` attributes are prefixed with `col_` and used accordingly in 
worldbody geoms.

Usage:
  python3 urdf_to_mjcf_xml.py path/to/robot.urdf path/to/meshes_folder -o out.xml [--recursive] [--backup]

The meshes folder must contain `visual/` and `collision/` subfolders (or files
organized however you like); the script will recurse when `--recursive` is
passed.
"""
import argparse
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from collections import OrderedDict

try:
    import mujoco
except Exception:
    mujoco = None


def _local_name(tag):
    """Return the local (un-namespaced) part of an XML tag safely."""
    if not isinstance(tag, str):
        return ''
    return tag.split('}')[-1] if '}' in tag else tag


def parse_mtl_file(mtl_path):
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
                    elif key in ('Ns','Ni') and len(parts) >= 2:
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
    Kd = props.get('Kd')
    Ks = props.get('Ks')
    Ns = props.get('Ns')
    d = props.get('d', 1.0)
    specular = 0.5
    if Ks:
        try:
            specular = sum(Ks) / 3.0
        except Exception:
            specular = 0.5
    shininess = 0.25
    if Ns is not None:
        try:
            shininess = float(Ns) / 1000.0
            if shininess > 1.0:
                shininess = 1.0
        except Exception:
            shininess = 0.25
    if Kd:
        r, g, b = Kd
    else:
        r, g, b = (0.5, 0.5, 0.5)
    a = d if d is not None else 1.0
    rgba_str = '{:.6f} {:.6f} {:.6f} {:.6f}'.format(r, g, b, a)
    mat = ET.Element('material')
    mat.set('name', name)
    mat.set('specular', '{:.6f}'.format(specular))
    mat.set('shininess', '{:.6f}'.format(shininess))
    mat.set('rgba', rgba_str)
    return mat


def add_materials_to_asset(asset, materials):
    existing = set()
    for child in asset.findall('material') + asset.findall('{*}material'):
        n = child.get('name')
        if n:
            existing.add(n)
    for name, props in materials.items():
        if name in existing:
            continue
        asset.append(material_element_from_props(name, props))


def remove_meshes_from_asset(asset):
    for child in list(asset):
        if isinstance(child.tag, str) and child.tag.endswith('mesh'):
            asset.remove(child)


def reorder_geom_attribs(elem):
    orig = list(elem.attrib.items())
    new = OrderedDict()
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
    elem.attrib.clear()
    elem.attrib.update(new)


def inject_meshes_into_mjcf(xml_path, meshes_folder, recursive=False, backup=False, actuator_mode='torque'):
    base_folder = meshes_folder
    obj_files = []
    stl_files = []
    for root, dirs, files in os.walk(base_folder):
        for fn in files:
            if fn.lower().endswith('.obj'):
                obj_files.append(os.path.join(root, fn))
            elif fn.lower().endswith('.stl'):
                stl_files.append(os.path.join(root, fn))
        if not recursive:
            break

    materials = OrderedDict()
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
                    obj_material_map[rel_no_visual] = first_use
        except Exception:
            pass

    ET.register_namespace('', '')
    tree = ET.parse(xml_path)
    root = tree.getroot()
    asset = None
    for child in root:
        if _local_name(child.tag) == 'asset':
            asset = child
            break
    if asset is None:
        asset = ET.Element('asset')
        root.insert(0, asset)

    remove_meshes_from_asset(asset)

    # Ensure compiler meshdir and an <option> element follow it
    for i, child in enumerate(list(root)):
        if _local_name(child.tag) == 'compiler':
            child.set('meshdir', 'meshes/')
            # check next sibling; if it's an option, update it, else insert one
            next_idx = i + 1
            opt = None
            children = list(root)
            if next_idx < len(children):
                cand = children[next_idx]
                if _local_name(cand.tag) == 'option':
                    opt = cand
            if opt is None:
                opt = ET.Element('option')
                root.insert(next_idx, opt)
            # set the requested attributes
            opt.set('gravity', '0 0 -9.81')
            opt.set('integrator', 'implicitfast')
            break

    def create_default_element():
        d_root = ET.Element('default')
        d_robot = ET.SubElement(d_root, 'default', {'class': 'robot'})
        d_motor = ET.SubElement(d_robot, 'default', {'class': 'motor'})
        ET.SubElement(d_motor, 'joint')
        ET.SubElement(d_motor, 'motor')
        d_visual = ET.SubElement(d_robot, 'default', {'class': 'visual'})
        ET.SubElement(d_visual, 'geom', {'contype': '0', 'conaffinity': '0', 'group': '2'})
        d_collision = ET.SubElement(d_robot, 'default', {'class': 'collision'})
        ET.SubElement(d_collision, 'geom', {
            'condim': '3', 'contype': '0', 'conaffinity': '1', 'priority': '1',
            'group': '1', 'solref': '0.005 1', 'solimp': '0.99 0.999 1e-05', 'friction': '1 0.01 0.01'
        })
        return d_root

    existing_default = None
    compiler_index = None
    for i, child in enumerate(list(root)):
        if _local_name(child.tag) == 'default':
            existing_default = child
        if _local_name(child.tag) == 'compiler':
            compiler_index = i
    if existing_default is not None:
        root.remove(existing_default)
    # Insert the <default> element after <compiler>. If an <option> was
    # inserted immediately after the compiler, place <default> after the
    # option so the final order is: <compiler>, <option>, <default>.
    insert_at = 0
    if compiler_index is not None:
        children = list(root)
        insert_at = compiler_index + 1
        if insert_at < len(children):
            cand = children[insert_at]
            if isinstance(cand.tag, str) and cand.tag.endswith('option'):
                insert_at += 1
    root.insert(insert_at, create_default_element())

    if materials:
        add_materials_to_asset(asset, materials)

    added_files = set()
    for p in sorted(obj_files):
        rel = os.path.relpath(p, base_folder).replace(os.path.sep, '/')
        rel_no_visual = rel[len('visual/'):] if rel.startswith('visual/') else rel
        if '/' not in rel_no_visual:
            continue
        file_attr = 'visual/' + rel_no_visual
        if file_attr in added_files:
            continue
        name = os.path.splitext(os.path.basename(rel_no_visual))[0]
        m = ET.Element('mesh')
        m.set('name', name)
        m.set('file', file_attr)
        mat = obj_material_map.get(rel_no_visual)
        if mat:
            m.set('material', mat)
        asset.append(m)
        added_files.add(file_attr)

    for p in sorted(stl_files):
        rel = os.path.relpath(p, base_folder).replace(os.path.sep, '/')
        rel_no_collision = rel[len('collision/'):] if rel.startswith('collision/') else (rel[len('visual/'):] if rel.startswith('visual/') else rel)
        file_attr = 'collision/' + rel_no_collision
        if file_attr in added_files:
            continue
        name = os.path.splitext(os.path.basename(rel_no_collision))[0]
        m = ET.Element('mesh')
        m.set('name', 'col_' + name)
        m.set('file', file_attr)
        asset.append(m)
        added_files.add(file_attr)

    # Remove redundant content_type attributes and build asset_meshes
    asset_meshes = []
    for child in asset:
        if _local_name(child.tag) == 'mesh':
            # drop content_type if present
            if 'content_type' in child.attrib:
                del child.attrib['content_type']
            f = child.get('file')
            if not f:
                continue
            f = f.replace('\\', '/')
            filename = os.path.basename(f)
            name_attr = child.get('name')
            base = name_attr if name_attr else os.path.splitext(filename)[0]
            parent = f.split('/')[0] if '/' in f else None
            ext = os.path.splitext(filename)[1].lower()
            logical = re.sub(r'^col_', '', base)
            asset_meshes.append({'file': f, 'filename': filename, 'basename': base, 'logical': logical, 'parent': parent, 'ext': ext})

    world = None
    for child in root:
        if _local_name(child.tag) == 'worldbody':
            world = child
            break

    # Ensure worldbody is wrapped in a robot body with a freejoint (floating base).
    # If the first child is already a body with childclass="robot" and contains
    # a freejoint, we leave it alone. Otherwise, wrap the existing children.
    if world is not None:
        children = list(world)
        need_wrap = True
        if children:
            first = children[0]
            if _local_name(first.tag) == 'body' and first.get('childclass') == 'robot':
                # check for a freejoint inside
                if any(_local_name(c.tag) == 'freejoint' for c in first):
                    need_wrap = False
        if need_wrap:
            wrapper = ET.Element('body')
            wrapper.set('pos', '0 0 0')
            wrapper.set('quat', '1 0 0 0')
            wrapper.set('childclass', 'robot')
            ET.SubElement(wrapper, 'freejoint').set('name', 'floating_base')
            # move existing children into wrapper
            for c in children:
                world.remove(c)
                wrapper.append(c)
            world.append(wrapper)

    # Ensure the root <mujoco> model attribute matches the xml filename (no extension)
    try:
        model_name = os.path.splitext(os.path.basename(xml_path))[0]
        if model_name:
            root.set('model', model_name)
    except Exception:
        pass

    if world is not None and asset_meshes:
        basename_map = {}
        parent_map = {}
        obj_map = {}
        stl_map = {}
        for m in asset_meshes:
            key = m.get('logical', m['basename'])
            basename_map.setdefault(key, []).append(m)
            if m['parent']:
                parent_map.setdefault(m['parent'], []).append(m)
            if m['ext'] == '.obj':
                obj_map.setdefault(key, []).append(m)
            if m['ext'] == '.stl':
                stl_map.setdefault(key, []).append(m)

        coll_attrs = ('contype', 'conaffinity', 'group', 'density', 'condim', 'priority', 'solref', 'solimp', 'friction')

        for elem in world.iter():
            if not isinstance(elem.tag, str) or not elem.tag.endswith('geom'):
                continue
            if elem.get('type') != 'mesh' and elem.get('mesh') is None:
                continue
            is_collision = any(k in elem.attrib for k in coll_attrs)
            current = elem.get('mesh')
            current_key = re.sub(r'^col_', '', current) if current else None
            chosen_asset = None
            if is_collision:
                if current_key and current_key in stl_map and stl_map[current_key]:
                    chosen_asset = stl_map[current_key][0]
                if chosen_asset is None and current_key and current_key in basename_map:
                    for cand in basename_map[current_key]:
                        if cand['ext'] == '.stl':
                            chosen_asset = cand
                            break
                if chosen_asset is None and current_key and current_key in parent_map:
                    for cand in parent_map[current_key]:
                        if cand['ext'] == '.stl':
                            chosen_asset = cand
                            break
            else:
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

            if chosen_asset is None and current_key:
                for b, lst in basename_map.items():
                    if b.startswith(current_key + '_'):
                        for cand in lst:
                            if (not is_collision and cand['ext'] == '.obj') or (is_collision and cand['ext'] == '.stl'):
                                chosen_asset = cand
                                break
                        if chosen_asset:
                            break
                if chosen_asset is None:
                    for b, lst in basename_map.items():
                        if current_key and current_key in b:
                            for cand in lst:
                                if (not is_collision and cand['ext'] == '.obj') or (is_collision and cand['ext'] == '.stl'):
                                    chosen_asset = cand
                                    break
                            if chosen_asset:
                                break

            if chosen_asset is not None:
                elem.set('mesh', chosen_asset['basename'])
                if chosen_asset['ext'] == '.stl':
                    elem.set('class', 'collision')
                else:
                    elem.set('class', 'visual')
            else:
                elem.set('class', 'collision' if is_collision else 'visual')

            for k in coll_attrs:
                if k in elem.attrib:
                    del elem.attrib[k]

            reorder_geom_attribs(elem)

        parent_of = {}
        for p in root.iter():
            for c in list(p):
                parent_of[c] = p

        existing_geoms = {}
        for g in world.iter():
            if not isinstance(g.tag, str) or not g.tag.endswith('geom'):
                continue
            meshname = g.get('mesh')
            if not meshname:
                continue
            body = parent_of.get(g)
            while body is not None and not (isinstance(body.tag, str) and body.tag.endswith('body')):
                body = parent_of.get(body)
            existing_geoms.setdefault(meshname, []).append((g, body))
            logical = re.sub(r'^col_', '', meshname)
            if logical != meshname:
                existing_geoms.setdefault(logical, []).append((g, body))

    # If the MJCF contains no <inertial> elements at all, add simple
    # inertial blocks before each joint. Mass starts at 20 and is
    # reduced by 10% for each subsequent unique joint/body.
    try:
        any_inertial = any(_local_name(e.tag) == 'inertial' for e in root.iter())
    except Exception:
        any_inertial = False

    if (not any_inertial) and (world is not None):
        # Build parent map to locate the body that contains a joint
        parent_of = {}
        for p in root.iter():
            for c in list(p):
                parent_of[c] = p

        assigned_bodies = set()
        base_mass = 20.0
        for j in world.iter():
            if _local_name(j.tag) != 'joint':
                continue
            # find enclosing body for this joint
            body = parent_of.get(j)
            while body is not None and not (isinstance(body.tag, str) and body.tag.endswith('body')):
                body = parent_of.get(body)
            if body is None:
                continue
            # skip if this body already has an inertial child
            has_in = any(_local_name(ch.tag) == 'inertial' for ch in list(body))
            if has_in:
                continue

            # compute mass: reduce 10% per previously assigned body
            mass = base_mass * (0.9 ** len(assigned_bodies))
            # create inertial element and insert before the joint
            inert = ET.Element('inertial')
            inert.set('pos', '0 0 0')
            # round mass to a sensible number of decimals
            inert.set('mass', ('%g' % round(mass, 6)))
            inert.set('diaginertia', '0.01 0.01 0.01')

            # insert inertial before joint element inside the body
            try:
                children = list(body)
                idx = children.index(j)
                body.insert(idx, inert)
            except Exception:
                # fallback: prepend
                body.insert(0, inert)

            assigned_bodies.add(id(body))

        groups = {}
        for m in asset_meshes:
            rootname = re.sub(r'_[0-9]+$', '', m['logical'])
            groups.setdefault(rootname, []).append(m)

        def find_body_for_root(rootname):
            for member in groups[rootname]:
                key = member['logical']
                if key in existing_geoms and existing_geoms[key]:
                    for (_, body) in existing_geoms[key]:
                        if body is not None:
                            return body
            for b in world.iter():
                if not isinstance(b.tag, str) or not b.tag.endswith('body'):
                    continue
                name = b.get('name','')
                if rootname in name:
                    return b
            return world

        for rootname, members in groups.items():
            target_body = find_body_for_root(rootname)
            src_pos = None
            src_quat = None
            for member in members:
                key = member['logical']
                if key in existing_geoms and existing_geoms[key]:
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
                if key in existing_geoms:
                    continue
                newg = ET.Element('geom')
                newg.set('type', 'mesh')
                newg.set('mesh', bn)
                newg.set('class', 'collision' if member['ext'] == '.stl' else 'visual')
                if src_pos:
                    newg.set('pos', src_pos)
                if src_quat:
                    newg.set('quat', src_quat)
                reorder_geom_attribs(newg)
                try:
                    children = list(target_body)
                except Exception:
                    children = []
                insert_idx = None
                for i, ch in enumerate(children):
                    if not isinstance(ch.tag, str):
                        continue
                    if ch.tag.endswith('geom') and ch.get('class') == 'collision':
                        insert_idx = i + 1
                if insert_idx is None:
                    for i, ch in enumerate(children):
                        if not isinstance(ch.tag, str):
                            continue
                        if ch.tag.endswith('joint') or ch.tag.endswith('inertial'):
                            insert_idx = i + 1
                if insert_idx is None:
                    target_body.append(newg)
                else:
                    target_body.insert(insert_idx, newg)
                existing_geoms.setdefault(bn, []).append((newg, target_body))
                logical = re.sub(r'^col_', '', bn)
                if logical != bn:
                    existing_geoms.setdefault(logical, []).append((newg, target_body))

    # Build actuator block: one motor per joint found under <worldbody>.
    # Remove any existing top-level <actuator> then insert a new one after <worldbody>.
    try:
        for child in list(root):
            if _local_name(child.tag) == 'actuator':
                root.remove(child)
        if world is not None:
            actuator = ET.Element('actuator')
            for j in world.iter():
                if _local_name(j.tag) != 'joint':
                    continue
                jname = j.get('name')
                if not jname:
                    continue

                # Read and remove joint ranges if present
                jr = None
                if j.get('range') is not None:
                    jr = j.get('range')
                    j.attrib.pop('range', None)

                jf = None
                for attr_name in ('actuatorfrcrange', 'actuatorfrc_range', 'forcerange', 'actuator_force_range'):
                    if j.get(attr_name) is not None:
                        jf = j.get(attr_name)
                        j.attrib.pop(attr_name, None)
                        break

                if actuator_mode == 'position':
                    pos = ET.Element('position')
                    pos.set('name', jname + '_ctrl')
                    pos.set('joint', jname)
                    # defaults for position controller gains
                    pos.set('kp', '200')
                    pos.set('kv', '20')
                    if jr:
                        pos.set('ctrlrange', jr)
                    actuator.append(pos)
                else:
                    motor = ET.Element('motor')
                    motor.set('name', jname + '_ctrl')
                    motor.set('joint', jname)
                    motor.set('gear', '100.0')
                    if jr:
                        motor.set('ctrlrange', jr)
                    if jf:
                        motor.set('forcerange', jf)
                    motor.set('class', 'motor')
                    actuator.append(motor)

            if len(actuator):
                children = list(root)
                try:
                    idx = children.index(world)
                except ValueError:
                    idx = None
                if idx is None:
                    root.append(actuator)
                else:
                    root.insert(idx + 1, actuator)
    except Exception:
        pass

    if backup:
        bak = xml_path + '.bak'
        shutil.copy2(xml_path, bak)
        print('Backup written to', bak)

    # Clean up whitespace-only text/tail nodes so pretty-printer doesn't
    # introduce excessive blank lines, then pretty-print with minidom.
    def _strip_whitespace_nodes(e):
        if e is None:
            return
        if e.text is not None and e.text.strip() == '':
            e.text = None
        for c in list(e):
            _strip_whitespace_nodes(c)
            if c.tail is not None and c.tail.strip() == '':
                c.tail = None

    try:
        _strip_whitespace_nodes(root)
        xml_bytes = ET.tostring(root, encoding='utf-8', method='xml')
        from xml.dom import minidom
        parsed = minidom.parseString(xml_bytes)
        pretty = parsed.toprettyxml(indent='  ')
        # Collapse runs of blank lines introduced by different pretty-printers
        pretty = re.sub(r"\n\s*\n+", "\n", pretty)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(pretty)
    except Exception:
        # fallback: write the compact bytes
        xml_bytes = ET.tostring(root, encoding='utf-8', method='xml')
        with open(xml_path, 'wb') as f:
            f.write(xml_bytes)


def main():
    parser = argparse.ArgumentParser(description='Convert URDF to MJCF and inject meshes')
    parser.add_argument('urdf', type=Path, help='Path to input URDF')
    parser.add_argument('meshes', help='Folder containing meshes (visual/ and collision/)')
    parser.add_argument('-o', '--out', type=Path, default=None, help='Output MJCF xml path')
    parser.add_argument('--recursive', action='store_true')
    parser.add_argument('--backup', action='store_true')
    parser.add_argument('--actuator-mode', choices=['torque', 'position'], default='torque', help='Generate torque (motor) or position actuators')
    args = parser.parse_args()

    urdf_path = args.urdf.resolve()
    meshes_folder = os.path.abspath(args.meshes)
    out_path = (args.out or urdf_path.with_suffix('.xml')).resolve()

    if not urdf_path.exists():
        print('URDF not found:', urdf_path, file=sys.stderr)
        sys.exit(2)
    if not os.path.isdir(meshes_folder):
        print('Meshes folder not found or not a directory:', meshes_folder, file=sys.stderr)
        sys.exit(3)

    original_txt = urdf_path.read_text(encoding='utf-8')
    input_filename = urdf_path.name
    temp_path = None
    if '<mujoco' not in original_txt.lower():
        m = re.search(r'(<robot[^>]*>)', original_txt, flags=re.IGNORECASE)
        if m:
            insert = ("\n  <mujoco>\n    <compiler discardvisual=\"false\" meshdir=\"meshes/visual/\"/>\n  </mujoco>\n")
            new_txt = original_txt[: m.end()] + insert + original_txt[m.end():]
            try:
                root_et = ET.fromstring(new_txt)
                changed = False
                for el in root_et.iter():
                    tag = el.tag
                    local = tag.split('}')[-1] if '}' in tag else tag
                    if local.lower() != 'mesh':
                        continue
                    fn = el.get('filename')
                    if fn and (fn.lower().endswith('.dae') or '.dae' in fn.lower()):
                        if fn.lower().endswith('.dae'):
                            newfn = fn[:-4] + '.obj'
                        else:
                            newfn = re.sub(r'\\.dae', '.obj', fn, flags=re.IGNORECASE)
                        el.set('filename', newfn)
                        changed = True
                if changed:
                    new_txt = ET.tostring(root_et, encoding='unicode')
            except Exception:
                new_txt = re.sub(r'\\.dae', '.obj', new_txt, flags=re.IGNORECASE)
            tf = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', dir=str(urdf_path.parent), suffix='.xml')
            tf.write(new_txt)
            tf.close()
            temp_path = tf.name
            input_filename = os.path.basename(temp_path)

    if mujoco is None:
        print('ERROR: mujoco python bindings not available. Install mujoco.', file=sys.stderr)
        if temp_path:
            print('Preprocessed URDF left at:', temp_path, file=sys.stderr)
        sys.exit(4)

    cwd = os.getcwd()
    try:
        os.chdir(urdf_path.parent)
        try:
            model = mujoco.MjModel.from_xml_path(input_filename)
            mujoco.mj_saveLastXML(str(out_path), model)
        except Exception as e:
            print('ERROR: MuJoCo failed to process URDF:', e, file=sys.stderr)
            if temp_path:
                print('Preprocessed URDF left at:', temp_path, file=sys.stderr)
            raise
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
    finally:
        os.chdir(cwd)

    inject_meshes_into_mjcf(str(out_path), meshes_folder, recursive=args.recursive, backup=args.backup, actuator_mode=args.actuator_mode)
    print('Wrote cleaned MJCF to:', out_path)


if __name__ == '__main__':
    main()
