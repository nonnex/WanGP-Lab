# WanGP-Lab

Operator suite: **WanGP cockpit** + **Lab motor** (ai-img-seq-kimi) + thin **bridge**.

```
WanGP-Lab/
  suite/     ← our code (finetunes, plugin, scripts, tools, docs)
  wangp/     ← full Wan2GP checkout (local; not pushed with weights)
  data/      ← suite cache / experiments
  config/    ← suite.env
```

## Layout

| Path | Role |
|------|------|
| `suite/finetunes/` | Mission model presets |
| `suite/plugins/wan2gp-lab-bridge/` | Lab Bridge UI plugin |
| `suite/scripts/` | install, start, gate, status |
| `suite/tools/` | track builder, headless move |
| `suite/docs/` | architecture |
| `wangp/` | [deepbeepmeep/Wan2GP](https://github.com/deepbeepmeep/Wan2GP) clone + local `.venv` / `ckpts` |
| `data/cache/wanmove/` | stills + trajectory `.npy` |

## Venvs (never mix)

| | |
|--|--|
| WanGP | `wangp/.venv` |
| Lab motor | `$LAB_MOTOR_ROOT/pipeline/.venv` |

## Quick start

```bash
cd ~/AI/Projects/WanGP-Lab

# first time / after pull of suite only:
bash suite/scripts/bootstrap_wangp.sh   # clone wangp if missing
bash suite/scripts/install_bridge.sh    # copy finetunes + plugin into wangp/
bash suite/scripts/status.sh
bash suite/scripts/start_wangp.sh       # profile 4 + sage
# → http://localhost:7860
```

## Update WanGP upstream (no merge hell)

```bash
cd wangp
git fetch origin
git pull --ff-only origin main
cd ..
bash suite/scripts/install_bridge.sh    # re-apply suite finetunes/plugin
```

Do **not** edit `wangp/defaults/` or `wangp/wgp.py` for suite features.

## Iterate ladder

| L | Model | |
|---|--------|--|
| 0 | `lab_ti2v5b_fast_e01` | smoke |
| 1 | `lab_wanmove_e01_smoke` | 33f×8 |
| 2 | `lab_wanmove_e01` | 49f×16 + pose_gate |
| 3 | multi-seed Move | |
| 4 | lab-motor e12/ship | only after open_end PASS |

## Git

- This repo tracks **suite/** + config + docs + small data assets.
- **`wangp/` weights, venv, outputs are gitignored** (see `.gitignore`).
- Local `wangp/` stays a normal git clone of upstream Wan2GP.
