# Sources (2026-07-26)

## Local

- `_COMMON/VENDORS/MHR` — package `mhr` 1.0.1.post5…, `assets/` (~11 GB), `demo.py`, pixi
- `_COMMON/VENDORS/momentum` — C++/pymomentum source tree (~902 MB)
- Lab venv: `pymomentum` importable (`site-packages/pymomentum`)
- SAM3D JIT:  
  `_COMMON/MODELS/hub/models--facebook--sam-3d-body-dinov3/.../assets/mhr_model.pt`  
  and/or `VENDORS/MHR/assets/mhr_model.pt`
- Integration:  
  `pipeline/vendor/sam-3d-body/.../heads/mhr_head.py`  
  `pipeline/_bootstrap.py` (Path A/B switch)  
  lab npz: `_data/analysis/0009/sam3d_body.npz` (`mhr_model_params` 204, verts 18439, joints 127)

## Upstream

- https://github.com/facebookresearch/MHR  
- https://github.com/facebookresearch/momentum  
- https://facebookresearch.github.io/MHR/  
- https://facebookresearch.github.io/momentum/  
- https://arxiv.org/abs/2511.15586 (MHR)  
- https://arxiv.org/abs/2602.15989 (SAM 3D Body — consumes MHR)  
- ATLAS ICCV 2025 (decoupled skeleton/shape precursor)

## Lab constraints (memory)

- Default JIT path; group/full Momentum not ship-default  
- `with_blend_shape` / from_files SEGFAULT or hang on pip path historically  
- Assets kept on disk for future Path B verification
