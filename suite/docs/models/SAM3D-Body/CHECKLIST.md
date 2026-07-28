# SAM 3D Body — quick checklist

- [ ] `import _bootstrap` before `sam_3d_body`
- [ ] Weights: `facebook/sam-3d-body-dinov3` under `pipeline/models` (HF gated OK)
- [ ] Default: `MOMENTUM_ENABLED=0` (JIT `mhr_model.pt`)
- [ ] Analyze mode **full** unless mask path proven
- [ ] After inference: **project** kp3d→kp2d with `focal` + `pred_cam_t`
- [ ] Persist `skeleton_trust` / score / json on every npz
- [ ] Leg metrics only if `trust=True` and knees in image
- [ ] MHR70: L-knee=11, R-knee=12; on_top = smaller image-y
- [ ] open_end gate: dy&lt;45 and dx&gt;55 (seated 480–1080p heuristic)
- [ ] Do not use sequential i→i+1 stick as anatomy
- [ ] Blender for real skeleton QA; gates for automation
- [ ] 1-person assumption; multi-person fixtures unsupported
- [ ] Do not run cold SAM3D load concurrent with peak Wan denoise
- [ ] Gen frames: integrity (mean/std) before pose_gate
- [ ] License = SAM License (not Apache) — check before redistribute
