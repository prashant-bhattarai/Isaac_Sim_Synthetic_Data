import numpy as np
import json
import os
import shutil
from PIL import Image

base_dir = r"E:\Software_Projects\IS_01_Synthetic_Data\output\box_dataset"
yolo_dir = r"E:\Software_Projects\IS_01_Synthetic_Data\output\yolo_dataset"

images_out = os.path.join(yolo_dir, "images")
labels_out = os.path.join(yolo_dir, "labels")
os.makedirs(images_out, exist_ok=True)
os.makedirs(labels_out, exist_ok=True)

class_names = ["shipping_box"]
class_to_id = {name: i for i, name in enumerate(class_names)}

batch_dirs = sorted(
    d for d in os.listdir(base_dir)
    if d.startswith("batch_") and os.path.isdir(os.path.join(base_dir, d))
)
print(f"Found {len(batch_dirs)} batch folders")

total_images = 0
total_boxes = 0

for batch_name in batch_dirs:
    batch_path = os.path.join(base_dir, batch_name)
    rgb_files = sorted(f for f in os.listdir(batch_path) if f.startswith("rgb_") and f.endswith(".png"))

    for rgb_file in rgb_files:
        frame_id = rgb_file[len("rgb_"):-len(".png")]  # e.g. "0000"

        bbox_path = os.path.join(batch_path, f"bounding_box_2d_tight_{frame_id}.npy")
        labels_path = os.path.join(batch_path, f"bounding_box_2d_tight_labels_{frame_id}.json")
        if not os.path.exists(bbox_path):
            continue

        bbox_data = np.load(bbox_path)
        with open(labels_path) as f:
            id_to_label = json.load(f)

        img = Image.open(os.path.join(batch_path, rgb_file))
        img_w, img_h = img.size

        lines = []
        for box in bbox_data:
            label = id_to_label[str(box["semanticId"])]["class"]
            labels_list = [l.strip() for l in label.split(",")]
            matched = [l for l in labels_list if l in class_to_id]
            if not matched:
                continue

            x_min, y_min = box["x_min"], box["y_min"]
            x_max, y_max = box["x_max"], box["y_max"]
            if x_max <= x_min or y_max <= y_min:
                continue

            cx = ((x_min + x_max) / 2) / img_w
            cy = ((y_min + y_max) / 2) / img_h
            w = (x_max - x_min) / img_w
            h = (y_max - y_min) / img_h

            class_id = class_to_id[matched[0]]
            lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            total_boxes += 1

        out_stem = f"{batch_name}_{frame_id}"
        shutil.copy(os.path.join(batch_path, rgb_file), os.path.join(images_out, f"{out_stem}.png"))
        with open(os.path.join(labels_out, f"{out_stem}.txt"), "w") as f:
            f.write("\n".join(lines))

        total_images += 1

print(f"Converted {total_images} images, {total_boxes} boxes total")
print(f"Output: {yolo_dir}")