import os
import random
import shutil

random.seed(42)

source_images = r"E:\Software_Projects\IS_01_Synthetic_Data\output\yolo_dataset\images"
source_labels = r"E:\Software_Projects\IS_01_Synthetic_Data\output\yolo_dataset\labels"

dataset_root = r"E:\Software_Projects\IS_01_Synthetic_Data\output\yolo_dataset_split"
train_images = os.path.join(dataset_root, "train", "images")
train_labels = os.path.join(dataset_root, "train", "labels")
val_images = os.path.join(dataset_root, "val", "images")
val_labels = os.path.join(dataset_root, "val", "labels")

for d in [train_images, train_labels, val_images, val_labels]:
    os.makedirs(d, exist_ok=True)

val_ratio = 0.15

stems = sorted(
    os.path.splitext(f)[0]
    for f in os.listdir(source_images)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
)

random.shuffle(stems)

split_idx = int(len(stems) * (1 - val_ratio))
train_stems = stems[:split_idx]
val_stems = stems[split_idx:]

print(f"Total images: {len(stems)}")
print(f"Train: {len(train_stems)}  Val: {len(val_stems)}")


def copy_split(stem_list, dst_images, dst_labels):
    copied = 0
    skipped = 0
    for stem in stem_list:
        image_path = None
        for ext in (".png", ".jpg", ".jpeg"):
            candidate = os.path.join(source_images, stem + ext)
            if os.path.exists(candidate):
                image_path = candidate
                break

        label_path = os.path.join(source_labels, stem + ".txt")

        if image_path is None or not os.path.exists(label_path):
            print(f"Skipping {stem}: missing image or label")
            skipped += 1
            continue

        shutil.copy(image_path, os.path.join(dst_images, os.path.basename(image_path)))
        shutil.copy(label_path, os.path.join(dst_labels, os.path.basename(label_path)))
        copied += 1

    return copied, skipped


train_copied, train_skipped = copy_split(train_stems, train_images, train_labels)
val_copied, val_skipped = copy_split(val_stems, val_images, val_labels)

print(f"Train copied: {train_copied}, skipped: {train_skipped}")
print(f"Val copied: {val_copied}, skipped: {val_skipped}")
print(f"Output at: {dataset_root}")