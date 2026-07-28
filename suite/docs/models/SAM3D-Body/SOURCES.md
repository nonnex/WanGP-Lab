# Sources (2026-07-26)

## Local

- Hub: `_COMMON/MODELS/hub/models--facebook--sam-3d-body-dinov3`  
  snapshot `11aaa346c7204874a1cbafe3d39a979080b2c55a`  
  (`model.ckpt`, `model_config.yaml`, `assets/mhr_model.pt`, LICENSE, README)
- Code: `_COMMON/VENDORS/sam-3d-body` → `pipeline/vendor/sam-3d-body`  
  (`sam_3d_body/metadata/mhr70.py`, `models/heads/mhr_head.py`, …)
- DINOv3: `_COMMON/MODELS/torch/hub/facebookresearch_dinov3_main`
- Optional MHR FBX: `_COMMON/VENDORS/MHR/assets` (not default decode)
- Lab analysis example: `_data/analysis/0009/sam3d_body.npz`
- Lab code:  
  `pipeline/analyze_anchors.py`, `auto_motion.py`, `pose_gate.py`,  
  `pose_lattice.py`, `interpolate_mid_poses.py`, `_bootstrap.py`,  
  `smoke_sam3dbody.py`, Blender DebugTool queue/push

## Upstream

- https://huggingface.co/facebook/sam-3d-body-dinov3  
- https://huggingface.co/facebook/sam-3d-body-vith  
- https://github.com/facebookresearch/sam-3d-body  
- https://github.com/facebookresearch/MHR  
- https://arxiv.org/abs/2602.15989  
- https://ai.meta.com/research/publications/sam-3d-body-robust-full-body-human-mesh-recovery/  
- https://ai.meta.com/sam3d/  
- Dataset: https://huggingface.co/datasets/facebook/sam-3d-body-dataset  
- License: SAM License (repo LICENSE; HF gated)

## Lab measurements

- Trusted stills 675/677: left→right on_top flip, trust≈1.0 after full+project path  
- pose_gate on kick e01 (`20260726_151117`): `open_end` FAIL (dy≈148, not open)  
- Kick vs open heuristics calibrated for seated 832×480 gen frames
