from isaacsim import SimulationApp

config = {
    "headless": False,
    "width": 1280,
    "height": 720,
    "anti_aliasing": 0,
}
simulation_app = SimulationApp(config)

import random
import carb
import omni.usd
from pxr import UsdGeom
from isaacsim.core.api import World
from isaacsim.storage.native import get_assets_root_path
from isaacsim.core.utils.stage import add_reference_to_stage
import omni.replicator.core as rep
import os

settings = carb.settings.get_settings()
settings.set("/rtx/post/dlss/execMode", 0)

out_dir = os.path.join(os.getcwd(), "output", "box_dataset")
print(f"Saving data to: {out_dir}")

assets_root_path = get_assets_root_path()
if assets_root_path is None:
    print("Could not find Isaac Sim assets server!")
    quit()

warehouse_usd = assets_root_path + "/Isaac/Environments/Simple_Warehouse/full_warehouse.usd"

box_usds = [
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxA_01_310.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxA_01_714.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxB_01.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxC_01.usd",
]

floor_mdl_urls = [
    assets_root_path + "/Isaac/Materials/Base/Natural/Asphalt.mdl",
    assets_root_path + "/Isaac/Materials/Base/Stone/Slate.mdl",
]

world = World()
add_reference_to_stage(usd_path=warehouse_usd, prim_path="/World/Warehouse")

box_prim_paths = []
for i, box_path in enumerate(box_usds):
    prim_path = f"/World/Boxes/Box_{i}"
    add_reference_to_stage(usd_path=box_path, prim_path=prim_path)
    box_prim_paths.append(prim_path)

all_boxes = rep.get.prims(path_pattern="/World/Boxes/Box_.*")
with all_boxes:
    rep.modify.semantics([('class', 'shipping_box')])

# --- discover real floor mesh paths by traversal, no more guessing ---
stage = omni.usd.get_context().get_stage()
floor_meshes = [
    str(p.GetPath()) for p in stage.Traverse()
    if "SM_floor" in str(p.GetPath()) and p.IsA(UsdGeom.Mesh)
]
print(f"Floor meshes found: {len(floor_meshes)}")
if floor_meshes:
    print(f"Example path: {floor_meshes[0]}")

# camera close enough for ~0.3-0.7m real-scale boxes to read clearly
camera = rep.create.camera(position=(0, -2.3, 2.0), look_at=(0, 0, 0.15))
render_product = rep.create.render_product(camera, (1024, 1024))

writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

# fixed, well-separated slots — guarantees no overlap regardless of which/how many boxes show
slots = [(-0.5, -0.4, 0.1), (0.5, -0.4, 0.1), (-0.5, 0.5, 0.1), (0.5, 0.5, 0.1)]


def randomize_box():
    num_visible = random.randint(1, min(len(slots), len(box_prim_paths)))  # always >= 1
    chosen_boxes = random.sample(box_prim_paths, num_visible)
    chosen_slots = random.sample(slots, num_visible)

    for path in box_prim_paths:
        prim_group = rep.get.prims(path_pattern=path)
        if path in chosen_boxes:
            idx = chosen_boxes.index(path)
            with prim_group:
                rep.modify.visibility(True)
                rep.modify.pose(
                    position=chosen_slots[idx],
                    rotation=(0, 0, random.uniform(-180, 180)),
                )
        else:
            with prim_group:
                rep.modify.visibility(False)
    return all_boxes.node


def randomize_floor():
    if not floor_meshes:
        return None
    chosen_material = random.choice(floor_mdl_urls)  # same material on all tiles
    floor_group = rep.create.group(floor_meshes)
    with floor_group:
        rep.randomizer.materials(materials=[chosen_material])
    return floor_group.node


def randomize_light():
    lights = rep.create.light(
        light_type="Sphere",
        color=rep.distribution.uniform((0.7, 0.7, 0.7), (1.0, 1.0, 1.0)),
        intensity=rep.distribution.uniform(2000, 4000),
        position=rep.distribution.uniform((-2, -2, 3), (2, 2, 4)),
        scale=rep.distribution.uniform(1, 2.5),
        count=2,
    )
    return lights.node


rep.randomizer.register(randomize_box)
rep.randomizer.register(randomize_floor)
rep.randomizer.register(randomize_light)

with rep.trigger.on_frame(max_execs=10, rt_subframes=48):
    rep.randomizer.randomize_box()
    rep.randomizer.randomize_floor()
    rep.randomizer.randomize_light()

rep.orchestrator.run()

while rep.orchestrator.get_is_started():
    simulation_app.update()

print("Dataset generated successfully!")
simulation_app.close()