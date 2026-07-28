# Architecture — WanGP Cockpit + Lab Motor

**Status:** agreed

```
WanGP UI  = Cockpit (Gen, Tracks, A/B, Queue)
Lab       = Motor (Analyze, Tracks, Gate, Ship)
Bridge    = finetunes + Lab Bridge plugin + headless scripts
```

## Boundaries

| Layer | Owns | Does not own |
|-------|------|----------------|
| **WanGP** (`wangp/`) | Generate, UI, queue, Motion Designer, DA3 | Pose truth, hard_ok |
| **Lab** (motor) | SAM3D/MHR70, tracks, pose_gate, ship | Daily gen UI |
| **Bridge** (`suite/`) | finetunes, plugin, scripts/tools | Merging venvs / forking core |

## Rules

1. WanGP only in `wangp/.venv` — never Lab `pipeline/.venv`.
2. Lab pose tools only in `pipeline/.venv`.
3. No SAM3D inside WanGP process; plugin = subprocess to Lab.
4. Ship signal = Lab `pose_gate`, not UI “looks ok”.

## Bridge assets (SoT)

| Piece | Path |
|-------|------|
| Finetunes | `suite/finetunes/` |
| Plugin | `suite/plugins/wan2gp-lab-bridge/` |
| Installer | `bash suite/scripts/install_bridge.sh` |
| Headless Move | `bash suite/tools/run_move_e01.sh` |
| Cache | `data/cache/wanmove/` |
| Critical | `suite/docs/SUITE_CRITICAL.md` |

Install copies finetunes/plugin/settings/assets into local `wangp/`.
