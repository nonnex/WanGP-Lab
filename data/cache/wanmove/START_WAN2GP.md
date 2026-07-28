# Wan2GP Move — start checklist (16 GB)

```bash
cd /home/nick/AI/_COMMON/VENDORS/Wan2GP
source .venv/bin/activate
python wgp.py --profile 5
```

| UI | Value |
|----|--------|
| Model | Wan2.1 Wan-Move 480p 14B |
| Quant | **int8** (quanto … int8) |
| Memory | Profile **5** (or 4) |
| image_start | `mask_outputs/lab_still_675_832x480.jpg` |
| custom_guide | `mask_outputs/lab_e01_open_t81.npy` |
| Size | 480×832 |
| Frames | ≤81 first try |
| Prompt enhancer | OFF |

Lab gate after export:

```bash
cd /home/nick/AI/Projects/ai-img-seq-kimi
pipeline/.venv/bin/python pipeline/pose_gate.py hop --frames <dir> --mode open_end
```

## Headless (preferred — no UI)

Stop UI if it holds GPU, then:

```bash
cd ~/AI/Projects/ai-img-seq-kimi
bash lab/tools/wan2gp_move_e01.sh
# log + frames under _data/experiments/<ts>_wan2gp_move_e01/
tail -f _data/experiments/*_wan2gp_move_e01/wan2gp_api.log
```

Options: `--steps 30 --frames 81 --profile 5 --seed 33`
