# WanGP-Lab

Operator suite: **WanGP cockpit** + **Lab motor** (ai-img-seq-kimi) + thin **bridge**.

```
WanGP-Lab/
  suite/     ← our code (finetunes, plugin, scripts, tools, docs)
  wangp/     ← Wan2GP checkout (local; weights not pushed)
  data/      ← cache / experiments
  config/    ← suite.env
```

## Quick start

```bash
cd ~/AI/Projects/WanGP-Lab
bash suite/scripts/bootstrap_wangp.sh    # if wangp/ missing
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp_ui.sh     # → http://localhost:7860
```

**Windows Desktop:** `bash suite/scripts/install_windows_shortcut.sh` → double-click **WanGP-Lab**.

## Commands

| | |
|--|--|
| Status | `bash suite/scripts/status.sh` |
| UI | `bash suite/scripts/start_wangp_ui.sh` |
| Tracks | `bash suite/scripts/build_tracks.sh 49` |
| Headless Move | `bash suite/tools/run_move_e01.sh --frames 49 --steps 16` |
| Gate | `bash suite/scripts/gate_output.sh <mp4>` |

## Venvs (never mix)

| | |
|--|--|
| WanGP | `wangp/.venv` |
| Lab | `$LAB_MOTOR_ROOT/pipeline/.venv` |

## Iterate ladder (Lab Bridge tab)

| L | UI button | |
|---|-----------|--|
| 0 | L0 FastWan smoke | UI alive |
| 1 | L1 Move 33×8 | tracks on-body |
| 2 | L2 Move 49×16 | + **Gate last** |
| 3 | multi-seed / track A/B | |
| 4 | motor e12/ship | only after open_end PASS |

Best seed so far: **7** · tracks **apart-dx 100** · progress ~0.86.

## Update WanGP upstream

```bash
cd wangp && git pull --ff-only origin main && cd ..
bash suite/scripts/install_bridge.sh
```

Do **not** edit `wangp/defaults/` or `wangp/wgp.py` for suite features.

Docs: [`suite/docs/SUITE_CRITICAL.md`](suite/docs/SUITE_CRITICAL.md) · [`suite/docs/README.md`](suite/docs/README.md)
