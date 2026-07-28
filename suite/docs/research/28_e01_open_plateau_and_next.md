# 28 — e01 open plateau (TI2V-5B) + next decision

**Date:** 2026-07-26  
**Decision owner:** lab (auto)  
**Fixture:** `day21_10` hard-case 675→677 leg side-switch  

---

## Decision (binding)

1. **Stop burning pure TI2V-5B e01** for open-knee (dy&lt;45 ∧ dx&gt;55).  
2. **No e12 / L3 / L4 / soft-ship** until a structure path opens e01 or we explicitly reopen 5B search.  
3. **day21_10 uncross→open** is a **5B-negative benchmark** (methods/gates still valid).  
4. **Next structural candidate:** Wan-Move trajectory I2V — **feasibility first**, no blind 14B download.  
5. Keep lab IP: pose_gate, progress rank, prompt compiler, Bridge-Search doctrine.

---

## Evidence (measured)

| Run | What | Open pass |
|-----|------|-----------|
| `20260726_145300` lattice_dev | 12st long prompt | uncross not visible |
| `20260726_151117` short prompt 28st | motion↑, **kick** | no |
| `20260726_154025` search 11/22/33 | 33 near-miss dy↓ | 0/3 |
| `20260726_160408` Two-Beat cluster | contact junk / kicks | 0/5 |
| `20260726_162949` + `e01_apart` | apart hop dy/dx flat | **no** |

Best pure-I2V: seed **33** partial height uncross; **dx never** reaches open.  
`e01_apart` from late-33: progress Δ≈0 → 5B does not take lateral instruction from first-frame+text.

Model physics (`_docs/Wan2_2-TI2V-5B`): first-frame clamp, no `last_image`, T5 226 — consistent with fails.

---

## What we keep (do not throw away)

- `pipeline/pose_gate.py` — live open/flip + progress  
- `lab/run.sh` search / stop-on-open / e01_apart (octal seed fix)  
- `lab/tools/e01_apart_from_run.py`  
- Short motion-first prompts (`build_side_switch_motions`)  
- Doctrine: Wan = proposal, SAM3D-MHR = pose truth  
- Docs: `_docs/Wan2_2-TI2V-5B`, `SAM3D-Body`, `momentum`

---

## Next: Wan-Move spike (conditional)

See `_plan/research/29_wan_move_spike.md`.

**Hard constraint:** upstream claims **~40 GB** single-GPU with offload for Wan-Move-14B-480P.  
Lab is **16 GB** → default outcome may be **no-go on this host** unless Wan2GP/quant path works.

If no-go: hard-case stays 5B-negative; optional cloud/40 GB later; do not regress to pure-I2V spam.

---

## Explicitly not next

- WHAM as DiT control  
- Noise latent push / mid-denoise branching  
- DA3 for leg open  
- FastWan/Turbo as ship signal  
- ID-LoRA before geometry  
- More 5-seed Two-Beat e01 clusters
