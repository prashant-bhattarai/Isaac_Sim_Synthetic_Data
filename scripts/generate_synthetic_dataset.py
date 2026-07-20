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

warehouse_usd = assets_root_path + "/Isaac/Environments/Simple_Warehouse/warehouse.usd"
box_usd = assets_root_path + "/Isaac/Props/Blocks/cardboard_box.usd"

world = World()
add_reference_to_stage(usd_path=warehouse_usd, prim_path="/World/Warehouse")

camera = rep.create.camera(position=(0, -5, 5), look_at=(0, 0, 0))
render_product = rep.create.render_product(camera, (1024, 1024))

writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=out_dir, rgb=True, bounding_box_2d_tight=True)
writer.attach([render_product])

with rep.new_layer():
    box = rep.create.from_usd(box_usd, semantics=[('class', 'shipping_box')])

    def randomize_box():
        boxes = rep.get.prims(semantics=[('class', 'shipping_box')])
        with boxes:
            rep.modify.pose(
                position=rep.distribution.uniform((-2, -2, 0.2), (2, 2, 0.2)),
                rotation=rep.distribution.uniform((0, 0, -180), (0, 0, 180))
            )
        return boxes.node

    rep.randomizer.register(randomize_box)

with rep.trigger.on_frame(max_execs=10):
    rep.randomizer.randomize_box()

#Generating 10 randomized images

world.reset()

rep.orchestrator.run()

while rep.orchestrator.get_is_started():
    simulation_app.update()

print("Dataset generated successfully!")

simulation_app.close()