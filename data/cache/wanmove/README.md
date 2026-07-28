# Mission assets (SoT)

| File | Role |
|------|------|
| `still_675_832x480.jpg` | Move start @ 480p |
| `still_675_640x352.jpg` | FastWan smoke still |
| `tracks_e01_open_hands_t{33,49,81}.npy` | custom_guide trajectories |

Rebuild tracks:

```bash
bash suite/scripts/build_tracks.sh 49
```

`wangp/mask_outputs/` holds **copies** for UI pickers (from `install_bridge.sh`).
