# 30 — Wan2GP + Wan-Move spike runbook (16 GB)

**Goal:** e01 open on 675 with trajectory control.  
**Host:** RTX 5060 Ti 16 GB  
**Stack:** isolated Wan2GP (not lab `pipeline/.venv`)

---

## Layout

| Path | Role |
|------|------|
| `/home/nick/AI/_COMMON/VENDORS/Wan2GP` | clone (done) |
| `Wan2GP` venv | separate conda/venv — **never** lab torch 2.11 |
| Weights (auto or manual) | HF `DeepBeepMeep/Wan2.1` → prefer **int8** URLs in `defaults/wanmove.json` |
| Tracks | `_data/cache/wanmove/tracks_e01_open_t81.npy` |
| Out | `_data/experiments/<ts>_wan2gp_move_e01/` |

### Weights (from `defaults/wanmove.json`)

1. `wan2.1_wanmove_14B_quanto_mbf16_int8.safetensors` ← **prefer 16 GB**  
2. `wan2.1_wanmove_14B_quanto_mfp16_int8.safetensors`  
3. `wan2.1_wanmove_14B_mbf16.safetensors` ← last resort (fat)

---

## Track format (verified in Wan2GP source)

```python
# Motion Designer → custom_guide
np.save(path, trajectory_array)  # float32, shape [T, N, 2]
# any2video wanmove:
track = np.load(input_custom)  # [T,N,2]
# if track.max() <= 1: scale by width, height
```

Lab exporter: `lab/tools/mhr70_to_wanmove_tracks.py`

```bash
pipeline/.venv/bin/python lab/tools/mhr70_to_wanmove_tracks.py \
  --analysis _data/analysis/0009 \
  --out _data/cache/wanmove/tracks_e01_open_t81.npy \
  --frames 81 --width 832 --height 480 --vis
```

---

## Install (Linux RTX 50xx — from Wan2GP docs)

```bash
cd /home/nick/AI/_COMMON/VENDORS/Wan2GP
# Prefer conda if available; else venv + matching torch wheel
python3.11 -m venv .venv   # or conda create -n wan2gp python=3.11.14
source .venv/bin/activate
# Docs recommend torch 2.10 + cu130 for 50xx; adapt if cu130 not installed —
# fallback: torch 2.7.1+cu128 may work with reduced kernels
pip install -U pip
pip install -r requirements.txt
# then torch matching your CUDA
```

**Do not** install into `ai-img-seq-kimi/pipeline/.venv`.

---

## Smoke order

1. `python wgp.py --help` or start UI once  
2. Select model **Wan2.1 Wan-Move 480p 14B** (int8 quant)  
3. Memory profile: most aggressive / low VRAM  
4. `image_start` = 675 still (832×480 or let UI resize)  
5. `custom_guide` = tracks npy  
6. Short length if possible; 480p  
7. Export frames → lab:

```bash
pipeline/.venv/bin/python pipeline/pose_gate.py hop \
  --frames _data/experiments/.../frames --mode open_end
```

---

## 16 GB hard rules (do not skip)

Community/official CLI tips map **differently** on Wan2GP:

| Tip (official `generate.py` / forums) | Lab action |
|---------------------------------------|------------|
| `--t5_cpu` + `--offload_model True` | Wan2GP: **`python wgp.py --profile 5`** (or 4). Not the same flag names. |
| `--offload_blocks True --offload_blocks_num 1` | **Not in stock Wan2GP**. mmgp profiles already stream DiT blocks. Do not invent flags. |
| `--ulysses_size 1` | Single GPU default; do not enable multi-GPU/Ulysses. |
| Resolution hard-cap 480p | **Mandatory:** still **832×480** (not 1920×1080). Tracks in same pixel space. |
| Frames | Prefer **81** (lab tracks) or UI default ≤ ~5s; do not start at 121+ on first try. |
| Quant | **int8** Move weights only on first smoke. |
| Prompt enhancer | **OFF** |

### Pre-baked assets (lab)

| File | Size / role |
|------|-------------|
| `_data/cache/wanmove/still_675_832x480.jpg` | first frame @ Move res |
| `Wan2GP/mask_outputs/lab_still_675_832x480.jpg` | copy for UI |
| `_data/cache/wanmove/tracks_e01_open_t81.npy` | `[81,4,2]` px coords in 832×480 |
| `Wan2GP/mask_outputs/lab_e01_open_t81.npy` | copy for `custom_guide` |

**Never** feed raw `_src/0009_…675.jpeg` (1920×1080) as Move start without resize — that alone OOMs 16 GB.

If still OOM after profile 5 + int8 + 832×480 + 81f → **host no-go**, park Move (do not chase unofficial block-swap forks unless planned).

---

## Kill criteria

| Fail | Action |
|------|--------|
| Install blocked (CUDA/torch) | document, stop same day |
| OOM int8 + profile 5 + 832×480 + 81f | **no-go 16 GB**, park Move |
| Runs but open_end fail ×2 track variants | park; hard-case stays 5B-negative |
| Wall > 4h without one forward | park |

---

## Success

`pose_gate open_end` pass **or** clear human side-by-side knees on late frame.

Then: optional thin lab recipe wrapper; else keep Wan2GP as specialist tool.

---

## Progress 2026-07-26

| Step | Status |
|------|--------|
| Clone Wan2GP | ✅ `_COMMON/VENDORS/Wan2GP` |
| Track format verified | ✅ `[T,N,2]` npy → `custom_guide` |
| MHR70→tracks exporter | ✅ `lab/tools/mhr70_to_wanmove_tracks.py` |
| Tracks e01 open | ✅ `_data/cache/wanmove/tracks_e01_open_t{33,81}.npy` + vis; also `Wan2GP/mask_outputs/lab_e01_open_t81.npy` |
| end pose metrics | dy=0, dx≈100 @ 832×480 (gate-open geometry on tracks) |
| Isolated venv + weights | ⏳ next — prefer **int8** URL from `defaults/wanmove.json` |
| One gen + pose_gate | ⏳ |

### Next commands (human / agent with network+disk)

```bash
cd /home/nick/AI/_COMMON/VENDORS/Wan2GP
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
# match CUDA: try lab-compatible cu128 first if cu130 unavailable
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
pip install -r requirements.txt

# 16GB: force LowVRAM profile (Wan2GP equivalent of offload + T5 out of VRAM)
# Official Wan-Move CLI uses --t5_cpu --offload_model True;
# Wan2GP maps that to mmgp Memory Profile 4 or 5 (default is already LowRAM_LowVRAM).
python wgp.py --profile 5
# If RAM ≥32GB and 5 is too slow: --profile 4
```

**UI (after start):**

| Setting | Value |
|---------|--------|
| Model | **Wan2.1 Wan-Move 480p 14B** |
| Quant | **int8** (`…_quanto_mbf16_int8` / mfp16_int8) — not full mbf16 |
| Memory profile | **5** (fail-safe) or **4** (recommended low VRAM) |
| Attention | sdpa (safe) unless sage2 already installed |
| image_start | 675 still |
| custom_guide | `mask_outputs/lab_e01_open_t81.npy` |
| Resolution | 480×832 |
| Prompt enhancer | **OFF** (extra VRAM) |

### Flag mapping (official Move CLI → Wan2GP)

| Official `generate.py` | Wan2GP |
|------------------------|--------|
| `--t5_cpu` | Memory profile **4/5**: `text_encoder` budget tiny / CPU-side via mmgp |
| `--offload_model True` | same profiles: transformer streamed, not fully resident |
| `--dtype bf16` | int8 quant weights preferred on 16 GB |
| (no profile) | **Do not** use Profile 1–3 (need 24 GB+ VRAM) |

After frames exported:

```bash
cd /home/nick/AI/Projects/ai-img-seq-kimi
pipeline/.venv/bin/python pipeline/pose_gate.py hop --frames <frames_dir> --mode open_end
```
