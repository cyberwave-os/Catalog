"""Render the exported OBJ/MTL geometry plus the URDF collision boxes (wireframe overlay).
Run with: Blender --background --python this_file.py. Uses a new scene.
Adapted from Rail_Bogie_Small/source/render_preview.py.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import bpy
from mathutils import Vector

ASSET_DIR = Path(__file__).resolve().parents[1]
ASSET_NAME = "server_rack_42u"

def srgb_to_linear(v):
    return v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4

def main():
    scene=bpy.data.scenes.new('Server rack export preview')
    bpy.context.window.scene=scene
    tree=ET.parse(ASSET_DIR/f'urdf/{ASSET_NAME}.urdf')
    all_points=[]
    for link in tree.findall('link'):
        visual=link.find('visual/geometry/mesh')
        if visual is None: continue
        path=(ASSET_DIR/'urdf'/visual.get('filename')).resolve()
        mats={}; current=None
        for line in path.with_suffix('.mtl').read_text().splitlines():
            p=line.split()
            if not p: continue
            if p[0]=='newmtl':
                current=bpy.data.materials.new(p[1]); current.use_nodes=True; mats[p[1]]=current
            if current is None: continue
            shader=next(n for n in current.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            if p[0]=='Kd': shader.inputs['Base Color'].default_value=tuple(srgb_to_linear(float(v)) for v in p[1:4])+(1,)
            if p[0]=='Ks': shader.inputs['Metallic'].default_value=float(p[1])
            if p[0]=='Ns': shader.inputs['Roughness'].default_value=max(.05,1-float(p[1])/250)
            if p[0]=='d' and float(p[1])<1:
                shader.inputs['Alpha'].default_value=float(p[1])
                try: current.blend_method='BLEND'
                except Exception: pass
        vertices=[]; faces=[]; material_names=[]; current='default_material'
        for line in path.read_text().splitlines():
            p=line.split()
            if not p: continue
            if p[0]=='v': vertices.append(tuple(map(float,p[1:4])))
            elif p[0]=='usemtl': current=p[1]
            elif p[0]=='f':
                faces.append(tuple(int(v.split('/')[0])-1 for v in p[1:])); material_names.append(current)
        mesh=bpy.data.meshes.new(link.get('name')); mesh.from_pydata(vertices,[],faces); mesh.update()
        keys=list(mats)
        for material in mats.values(): mesh.materials.append(material)
        for polygon,name in zip(mesh.polygons,material_names): polygon.material_index=keys.index(name)
        obj=bpy.data.objects.new(link.get('name'),mesh); scene.collection.objects.link(obj)
        all_points.extend(Vector(v) for v in vertices)
        # Collision boxes as wireframes so the primitive fit can be checked by eye.
        wire=bpy.data.materials.new('collision_wire'); wire.use_nodes=True
        emit=next(n for n in wire.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        emit.inputs['Base Color'].default_value=(0.1,0.9,0.3,1); emit.inputs['Emission Color'].default_value=(0.1,0.9,0.3,1); emit.inputs['Emission Strength'].default_value=2
        for collision in link.findall('collision'):
            box=collision.find('geometry/box')
            if box is None: continue
            size=Vector(map(float,box.get('size').split())); centre=Vector(map(float,collision.find('origin').get('xyz').split()))
            bpy.ops.mesh.primitive_cube_add(size=1,location=centre)
            cube=bpy.context.active_object; cube.name=collision.get('name'); cube.scale=size
            cube.data.materials.append(wire)
            mod=cube.modifiers.new('wire','WIREFRAME'); mod.thickness=0.006; mod.use_relative_offset=False
    lo=Vector(min(p[i] for p in all_points) for i in range(3)); hi=Vector(max(p[i] for p in all_points) for i in range(3))
    center=(lo+hi)/2
    camera=bpy.data.cameras.new('Preview camera'); obj=bpy.data.objects.new('Preview camera',camera); scene.collection.objects.link(obj)
    obj.location=center+Vector((3.2,-2.6,1.6)); obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    camera.type=next(i.identifier for i in camera.bl_rna.properties['type'].enum_items if i.identifier=='ORTHO'); camera.ortho_scale=2.6; scene.camera=obj
    for name,offset,power,size in [('Key',(2.5,-2,3),900,3),('Fill',(-2,-1.5,2),500,3),('Rim',(-1,2.5,2.5),900,3)]:
        kind=next(i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items if i.identifier=='AREA')
        light=bpy.data.lights.new(name,kind); light.energy=power; light.size=size
        obj=bpy.data.objects.new(name,light); scene.collection.objects.link(obj); obj.location=center+Vector(offset); obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
    world=bpy.data.worlds.new('Preview world'); scene.world=world; world.use_nodes=True
    bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND'); bg.inputs[0].default_value=(.07,.085,.11,1); bg.inputs[1].default_value=.5
    for engine in ('BLENDER_EEVEE_NEXT','BLENDER_EEVEE'):
        try: scene.render.engine=engine; break
        except TypeError: pass
    scene.render.resolution_x=1000; scene.render.resolution_y=1400; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format=next(i.identifier for i in scene.render.image_settings.bl_rna.properties['file_format'].enum_items if i.identifier=='PNG')
    (ASSET_DIR/'preview').mkdir(exist_ok=True)
    scene.render.filepath=str(ASSET_DIR/f'preview/{ASSET_NAME}.png')
    bpy.ops.render.render(write_still=True)

if __name__=='__main__': main()
