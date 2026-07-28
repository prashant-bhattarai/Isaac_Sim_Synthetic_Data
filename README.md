# Industrial Synthetic Data Generator — Fallen Cardboard Box Detection

Goal: Generate a synthetic training dataset in NVIDIA Isaac Sim, train a YOLO
detector for fallen cardboard shipping boxes, and deploy real-time inference
in a ROS2 (WSL) node subscribing to a live camera feed.

## Status
- [x] Synthetic data generation pipeline (Isaac Sim Replicator)
- [x] YOLO-format label conversion
- [x] Model training (YOLO11s, 95 epochs, val mAP50-95: 0.99)
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

## Known limitations

Validation mAP50-95 of 0.99 reflects performance on synthetic data drawn
from the same generator as training, not real-world performance. Testing
the trained model against real photos (own photos plus a small internet
sample) showed a significant sim-to-real gap: the model produces false
positives on unrelated objects and misses real cardboard boxes.

Likely cause: the generation pipeline used a fixed camera angle, always
included exactly one to four boxes per frame with no box-free scenes, and
included no distractor objects, so the model plausibly learned scene-level
shortcuts rather than actual box features.

Planned next iteration: randomized camera pose, background-only frames,
non-box distractor objects in the scene, and a small real-photo fine-tune
pass. Tracked as a follow-up, independent of the ROS2 deployment work
below, which was built against the current model.

->The experiment folder include some simple script that help me experiment stuff while making this project. 