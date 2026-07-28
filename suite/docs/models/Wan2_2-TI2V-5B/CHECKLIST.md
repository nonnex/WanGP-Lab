# TI2V-5B — quick checklist (before changing gen)

- [ ] Using `WanImageToVideoPipeline` (not bare `WanPipeline` for I2V)
- [ ] Prompt ≲ 200 tokens (real T5 count); motion first
- [ ] Not relying on `last_image` / FLF for this checkpoint
- [ ] Base motion QA: steps ≥ 28, CFG ~5 (not turbo CFG=1)
- [ ] Turbo/FastWan = smoke only, never ship/ID verdict
- [ ] Frames = 4k+1; H/W multiple of 32
- [ ] T5 encode → free before multi-seed
- [ ] Offload: `model_cpu_offload` default (not broken group+T5-free)
- [ ] LoRA only under `loras/wan22_ti2v_5b/…`
- [ ] Pose claims verified by live geometry gate, not skipped `leg_switch`
