from ultralytics import YOLO

model = YOLO(r"E:\Software_Projects\IS_01_Synthetic_Data\runs\detect\runs\shipping_box_v1\weights\best.pt")

results = model.predict(
    source=r"E:\Software_Projects\IS_01_Synthetic_Data\real_test_images",
    save=True,
    conf=0.25,
    project="runs",
    name="real_world_test",
)