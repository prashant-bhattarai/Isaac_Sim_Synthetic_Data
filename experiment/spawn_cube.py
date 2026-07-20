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

world.reset()
print("Simulation running! Press Ctrl+C in the terminal to close.")

while simulation_app.is_running():
    world.step(render=True)

simulation_app.close()