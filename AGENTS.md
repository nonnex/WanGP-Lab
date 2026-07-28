# WanGP-Lab — Resume-Karte (Kilo)

## Mission

**Operator suite** for still→motion hard-cases: WanGP as **cockpit**, ai-img-seq-kimi as **motor**, thin **bridge** (finetunes + Lab Bridge plugin).

Primary hard-case: day21_10 leg uncross→open (675→open), then side-switch toward 677.

## Layout

| Path | Role |
|------|------|
| `suite/finetunes/` | Mission models (`lab_wanmove_*`, `lab_ti2v5b_fast_*`) |
| `suite/plugins/wan2gp-lab-bridge/` | UI tab: tracks → preset → gate |
| `suite/scripts/` | install, start, status, gate, tracks |
| `suite/tools/` | headless Move, track builder |
| `suite/settings/` | WanGP UI defaults SoT |
| `suite/docs/` | architecture + research |
| `wangp/` | local Wan2GP clone + `.venv` + `ckpts` (gitignored heavy) |
| `data/cache/wanmove/` | stills + trajectory npy |
| `config/suite.env` | single path config |

## Venvs (never mix)

| | Python |
|--|--------|
| WanGP | `wangp/.venv/bin/python` |
| Lab motor | `/home/nick/AI/Projects/ai-img-seq-kimi/pipeline/.venv/bin/python` |

## Commands

```bash
bash suite/scripts/status.sh
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp.sh          # profile 4 + sage → :7860
bash suite/scripts/build_tracks.sh 49
bash suite/scripts/gate_output.sh <mp4>
bash suite/tools/run_move_e01.sh --frames 49 --steps 16 --profile 4
```

## Host

- CPU: i7-12700F · RAM ~24 GB · GPU RTX 5060 Ti 16 GB
- Default Memory Profile **4** (Profile 2 only if much RAM free)
- Attention **sage** (1.0.6 in wangp venv) · Quant **int8**

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
- Indexing **off** (no embedding of ckpts/venv)
- Slash examples: `/status`, `/start`, `/gate`

## Related

- Motor lab: `/home/nick/AI/Projects/ai-img-seq-kimi`
- GitHub: https://github.com/nonnex/WanGP-Lab
