
# RayLvl (raylib)

Author: **@jabbadablack**  
Blender add‑on for exporting levels you can load from **any raylib binding**—C (clang/gcc), C++, Python, Rust, Go, C#, Zig, Java, etc.

This add‑on writes:
- **`level.glb`** — a single GLB scene you can load with raylib’s `LoadModel()`.
- **`level.json`** — a small manifest with nodes, Y‑up transforms (`Vector3`/`Quaternion` field names), custom props, and optional local‑space mesh colliders.

> Why GLB+JSON? GLB carries renderable geometry/materials that raylib can draw, while JSON carries your **gameplay metadata** (spawns, triggers, etc.) in a language‑agnostic way.

---

## Quick Start

1) Save the add‑on to your repo as `raylvl.py`.  
2) In Blender: **Edit → Preferences → Add‑ons → Install…**, select the script, enable it.  
3) Export via **File → Export → Level (raylib)**.  
4) You’ll get `level.glb` + `level.json`. Load the GLB with raylib in your language of choice, and parse the JSON to place gameplay objects.

---

## Export Options

- **Selection Only** — export only selected objects.
- **Include Mesh Colliders (JSON)** — exports per‑mesh local triangles in **object‑local** space.
- **Apply Modifiers (for colliders)** — bakes evaluated modifiers.
- **Unit Scale** — multiplies positions and scales at export time.
- **Export GLB** — writes a GLB usable with `LoadModel()` in all raylib bindings.

**Coordinate system:** Blender is **Z‑up, right‑handed**; raylib is **Y‑up, right‑handed**. The exporter rotates **−90° around +X** so Blender’s Z becomes raylib’s Y. The JSON you get is already Y‑up.

---

## Files & Schema

### `level.glb`
- Loadable with `LoadModel("level.glb")` in raylib (C API mirrored across bindings).

### `level.json` (manifest)
```json
{
  "schema": "raylib.level/1.0",
  "coordinateSystem": "Y_UP_RIGHT",
  "unitScale": 1.0,
  "glb": "level.glb",
  "nodes": [
    {
      "name": "Spawn01",
      "kind": "spawner",
      "transform": {
        "position": {"x":0,"y":1,"z":0},
        "rotation": {"x":0,"y":0,"z":0,"w":1},
        "scale":    {"x":1,"y":1,"z":1}
      },
      "props": { "team": 1 },
      "collider": {
        "vertices": [[x,y,z], ...],
        "triangles": [[i0,i1,i2], ...]
      }
    }
  ]
}
```

- `nodes[*].collider` is **optional** and local to the mesh. Instance it by applying the node transform on your side.

---

## Loading the GLB

All bindings share the same idea: create a 3D camera, call `LoadModel("level.glb")`, and draw it in a 3D pass.

**C (clang/gcc)**
```c
#include "raylib.h"
int main(void) {
    InitWindow(1280, 720, "level");
    Camera3D cam = {0};
    cam.position = (Vector3){6,6,6};
    cam.target   = (Vector3){0,1,0};
    cam.up       = (Vector3){0,1,0};
    cam.fovy = 60; cam.projection = CAMERA_PERSPECTIVE;

    Model level = LoadModel("level.glb");
    SetTargetFPS(60);
    while (!WindowShouldClose()) {
        BeginDrawing(); ClearBackground(RAYWHITE);
        BeginMode3D(cam);
        DrawModel(level, (Vector3){0,0,0}, 1.0f, WHITE);
        EndMode3D();
        EndDrawing();
    }
    UnloadModel(level); CloseWindow(); return 0;
}
```

---

## Reading the JSON (per‑language snippets)

Pick your binding and drop one of these into your project. They only parse what the schema exposes; feel free to extend.

### C (clang/gcc) + raylib (cJSON)
```c
#include "raylib.h"
#include "cJSON.h"
#include <stdio.h>
#include <stdlib.h>

typedef struct { Vector3 position; Quaternion rotation; Vector3 scale; } NodeXform;

static int LoadLevelManifest(const char* path, NodeXform* out, int maxNodes) {
    FILE* f = fopen(path, "rb"); if (!f) return 0;
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    char* buf = (char*)malloc((size_t)len+1); fread(buf, 1, (size_t)len, f); buf[len]=0; fclose(f);
    cJSON* root = cJSON_Parse(buf); free(buf); if (!root) return 0;
    cJSON* nodes = cJSON_GetObjectItem(root, "nodes"); if (!cJSON_IsArray(nodes)) { cJSON_Delete(root); return 0; }
    int count = 0; for (cJSON* n = nodes->child; n && count < maxNodes; n = n->next) {
        cJSON* t = cJSON_GetObjectItem(n, "transform");
        cJSON* p = cJSON_GetObjectItem(t, "position");
        cJSON* r = cJSON_GetObjectItem(t, "rotation");
        cJSON* s = cJSON_GetObjectItem(t, "scale");
        out[count].position = (Vector3){ (float)cJSON_GetObjectItem(p,"x")->valuedouble,
                                         (float)cJSON_GetObjectItem(p,"y")->valuedouble,
                                         (float)cJSON_GetObjectItem(p,"z")->valuedouble };
        out[count].rotation = (Quaternion){ (float)cJSON_GetObjectItem(r,"x")->valuedouble,
                                            (float)cJSON_GetObjectItem(r,"y")->valuedouble,
                                            (float)cJSON_GetObjectItem(r,"z")->valuedouble,
                                            (float)cJSON_GetObjectItem(r,"w")->valuedouble };
        out[count].scale    = (Vector3){ (float)cJSON_GetObjectItem(s,"x")->valuedouble,
                                         (float)cJSON_GetObjectItem(s,"y")->valuedouble,
                                         (float)cJSON_GetObjectItem(s,"z")->valuedouble };
        ++count;
    }
    cJSON_Delete(root); return count;
}
```

### C++ (raylib-cpp, nlohmann/json)
```cpp
#include "raylib-cpp.hpp"
#include <nlohmann/json.hpp>
#include <fstream>
struct NodeXform { ::Vector3 p, s; ::Quaternion q; };
std::vector<NodeXform> load_manifest(const std::string& path){
    std::ifstream f(path); nlohmann::json j; f >> j; std::vector<NodeXform> out;
    for (auto& n : j["nodes"]) {
        auto& t = n["transform"];
        NodeXform nx;
        nx.p = { t["position"]["x"], t["position"]["y"], t["position"]["z"] };
        nx.q = { t["rotation"]["x"], t["rotation"]["y"], t["rotation"]["z"], t["rotation"]["w"] };
        nx.s = { t["scale"]["x"], t["scale"]["y"], t["scale"]["z"] };
        out.push_back(nx);
    }
    return out;
}
```

### Python (pyray / raylib-py)
```python
import json, pyray as rl
with open("level.json", "r", encoding="utf-8") as f:
    data = json.load(f)
nodes = []
for n in data["nodes"]:
    t = n["transform"]
    pos = rl.Vector3(t["position"]["x"], t["position"]["y"], t["position"]["z"])
    rot = rl.Quaternion(t["rotation"]["x"], t["rotation"]["y"], t["rotation"]["z"], t["rotation"]["w"])
    scl = rl.Vector3(t["scale"]["x"], t["scale"]["y"], t["scale"]["z"])
    nodes.append((pos, rot, scl))
```

### Rust (raylib-rs + serde)
```rust
use serde::Deserialize;
#[derive(Deserialize)] struct V3 { x:f32,y:f32,z:f32 }
#[derive(Deserialize)] struct Q { x:f32,y:f32,z:f32,w:f32 }
#[derive(Deserialize)] struct T { position:V3, rotation:Q, scale:V3 }
#[derive(Deserialize)] struct Node { transform:T }
#[derive(Deserialize)] struct Manifest { nodes: Vec<Node> }
let mf: Manifest = serde_json::from_reader(std::fs::File::open("level.json")?)?;
for n in &mf.nodes {
    let _p = &n.transform.position;
    let _q = &n.transform.rotation;
    let _s = &n.transform.scale;
}
```

### Go (raylib-go)
```go
package main
import ("encoding/json"; "os")
type V3 struct{ X, Y, Z float32 }
type Q  struct{ X, Y, Z, W float32 }
type T  struct{ Position V3; Rotation Q; Scale V3 }
type Node struct{ Transform T }
type Manifest struct{ Nodes []Node }
func loadManifest(path string) (*Manifest, error) {
    b, err := os.ReadFile(path); if err != nil { return nil, err }
    var m Manifest; if err := json.Unmarshal(b, &m); err != nil { return nil, err }
    return &m, nil
}
```

### C# (.NET, Raylib-cs)
```csharp
using System.Text.Json;
public record V3(float x, float y, float z);
public record Q(float x, float y, float z, float w);
public record T(V3 position, Q rotation, V3 scale);
public record Node(T transform);
public record Manifest(Node[] nodes);
var m = JsonSerializer.Deserialize<Manifest>(File.ReadAllText("level.json"))!;
```

### Zig (std.json)
```zig
const std = @import("std");
const V3 = struct { x: f32, y: f32, z: f32 };
const Q  = struct { x: f32, y: f32, z: f32, w: f32 };
const T  = struct { position: V3, rotation: Q, scale: V3 };
const Node = struct { transform: T };
const Manifest = struct { nodes: []Node };
pub fn loadManifest(alloc: std.mem.Allocator, path: []const u8) !Manifest {
    const data = try std.fs.cwd().readFileAlloc(alloc, path, 1 << 26);
    defer alloc.free(data);
    var p = std.json.Parser.init(alloc, .{});
    defer p.deinit();
    const tree = try p.parse(data);
    return try std.json.fromValue(Manifest, tree.root, .{ .allocator = alloc });
}
```

### Java (Jackson)
```java
public record V3(float x,float y,float z) {}
public record Q (float x,float y,float z,float w) {}
public record T (V3 position, Q rotation, V3 scale) {}
public record Node(T transform) {}
public record Manifest(java.util.List<Node> nodes) {}
// Manifest mf = new ObjectMapper().readValue(new File("level.json"), Manifest.class);
```

---

## Tips & Troubleshooting

- **Nothing shows up?** Make sure you’re drawing the model in a 3D pass (`BeginMode3D/EndMode3D`) and your camera looks at the origin (many scenes export centered at world 0).  
- **Weird orientation?** The exporter already rotates Z‑up → Y‑up; double‑check you’re not re‑rotating in code.  
- **Colliders misaligned?** They’re **object‑local**. Apply the node’s transform when building physics shapes.  
- **Animations?** GLB import is supported in raylib; animation support varies by version—test animated assets in your target build.

---

## References

- raylib cheatsheet (API overview): https://www.raylib.com/cheatsheet/cheatsheet.html  
- Models (load/draw) examples: https://www.raylib.com/examples/models/loader.html  
- GLTF/GLB example in raylib repo: search for `models_loading_gltf` in the official examples

---

## License

- Add‑on and README: **MIT**.  
- Your exported content is yours.  
- raylib is licensed separately (see the raylib repo).
