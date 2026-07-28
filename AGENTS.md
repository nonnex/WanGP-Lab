# WanGP-Lab — Resume-Karte (Kilo)

## Mission

**Operator suite** for still→motion hard-cases: WanGP **cockpit**, ai-img-seq-kimi **motor**, thin **bridge**.

Primary hard-case: day21_10 leg uncross→open (675→open), then side-switch toward 677.

## Layout

| Path | Role |
|------|------|
| `suite/finetunes/` | `lab_wanmove_*`, `lab_ti2v5b_fast_*` |
| `suite/plugins/wan2gp-lab-bridge/` | UI: tracks → preset → gate |
| `suite/scripts/` | install, start UI, status, gate, tracks, Windows shortcut |
| `suite/tools/` | headless Move, track builder `.py` |
| `suite/settings/` | WanGP UI defaults SoT |
| `suite/docs/` | architecture (start at `SUITE_CRITICAL.md`) |
| `wangp/` | Wan2GP clone + `.venv` + `ckpts` (local) |
| `data/cache/wanmove/` | stills + trajectory npy |
| `config/suite.env` | single path config |

## Venvs (never mix)

| | Python |
|--|--------|
| WanGP | `wangp/.venv/bin/python` |
| Lab motor | `$LAB_MOTOR_ROOT/pipeline/.venv/bin/python` |

## Commands

```bash
bash suite/scripts/status.sh
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp_ui.sh       # profile 4 + sage → :7860
bash suite/scripts/install_windows_shortcut.sh
bash suite/scripts/build_tracks.sh 49
bash suite/scripts/gate_output.sh <mp4>
bash suite/tools/run_move_e01.sh --frames 49 --steps 16 --profile 4
```

## Host

- CPU: i7-12700F · RAM ~24 GB · GPU RTX 5060 Ti 16 GB
- Memory Profile **4** · Attention **sage** · Quant **int8**

## Rules

1. Do not edit `wangp/defaults/` or `wangp/wgp.py` for suite features
2. After `git pull` inside `wangp/`: re-run `install_bridge.sh`
3. Pose truth = motor `pose_gate` / SAM3D — not UI “looks ok”
4. FastWan = smoke only, never ship signal
5. Content-open lab (same policy as kimi motor)

## Kilo

- Config: `.kilo/kilo.jsonc`
- Commands: `.kilo/command/{status,start,install,gate,tracks,handoff}.md`
- Agent: `.kilo/agents/suite.md`
- Indexing **off**

## Related

- Motor: `/home/nick/AI/Projects/ai-img-seq-kimi`
- GitHub: https://github.com/nonnex/WanGP-Lab
