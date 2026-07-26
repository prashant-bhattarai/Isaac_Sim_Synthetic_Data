from isaacsim import SimulationApp

config = {
    "headless": True,
    "width": 1280,
    "height": 720,
    "anti_aliasing": 0,
}
simulation_app = SimulationApp(config)

import random
import math
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
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_05_946.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_02.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxC_02_540.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_04_1118.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxC_01.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_01.usd",
    assets_root_path + "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_03.usd",
]

floor_mdl_urls = [
    assets_root_path + "/Isaac/Materials/Base/Natural/Asphalt.mdl",
    assets_root_path + "/Isaac/Materials/Base/Stone/Slate.mdl",
    assets_root_path + "/Isaac/Materials/Base/Stone/Porcelain_Tile_4_Linen.mdl",
    assets_root_path + "/Isaac/Materials/Base/Masonry/Brick_Pavers.mdl",
    assets_root_path + "/Isaac/Materials/Base/Architecture/Shingles_01.mdl",
    assets_root_path + "/Isaac/Materials/Base/Wood/Walnut_Planks.mdl",
    assets_root_path + "/Isaac/Materials/Base/Wood/Oak.mdl",
    assets_root_path + "/Isaac/Materials/Base/Wood/Cherry_Planks.mdl",
    assets_root_path + "/Isaac/Materials/Base/Wood/Bamboo.mdl",
    assets_root_path + "/Isaac/Materials/Base/Wood/Ash_Planks.mdl",
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

stage = omni.usd.get_context().get_stage()

floor_meshes = [
    str(p.GetPath()) for p in stage.Traverse()
    if "SM_floor" in str(p.GetPath()) and p.IsA(UsdGeom.Mesh)
]
print(f"Floor meshes found: {len(floor_meshes)}")

disabled_lights = 0
for prim in stage.Traverse():
    path_str = str(prim.GetPath())
    if path_str.startswith("/World/Warehouse") and "Light" in prim.GetTypeName():
        UsdGeom.Imageable(prim).MakeInvisible()
        disabled_lights += 1
print(f"Disabled {disabled_lights} warehouse light prim(s)")

camera = rep.create.camera(position=(0, -2.3, 3.6), look_at=(0, 0, 0.15))
render_product = rep.create.render_product(camera, (1024, 1024))

writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

slot_xy = [(-0.7, -0.6), (0.7, -0.6), (-0.7, 0.6), (0.7, 0.6)]

light_radius = 3.0
light_height = 3.0

lights = rep.create.light(
    light_type="Sphere",
    color=rep.distribution.uniform((0.9, 0.85, 0.75), (1.0, 1.0, 0.95)),
    intensity=rep.distribution.uniform(4000, 9000),
    scale=rep.distribution.uniform(1.0, 1.5),
    position=(0, 0, light_height),
    count=1,
)


def randomize_box():
    num_visible = random.randint(1, min(len(slot_xy), len(box_prim_paths)))
    chosen_boxes = random.sample(box_prim_paths, num_visible)
    chosen_slots = random.sample(slot_xy, num_visible)

    for path in box_prim_paths:
        prim_group = rep.get.prims(path_pattern=path)
        if path in chosen_boxes:
            idx = chosen_boxes.index(path)
            x, y = chosen_slots[idx]
            with prim_group:
                rep.modify.visibility(True)
                rep.modify.pose(
                    position=(x, y, 0),
                    rotation=(0, 0, random.uniform(-180, 180)),
                    pivot=(0, 0, -1),
                )
        else:
            with prim_group:
                rep.modify.visibility(False)


def randomize_floor():
    if not floor_meshes:
        return
    chosen_material = random.choice(floor_mdl_urls)
    floor_group = rep.create.group(floor_meshes)
    with floor_group:
        rep.randomizer.materials(materials=[chosen_material])


def randomize_light_position():
    angle = random.uniform(0, 2 * math.pi)
    x = light_radius * math.cos(angle)
    y = light_radius * math.sin(angle)
    with lights:
        rep.modify.pose(position=(x, y, light_height))


num_frames = 10
for i in range(num_frames):
    randomize_box()
    randomize_floor()
    randomize_light_position()
    rep.orchestrator.step(rt_subframes=96)
    print(f"frame {i + 1}/{num_frames}")

print("Dataset generated successfully!")
simulation_app.close()