# Missions (generic hard-cases)

A **mission** is one reproducible still→motion research recipe.  
The suite is **not** tied to e01 leg-uncross — that is only the first pack.

```
suite/missions/
  README.md
  gate_hints.json          # phase → next-action (shared)
  _template/mission.json   # copy for new hard-cases
  e01_uncross_open/        # current primary mission
    mission.json
```

Assets (stills, tracks) live under `data/cache/<mission_id>/`  
(or any path in `mission.json`). e01 currently uses `data/cache/wanmove/` for back-compat.

## mission.json (minimal)

```json
{
  "id": "my_case",
  "title": "Short title",
  "gate": { "mode": "open_end", "tool": "pose_gate" },
  "assets": {
    "still": "data/cache/my_case/still.jpg",
    "tracks": { "49": "data/cache/my_case/tracks_t49.npy" }
  },
  "ladder": {
    "L0": { "model": "lab_ti2v5b_fast_e01", "frames": 33, "steps": 4, "use_tracks": false },
    "L1": { "model": "lab_wanmove_e01_smoke", "frames": 33, "steps": 8, "use_tracks": true },
    "L2": { "model": "lab_wanmove_e01", "frames": 49, "steps": 16, "use_tracks": true, "seed": 7 }
  },
  "prompt": "...",
  "negative_prompt": "...",
  "track_build": { "analysis": "...", "src_still": "...", "apart_dx": 100 }
}
```

## New mission

```bash
cp -a suite/missions/_template suite/missions/my_case
# edit mission.json + put assets in data/cache/my_case/
bash suite/scripts/install_bridge.sh
# UI: Lab Bridge → Mission dropdown → my_case
```

## CLI

```bash
bash suite/tools/run_mission.sh my_case --level L2
bash suite/scripts/gate_output.sh <mp4>          # uses active/default gate mode
```
