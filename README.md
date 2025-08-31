
# RayLvl

**RayLvl** is a Blender add‑on that exports your scene for **raylib** (any binding):
- **`level.glb`** — load with `LoadModel()`
- **`level.json`** — simple metadata (nodes, Y‑up transforms, custom props, optional colliders)

> Blender is Z‑up. RayLvl converts to **Y‑up (right‑handed)** for raylib.

---

## Quick Start
1. Put `RayLvl.py` in your repo. In Blender: **Edit → Preferences → Add‑ons → Install…** → pick the file → enable.
2. **File → Export → RayLvl** → choose a base name (e.g. `level`).
3. You get `level.glb` + `level.json` next to that path.

**Options:** Selection Only • Include Mesh Colliders • Apply Modifiers • Unit Scale • Export GLB

---

## Files
- **GLB**: `LoadModel("level.glb")` in all raylib bindings.
- **JSON** (tiny schema):
```json
{
  "schema":"raylib.level/1.0",
  "glb":"level.glb",
  "nodes":[
    {"name":"Spawn01","kind":"spawner",
     "transform":{"position":{"x":0,"y":1,"z":0},
                  "rotation":{"x":0,"y":0,"z":0,"w":1},
                  "scale":{"x":1,"y":1,"z":1}}}
  ]
}
```

---

## Load the GLB (raylib)
```c
// C (clang/gcc)
#include "raylib.h"
int main(){ InitWindow(800,450,"lvl"); Camera3D c={0};
c.position=(Vector3){6,6,6}; c.target=(Vector3){0,1,0}; c.up=(Vector3){0,1,0}; c.fovy=60; c.projection=CAMERA_PERSPECTIVE;
Model m=LoadModel("level.glb"); while(!WindowShouldClose()){ BeginDrawing(); ClearBackground(RAYWHITE);
BeginMode3D(c); DrawModel(m,(Vector3){0,0,0},1,WHITE); EndMode3D(); EndDrawing(); } UnloadModel(m); CloseWindow(); }
```

---

## Read the JSON (pick your binding)

### C (clang) + cJSON (tiny)
```c
#include "cJSON.h"
typedef struct { Vector3 p; Quaternion q; Vector3 s; } X;
int load(const char* path, X* out, int cap){
  FILE* f=fopen(path,"rb"); if(!f) return 0;
  fseek(f,0,SEEK_END); long n=ftell(f); fseek(f,0,SEEK_SET);
  char* b=malloc((size_t)n+1); fread(b,1,(size_t)n,f); b[n]=0; fclose(f);
  cJSON* r=cJSON_Parse(b); free(b); if(!r) return 0; cJSON* a=cJSON_GetObjectItem(r,"nodes"); int i=0;
  for(cJSON* it=a?a->child:0; it && i<cap; it=it->next,++i){
    cJSON* t=cJSON_GetObjectItem(it,"transform");
    #define G(o,k) (float)cJSON_GetObjectItem((o),(k))->valuedouble
    cJSON* P=cJSON_GetObjectItem(t,"position"); out[i].p=(Vector3){G(P,"x"),G(P,"y"),G(P,"z")};
    cJSON* R=cJSON_GetObjectItem(t,"rotation"); out[i].q=(Quaternion){G(R,"x"),G(R,"y"),G(R,"z"),G(R,"w")};
    cJSON* S=cJSON_GetObjectItem(t,"scale");    out[i].s=(Vector3){G(S,"x"),G(S,"y"),G(S,"z")};
    #undef G
  } cJSON_Delete(r); return i;
}
```

### C++ (nlohmann/json)
```cpp
#include <nlohmann/json.hpp> #include <fstream>
struct V3{float x,y,z;}; struct Q{float x,y,z,w;};
struct X{V3 p,s; Q q;};
std::vector<X> load(std::string p){
  std::ifstream f(p); nlohmann::json j; f>>j; std::vector<X> out;
  for(auto& n: j["nodes"]) { auto&t=n["transform"]; X x;
    x.p={t["position"]["x"],t["position"]["y"],t["position"]["z"]};
    x.q={t["rotation"]["x"],t["rotation"]["y"],t["rotation"]["z"],t["rotation"]["w"]};
    x.s={t["scale"]["x"],t["scale"]["y"],t["scale"]["z"]};
    out.push_back(x); } return out;
}
```

### Python (pyray)
```python
import json, pyray as rl
nodes=[(rl.Vector3(t["position"]["x"],t["position"]["y"],t["position"]["z"]),
        rl.Quaternion(t["rotation"]["x"],t["rotation"]["y"],t["rotation"]["z"],t["rotation"]["w"]),
        rl.Vector3(t["scale"]["x"],t["scale"]["y"],t["scale"]["z"])) 
       for t in (n["transform"] for n in json.load(open("level.json"))["nodes"])]
```

### Rust (serde)
```rust
use serde::Deserialize; #[derive(Deserialize)] struct V3{ x:f32,y:f32,z:f32 }
#[derive(Deserialize)] struct Q{ x:f32,y:f32,z:f32,w:f32 } #[derive(Deserialize)] struct T{ position:V3,rotation:Q,scale:V3 }
#[derive(Deserialize)] struct N{ transform:T } #[derive(Deserialize)] struct M{ nodes:Vec<N> }
let m: M = serde_json::from_reader(std::fs::File::open("level.json")?)?;
```

### Go
```go
type V3 struct{ X,Y,Z float32 } ; type Q struct{ X,Y,Z,W float32 }
type T struct{ Position V3; Rotation Q; Scale V3 }
type N struct{ Transform T } ; type M struct{ Nodes []N }
var m M; _ = json.Unmarshal([]byte(os.ReadFile("level.json")),&m)
```

### C# (.NET)
```csharp
public record V3(float x,float y,float z); public record Q(float x,float y,float z,float w);
public record T(V3 position,Q rotation,V3 scale); public record N(T transform);
var m = System.Text.Json.JsonSerializer.Deserialize<Dictionary<string,object>>(File.ReadAllText("level.json"));
```

---

## Tips
- Draw in a 3D pass (`BeginMode3D`/`EndMode3D`).
- JSON colliders are **object‑local**; apply node transforms when building physics shapes.
- If it’s rotated wrong, make sure you didn’t rotate again in code—RayLvl already outputs Y‑up.

---

License: **MIT**
