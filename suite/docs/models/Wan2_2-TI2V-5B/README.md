# Wan2.2-TI2V-5B — Lab reference

**Status:** verified against local weights + Diffusers 0.39 + HF/docs (2026-07-26)  
**Checkpoint:** `Wan-AI/Wan2.2-TI2V-5B-Diffusers`  
**Snapshot:** `b8fff7315c768468a5333511427288870b2e9635`  
**On disk:** `pipeline/models` → `/home/nick/AI/_COMMON/MODELS/hub/models--Wan-AI--Wan2.2-TI2V-5B-Diffusers` (~34 GB)  
**License:** Apache-2.0 · Paper: [arXiv:2503.20314](https://arxiv.org/abs/2503.20314)

This folder is the **canonical lab note** for what this model can and cannot do in *our* stack. Prefer this over ad-hoc chat memory when changing gen/conditioning.

---

## 1. Identity

| | |
|--|--|
| Full name | Wan2.2 Text-Image-to-Video 5B (hybrid TI2V) |
| Role | **One dense 5B DiT** for **T2V and I2V** |
| Family | Wan2.2 “Efficient HD Hybrid” — **not** MoE A14B |
| MoE / dual expert | **No** — `transformer_2=null`, `boundary_ratio=null` |
| Text encoder | **UMT5-XXL** (`text_dim=4096`) |
| CLIP image encoder | **No** in this checkpoint (`image_dim=null`, no `image_encoder` in `model_index`) |
| VAE | Wan2.2 high-compression VAE |

Official pitch: 720P@24fps on consumer GPUs (4090-class with offload); T2V+I2V unified.

---

## 2. Architecture (local `model_index` / configs)

| Parameter | Value | Note |
|-----------|--------|------|
| DiT | `WanTransformer3DModel` | 30 layers, 24 heads, head_dim 128, ffn 14336 |
| `in_channels` / `out_channels` | **48** | = VAE `z_dim` |
| VAE spatial | **16×** | `scale_factor_spatial` |
| VAE temporal | **4×** | `scale_factor_temporal` |
| Patch size | `[1, 2, 2]` | extra ×2 spatial → ~**32×** spatial with patch |
| Compression (docs) | 4×16×16 (+patch → 4×32×32) | high compression |
| RoPE max seq | 1024 | |
| `expand_timesteps` | **`true`** | **defines TI2V-5B I2V conditioning** |
| Scheduler | UniPCMultistep | |

**Frame rule:** `num_frames = 4k + 1` (1, 5, …, 25, 33, 81, 121…). Lab already snaps to this.

**Resolution:** height/width multiples of **32** (VAE 16 × patch 2).  
Official demos often **1280×704** (not 1280×720). Lab default: **832×480**.

---

## 3. Correct Diffusers entrypoint

| Class | Use |
|-------|-----|
| `WanImageToVideoPipeline` | **I2V** ← lab uses this |
| `WanPipeline` | **T2V** (image arg often invalid / ignored) |

HF card snippets that only show `WanPipeline` + prompt are **T2V**, not our I2V path.  
Runtime: Diffusers **0.39** (lab `pipeline/.venv`).

---

## 4. I2V conditioning (critical)

### 4.1 What actually runs (`expand_timesteps=True`)

From Diffusers `WanImageToVideoPipeline.prepare_latents`:

```text
video_condition = first_image ONLY          # last_image ignored here
first_frame_mask[0] = 0                     # frame 0 hard-clamped to VAE(image)
first_frame_mask[1:] = 1                    # remaining frames free latents
# denoise mix:
latent_input = (1 - mask) * condition + mask * latents
```

Also at end of denoising (expand path): first latent frame is forced back toward the condition.

### 4.2 Feature matrix

| Feature | TI2V-5B (ours) | Wan2.1-I2V-14B / non-expand path |
|---------|----------------|-----------------------------------|
| First-frame hard lock | **Yes** | Yes (different mechanism) |
| **`last_image` / FLF** | API param exists; **IGNORED** in expand path | Works in non-expand branch |
| CLIP image embeds | **No** | Yes when `image_dim` set |
| Native end-pose force | **No** | FLF possible |
| Pose / depth / ControlNet | **No** (external only) | External |

Upstream confirmation: [diffusers#13167](https://github.com/huggingface/diffusers/issues/13167) — with `expand_timesteps`, only first frame is clamped; `last_image` is not applied to `video_condition`.

### 4.3 Lab implication

- Passing `last_image=open_mid` **does nothing** on this checkpoint.  
- Pure I2V = **start still + text (+ seed/steps/CFG/LoRA)**.  
- End pose is **not** natively constrained.  
- Do **not** plan FLF as a TI2V-5B feature.

---

## 5. Text / prompts

| | |
|--|--|
| Encoder | UMT5-XXL |
| `encode_prompt` default | **`max_sequence_length=226`** |
| `__call__` docstring default | 512 — **encode still uses 226** unless overridden end-to-end |
| Longer prompts | **Hard truncated** (lab measured e01 352 → 226 tokens) |
| CFG | `guidance_scale` (docs default 5.0). CFG ≤ 1 ⇒ negatives ~useless |
| Official negatives | Often Chinese + terms like 静止/静态 (static) |

**Lab doctrine (measured):** motion-first, short prompts (≲200 tok); long identity walls kill action.  
See `pipeline/pose_lattice.py` (`compile_prompt`, `PROMPT_TOKEN_BUDGET`).

---

## 6. Inference parameters

### 6.1 Reference (HF / Diffusers PR examples)

| Param | Typical |
|-------|---------|
| `num_inference_steps` | **50** |
| `guidance_scale` | **5.0** |
| `num_frames` | 81–121 @ ~720p area |
| Export fps | 24 |
| dtype | DiT bf16; VAE often loaded fp32 |
| Offload (official CLI) | `--offload_model`, `--t5_cpu`, etc. |

### 6.2 Lab measurements (RTX 5060 Ti 16 GB, model_cpu_offload, T5-free)

| Setting | Wall time | Peak VRAM |
|---------|-----------|-----------|
| 832×480, 25f, **12** steps | ~120 s | ~11.5 GB |
| 832×480, 33f, **28** steps | ~174 s | ~11.6 GB |

VRAM is dominated by resolution/offload, not strictly linear in steps.

### 6.3 Recommended lab defaults (this model)

| | Recommendation |
|--|----------------|
| Base steps (motion QA) | **28–50** (not 12 for pose experiments) |
| CFG Base | ~**5** |
| Turbo / distill / CFG~1 | **Smoke only** — not ship / not identity verdict |
| Prompt | ≤200 tok, motion first |
| FLF / `last_image` | **Not a feature of this CKPT** |

---

## 7. Memory / offload (16 GB)

| Component | Behavior |
|-----------|----------|
| UMT5-XXL | Huge **host RAM** if left resident |
| DiT 5B bf16 | Fits with offload |
| VAE encode/decode | Spikes; tiling/slicing optional |

**Lab path (required for multi-seed):** T5 encode once → **free T5** → denoise seeds sequentially.  
**Default offload:** `model_cpu_offload`.  
**Avoid as default:** group offload + T5-free (device mismatch — see project corrections).

---

## 8. Capabilities vs non-capabilities

### Can

- T2V and I2V from one weight  
- Strong first-frame fidelity (face/scene early frames)  
- Generic text-driven motion (breathing, fidget, *some* limb motion)  
- 16 GB with offload + T5-free  
- Base-scoped LoRAs (`wan22_ti2v_5b/{speed,identity,style}`)  
- Apache + Diffusers-native lab iteration  

### Cannot (natively)

| Desire | Reality |
|--------|---------|
| First+last frame (FLF) | **Not** in expand_timesteps path |
| Built-in pose/depth ControlNet | **No** |
| CLIP image embedding control | **No** |
| MoE dual-CFG / `guidance_scale_2` | **No** (`transformer_2` null) |
| Precise choreography (uncross→open) via text alone | **Unreliable** — first frame dominates |
| Drop-in A14B Lightning LoRA | Architecture mismatch |
| A14B I2V quality at same VRAM | Out of scope without quant/custom stack |

---

## 9. Do not confuse with

| ID | Relation |
|----|----------|
| `Wan2.2-I2V-A14B` | Different model, MoE I2V, much more VRAM |
| `Wan2.2-T2V-A14B` | T2V MoE |
| `Wan2.1-I2V-14B-*-Diffusers` | Older; CLIP + different cond; FLF more relevant |
| Turbo / FastWan on **5B** | Speed/smoke; CFG~1; not ship-ID |
| lightx2v Lightning | Primarily **A14B**; not TI2V-5B drop-in |

Cross-loading LoRAs across bases is forbidden (lab rule).

---

## 10. Hard-case implications (day21_10 / 675→677)

Lab evidence (2026-07-26):

- Long prompts + 12 steps → near-frozen fidget, no uncross.  
- Short motion-first prompt + 28 steps → **real motion**, still **wrong action** (kick/extend, not open knees).  
- Fits model physics: first-frame lock + free middle + weak text control of stacked-leg geometry.

**What can steer this CKPT**

1. First frame  
2. Text ≤226 tokens  
3. Steps / CFG / seed / Best-of-N  
4. Base LoRAs  
5. Lattice = **multiple short pure-I2V hops** (each hop still first-frame-only)  
6. Post-hoc verifiers (must be **live**, not skipped)

**What cannot**

- `last_image` / FLF end pose on TI2V-5B  
- Expecting prompt essays to force side-switch geometry  

**Next levers (ordered)**

1. Live leg-switch / open-knee gate (SAM3D on early/late frames)  
2. Better intermediate **first** frames only if a true open still exists (e12 start ≠ e01 end-pose fix)  
3. External structure (Control / other backbone) if 5B pure-I2V plateaus  
4. Do not burn L3/L4 multi-seed until e01 uncross is geometrically true  

---

## 11. Links

| | |
|--|--|
| HF Diffusers weights | https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B-Diffusers |
| HF original layout | https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B |
| Upstream repo | https://github.com/Wan-Video/Wan2.2 |
| expand_timesteps / no last-frame clamp | https://github.com/huggingface/diffusers/issues/13167 |
| Diffusers I2V 5B PR | https://github.com/huggingface/diffusers/pull/12006 |

---

## 12. Related lab files

| Path | Role |
|------|------|
| `pipeline/generate_segment.py` | I2V entry, embeds, offload |
| `pipeline/pose_lattice.py` | Short prompt compiler, hops |
| `pipeline/auto_motion.py` | Phase directives (short) |
| `pipeline/models_config.json` | `i2v.active` registry |
| `lab/recipes/lattice_dev.yaml` | DEV budget (e.g. 33f×28) |
| `_plan/research/11_wan22_lightning_turbo_eval.md` | Turbo/Lightning scope |
| `_plan/research/13_community_best_practices_wan22_2026.md` | Community practices |

---

## 13. One-line essence

**TI2V-5B = first-frame-clamped, text-guided, single-transformer 5B I2V/T2V with hard ~226-token T5 and no native last-frame/control — good 16 GB lab workhorse, not a precise pose controller for leg side-switch by itself.**
