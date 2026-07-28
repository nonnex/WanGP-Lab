# Experiment retention

## Policy

| Keep | Drop |
|------|------|
| Last **2** Move run dirs (`data/experiments/*_wan2gp_move_e01`) | Older runs |
| Last **2** console logs (`l3_*.log`) | Older logs |
| `HANDOFF*.md`, `.gitkeep`, rolling `last_pose_gate_open_end.json` | — |
| Last **2** mp4 under `wangp/outputs/` | Older UI exports |
| Mission SoT in `data/cache/wanmove/` | Transient `_gate_frames_*`, old `mask_outputs/lab_*` aliases |

**N=2** = current run + previous (A/B compare). Override: `WANGP_LAB_KEEP_RUNS=3`.

## Commands

```bash
bash suite/scripts/prune_experiments.sh          # keep 2
bash suite/scripts/prune_experiments.sh 3        # keep 3
bash suite/scripts/prune_experiments.sh --dry-run
```

Headless Move calls prune automatically after each run (env `WANGP_LAB_KEEP_RUNS`, default 2). Disable: `WANGP_LAB_NO_PRUNE=1`.

## What not to hoard

- Full frame dumps of failed seeds beyond last 2
- Duplicate stills/tracks in `wangp/mask_outputs` (install copies enough)
- `.kilo/node_modules` (gitignored)
- FastWan smoke videos (delete after L0 check)

## Leaderboard (tiny, keep forever)

Append one line per gated run to `data/experiments/LEADERBOARD.tsv` (seed, progress, phase, path) — not pruned.
