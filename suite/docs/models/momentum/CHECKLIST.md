# Momentum / MHR — quick checklist

- [ ] Know the split: **Momentum** (solver lib) ≠ **MHR** (body model) ≠ **SAM3D** (image→params)
- [ ] Production: `MOMENTUM_ENABLED=0` → JIT `mhr_model.pt` inside SAM3D
- [ ] Full path only with `AIIMGSEQ_USE_MHR_MOMENTUM=1` + assets + verified host
- [ ] Assets present: `lod1.fbx`, `compact_v6_1.model`, `corrective_blendshapes_lod1.npz`
- [ ] Lab mesh = LOD1 **18439** verts; joints for gates = **MHR70** (knees 11/12)
- [ ] Full model params dim **204**; shape **45**; face **72**
- [ ] Do not load lod0 correctives casually (~2.5 GB NPZ)
- [ ] Do not run full MHR load concurrent with Wan peak VRAM
- [ ] MHR license Apache-2.0; SAM3D weights still SAM License
- [ ] Pixi preferred for full MHR; pip pymomentum experimental
- [ ] Mission: pose truth / Blender / gates — not I2V substitute
