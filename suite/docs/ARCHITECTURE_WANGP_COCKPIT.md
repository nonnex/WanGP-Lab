# Architecture — WanGP Cockpit + Lab Motor (2026-07-28)

**Status:** agreed

```
WanGP UI  = Cockpit (Gen, Tracks, A/B, Queue)
Lab       = Motor (Analyze, Tracks bauen, Gate, Ship)
Bridge    = Zips + optional Plugin „Lab: analyze → tracks → gate“
```

## Boundaries

| Layer | Owns | Does not own |
|-------|------|----------------|
| **WanGP** | Generate (Move/FastWan/…), UI experiment, queue export/import, preprocess tools (DA3, Matanyone, Motion Designer) | Pose truth, hard_ok, fixture automation |
| **Lab** | SAM3D/MHR70, auto_motion, track export, pose_gate, lattice, ship | Replacing WanGP as daily gen UI |
| **Bridge** | Queue zips with media+settings; later plugin calling Lab venv | Merging venvs or forking WanGP core |

## Rules

1. WanGP runs only in `…/Wan2GP/.venv` — never Lab `pipeline/.venv`.
2. Lab pose tools run only in `pipeline/.venv`.
3. No SAM3D-Body inside WanGP core; optional plugin = subprocess to Lab.
4. Momentum/MHR stays Lab (JIT default); not required in WanGP.
5. Ship signal = Lab `pose_gate` / hard_ok, not UI “looks ok”.

## Bridge assets (current)

- `_data/cache/wanmove/` stills + tracks
- Downloads: `ti2v_2_2_fastwan_lab_e01_media.zip`, `wanmove_lab_e01_media.zip`
- Headless: `lab/tools/wan2gp_move_e01.py` (WanGP venv)

## Implemented bridge (2026-07-28)

| Piece | Path |
|-------|------|
| Finetunes SoT | `lab/wangp/finetunes/lab_wanmove_e01*.json`, `lab_ti2v5b_fast_e01.json` |
| Plugin SoT | `lab/wangp/plugin/wan2gp-lab-bridge/` |
| Installer | `bash lab/wangp/install_to_wangp.sh` |
| Critical design | `_docs/lab/SUITE_CRITICAL.md` |

Plugin tab **Lab Bridge**: build tracks → apply preset → switch finetune → pose_gate on output.

## Next

1. Human: restart WanGP, verify Lab Bridge tab + finetunes list  
2. Optional: wire Start-image file picker auto-fill from still path  
3. Optional: e12 preset only after open_end pass flag
