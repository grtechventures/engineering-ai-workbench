"""Bounded declarative 3D scenes. No script, URL, texture or loader fields."""
import math

def validate_scene(scene):
    def fail(): raise ValueError('Invalid 3D scene: use bounded geometry without scripts or external assets')
    def number(v):
        if type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1_000_000:fail()
    def vector(v):
        if not isinstance(v,list) or len(v)!=3:fail()
        for x in v:number(x)
    if not isinstance(scene,dict) or set(scene)-{'version','title','units','objects'}:fail()
    if scene.get('version')!=1:fail()
    for k in ('title','units'):
        if not isinstance(scene.get(k),str) or not 1<=len(scene[k])<=100:fail()
    objects=scene.get('objects')
    if not isinstance(objects,list) or not 1<=len(objects)<=100:fail()
    vertices=faces=0
    import re
    for o in objects:
        if not isinstance(o,dict):fail()
        kind=o.get('type')
        fields={'box':{'size'},'sphere':{'radius'},'cylinder':{'radius','height'},'line':{'points'},'mesh':{'vertices','faces'}}
        if kind not in fields or set(o)-({'type','color','position'}|fields[kind]):fail()
        if not isinstance(o.get('color','#5ab5ba'),str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',o.get('color','#5ab5ba')):fail()
        vector(o.get('position',[0,0,0]))
        if kind=='box':
            vector(o.get('size'))
            if any(x<=0 for x in o['size']):fail()
        if kind in ('sphere','cylinder'):
            for k in ('radius','height') if kind=='cylinder' else ('radius',):
                number(o.get(k))
                if o[k]<=0:fail()
        if kind in ('line','mesh'):
            vs=o.get('points' if kind=='line' else 'vertices')
            if not isinstance(vs,list) or not 2<=len(vs)<=5000:fail()
            vertices+=len(vs)
            for v in vs:vector(v)
            if kind=='mesh':
                fs=o.get('faces')
                if not isinstance(fs,list) or not 1<=len(fs)<=10000:fail()
                faces+=len(fs)
                for f in fs:
                    if not isinstance(f,list) or len(f)!=3 or any(type(i)!=int or not 0<=i<len(vs) for i in f):fail()
        if vertices>5000 or faces>10000:fail()
    return scene

SCENE_GUIDANCE = '''For interactive 3D sketches, write scene3d inside /outputs/result.json.
scene3d schema: {"version":1,"title":"Sketch","units":"user-specified units or illustrative units","objects":[{"type":"box","size":[2,1,1],"position":[0,0,0],"color":"#5ab5ba"}]}.
Object types: box(size xyz), sphere(radius), cylinder(radius,height; Y axis), line(points xyz arrays), mesh(vertices xyz arrays, faces triangle index arrays). Only type,color,position and those type-specific fields are allowed. Position is optional. No URLs, scripts, textures, HTML or external assets. Maximum 100 objects, 5000 total vertices/line points and 10000 triangles; finite coordinates bounded to +/-1000000. Use Python standard library/numpy to generate geometry. Three.js renders it in the browser, not Python. State assumptions; do not invent engineering dimensions. For illustrative sketches explicitly label illustrative units. Write json.dump({"summary": "description", "scene3d": scene}, file). Mesh faces must each have exactly three indices, never four. Convert all input dimensions into the declared scene units before generating vertices (1 inch = 0.0254 meters; 1 mm = 0.001 meters). Include summary in result.json. This is visualization, not CAD or a simulation solver.'''


def normalize_scene_output(payload):
    """Recognize standalone scenes without altering the saved artifact."""
    if not isinstance(payload, dict):
        return payload
    if 'scene3d' in payload:
        validate_scene(payload['scene3d'])
    elif {'version', 'objects'} <= payload.keys():
        return {'scene3d': validate_scene(payload)}
    return payload
