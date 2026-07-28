# 29 — Wan-Move spike (go/no-go)

**Status:** planned (not started)  
**Why:** TI2V-5B pure I2V plateau on e01 open (see `28_e01_open_plateau_and_next.md`)  
**Upstream:** [ali-vilab/Wan-Move](https://github.com/ali-vilab/Wan-Move) · weights [Ruihang/Wan-Move-14B-480P](https://huggingface.co/Ruihang/Wan-Move-14B-480P)  
**Base:** Wan**2.1** I2V-14B + trajectory extension (not TI2V-5B Diffusers)

---

## Goal (single question)

Can trajectory-conditioned I2V produce **visible knee uncross → open (dx)** on 675→open target better than 5B pure I2V, under lab constraints?

**Success (go):** late frame passes `pose_gate open_end` (or clear human open) on ≥1 clip.  
**Fail (no-go):** OOM on 16 GB after offload attempts, or runs but open still fails after 2 track variants.

---

## VRAM reality (critical) — researched 2026-07-26

### Official release (only one)

| Item | Detail |
|------|--------|
| Weights | **only** [Ruihang/Wan-Move-14B-480P](https://huggingface.co/Ruihang/Wan-Move-14B-480P) |
| Base | Wan**2.1**-I2V-**14B** (not TI2V-5B) |
| Official min GPU | **single 40 GB** + `--t5_cpu --offload_model True --dtype bf16` ([README](https://github.com/ali-vilab/Wan-Move)) |
| Official 5B Move | **not released** |

Paper trained **Wan-Move-Cog-*** on CogVideoX-**5B** for ablations — **weights not published** for that line. No “Wan-Move-5B” on HF for our stack.

### Community low-VRAM options (not official)

| Path | What | 16 GB lab? |
|------|------|------------|
| [vantagewithai/Wan-Move-14B-480P-GGUF](https://huggingface.co/vantagewithai/Wan-Move-14B-480P-GGUF) | Q2–Q8 GGUF of Move-14B (e.g. Q5 ~12 GB **file**) | **Maybe** via ComfyUI-GGUF / custom runner — **not** Diffusers drop-in; peak VRAM during denoise still unknown; quality/quant risk |
| [smthem/Wan-Move-14B-480P-diffuser-gguf](https://huggingface.co/smthem/Wan-Move-14B-480P-diffuser-gguf) | another GGUF packaging | same caveats |
| **[Wan2GP](https://github.com/deepbeepmeep/Wan2GP)** (v9.84+) | **Wan-Move supported** + Motion Designer tracks; low-VRAM framework (profiles, quant) | **Best practical 16 GB candidate** — separate app, not our Diffusers lab; needs smoke on 5060 Ti |
| Wan2.2 FP8 / GGUF I2V (wangkanai, QuantStack, …) | plain I2V quants | **no trajectory Move training** — not Wan-Move |
| **Time-to-Move (TTM)** via Wan2GP | control+mask videos, **no weight change** on Wan2.2 i2v | Interesting **5B-adjacent** idea; not Move weights; separate spike |

### Lab GPU

**RTX 5060 Ti 16 GB** + ~24 GB RAM class host.

| Verdict | |
|---------|--|
| Official bf16 Move-14B | **no-go** on this card (40 GB claim) |
| Official Move-5B | **does not exist** (public) |
| GGUF Move-14B | **experimental only** — try only if accepting Comfy/Wan2GP detour |
| Wan2GP + Move | **preferred feasibility path** for 16 GB |
| Stay pure Diffusers lab | Move stays blocked until 24–40 GB machine or proven quant path |

→ Spike step 0 = pick path (Wan2GP smoke vs park), **not** blind full bf16 download into lab venv.

---

## Spike steps (order)

### 0. Feasibility gate (no full quality work)

- [ ] Read Move track JSON schema + `generate.py` flags  
- [ ] Estimate weight size on disk (~14B bf16 class — tens of GB)  
- [ ] **Do not download** until either:  
  - (a) confirmed 16 GB path (Wan2GP/quant), or  
  - (b) explicit user OK for download + external 24–40 GB machine  
- [ ] Write go/no-go on VRAM in this file

### 1. Env (isolated — do not break lab 2.11+cu128 venv)

- [ ] Clone to `_COMMON/VENDORS/Wan-Move` or `pipeline/vendor/Wan-Move`  
- [ ] **Separate** venv/pixi (torch pin per Move requirements ≥2.4)  
- [ ] Smoke import + `--help` on generate

### 2. Tracks from lab truth (CPU)

- [ ] Tool: MHR70 knees 11/12 from `_data/analysis/0009` + synthetic **open** mid (equal y, larger |dx|) + optional 677  
- [ ] Emit Move-format point trajectories (knee L/R, maybe ankles)  
- [ ] Visualize tracks on 675 still (matplotlib/overlay PNG)

### 3. One hop gen (only if VRAM go)

- [ ] First frame: 675 still  
- [ ] Tracks: uncross+apart only (e01 fact)  
- [ ] 480×832, offload flags, shortest supported length  
- [ ] Save under `_data/experiments/<ts>_wan_move_spike/`  
- [ ] `pose_gate.py hop --mode open_end`

### 4. Compare

| Metric | 5B best (seed33) | Move |
|--------|------------------|------|
| open_end | fail | ? |
| dy/dx late | ~65 / ~7 | ? |
| wall / VRAM | ~3 min / ~12 GB | ? |

---

## Kill criteria (stop spike)

- Confirmed min VRAM &gt; 16 GB with no viable quant → **no-go**, document, stop  
- Two track recipes, both gate fail + human fail → structure alone insufficient; revisit later  
- &gt;1 day integration without one forward pass → park

---

## Integration later (only on go)

- `lab/recipes/lattice_move_e01.yaml` (optional engine)  
- Tracks from `auto_motion` / SAM3D  
- Gate remains SAM3D (MHR70), not Move’s internal metrics  

**Do not** replace 5B lab loop for probes; Move = hard-hop specialist if it fits.

---

## Non-goals

- Full lattice e12 ship on Move day one  
- Replacing Diffusers 5B for all recipes  
- WHAM / attention-mask hacks  

---

## Immediate lab action (today)

1. Freeze 5B e01 spam ✅  
2. This doc + plateau doc ✅  
3. **No weight download tonight** unless VRAM path cleared  
4. Next session: step 0–1 only (schema + env), or mark host no-go and move on to other lab work (fixtures, gates on easier beats)
