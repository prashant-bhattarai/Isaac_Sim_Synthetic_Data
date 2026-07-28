from ultralytics import YOLO

def main():
    data_yaml = r"E:\Software_Projects\IS_01_Synthetic_Data\output\yolo_dataset_split\data.yaml"

    model = YOLO("yolo11s.pt")

    results = model.train(
        data=data_yaml,
        epochs=100,
        imgsz=1024,
        batch=8,
        patience=20,
        project="runs",
        name="shipping_box_v1",
    )

if __name__ == "__main__":
    main()