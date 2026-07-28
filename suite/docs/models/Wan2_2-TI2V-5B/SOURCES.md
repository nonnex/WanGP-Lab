# Sources (2026-07-26)

## Local

- `pipeline/models` → `_COMMON/MODELS/hub/models--Wan-AI--Wan2.2-TI2V-5B-Diffusers`
- Snapshot `b8fff7315c768468a5333511427288870b2e9635` — `model_index.json`, `transformer/config.json`, `vae/config.json`
- Diffusers 0.39: `diffusers/pipelines/wan/pipeline_wan_i2v.py` (`prepare_latents`, `encode_prompt`, `__call__`)
- Lab runs: `_data/experiments/20260726_145300_lattice_dev`, `20260726_151117_lattice_dev`

## Upstream

- https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers
- https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B
- https://github.com/Wan-Video/Wan2.2
- https://arxiv.org/abs/2503.20314
- https://github.com/huggingface/diffusers/issues/13167 (expand_timesteps, no last-frame clamp)
- https://github.com/huggingface/diffusers/pull/12006 (5B I2V Diffusers)
- https://github.com/huggingface/diffusers/issues/13258 (must use WanImageToVideoPipeline for I2V)
