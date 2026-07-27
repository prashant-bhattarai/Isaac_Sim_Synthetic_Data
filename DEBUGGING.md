# Debugging Log: Isaac Sim Synthetic Data Generator

Notes from building a synthetic dataset pipeline in Isaac Sim to train a
YOLO detector for fallen cardboard shipping boxes. Twelve real problems
came up during development, listed here with root cause and final fix.

## 1. GPU pegged at 100%, laptop overheating on Standalone Python boot

Running the scene through the Isaac Sim GUI was smooth. Running the exact
same scene through `python.bat` (Standalone Python API) pegged the GPU
and caused thermal throttling within a minute.

The GUI boots with a laptop-friendly performance profile by default.
`SimulationApp` does not, it boots at full path tracing and heavy
anti-aliasing unless told otherwise. Fix was passing a lightweight config
before loading any assets:

```python
config = {
    "headless": True,
    "width": 1280,
    "height": 720,
    "anti_aliasing": 0,
}
simulation_app = SimulationApp(config)
```

Also explicitly disabled DLSS (`settings.set("/rtx/post/dlss/execMode", 0)`)
for the same reason, keeping output deterministic rather than upscaled.

## 2. Script asked for 10 images, got 600+

A manual physics/render loop (`while simulation_app.is_running():
world.step(render=True)`) was running alongside Replicator's own trigger
system. Replicator writes an image on every render it sees, so it wrote
one for every physics step in that loop, not once per intended frame.

Fix was removing the manual step loop entirely and letting Replicator's
own orchestrator drive frame count.

## 3. Randomization only changed once per run, not once per frame

Box position, rotation, and floor material were different each time the
script was *run*, but identical across every frame within a single run.
Lighting intensity and color did vary per frame in the same script, which
was the clue.

`rep.trigger.on_frame(...)` combined with `rep.randomizer.register(...)`
runs the registered function exactly once, to build the underlying
OmniGraph, not once per frame. Anything computed with plain Python inside
that function (`random.randint`, `random.sample`, `random.choice`)
resolves immediately at that point and gets baked into the graph as a
fixed value. Only values passed as `rep.distribution.*` objects actually
get resampled on each subsequent trigger, which is why lighting worked
and box placement did not.

Confirmed against NVIDIA's own forum guidance on this exact behavior, then
switched away from `trigger.on_frame`/`orchestrator.run()` entirely for
anything needing real per-frame logic. Final approach is a manual loop
calling `rep.orchestrator.step()` once per frame, with plain Python
randomizer functions called fresh immediately before each step:

```python
for i in range(num_frames):
    randomize_box()
    randomize_floor()
    randomize_light_position()
    rep.orchestrator.step(rt_subframes=96)
```

Simple continuous values (light color, intensity, scale) still use
`rep.distribution.uniform(...)` passed at object creation time. Those
correctly resample every step without needing to be in the manual loop.
Position needed to move to the manual loop too, see issue 9.

## 4. PhysX warnings on environment load, `GuCookingTriangleMesh`

Loading `warehouse_20x20_envi.usd` threw continuous warnings:
`TriangleMesh: triangles are too big, reduce their size to increase
simulation stability!`

That asset uses large single polygons for floor and ceiling, a common
visual-only shortcut. PhysX collision cooking is unstable against
oversized triangles like that. Switched to NVIDIA's `Simple_Warehouse`
asset (`full_warehouse.usd`), which is built for robotics/physics use and
carries no such warnings. Used for the rest of the project.

## 5. Ghosting: trailing duplicate boxes in captured images

Early captured frames showed motion-blur trails, a faint duplicate of a
box left behind after it moved or changed visibility.

RTX's temporal accumulation blends several frames together to reduce
noise. Teleporting an object between frames (as opposed to smoothly
moving it) gives the accumulation buffer no time to catch up, so the
previous position bleeds through. Fix was increasing `rt_subframes`,
which forces the engine to internally re-render multiple sub-frames per
capture until the accumulation actually converges before writing the
image:

```python
rep.orchestrator.step(rt_subframes=96)
```

Started at 48, still saw faint ghosting, moved to 96 and it cleared.
Confirmed this is the documented fix for scenes with quickly moving or
teleporting objects, not something specific to this setup.

## 6. Fatal Instancer crash trying to randomize between box variants

Tried `rep.randomizer.instantiate(list_of_box_urls)` to swap between
different SimReady box assets per frame. This threw a fatal `usdrt.hydra`
exception and produced multiple boxes stacked on top of each other before
crashing.

The Instancer that backs `instantiate` handles culling the previous
instance before spawning the next. Streaming several heavy assets in and
out this way caused it to lose sync and fail to clean up the prior
instance. Rather than chase the Instancer bug, restructured the approach
entirely: all 10 box variants get loaded once as permanent, separate
prims at startup (`Box_0` through `Box_9`), and each frame just toggles
`rep.modify.visibility(True/False)` on whichever ones are chosen for that
frame. No dynamic instancing, no culling, no crash.

## 7. Boxes overlapping despite generous slot spacing

Boxes were placed on four fixed, well separated floor slots (about 1.4m
apart), which should have made overlap impossible, but it still happened
occasionally.

`rep.modify.pose(rotation=...)` rotates a prim around its own authored
origin, not its visual center. Several of the imported box assets don't
have their mesh origin centered. Rotating one of those makes it swing in
an arc around that off-center point rather than spinning in place,
occasionally swinging its footprint into a neighboring slot even though
the slot centers were far enough apart. Fix was the `pivot` parameter on
`rep.modify.pose`, which is normalized -1 to 1 per axis based on the
prim's own bounding box:

```python
rep.modify.pose(
    position=(x, y, 0),
    rotation=(0, 0, random.uniform(-180, 180)),
    pivot=(0, 0, -1),
)
```

`pivot=(0, 0, -1)` centers the rotation in x and y and anchors it to the
bottom face in z. This fixed the overlap and, as a side effect, also
solved boxes floating above the floor (previously handled with a hardcoded
z offset that only worked for one box size). One parameter replaced both
the overlap fix and a separate per-asset bounding box calculation that
had been in an earlier draft.

## 8. Duplicate bounding boxes for the same physical box

The annotation output for a single visible box sometimes contained two
entries at identical pixel coordinates, one labeled `shipping_box`, the
other labeled `box,shipping_box`.

Two separate bugs stacked on top of each other. First,
`rep.get.prims(path_pattern="/World/Boxes/Box_.*")` is an unanchored
regex, so it matched not just `Box_0` but its children too
(`Box_0/Looks/MI_CardBoxA` and similar), tagging material and scope prims
with our semantic label along with the box itself. Second, and separately,
some of NVIDIA's box assets ship with their own pre-existing semantic
label baked in from the original asset (`class: box`) on a nested prim.
USD composes multiple semantic labels on the same prim into one
comma-joined string, which is where `box,shipping_box` came from.

Both had to be fixed. Anchored the tagging regex to match only the exact
box prim:

```python
all_boxes = rep.get.prims(path_pattern="^/World/Boxes/Box_[0-9]+$")
```

and stripped any pre-existing semantic schema before applying ours:

```python
for prim in stage.Traverse():
    if str(prim.GetPath()).startswith("/World/Boxes/"):
        for schema_name in list(prim.GetAppliedSchemas()):
            if "Semantic" in schema_name:
                prim.RemoveAppliedSchema(schema_name)
```

Verified by loading the raw `.npy`/`.json` writer output directly and
checking for duplicate coordinates, rather than trusting the rendered
image alone.

## 9. Console spam, `OgnSetVisibility` / `OgnSetPrimPose`, "Used null prim"

Every frame threw a wall of errors like `Empty typeName for
</World/Boxes/Box_0/Looks/MI_CardBoxA.visibility>` and `Assertion raised
in compute - Used null prim`.

Same unanchored regex problem as issue 8, but in a different place.
`randomize_box()` has its own internal call, `rep.get.prims(path_pattern=path)`,
using a plain unanchored string, which matched the same non-geometric
child prims (material scopes with no visibility or transform attributes
to set). Fixing the tagging regex in issue 8 did not fix this, since it's
a structurally separate call in a different function. Needed its own fix:

```python
prim_group = rep.get.prims(path_pattern=f"^{path}$")
```

## 10. Randomized lighting barely visible, then far too intense

First pass at randomizing a light's intensity and color showed almost no
visible difference between frames. Widening the range made it too
extreme in the other direction.

The `Simple_Warehouse` asset ships its own baked-in lighting meant to
simulate ambient indoor fill light. That baseline lighting was fighting
the added randomized light and masking most of its effect. Fix was
disabling the warehouse's own light prims before creating ours:

```python
for prim in stage.Traverse():
    if str(prim.GetPath()).startswith("/World/Warehouse") and "Light" in prim.GetTypeName():
        UsdGeom.Imageable(prim).MakeInvisible()
```

With the warehouse lighting off and our light as the only source, its
intensity and color range became controllable and visibly obvious frame
to frame.

## 11. Light position not changing despite `distribution.choice`

Color and intensity clearly varied per frame. Position, driven by
`rep.distribution.choice(perimeter_points)` over a list of preset points
on a circle, did not appear to move at all.

Not fully root caused. `distribution.choice` on a fixed list of position
tuples did not resample reliably under the manual `orchestrator.step()`
loop, even though `distribution.uniform` on that same light object's
color and intensity did. Rather than keep digging into the distribution
internals, switched to computing the position directly in plain Python
each frame, the same reliable pattern already used for box and floor
randomization:

```python
def randomize_light_position():
    angle = random.uniform(0, 2 * math.pi)
    x = light_radius * math.cos(angle)
    y = light_radius * math.sin(angle)
    with lights:
        rep.modify.pose(position=(x, y, light_height))
```

## 12. Generation slowed from seconds per frame to roughly a minute per frame over a long run

A single process generating 1000 frames started fast and got
progressively slower, taking about a minute per frame by frame 90, which
projected out to something like ten hours for the full run.

Every call to `rep.modify.pose()`, `rep.modify.visibility()`, or
`rep.modify.materials()` inside the manual per-frame loop creates a new
node in the underlying OmniGraph rather than reusing one. Visible directly
in the console log as a steadily climbing node counter,
`OgnSetPrimPose_04`, `_08`, `_13`, and so on, climbing past 40 by frame
five. Over a thousand frames with several objects modified per frame,
that's thousands of accumulated nodes in a single process, and graph
evaluation cost grows with it.

Fix was splitting generation into small batches, each run as its own
fresh process, so the graph resets to empty at the start of every batch
instead of growing across the whole run:

```python
batch_id = int(sys.argv[1])
out_dir = os.path.join(..., f"batch_{batch_id:03d}")
```

```powershell
for ($i = 0; $i -lt $numBatches; $i++) {
    C:\isaacsim\python.bat .\scripts\generate_synthetic_dataset.py $i
}
```

Batch size wasn't guessed. Timed 15 frames and 25 frames directly on the
target machine (15 frames took 2:40, 25 frames took 4:46) before settling
on 15 per batch, since the slowdown compounds rather than scaling
linearly, so more frequent restarts on smaller batches actually finish
faster overall than fewer, larger ones.

## 13. Writer output wasn't in YOLO's label format

Not a bug, a format mismatch. `BasicWriter` outputs absolute pixel corner
coordinates (`x_min`, `y_min`, `x_max`, `y_max`) per box plus a separate
JSON mapping semantic IDs to class names. YOLO expects one `.txt` file per
image, one line per box, normalized `class_id x_center y_center width
height`.

Wrote a separate conversion script, run once after generation, that reads
every batch folder's `.npy`/`.json` output, converts pixel corners to
normalized center and size, remaps semantic labels to YOLO class indices,
and writes out a single combined `images/` and `labels/` folder across
every batch. Runs in seconds regardless of how many images it's
processing.