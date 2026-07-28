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

```
L0  FastWan smoke           — UI alive?
L1  Move smoke 33f×8        — tracks on-body?
L2  Move e01 49f×16         — open_end gate
L3  Multi-seed / track A/B  — best progress
L4  Lab e12 + ship          — only if open_end PASS
```

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
