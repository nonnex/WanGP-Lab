# Workspace retention (keep last 2)

## Policy

| Keep | Drop |
|------|------|
| Last **2 complete** Move dirs | Older + **all incomplete** runs |
| Last **2** console logs | Older logs |
| `LEADERBOARD.tsv`, `HANDOFF*.md`, rolling gate JSON | — |
| Last **2** `wangp/outputs` videos | Older UI exports |
| Mission SoT `data/cache/wanmove/` | `_gate_frames_*`, old `mask_outputs/lab_*` |
| `.kilo/kilo.jsonc` + agents/commands | `.kilo/node_modules`, package*.json |

**N=2** = current + previous. Override: `WANGP_LAB_KEEP_RUNS=3`.

## Commands

```bash
bash suite/scripts/prune_experiments.sh          # keep 2 + clean kilo junk
bash suite/scripts/prune_experiments.sh 3
bash suite/scripts/prune_experiments.sh --dry-run
```

Headless Move auto-prunes after each run. Disable: `WANGP_LAB_NO_PRUNE=1`.

## Always drop

- Incomplete experiment dirs (no successful `result.json` / mp4)
- `.kilo/node_modules` (~60 MB IDE spam)
- suite `__pycache__`
- Transient gate frame extracts
