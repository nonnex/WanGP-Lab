# WanGP-Lab — Agent notes

Root: `/home/nick/AI/Projects/WanGP-Lab`

## Ownership

| Edit freely | External / careful |
|-------------|-------------------|
| `suite/**` | `wangp/` = upstream Wan2GP clone |
| `config/**` | only install into finetunes/ + plugins/ |
| `data/cache/wanmove/` (small assets) | never commit ckpts/venv |
| `docs` via suite/docs | lab-motor = ai-img-seq-kimi |

## Commands

```bash
bash suite/scripts/status.sh
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp.sh
bash suite/scripts/build_tracks.sh 49
bash suite/scripts/gate_output.sh /path/to.mp4
```

## Rules

- Two venvs, never mix
- No pose ship without lab-motor pose_gate
- FastWan ≠ pose success
- Profile 4 default on 24GB RAM host
