
import bpy, json, os
from math import radians
from mathutils import Matrix
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, FloatProperty, IntProperty

def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _depsgraph(ctx): return ctx.evaluated_depsgraph_get()
def _basis_to_raylib(): return Matrix.Rotation(radians(-90.0), 4, 'X')

def _world_to_raylib(obj, basis):
    m = basis @ obj.matrix_world
    loc, rot, scl = m.decompose()
    return ([float(loc.x), float(loc.y), float(loc.z)],
            [float(rot.x), float(rot.y), float(rot.z), float(rot.w)],
            [float(scl.x), float(scl.y), float(scl.z)])

def _export_mesh_collider(obj, deps, max_v, max_t, apply_mods):
    if obj.type != 'MESH': return None
    src = obj.evaluated_get(deps) if apply_mods else obj
    mesh = src.to_mesh(preserve_all_data_layers=False, depsgraph=deps) if apply_mods else obj.to_mesh()
    try:
        mesh.calc_loop_triangles()
        verts, tris = mesh.vertices, mesh.loop_triangles
        if len(verts) > max_v: raise RuntimeError(f"Collider vertex count {len(verts)} > {max_v} on {obj.name}.")
        if len(tris)  > max_t: raise RuntimeError(f"Collider tri count {len(tris)} > {max_t} on {obj.name}.")
        out_v = [[float(v.co.x), float(v.co.y), float(v.co.z)] for v in verts]
        out_t = [[int(l.vertices[0]), int(l.vertices[1]), int(l.vertices[2])] for l in tris]
        return {"vertices": out_v, "triangles": out_t}
    finally:
        if mesh is not None: obj.to_mesh_clear()

def _props(obj):
    d = {}
    for k in obj.keys():
        if k.startswith('_'): continue
        v = obj.get(k)
        if isinstance(v, (int, float, str, bool)): d[k] = v
        elif isinstance(v, (list, tuple)):
            simple, ok = [], True
            for it in v:
                if isinstance(it, (int, float, str, bool)): simple.append(it)
                else: ok = False; break
            if ok: d[k] = simple
    return d

def _kind(obj):
    k = obj.get("kind", None)
    if isinstance(k, str) and k: return k
    n = obj.name.lower()
    if n.startswith("plat"):  return "platform"
    if n.startswith("spawn"): return "spawner"
    if n.startswith("trig"):  return "trigger"
    return obj.type.lower()

class EXPORT_OT_raylvl(Operator):
    bl_idname = "export_scene.raylvl"
    bl_label = "RayLvl"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(name="Base Filepath", subtype='FILE_PATH', default="//level")
    selection_only: BoolProperty(name="Selection Only", default=False)
    include_colliders: BoolProperty(name="Include Mesh Colliders (JSON)", default=True)
    apply_modifiers: BoolProperty(name="Apply Modifiers (for colliders)", default=True)
    max_collider_vertices: IntProperty(name="Max Collider Vertices", default=20000, min=0)
    max_collider_triangles: IntProperty(name="Max Collider Triangles", default=40000, min=0)
    unit_scale: FloatProperty(name="Unit Scale", default=1.0)
    export_glb: BoolProperty(name="Export GLB (for raylib LoadModel)", default=True)

    def execute(self, context):
        try:
            basis = _basis_to_raylib()
            deps = _depsgraph(context)
            objs = context.selected_objects if self.selection_only else context.scene.objects
            allowed = {'MESH', 'EMPTY', 'LIGHT', 'CAMERA'}
            nodes = []
            for o in objs:
                if o.type not in allowed: continue
                pos, rot, scl = _world_to_raylib(o, basis)
                if self.unit_scale != 1.0:
                    pos = [p * self.unit_scale for p in pos]
                    scl = [s * self.unit_scale for s in scl]
                node = {
                    "name": o.name,
                    "kind": _kind(o),
                    "transform": {
                        "position": {"x": pos[0], "y": pos[1], "z": pos[2]},
                        "rotation": {"x": rot[0], "y": rot[1], "z": rot[2], "w": rot[3]},
                        "scale":    {"x": scl[0], "y": scl[1], "z": scl[2]}
                    },
                    "props": _props(o),
                    "raylib": {"vectorType": "Vector3", "quatType": "Quaternion"}
                }
                if self.include_colliders and o.type == 'MESH':
                    c = _export_mesh_collider(o, deps, self.max_collider_vertices, self.max_collider_triangles, self.apply_modifiers)
                    if c is not None: node["collider"] = c
                nodes.append(node)

            data = {"schema": "raylib.level/1.0", "coordinateSystem": "Y_UP_RIGHT", "unitScale": self.unit_scale, "glb": None, "nodes": nodes}

            base = bpy.path.abspath(self.filepath)
            root, _ = os.path.splitext(base)
            json_path = root + ".json"

            if self.export_glb:
                glb_path = root + ".glb"
                _ensure_dir(glb_path)
                kw = dict(filepath=glb_path, export_format='GLB', use_selection=self.selection_only, export_yup=True, export_apply=True)
                result = bpy.ops.export_scene.gltf(**kw)
                data["glb"] = os.path.basename(glb_path)
                if result not in {'FINISHED', 'CANCELLED'}:
                    self.report({'WARNING'}, f"GLB export returned: {result}")

            _ensure_dir(json_path)
            with open(json_path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

            self.report({'INFO'}, f"RayLvl exported: {os.path.basename(json_path)}" + (f" and {data['glb']}" if data["glb"] else ""))
            return {'FINISHED'}
        except Exception as ex:
            self.report({'ERROR'}, str(ex)); return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self); return {'RUNNING_MODAL'}

def menu_func(self, context): self.layout.operator(EXPORT_OT_raylvl.bl_idname, text="RayLvl")

def register():
    bpy.utils.register_class(EXPORT_OT_raylvl)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)
    bpy.utils.unregister_class(EXPORT_OT_raylvl)

if __name__ == "__main__": register()
