---
description: WanGP-Lab suite operator — cockpit/motor/bridge discipline
mode: primary
---

You work in **WanGP-Lab** (`/home/nick/AI/Projects/WanGP-Lab`).

## Architecture

```
suite/   = our bridge code (edit freely)
wangp/   = upstream Wan2GP + local venv/ckpts (no core forks)
lab-motor = ai-img-seq-kimi (SAM3D, pose_gate, fixtures)
```

## Hard rules

1. Never mix venvs: WanGP = `wangp/.venv`, motor = `lab-motor/pipeline/.venv`
2. Never edit `wangp/defaults/` or `wangp/wgp.py` for suite features
3. Never ship pose without motor `pose_gate` pass
4. FastWan ≠ pose success (smoke only)
5. Host default: Profile **4**, attention **sage**, quant **int8**
6. Do not commit `wangp/ckpts`, `.venv`, outputs

## Preferred commands

```bash
bash suite/scripts/status.sh
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp_ui.sh
bash suite/scripts/build_tracks.sh 49
bash suite/scripts/gate_output.sh <mp4|frames>
bash suite/tools/run_move_e01.sh --profile 4 --frames 49 --steps 16
```

## Iterate ladder

L0 FastWan smoke → L1 Move smoke 33×8 → L2 Move 49×16 + gate → L3 multi-seed → L4 lab e12 only if open_end PASS
