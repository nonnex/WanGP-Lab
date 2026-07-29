# WanGP-Lab — Resume-Karte (Kilo)

## Mission

**Operator suite** for still→motion hard-cases: WanGP **cockpit**, ai-img-seq-kimi **motor**, thin **bridge**.

Primary hard-case: day21_10 leg uncross→open (675→open), then side-switch toward 677.

## Layout

| Path | Role |
|------|------|
| `suite/missions/` | generic hard-case recipes (e01 = one pack) |
| `suite/finetunes/` | `lab_wanmove_*`, `lab_ti2v5b_fast_*` |
| `suite/plugins/wan2gp-lab-bridge/` | Mission cockpit: tracks+preview, L0–L2, gate last |
| `suite/scripts/` | install, start UI, status, gate, tracks, Windows shortcut |
| `suite/tools/` | headless Move, track builder `.py` |
| `suite/settings/` | WanGP UI defaults SoT |
| `suite/docs/` | architecture (start at `SUITE_CRITICAL.md`) |
| `wangp/` | Wan2GP clone + `.venv` + `ckpts` (local) |
| `data/cache/wanmove/` | stills + tracks + mission analysis/src (local) |
| `_outputs/` | WanGP UI videos (`wangp/outputs` → symlink) |
| `config/suite.env` | paths; `LAB_MOTOR_ROOT` = external pose_gate host |

## Venvs (never mix)

| | Python |
|--|--------|
| WanGP | `wangp/.venv/bin/python` |
| Pose gate (motor) | `$LAB_MOTOR_ROOT/pipeline/.venv/bin/python` |

Motor stays a **separate project** (~9GB venv/SAM3D) — do not copy into this repo. Mission stills/tracks/analysis live under `data/cache/wanmove/`.

## Commands

```bash
bash suite/scripts/status.sh
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp_ui.sh       # profile 4 + sage → :7860
bash suite/scripts/install_windows_shortcut.sh
bash suite/scripts/build_tracks.sh 49
bash suite/scripts/gate_output.sh <mp4>
bash suite/tools/run_move_e01.sh --frames 49 --steps 16 --profile 4
bash suite/scripts/lab_hygiene.sh         # keep lab clean (auto on start/Move/commit)
bash suite/scripts/install_git_hooks.sh   # once: pre-commit hygiene
```

## Host

- CPU: i7-12700F · RAM ~24 GB · GPU RTX 5060 Ti 16 GB
- Memory Profile **4** · Attention **sage** · Quant **int8**
- WanGP **base**: Py 3.11.14 · Torch 2.10.0+cu130 (`suite/docs/WANGP_STACK.md`)
- Rollback snap: `wangp/.venv-py312-torch271-cu128`
- **Channels:** base rock-solid · edge for nightlies/SoTA (`suite/docs/STACK_CHANNELS.md`)

## Rules

1. Do not edit `wangp/defaults/` or `wangp/wgp.py` for suite features
2. After `git pull` inside `wangp/`: re-run `install_bridge.sh`
3. Pose truth = motor `pose_gate` / SAM3D — not UI “looks ok”
4. FastWan = smoke only, never ship signal
5. Content-open lab (same policy as kimi motor)
6. **Iterate cheap without false reject:** L1 = direction; L2 once after HOLD/PROMOTE; never drop track on L1 FAIL alone (`suite/docs/ITERATE_POLICY.md`)
7. **Base solid, edge frontier:** nightlies/new torch on `\.venv-edge` (or snap swap); promote only after smoke+gate — never one-venv-for-everything

## Kilo

- Config: `.kilo/kilo.jsonc` only (no root `kilo.json`, no `extends`)
- Commands: `.kilo/command/{status,start,install,gate,tracks,handoff}.md`
- Agent: `.kilo/agents/suite.md`
- Indexing **off**
- New projects: `bash ~/AI/Projects/_kilo_template/scripts/apply.sh <dir>`

## Related

- Motor (in-repo local): `motor/` → pose_gate + venv (gitignored); upstream twin may still live at `~/AI/Projects/ai-img-seq-kimi`
- GitHub: https://github.com/nonnex/WanGP-Lab
