# Migration note

## Old location (removed)

`/home/nick/AI/_COMMON/VENDORS/Wan2GP` — stub only after move.

## New location

| What | Path |
|------|------|
| Workspace | `/home/nick/AI/Projects/WanGP-Lab` |
| WanGP tree | `WanGP-Lab/wangp/` (clone + `.venv` + `ckpts`) |
| Suite SoT | `WanGP-Lab/suite/` |
| Settings SoT | `WanGP-Lab/suite/settings/` |
| Mission assets | `WanGP-Lab/data/cache/wanmove/` |
| Lab motor | `/home/nick/AI/Projects/ai-img-seq-kimi` (unchanged) |

## Install / start

```bash
cd ~/AI/Projects/WanGP-Lab
bash suite/scripts/install_bridge.sh
bash suite/scripts/start_wangp.sh
```
