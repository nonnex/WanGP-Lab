# Suite critical design — WanGP Cockpit + Lab Motor

## One sentence

**WanGP is the cockpit; Lab is the motor; never merge the engines.**

---

## Layout (SoT)

| Path | Role |
|------|------|
| `suite/` | finetunes, plugin, scripts, tools, docs, settings |
| `wangp/` | local Wan2GP clone + `.venv` + `ckpts` (not pushed) |
| `data/cache/wanmove/` | stills + tracks `.npy` |
| `data/experiments/` | headless run outputs |
| `config/suite.env` | paths + host defaults |
| motor | `/home/nick/AI/Projects/ai-img-seq-kimi` |

---

## Boundaries

```
WanGP (.venv)  — gen · UI · queue · Motion Designer · mmgp
        │ zips / plugin subprocess / paths
Lab (pipeline/.venv) — SAM3D · tracks · pose_gate · ship
```

| Never | Why |
|-------|-----|
| Mix venvs | Torch/SAM3D vs WanGP ABI |
| Patch `wangp/defaults/` or `wgp.py` | breaks `git pull` |
| pose_gate inside WanGP process | VRAM + wrong truth layer |
| FastWan as pose pass | smoke only |
| Profile 2 always-on on 24 GB RAM | swap thrash |

---

## Product surface

1. Finetunes: `lab_wanmove_e01`, `lab_wanmove_e01_smoke`, `lab_ti2v5b_fast_e01`
2. Lab Bridge tab: tracks → preset → gate
3. Motion Designer (bundled) when auto tracks fail
4. Headless: `suite/tools/run_move_e01.sh`

Bridge install: `suite/scripts/install_bridge.sh` → copies into `wangp/`.

---

## Iterate ladder

**Default experiment = L1 (direction).** L2 confirms amplitude — not every tweak, but  
**never drop a track on L1 FAIL alone** (false reject). Full policy: [ITERATE_POLICY.md](./ITERATE_POLICY.md).

```
L0  FastWan smoke           — UI alive only (NOT pose signal)
L1  Move smoke 33f×8        — direction screen → KILL | HOLD | PROMOTE
L2  Move 49f×16 seed7       — amplitude + Gate SoT (required after HOLD/PROMOTE)
L3  Multi-seed / track A/B  — after ≥1 solid L2
L4  Lab e12 + ship          — only if open_end PASS
```

| Verdict | Action |
|---------|--------|
| **KILL** | Wrong direction (kick/freeze/bad END) — no L2 |
| **HOLD** | Ambiguous / “fehlt Rest” — **one L2** before drop |
| **PROMOTE** | Direction OK — L2 now |
| **PASS** | Gate ok on L2+ — ship path |

Ship signal = gate PASS on L2+, never L0/L1 alone.

---

## Ops

```bash
cd ~/AI/Projects/WanGP-Lab
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp_ui.sh          # WSL
# Windows Desktop: WanGP-Lab.lnk  (install_windows_shortcut.sh)

bash suite/tools/run_move_e01.sh --profile 4 --frames 49 --steps 16
bash suite/scripts/gate_output.sh <mp4>
```

Host: Profile **4**, attention **sage**, quant **int8**, 832×480 Move.

ORT DRM warning on WSL (`card0/device/vendor`): see [ORT_WSL_DRM.md](./ORT_WSL_DRM.md) —
not a dead GPU; `with_ort_wsl_env.sh` handles discovery cleanly.
