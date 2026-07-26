import numpy as np
import json
import os
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib.patches as patches

out_dir = r"E:\Software_Projects\IS_01_Synthetic_Data\output\box_dataset"

print("Files in folder:")
for f in sorted(os.listdir(out_dir))[:10]:
    print(" ", f)

# adjust the filename below to whatever you actually see printed above
rgb_path = os.path.join(out_dir, "rgb_0000.png")
bbox_path = os.path.join(out_dir, "bounding_box_2d_tight_0000.npy")
labels_path = os.path.join(out_dir, "bounding_box_2d_tight_labels_0000.json")

bbox_data = np.load(bbox_path)
with open(labels_path) as f:
    id_to_label = json.load(f)

print(bbox_data)
print(id_to_label)

img = Image.open(rgb_path)
fig, ax = plt.subplots()
ax.imshow(img)
for box in bbox_data:
    label = id_to_label[str(box["semanticId"])]
    rect = patches.Rectangle(
        (box["x_min"], box["y_min"]),
        box["x_max"] - box["x_min"],
        box["y_max"] - box["y_min"],
        linewidth=2, edgecolor="lime", facecolor="none"
    )
    ax.add_patch(rect)
    ax.text(box["x_min"], box["y_min"] - 5, label, color="lime")
plt.show()