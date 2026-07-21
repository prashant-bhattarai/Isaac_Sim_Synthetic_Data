from isaacsim import SimulationApp

config = {
    "headless": False,
    "width": 1280,  
    "height": 720,
    "anti_aliasing": 0,
}
simulation_app = SimulationApp(config)

from isaacsim.core.api import World
from isaacsim.storage.native import get_assets_root_path
from isaacsim.core.utils.stage import add_reference_to_stage
import omni.replicator.core as rep
import numpy as np
import os

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
    assets_root_path + "/Isaac/SimReady/Industrial/Warehouse/Boxes/Cube_Box_A09/sm_box_cube_a09_01.usd"
]

world = World()
add_reference_to_stage(usd_path=warehouse_usd, prim_path="/World/Warehouse")

camera = rep.create.camera(position=(0, -7, 7), look_at=(0, 0, 0))
render_product = rep.create.render_product(camera, (1024, 1024))

writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

with rep.new_layer():
    def randomize_box():
        boxes = rep.randomizer.instantiate(box_usds, size=1)
        with boxes:
            rep.modify.semantics([('class', 'shipping_box')])
            rep.modify.pose(
                position=rep.distribution.uniform((-2, -2, 0.2), (2, 2, 0.2)),
                rotation=rep.distribution.uniform((0, 0, -180), (0, 0, 180)),
                scale=rep.distribution.uniform((2.0, 2.0, 2.0), (4.0, 4.0, 4.0))
            )
        return boxes.node

    rep.randomizer.register(randomize_box)

with rep.trigger.on_frame(max_execs=20, rt_subframes=90):
    rep.randomizer.randomize_box()

#Generating 10 randomized images

rep.orchestrator.run()

while rep.orchestrator.get_is_started():
    simulation_app.update()

print("Dataset generated successfully!")

simulation_app.close()