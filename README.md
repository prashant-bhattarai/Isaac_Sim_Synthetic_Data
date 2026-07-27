# Industrial Synthetic Data Generator — Fallen Cardboard Box Detection

Goal: Generate a synthetic training dataset in NVIDIA Isaac Sim, train a YOLO
detector for fallen cardboard shipping boxes, and deploy real-time inference
in a ROS2 (WSL) node subscribing to a live camera feed.

## Status
- [x] Synthetic data generation pipeline (Isaac Sim Replicator)
- [x] YOLO-format label conversion
- [ ] Model training
- [ ] ROS2 real-time inference node
- [ ] Real-camera validation

## Pipeline
1. `scripts/generate_synthetic_dataset.py` — batched scene randomization + capture
2. `scripts/convert_to_yolo.py` — converts BasicWriter output to YOLO format
3. (training scripts — coming next)

## Dataset
Regenerate via the scripts above, or download the pre-built set from
[Releases](../../releases) (`yolo_dataset_v1.zip`).

## Notable engineering challenges
See `DEBUGGING.md` for a full write-up of issues encountered and solved
during dataset generation (ghosting, semantic label collisions, graph
performance degradation, etc.)

## The experiment folder include some simple script that help me experiment stuff while making this project. 