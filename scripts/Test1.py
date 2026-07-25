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
from isaacsim.core.api import World
from isaacsim.storage.native import get_assets_root_path
from isaacsim.core.utils.stage import add_reference_to_stage
import omni.replicator.core as rep
import os

settings = carb.settings.get_settings()
settings.set("/rtx/post/dlss/execMode", 0)  # Quality mode

out_dir = os.path.join(os.getcwd(), "output", "box_dataset")
print(f"Saving data to: {out_dir}")

assets_root_path = get_assets_root_path()
if assets_root_path is None:
    print("Could not find Isaac Sim assets server!")
    quit()

warehouse_usd = assets_root_path + "/Isaac/Environments/Simple_Warehouse/full_warehouse.usd"

box_usds = [
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cardboard_Box_A01/sm_box_cardboard_a01_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cardboard_Box_A03/sm_box_cardboard_a03_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cardboard_Box_B02/sm_box_cardboard_b02_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cardboard_Box_C03/sm_box_cardboard_c03_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cardboard_Box_D02/sm_box_cardboard_d02_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Corrugated_Brown_Box_B09/sm_box_corrugated_brown_b09_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Corrugated_Brown_Box_B13/sm_box_corrugated_brown_b13_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Corrugated_Brown_Box_B19/sm_box_corrugated_brown_b19_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Corrugated_Brown_Box_B28/sm_box_corrugated_brown_b28_01.usd",
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cube_Box_A09/sm_box_cube_a09_01.usd",
]

# Start with a small subset for the first test — expand once confirmed stable
floor_mdl_urls = [
    assets_root_path + "/Isaac/Materials/Base/Natural/Asphalt.mdl",
    assets_root_path + "/Isaac/Materials/Base/Stone/Slate.mdl",
    assets_root_path + "/Isaac/Materials/Base/Stone/Porcelain_Tile_4_Linen.mdl",
    assets_root_path + "/Isaac/Materials/Base/Masonry/Brick_Pavers.mdl",
    # add the rest (Shingles_01, Rubber_Textured, Vinyl, Walnut_Planks, Oak,
    # Cherry_Planks, Bamboo, Ash_Planks) once this batch is confirmed working
]

world = World()
add_reference_to_stage(usd_path=warehouse_usd, prim_path="/World/Warehouse")

import omni.usd
from pxr import Usd, UsdPhysics

stage = omni.usd.get_context().get_stage()

floor_path_pattern = "/World/Warehouse/SM_floor(39|32|47|58)/SM_floor02"  # moved up, before first use

# --- Preload all boxes once, toggle visibility per frame (no accumulation) ---
box_prim_paths = []
for i, box_path in enumerate(box_usds):
    prim_path = f"/World/Boxes/Box_{i}"
    add_reference_to_stage(usd_path=box_path, prim_path=prim_path)
    box_prim_paths.append(prim_path)

# de-instance everything nested, so physics API can actually be edited
for box_path in box_prim_paths:
    box_prim = stage.GetPrimAtPath(box_path)
    for prim in Usd.PrimRange(box_prim, Usd.TraverseInstanceProxies()):
        if prim.IsInstance():
            prim.SetInstanceable(False)

# now disable rigid bodies for real
for box_path in box_prim_paths:
    box_prim = stage.GetPrimAtPath(box_path)
    for prim in Usd.PrimRange(box_prim):
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            UsdPhysics.RigidBodyAPI(prim).GetRigidBodyEnabledAttr().Set(False)

all_boxes = rep.get.prims(path_pattern="/World/Boxes/Box_.*")
floor_check = rep.get.prims(path_pattern=floor_path_pattern)
print(f"Floor prims matched: {floor_check.node}")
with all_boxes:
    rep.modify.semantics([('class', 'shipping_box')])

camera = rep.create.camera(position=(0, -7, 7), look_at=(0, 0, 0))
render_product = rep.create.render_product(camera, (1024, 1024))

writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

floor_path_pattern = "/World/Warehouse/SM_floor(39|32|47|58)/SM_floor02"


def randomize_box():
    boxes = rep.get.prims(path_pattern="/World/Boxes/Box_.*")
    with boxes:
        rep.modify.visibility(rep.distribution.choice([True, False, False, False]))
        rep.modify.pose(
            position=rep.distribution.uniform((-2, -2, 0.2), (2, 2, 0.2)),
            rotation=rep.distribution.uniform((0, 0, -180), (0, 0, 180)),
            scale=rep.distribution.uniform((2.0, 2.0, 2.0), (4.0, 4.0, 4.0)),
        )
    return boxes.node


def randomize_floor():
    floors = rep.get.prims(path_pattern=floor_path_pattern)
    chosen_material = random.choice(floor_mdl_urls)  # same pick for all 4 tiles
    with floors:
        rep.randomizer.materials(materials=[chosen_material])
    return floors.node


def randomize_dome_light():
    lights = rep.create.light(
        light_type="Dome",
        rotation=rep.distribution.uniform((0, 0, 0), (360, 0, 0)),
        color=rep.distribution.uniform((0.7, 0.7, 0.7), (1.0, 1.0, 1.0)),
    )
    with lights:
        rep.modify.attribute("inputs:intensity", rep.distribution.uniform(500, 2000))
    return lights.node


rep.randomizer.register(randomize_box)
rep.randomizer.register(randomize_floor)
rep.randomizer.register(randomize_dome_light)

with rep.trigger.on_frame(max_execs=10, rt_subframes=90):
    rep.randomizer.randomize_box()
    rep.randomizer.randomize_floor()
    rep.randomizer.randomize_dome_light()

rep.orchestrator.run()

while rep.orchestrator.get_is_started():
    simulation_app.update()

print("Dataset generated successfully!")
simulation_app.close()