from isaacsim import SimulationApp

config = {
    "headless": False,
    "width": 1280,  
    "height": 720,
    "anti_aliasing": 0,
}
simulation_app = SimulationApp(config)

from isaacsim.core.api import World
from isaacsim.core.api.objects import DynamicCuboid
import omni.replicator.core as rep
import numpy as np

world = World()
world.scene.add_default_ground_plane()

world.scene.add(
    DynamicCuboid(
        prim_path="/World/MyCube",
        name="my_cube",
        position=np.array([0, 0, 2.0]),
        scale=np.array([0.5, 0.5, 0.5]),
        color=np.array([0.0, 0.0, 1.0])
    )
)

camera = rep.create.camera(position=(0, -5, 5), look_at=(0, 0, 0))

render_product = rep.create.render_product(camera, (1024, 1024))
writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir="../output/my_first_dataset", rgb=True)
writer.attach([render_product])

world.reset()
print("Simulation running! Press Ctrl+C in the terminal to close.")

while simulation_app.is_running():
    world.step(render=True)

rep.orchestrator.step()

simulation_app.close()