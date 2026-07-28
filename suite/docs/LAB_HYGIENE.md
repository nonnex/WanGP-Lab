# Lab hygiene — stay clean by default

## Layout (only these at repo root)

```
WanGP-Lab/
  AGENTS.md README.md
  config/ suite/ data/ wangp/   # code + motor paths
  _outputs/                     # UI videos (wangp/outputs → here)
  _logs/                        # empty / transient
  .kilo/ .vscode/               # editor (no node_modules)
```

| Path | Keep |
|------|------|
| `data/experiments/` | last **2** complete runs + `LEADERBOARD.tsv` + `HANDOFF.md` |
| `_outputs/` | last **2** mp4 |
| `data/cache/wanmove/` | mission stills + tracks SoT |
| `.kilo/` | `kilo.jsonc`, agents, commands only |

## Auto mechanisms

| When | What |
|------|------|
| After headless Move | `prune_experiments.sh` (keep 2) |
| `start_wangp_ui.sh` | `lab_hygiene.sh --quiet` |
| `install_bridge.sh` | outputs symlink + hygiene quiet |
| `status.sh` | hygiene **check** (reports dirty) |
| `git commit` | pre-commit: auto-fix then fail if still dirty |
| Manual | `bash suite/scripts/lab_hygiene.sh` |

```bash
bash suite/scripts/lab_hygiene.sh          # fix now
bash suite/scripts/lab_hygiene.sh --check  # CI / status
bash suite/scripts/install_git_hooks.sh    # once per clone
```

## Env

| Var | Default |
|-----|---------|
| `WANGP_LAB_KEEP_RUNS` | `2` |
| `WANGP_LAB_NO_PRUNE` | unset (set `1` to skip post-Move prune) |
| `WANGP_LAB_OUTPUTS` | `$ROOT/_outputs` |

## Never commit

weights, venv, `_outputs/*`, experiment frames, `.kilo/node_modules`, secrets.
